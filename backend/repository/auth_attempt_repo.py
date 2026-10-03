from datetime import timedelta

from sqlalchemy import Interval, cast, func, literal
from sqlalchemy.orm import Session

from models.auth_attempt import AuthAttempt


class AuthAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def _cutoff(self, window: timedelta):
        """Window start, from the database's clock rather than the app's."""
        return func.now() - cast(literal(window), Interval)

    def count_for_identity(self, username: str, client_ip: str, window: timedelta) -> int:
        return (
            self.db.query(AuthAttempt)
            .filter(
                AuthAttempt.username == username,
                AuthAttempt.client_ip == client_ip,
                AuthAttempt.created_at >= self._cutoff(window),
            )
            .count()
        )

    def count_for_ip(self, client_ip: str, window: timedelta) -> int:
        return (
            self.db.query(AuthAttempt)
            .filter(
                AuthAttempt.client_ip == client_ip,
                AuthAttempt.created_at >= self._cutoff(window),
            )
            .count()
        )

    def record_failure(self, username: str, client_ip: str) -> None:
        """Commits on its own: the caller is about to raise, and a rollback
        would otherwise throw the evidence away and make the limit useless."""
        self.db.add(AuthAttempt(username=username, client_ip=client_ip))
        self.db.commit()

    def clear_for_identity(self, username: str, client_ip: str) -> None:
        """Called after a successful login, so a couple of typos followed by
        the right password leaves nothing behind."""
        deleted = (
            self.db.query(AuthAttempt)
            .filter(AuthAttempt.username == username, AuthAttempt.client_ip == client_ip)
            .delete(synchronize_session=False)
        )
        if deleted:
            self.db.commit()
