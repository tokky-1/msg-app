from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from repository.mes_repo import MessageRepository
from repository.user_repo import UserRepository
from schema.messages import MessageCreate
from core.errors import (EditWindowExpiredError, MessageAccessDeniedError, MessageNotFoundError,RateLimitExceededError,ReceiverNotFoundError,SelfMessagingError)

# Configuration constants
MAX_MESSAGES_PER_MINUTE = 10
RATE_LIMIT_WINDOW = timedelta(minutes=1)
EDIT_WINDOW_MINUTES = 10

class MessageService:
    def __init__(self, db: Session):
        self.repo = MessageRepository(db)
        self.user_repo = UserRepository(db)

    def send_message(self, sender_id: int, message_data: MessageCreate):
        if sender_id == message_data.receiver_id:
            raise SelfMessagingError()

        # Without this the insert hits the receiver_id foreign key and surfaces as a 500.
        if self.user_repo.get_by_id(message_data.receiver_id) is None:
            raise ReceiverNotFoundError(message_data.receiver_id)

        # 1. Rate limiting.
        # The lock comes first: counting and inserting are two statements, and
        # without it two of this sender's requests can both read a count under
        # the cap and both go through. It is released when create_message
        # commits, or when the session rolls back on the raise below.
        self.user_repo.lock_for_update(sender_id)

        recent_count = self.repo.count_sends_in_window(sender_id, RATE_LIMIT_WINDOW)

        if recent_count >= MAX_MESSAGES_PER_MINUTE:
            raise RateLimitExceededError(MAX_MESSAGES_PER_MINUTE)

        # Logged before the message and in the same transaction, so quota is
        # spent whether or not the message survives: deleting your own
        # messages no longer buys you a fresh allowance.
        self.repo.record_send(sender_id)

        return self.repo.create_message(
            sender_id=sender_id,
            receiver_id=message_data.receiver_id,
            content=message_data.content
        )

    def get_message(self, message_id: int, current_user_id: int):
        message = self.repo.get_by_id(message_id)
        if not message:
            raise MessageNotFoundError(message_id)

        # Authorization: Only sender or receiver can view
        if current_user_id not in (message.sender_id, message.receiver_id):
            raise MessageAccessDeniedError()

        return message

    def edit_message(self, message_id: int, current_user_id: int, new_content: str):
        message = self.repo.get_by_id(message_id)
        if not message:
            raise MessageNotFoundError(message_id)

        # Authorization check
        if message.sender_id != current_user_id:
            raise MessageAccessDeniedError("Only the sender can edit this message")

        # 2. 10-Minute Time Window Check
        # Ensure timestamp comparison accounts for timezones
        msg_time = message.timestamp
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        time_elapsed = now - msg_time

        if time_elapsed > timedelta(minutes=EDIT_WINDOW_MINUTES):
            raise EditWindowExpiredError(EDIT_WINDOW_MINUTES)

        return self.repo.update_content(message, new_content)

    def delete_message(self, message_id: int, current_user_id: int):
        message = self.repo.get_by_id(message_id)
        if not message:
            raise MessageNotFoundError(message_id)

        # Authorization: Only sender can delete
        if message.sender_id != current_user_id:
            raise MessageAccessDeniedError("Only the sender can delete this message")

        self.repo.delete_message(message)
        return {"detail": "Message successfully deleted"}

    def get_inbox(self, user_id: int):
        return self.repo.get_inbox(user_id)

    def get_conversation_history(self, current_user_id: int, other_user_id: int, limit: int = 50, offset: int = 0):
        return self.repo.get_conversation(current_user_id, other_user_id, limit=limit, offset=offset)