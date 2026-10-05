"""Login throttling in services/user_service.py, against a mocked repository.

The service's job here is narrow: ask the repository to reserve an attempt,
refuse if it says no, and clear the slate on success. The counting itself is
one atomic step inside the repository, so that is tested against a real
database in test_auth_attempt_repo.py - a mock cannot catch a mistake in the
SQL, and the concurrency bug these tests originally missed lived exactly
there.

Boundary pinned here: the service refuses whenever reserve() returns a number
of seconds, and proceeds whenever it returns None.
"""

from datetime import timedelta

import pytest

from core.config import settings
from core.errors import AuthenticationError, TooManyLoginAttemptsError
from schema.auth import LoginRequest

IP = "203.0.113.7"


@pytest.fixture
def throttle(mocker):
    """Stateful stand-in for AuthAttemptRepository.

    reserve() is modelled the way the real one behaves: it records the attempt
    itself and answers from what it has recorded, so the count and the write
    cannot drift apart in the test the way they did in the code.
    """
    repo = mocker.patch(
        "services.user_service.AuthAttemptRepository", autospec=True
    ).return_value
    failures = []

    def reserve(username, client_ip, window, max_identity, max_ip):
        identity = sum(1 for u, i in failures if u == username and i == client_ip)
        from_ip = sum(1 for _, i in failures if i == client_ip)
        if identity >= max_identity or from_ip >= max_ip:
            return 42  # seconds; the exact value comes from SQL in real life
        failures.append((username, client_ip))
        return None

    def clear(username, client_ip):
        failures[:] = [(u, i) for u, i in failures if not (u == username and i == client_ip)]

    repo.reserve.side_effect = reserve
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

    with pytest.raises(TooManyLoginAttemptsError) as exc_info:
        attempt(service, "guess-again")

    assert exc_info.value.retry_after_seconds == 42
    # The refusal lands before the password is even looked up.
    assert user_repo.get_user_by_username.call_count == settings.AUTH_MAX_ATTEMPTS


def test_the_attempt_is_reserved_before_the_password_is_looked_at(
    service, throttle, user_repo, real_user
):
    """The ordering is the fix for the race, so it is worth pinning.

    reserve() must have both counted and recorded before the service goes
    anywhere near the user record or the hash.
    """
    order = []
    throttle.reserve.side_effect = lambda *a, **k: order.append("reserve")
    user_repo.get_user_by_username.side_effect = lambda u: order.append("lookup") or real_user

    attempt(service, "correct")

    assert order == ["reserve", "lookup"]


def test_the_correct_password_still_works_on_the_last_allowed_try(
    service, throttle, user_repo, real_user
):
    user_repo.get_user_by_username.return_value = real_user

    for n in range(settings.AUTH_MAX_ATTEMPTS - 1):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}")

    assert attempt(service, "correct") is real_user
    assert throttle.failures == [], "a success clears what was counted against you"

    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"later{n}")


def test_an_unknown_username_is_counted_the_same_way(service, throttle, user_repo):
    """Otherwise a sweep across guessed usernames would be free."""
    user_repo.get_user_by_username.return_value = None

    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}", username="ghost")

    with pytest.raises(TooManyLoginAttemptsError):
        attempt(service, "guess-again", username="ghost")


def test_a_refused_attempt_does_not_clear_the_slate(service, throttle, user_repo, real_user):
    """A lockout must not be escapable by sending the right password."""
    user_repo.get_user_by_username.return_value = real_user

    for n in range(settings.AUTH_MAX_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            attempt(service, f"guess{n}")

    with pytest.raises(TooManyLoginAttemptsError):
        attempt(service, "correct")

    throttle.clear_for_identity.assert_not_called()


def test_the_window_handed_to_the_repository_is_the_configured_lockout(
    service, throttle, user_repo, real_user
):
    user_repo.get_user_by_username.return_value = real_user
    attempt(service, "correct")

    username, client_ip, window, max_identity, max_ip = throttle.reserve.call_args.args
    assert window == timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
    assert max_identity == settings.AUTH_MAX_ATTEMPTS
    assert max_ip == settings.AUTH_MAX_ATTEMPTS_PER_IP
    assert (username, client_ip) == ("ada", IP)


def test_the_message_reports_the_measured_wait_not_a_fixed_one():
    assert "45 seconds" in TooManyLoginAttemptsError(45).message
    assert "1 minute" in TooManyLoginAttemptsError(60).message
    assert "2 minutes" in TooManyLoginAttemptsError(61).message
