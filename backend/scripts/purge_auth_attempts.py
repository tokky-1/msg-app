"""Delete login-attempt rows that have aged out of the lockout window.

A login already clears the expired rows for the address it is serving, which
covers every address that keeps showing up. This is for the rest: an address
that fails three times and never returns leaves rows behind until something
sweeps them.

Run it from cron, a Kubernetes CronJob, or by hand:

    uv run python scripts/purge_auth_attempts.py
"""

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import settings  # noqa: E402
from db.connect import SessionLocal  # noqa: E402
from repository.auth_attempt_repo import AuthAttemptRepository  # noqa: E402


def main() -> None:
    window = timedelta(minutes=settings.AUTH_LOCKOUT_MINUTES)
    with SessionLocal() as db:
        removed = AuthAttemptRepository(db).purge_expired(window)
    print(f"removed {removed} expired login attempts (window {window})")


if __name__ == "__main__":
    main()
