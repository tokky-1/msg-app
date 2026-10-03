from sqlalchemy import Column, DateTime, Index, Integer, String, func
from db.connect import Base


class AuthAttempt(Base):
    """One row per *failed* login, kept only to throttle guessing.

    username is a plain column, not a foreign key: most of the rows that
    matter name an account that does not exist, which is exactly what a sweep
    looks like. A successful login deletes that identity's rows, so typing
    your password wrong twice and then correctly costs you nothing.

    created_at comes from the database, the same clock the window is measured
    against, so a drifting app container cannot widen or shrink the lockout.
    """

    __tablename__ = "auth_attempts"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    # 45 characters is the longest possible IPv6 form.
    client_ip = Column(String(45), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_auth_attempts_identity", "username", "client_ip", "created_at"),
        Index("ix_auth_attempts_ip", "client_ip", "created_at"),
    )
