"""Business rules in services/mes_service.py, tested against mocked repositories.

No database is involved. Each test asserts both halves of a rule: the right
domain error is raised, *and* the service stopped before reaching the repo.

Boundary decisions pinned here:
  * rate limit -- the check is ``recent_count >= 10``, so 10 messages inside the
    window are allowed and the 11th is rejected.
  * edit window -- the check is ``elapsed > timedelta(minutes=10)``, so the
    boundary is INCLUSIVE: a message edited at exactly 10:00.000000 still goes
    through, and 10:00.000001 does not.
"""

from datetime import timedelta
from types import SimpleNamespace

import pytest

from conftest import OUTSIDER_ID, RECEIVER_ID, SENDER_ID
from core.errors import (
    EditWindowExpiredError,
    MessageAccessDeniedError,
    RateLimitExceededError,
    ReceiverNotFoundError,
    SelfMessagingError,
)
from schema.messages import MessageCreate
from services.mes_service import EDIT_WINDOW_MINUTES, MAX_MESSAGES_PER_MINUTE


# ---------------------------------------------------------------------------
# send_message: self-messaging
# ---------------------------------------------------------------------------

def test_messaging_yourself_is_rejected_before_any_repo_call(service, message_repo, user_repo):
    with pytest.raises(SelfMessagingError):
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=SENDER_ID, content="talking to myself")
        )

    message_repo.create_message.assert_not_called()
    # The guard runs first, so we never look the user up or count anything either.
    user_repo.get_by_id.assert_not_called()
    message_repo.count_messages_sent_since.assert_not_called()


# ---------------------------------------------------------------------------
# send_message: unknown receiver
# ---------------------------------------------------------------------------

def test_unknown_receiver_is_rejected_before_the_insert(service, message_repo, user_repo):
    user_repo.get_by_id.return_value = None

    with pytest.raises(ReceiverNotFoundError) as exc_info:
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=404, content="anyone there?")
        )

    assert exc_info.value.receiver_id == 404
    # The whole point of the lookup: never let the insert hit the foreign key.
    message_repo.create_message.assert_not_called()
    message_repo.count_messages_sent_since.assert_not_called()


# ---------------------------------------------------------------------------
# send_message: happy path
# ---------------------------------------------------------------------------

def test_a_valid_message_is_handed_to_the_repo_intact(
    service, message_repo, user_repo, existing_receiver, frozen_now
):
    user_repo.get_by_id.return_value = existing_receiver
    message_repo.count_messages_sent_since.return_value = 0

    result = service.send_message(
        SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content="hello")
    )

    message_repo.create_message.assert_called_once_with(
        sender_id=SENDER_ID, receiver_id=RECEIVER_ID, content="hello"
    )
    assert result is message_repo.create_message.return_value
    # The rate-limit window is the last minute, not some other span.
    message_repo.count_messages_sent_since.assert_called_once_with(
        SENDER_ID, frozen_now - timedelta(minutes=1)
    )


# ---------------------------------------------------------------------------
# send_message: rate limit
# ---------------------------------------------------------------------------

def test_ten_messages_a_minute_go_through_and_the_eleventh_is_rejected(
    service, message_repo, user_repo, existing_receiver, frozen_now
):
    """Walk the real sequence rather than asserting against a single count.

    The fake repo counts what it has actually created, so an off-by-one in the
    threshold cannot hide behind a hand-picked number.
    """
    user_repo.get_by_id.return_value = existing_receiver
    created = []

    def count_messages_sent_since(sender_id, since_time):
        assert sender_id == SENDER_ID
        assert since_time == frozen_now - timedelta(minutes=1)
        return len(created)

    def create_message(sender_id, receiver_id, content):
        row = SimpleNamespace(
            id=len(created) + 1,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            timestamp=frozen_now,
        )
        created.append(row)
        return row

    message_repo.count_messages_sent_since.side_effect = count_messages_sent_since
    message_repo.create_message.side_effect = create_message

    for n in range(1, 11):
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content=f"message {n}")
        )

    assert len(created) == 10, "the tenth message inside the window should still be allowed"

    with pytest.raises(RateLimitExceededError) as exc_info:
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content="message 11")
        )

    assert exc_info.value.max_per_minute == 10
    assert message_repo.create_message.call_count == 10, "the eleventh must not reach the repo"
    assert len(created) == 10


@pytest.mark.parametrize(
    "already_sent_this_minute, expect_rejection",
    [
        (0, False),
        (8, False),
        (9, False),   # this send is the tenth -- still allowed
        (10, True),   # this send would be the eleventh
        (11, True),
    ],
)
def test_rate_limit_threshold_sits_exactly_at_ten(
    service,
    message_repo,
    user_repo,
    existing_receiver,
    frozen_now,
    already_sent_this_minute,
    expect_rejection,
):
    user_repo.get_by_id.return_value = existing_receiver
    message_repo.count_messages_sent_since.return_value = already_sent_this_minute

    payload = MessageCreate(receiver_id=RECEIVER_ID, content="one more")

    if expect_rejection:
        with pytest.raises(RateLimitExceededError):
            service.send_message(SENDER_ID, payload)
        message_repo.create_message.assert_not_called()
    else:
        service.send_message(SENDER_ID, payload)
        message_repo.create_message.assert_called_once()


# ---------------------------------------------------------------------------
# edit_message: the 10-minute window
# ---------------------------------------------------------------------------

def test_edit_well_inside_the_window_succeeds(service, message_repo, frozen_now, make_message):
    message = make_message(sent_ago=timedelta(minutes=3))
    message_repo.get_by_id.return_value = message
    message_repo.update_content.return_value = message

    result = service.edit_message(message.id, SENDER_ID, "edited content")

    message_repo.update_content.assert_called_once_with(message, "edited content")
    assert result is message


def test_edit_at_exactly_ten_minutes_succeeds(service, message_repo, frozen_now, make_message):
    """The window is inclusive: ``elapsed > 10min`` is False at exactly 10:00."""
    message = make_message(sent_ago=timedelta(minutes=EDIT_WINDOW_MINUTES))
    message_repo.get_by_id.return_value = message
    message_repo.update_content.return_value = message

    service.edit_message(message.id, SENDER_ID, "edited on the buzzer")

    message_repo.update_content.assert_called_once_with(message, "edited on the buzzer")


def test_edit_one_microsecond_past_ten_minutes_fails(
    service, message_repo, frozen_now, make_message
):
    """The smallest possible step past the boundary is already too late."""
    message = make_message(sent_ago=timedelta(minutes=EDIT_WINDOW_MINUTES, microseconds=1))
    message_repo.get_by_id.return_value = message

    with pytest.raises(EditWindowExpiredError) as exc_info:
        service.edit_message(message.id, SENDER_ID, "one microsecond too slow")

    assert exc_info.value.window_minutes == 10
    message_repo.update_content.assert_not_called()


@pytest.mark.parametrize(
    "sent_ago, expect_expiry",
    [
        (timedelta(minutes=EDIT_WINDOW_MINUTES), False),
        (timedelta(minutes=EDIT_WINDOW_MINUTES, microseconds=1), True),
    ],
)
def test_a_naive_timestamp_is_read_as_utc_at_the_same_boundary(
    service, message_repo, frozen_now, make_message, sent_ago, expect_expiry
):
    """A timestamp that came back without tzinfo must not shift the boundary."""
    message = make_message(sent_ago=sent_ago, naive=True)
    message_repo.get_by_id.return_value = message
    message_repo.update_content.return_value = message

    if expect_expiry:
        with pytest.raises(EditWindowExpiredError):
            service.edit_message(message.id, SENDER_ID, "edited")
        message_repo.update_content.assert_not_called()
    else:
        service.edit_message(message.id, SENDER_ID, "edited")
        message_repo.update_content.assert_called_once_with(message, "edited")


# ---------------------------------------------------------------------------
# edit_message / delete_message: only the sender
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "caller_id",
    [
        pytest.param(RECEIVER_ID, id="receiver"),
        pytest.param(OUTSIDER_ID, id="unrelated_user"),
    ],
)
def test_only_the_sender_may_edit(service, message_repo, frozen_now, make_message, caller_id):
    # Fresh message: the denial comes from authorship, not from the time window.
    message = make_message(sent_ago=timedelta(seconds=30))
    message_repo.get_by_id.return_value = message

    with pytest.raises(MessageAccessDeniedError) as exc_info:
        service.edit_message(message.id, caller_id, "not mine to edit")

    assert "sender" in exc_info.value.message
    message_repo.update_content.assert_not_called()
    assert message.content == "original content"


@pytest.mark.parametrize(
    "caller_id",
    [
        pytest.param(RECEIVER_ID, id="receiver"),
        pytest.param(OUTSIDER_ID, id="unrelated_user"),
    ],
)
def test_only_the_sender_may_delete(service, message_repo, make_message, caller_id):
    message = make_message()
    message_repo.get_by_id.return_value = message

    with pytest.raises(MessageAccessDeniedError) as exc_info:
        service.delete_message(message.id, caller_id)

    assert "sender" in exc_info.value.message
    message_repo.delete_message.assert_not_called()


def test_the_sender_may_delete(service, message_repo, make_message):
    """Positive control, so the assertions above cannot pass on a broken path."""
    message = make_message()
    message_repo.get_by_id.return_value = message

    service.delete_message(message.id, SENDER_ID)

    message_repo.delete_message.assert_called_once_with(message)


# ---------------------------------------------------------------------------
# The numbers above are hard-coded on purpose; this is where a change surfaces.
# ---------------------------------------------------------------------------

def test_the_configured_limits_are_the_ones_these_tests_assume():
    assert MAX_MESSAGES_PER_MINUTE == 10
    assert EDIT_WINDOW_MINUTES == 10
