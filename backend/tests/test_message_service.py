"""Business rules in services/mes_service.py, tested against mocked repositories.

No database is involved. Each test asserts both halves of a rule: the right
domain error is raised, *and* the service stopped before reaching the repo.

Boundary decisions pinned here:
  * rate limit -- the check is ``recent_count >= 10``, so 10 messages inside the
    window are allowed and the 11th is rejected. The count comes from an
    append-only send log, so deleting messages cannot hand quota back.
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
from services.mes_service import (
    EDIT_WINDOW_MINUTES,
    MAX_MESSAGES_PER_MINUTE,
    RATE_LIMIT_WINDOW,
)


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
    user_repo.lock_for_update.assert_not_called()
    message_repo.count_sends_in_window.assert_not_called()


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
    user_repo.lock_for_update.assert_not_called()
    message_repo.count_sends_in_window.assert_not_called()


# ---------------------------------------------------------------------------
# send_message: happy path
# ---------------------------------------------------------------------------

def test_a_valid_message_is_handed_to_the_repo_intact(
    service, message_repo, user_repo, existing_receiver
):
    user_repo.get_by_id.return_value = existing_receiver
    message_repo.count_sends_in_window.return_value = 0

    result = service.send_message(
        SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content="hello")
    )

    message_repo.create_message.assert_called_once_with(
        sender_id=SENDER_ID, receiver_id=RECEIVER_ID, content="hello"
    )
    assert result is message_repo.create_message.return_value
    # The rate-limit window is the last minute, not some other span.
    message_repo.count_sends_in_window.assert_called_once_with(SENDER_ID, RATE_LIMIT_WINDOW)
    assert RATE_LIMIT_WINDOW == timedelta(minutes=1)
    # An accepted send is logged, and logged once.
    message_repo.record_send.assert_called_once_with(SENDER_ID)


# ---------------------------------------------------------------------------
# send_message: rate limit
# ---------------------------------------------------------------------------

def _wire_stateful_repo(message_repo, frozen_now):
    """A fake that counts the append-only send log, the way the real one does.

    `sends` is what the limiter reads; `created` is what survives deletion.
    Keeping them separate is the point: the two must be able to disagree.
    """
    sends = []
    created = []

    def record_send(sender_id):
        assert sender_id == SENDER_ID
        sends.append(sender_id)

    def count_sends_in_window(sender_id, window):
        assert sender_id == SENDER_ID
        assert window == RATE_LIMIT_WINDOW
        return len(sends)

    def create_message(sender_id, receiver_id, content):
        row = SimpleNamespace(
            id=len(sends),
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            timestamp=frozen_now,
        )
        created.append(row)
        return row

    message_repo.record_send.side_effect = record_send
    message_repo.count_sends_in_window.side_effect = count_sends_in_window
    message_repo.create_message.side_effect = create_message
    return sends, created


def test_ten_messages_a_minute_go_through_and_the_eleventh_is_rejected(
    service, message_repo, user_repo, existing_receiver, frozen_now
):
    """Walk the real sequence rather than asserting against a single count.

    The fake counts what the service actually logged, so an off-by-one in the
    threshold cannot hide behind a hand-picked number.
    """
    user_repo.get_by_id.return_value = existing_receiver
    sends, created = _wire_stateful_repo(message_repo, frozen_now)

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
    assert len(sends) == 10, "a rejected send must not consume quota"


def test_deleting_your_own_messages_does_not_hand_back_quota(
    service, message_repo, user_repo, existing_receiver, frozen_now
):
    """The defect that made the limit decorative.

    The window used to count rows in `messages`, and DELETE /messages/{id} is a
    hard delete, so send ten, delete ten, send ten more ran forever. Against the
    live API that bought exactly one extra send per deletion.
    """
    user_repo.get_by_id.return_value = existing_receiver
    sends, created = _wire_stateful_repo(message_repo, frozen_now)

    for n in range(MAX_MESSAGES_PER_MINUTE):
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content=f"message {n}")
        )

    # Every one of them is deleted, exactly as the delete route would.
    created.clear()

    with pytest.raises(RateLimitExceededError):
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content="a free one, surely")
        )

    assert len(sends) == MAX_MESSAGES_PER_MINUTE
    assert message_repo.create_message.call_count == MAX_MESSAGES_PER_MINUTE


def test_the_sender_is_locked_before_the_window_is_counted(
    service, message_repo, user_repo, existing_receiver
):
    """Counting and inserting are two statements.

    Without a lock held across both, two of this sender's requests can each
    read a count under the cap and both be allowed through.
    """
    user_repo.get_by_id.return_value = existing_receiver
    steps = []

    user_repo.lock_for_update.side_effect = lambda user_id: steps.append(("lock", user_id))
    message_repo.count_sends_in_window.side_effect = (
        lambda sender_id, window: steps.append(("count", sender_id)) or 0
    )
    message_repo.record_send.side_effect = lambda sender_id: steps.append(("record", sender_id))
    message_repo.create_message.side_effect = lambda **kw: steps.append(("insert", kw["sender_id"]))

    service.send_message(SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content="hello"))

    assert [name for name, _ in steps] == ["lock", "count", "record", "insert"]
    assert {user_id for _, user_id in steps} == {SENDER_ID}


def test_a_rejected_send_still_locks_but_logs_nothing(
    service, message_repo, user_repo, existing_receiver
):
    user_repo.get_by_id.return_value = existing_receiver
    message_repo.count_sends_in_window.return_value = MAX_MESSAGES_PER_MINUTE

    with pytest.raises(RateLimitExceededError):
        service.send_message(
            SENDER_ID, MessageCreate(receiver_id=RECEIVER_ID, content="over the line")
        )

    user_repo.lock_for_update.assert_called_once_with(SENDER_ID)
    message_repo.record_send.assert_not_called()
    message_repo.create_message.assert_not_called()


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
    message_repo.count_sends_in_window.return_value = already_sent_this_minute

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
