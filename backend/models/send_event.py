from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, func
from db.connect import Base


class MessageSendEvent(Base):
    """One row per accepted send, kept only to enforce the rate limit.

    The limit used to count rows in `messages`, which meant deleting your own
    messages handed back quota: send ten, delete ten, send ten more, forever.
    This log is append-only and nothing deletes from it, so the window counts
    what you actually did rather than what still exists.

    created_at is set by the database, the same clock the window is measured
    against, so an app container whose clock drifts from the database cannot
    widen or narrow the window.
    """

    __tablename__ = "message_send_events"

    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    # Every send runs the window count, so it must not scan the table.
    __table_args__ = (
        Index("ix_message_send_events_sender_created", "sender_id", "created_at"),
    )
