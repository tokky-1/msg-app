from datetime import timedelta

from sqlalchemy import Interval, cast, func, literal, select
from sqlalchemy.orm import Session

from models.auth_attempt import AuthAttempt

# Defensive: schema/auth.py already caps the username, but nothing should be
# able to put unbounded text into a table that an unauthenticated caller can
# write to.
MAX_STORED_USERNAME = 150


class AuthAttemptRepository:
    def __init__(self, db: Session):
        self.db = db

    def _cutoff(self, window: timedelta):
        """Window start, from the database's clock rather than the app's."""
        return func.now() - cast(literal(window), Interval)

    def _seconds_until_space(self, window: timedelta, *conditions):
        """How long until the oldest counted failure ages out.

        Computed in SQL so it comes from the same clock as the window itself.
        """
        oldest = func.min(AuthAttempt.created_at)
        expression = func.ceil(
            func.extract("epoch", oldest + cast(literal(window), Interval) - func.now())
        )
        value = self.db.query(expression).filter(*conditions).scalar()
        return max(1, int(value)) if value is not None else 1

    def reserve(
        self,
        username: str,
        client_ip: str,
        window: timedelta,
        max_identity: int,
        max_ip: int,
    ) -> int | None:
        """Decide whether this attempt is allowed, and consume it if so.

        Returns None when the caller may proceed, or the number of seconds to
        wait when they may not.

        Everything here happens under one advisory lock and one commit, which
        is the whole point. Counting and then recording as two separate steps
        with a ~100ms password verify in between let 30 simultaneous requests
        all read "0 failures" before any of them wrote a row: measured, 17
        guesses got through against a cap of 3.

        The lock is keyed on the address alone rather than the (username,
        address) pair. The per-address ceiling has to be atomic too, and a
        single lock cannot deadlock against itself the way two ordered locks
        might. It is held only for this counting and insert, never across the
        password verify - holding a pooled connection for the length of an
        Argon2 hash would hand out a way to exhaust the pool.
        """
        # pg_advisory_xact_lock releases on commit or rollback, so there is no
        # path that leaks it.
        self.db.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(client_ip, 0)))
        )

        cutoff = self._cutoff(window)

        # This address's expired rows, cleared while we already hold the lock
        # and are already writing. Bounded by the address's own activity and
        # served by ix_auth_attempts_ip.
        self.db.query(AuthAttempt).filter(
            AuthAttempt.client_ip == client_ip,
            AuthAttempt.created_at < cutoff,
        ).delete(synchronize_session=False)

        identity_conditions = (
            AuthAttempt.username == username,
            AuthAttempt.client_ip == client_ip,
            AuthAttempt.created_at >= cutoff,
        )
        ip_conditions = (
            AuthAttempt.client_ip == client_ip,
            AuthAttempt.created_at >= cutoff,
        )

        identity_failures = self.db.query(AuthAttempt).filter(*identity_conditions).count()
        ip_failures = self.db.query(AuthAttempt).filter(*ip_conditions).count()

        if identity_failures >= max_identity:
            retry = self._seconds_until_space(window, *identity_conditions)
            self.db.commit()
            return retry

        if ip_failures >= max_ip:
            retry = self._seconds_until_space(window, *ip_conditions)
            self.db.commit()
            return retry

        # Recorded before the password is checked, not after. The quota is
        # spent on the attempt itself, so a request that dies mid-verify still
        # counts: this fails closed.
        self.db.add(
            AuthAttempt(username=username[:MAX_STORED_USERNAME], client_ip=client_ip)
        )
        self.db.commit()
        return None

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

    def purge_expired(self, window: timedelta) -> int:
        """Every expired row, for anything scheduled outside a request.

        reserve() only clears the address it is serving, so rows left by an
        address that never comes back would otherwise sit there.
        """
        deleted = (
            self.db.query(AuthAttempt)
            .filter(AuthAttempt.created_at < self._cutoff(window))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted
