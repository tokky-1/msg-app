"""Login throttling in services/user_service.py, against mocked repositories.

Boundary pinned here: the check is ``failures >= AUTH_MAX_ATTEMPTS``, so with
the default of 3 the first three wrong passwords are answered with 401 and the
fourth attempt is refused with the rate-limit error before the password is
looked at.
"""

from datetime import timedelta

import pytest

from core.config import settings
from core.errors import AuthenticationError, TooManyLoginAttemptsError
from schema.auth import LoginRequest

IP = "203.0.113.7"
OTHER_IP = "198.51.100.4"


@pytest.fixture
def throttle(mocker):
    """A stateful stand-in for AuthAttemptRepository.

    It stores the failures it was told about and answers the counts from that
    store, so an off-by-one in the threshold cannot hide behind a hand-picked
    return value.
    """
    repo = mocker.patch(
        "services.user_service.AuthAttemptRepository", autospec=True
    ).return_value
    failures = []

    repo.record_failure.side_effect = lambda username, client_ip: failures.append(
        (username, client_ip)
    )
    repo.count_for_identity.side_effect = lambda username, client_ip, window: sum(
        1 for u, i in failures if u == username and i == client_ip
    )
    repo.count_for_ip.side_effect = lambda client_ip, window: sum(
        1 for _, i in failures if i == client_ip
    )

    def clear(username, client_ip):
        failures[:] = [(u, i) for u, i in failures if not (u == username and i == client_ip)]

    repo.clear_for_identity.side_effect = clear
    repo.failures = failures
    return repo


@pytest.fixture
def user_repo(mocker):
    return mocker.patch("services.user_service.UserRepository", autospec=True).return_value


@pytest.fixture
def service(throttle, user_repo):
    from services.user_service import UserService

    return UserService(db=None)


@pytest.fixture
def real_user(mocker):
    """A user whose stored hash only matches the password "correct"."""
    mocker.patch(
        "services.user_service.verifyhash",
        side_effect=lambda plain, hashed: plain == "correct",
    )
    return type("U", (), {"id": 1, "username": "ada", "hashed_password": "stored"})()


def attempt(service, password, username="ada", ip=IP):
    return service.authenticate(LoginRequest(username=username, password=password), ip)


def test_three_wrong_passwords_are_401_and_the_fourth_is_refused(
    service, throttle, user_repo, real_user
):
    user_repo.get_user_by_username.return_value = real_user

    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}")

    assert len(throttle.failures) == settings.AUTH_MAX_ATTEMPTS

    with pytest.raises(TooManyLoginAttemptsError) as exc_info:
        attempt(service, "guess-again")

    assert exc_info.value.lockout_minutes == settings.AUTH_LOCKOUT_MINUTES
    # The refusal must land before the password is even looked up.
    assert user_repo.get_user_by_username.call_count == settings.AUTH_MAX_ATTEMPTS


def test_the_correct_password_still_works_on_the_last_allowed_try(
    service, throttle, user_repo, real_user
):
    user_repo.get_user_by_username.return_value = real_user

    for n in range(settings.AUTH_MAX_ATTEMPTS - 1):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}")

    assert attempt(service, "correct") is real_user
    assert throttle.failures == [], "a success clears what was counted against you"

    # And the slate really is clean: a full run of wrong guesses is available
    # again rather than the next one tipping over.
    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"later{n}")


def test_an_unknown_username_is_counted_the_same_way(service, throttle, user_repo, real_user):
    """Otherwise a sweep across guessed usernames would be free."""
    user_repo.get_user_by_username.return_value = None

    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}", username="ghost")

    with pytest.raises(TooManyLoginAttemptsError):
        attempt(service, "guess-again", username="ghost")


def test_locking_one_pair_does_not_lock_the_account_elsewhere(
    service, throttle, user_repo, real_user
):
    """The counter is keyed on username *and* address.

    Keyed on the username alone, anyone could lock anyone else out of their
    account with three deliberate failures.
    """
    user_repo.get_user_by_username.return_value = real_user

    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}", ip=IP)

    with pytest.raises(TooManyLoginAttemptsError):
        attempt(service, "correct", ip=IP)

    # The real owner, somewhere else, is unaffected.
    assert attempt(service, "correct", ip=OTHER_IP) is real_user


def test_one_address_cannot_spray_three_guesses_across_many_usernames(
    service, throttle, user_repo
):
    user_repo.get_user_by_username.return_value = None

    allowed = 0
    for n in range(settings.AUTH_MAX_ATTEMPTS_PER_IP + 5):
        try:
            attempt(service, "guess", username=f"victim{n}")
        except AuthenticationError:
            allowed += 1
        except TooManyLoginAttemptsError:
            break

    assert allowed == settings.AUTH_MAX_ATTEMPTS_PER_IP, (
        "the per-address ceiling should stop the sweep even though every "
        "username is fresh"
    )


def test_the_window_handed_to_the_repository_is_the_configured_lockout(
    service, throttle, user_repo, real_user
):
    user_repo.get_user_by_username.return_value = real_user
    attempt(service, "correct")

    expected = timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
    assert throttle.count_for_identity.call_args.args[2] == expected
    assert throttle.count_for_ip.call_args.args[1] == expected
