from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from repository.mes_repo import MessageRepository
from schema.messages import MessageCreate

# Configuration constants
MAX_MESSAGES_PER_MINUTE = 10
EDIT_WINDOW_MINUTES = 10

class MessageService:
    def __init__(self, db: Session):
        self.repo = MessageRepository(db)

    def send_message(self, sender_id: int, message_data: MessageCreate):
        if sender_id == message_data.receiver_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot send a message to yourself."
            )

        # 1. Rate Limiting Check
        one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        recent_count = self.repo.count_messages_sent_since(sender_id, one_minute_ago)
        
        if recent_count >= MAX_MESSAGES_PER_MINUTE:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {MAX_MESSAGES_PER_MINUTE} messages per minute."
            )

        return self.repo.create_message(
            sender_id=sender_id,
            receiver_id=message_data.receiver_id,
            content=message_data.content
        )

    def get_message(self, message_id: int, current_user_id: int):
        message = self.repo.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        # Authorization: Only sender or receiver can view
        if current_user_id not in (message.sender_id, message.receiver_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return message

    def edit_message(self, message_id: int, current_user_id: int, new_content: str):
        message = self.repo.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        # Authorization check
        if message.sender_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the sender can edit this message")

        # 2. 10-Minute Time Window Check
        # Ensure timestamp comparison accounts for timezones
        msg_time = message.timestamp
        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        time_elapsed = now - msg_time

        if time_elapsed > timedelta(minutes=EDIT_WINDOW_MINUTES):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Messages can only be edited within {EDIT_WINDOW_MINUTES} minutes of sending."
            )

        return self.repo.update_content(message, new_content)

    def delete_message(self, message_id: int, current_user_id: int):
        message = self.repo.get_by_id(message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

        # Authorization: Only sender can delete
        if message.sender_id != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the sender can delete this message")

        self.repo.delete_message(message)
        return {"detail": "Message successfully deleted"}

    def get_conversation_history(self, current_user_id: int, other_user_id: int):
        return self.repo.get_conversation(current_user_id, other_user_id)