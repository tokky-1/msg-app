from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import case, func
from sqlalchemy.orm import Session, aliased
from models.message import Message
from models.user import User

class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_message(self, sender_id: int, receiver_id: int, content: str) -> Message:
        db_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content
        )
        self.db.add(db_message)
        self.db.commit()
        self.db.refresh(db_message)
        return db_message

    def get_by_id(self, message_id: int) -> Optional[Message]:
        return self.db.query(Message).filter(Message.id == message_id).first()

    def get_conversation(self, user_1_id: int, user_2_id: int, limit: int = 50, offset: int = 0) -> List[Message]:
        """Fetch messages between two users ordered by time."""
        return (
            self.db.query(Message)
            .filter(
                ((Message.sender_id == user_1_id) & (Message.receiver_id == user_2_id)) |
                ((Message.sender_id == user_2_id) & (Message.receiver_id == user_1_id))
            )
            .order_by(Message.timestamp.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_inbox(self, user_id: int) -> List[Tuple[Message, str]]:
        """Fetch the most recent message per conversation partner, newest first,
        paired with that partner's username."""
        # Whichever side of the row isn't this user.
        partner_id = case(
            (Message.sender_id == user_id, Message.receiver_id),
            else_=Message.sender_id,
        )

        # id breaks ties so two messages sharing a timestamp still rank deterministically.
        row_number = func.row_number().over(
            partition_by=partner_id,
            order_by=(Message.timestamp.desc(), Message.id.desc()),
        )

        ranked = (
            self.db.query(
                Message,
                partner_id.label("partner_id"),
                row_number.label("row_number"),
            )
            .filter(
                (Message.sender_id == user_id) | (Message.receiver_id == user_id)
            )
            .subquery()
        )

        latest = aliased(Message, ranked)
        partner = aliased(User)

        return (
            self.db.query(latest, partner.username)
            .join(partner, partner.id == ranked.c.partner_id)
            .filter(ranked.c.row_number == 1)
            .order_by(ranked.c.timestamp.desc(), ranked.c.id.desc())
            .all()
        )

    def update_content(self, message: Message, new_content: str) -> Message:
        setattr(message, "content", new_content)
        self.db.commit()
        self.db.refresh(message)
        return message

    def delete_message(self, message: Message) -> None:
        self.db.delete(message)
        self.db.commit()

    def count_messages_sent_since(self, sender_id: int, since_time: datetime) -> int:
        """Helper query used by Service layer for rate limiting."""
        return (
            self.db.query(Message)
            .filter(
                Message.sender_id == sender_id,
                Message.timestamp >= since_time
            )
            .count()
        )