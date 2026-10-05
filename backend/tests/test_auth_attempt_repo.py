"""AuthAttemptRepository against a real Postgres.

These exist because the unit tests could not have caught the bug that shipped.
A mocked repository answers whatever the fake says, so it cannot tell you that
``func.now() - cast(literal(window), Interval)`` compiles to the right SQL, and
it cannot tell you what happens when thirty requests arrive at once. The
original guard counted and then recorded with a ~100ms password verify in
between; measured against the running API, 30 simultaneous guesses got 17
through against a cap of 3.

Skipped when no database is reachable, so the suite still runs on a bare
checkout.
"""

import pathlib
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import text

from models.auth_attempt import AuthAttempt
from repository.auth_attempt_repo import AuthAttemptRepository

# Its own engine, not db.connect's. conftest pins DB_USER/PASSWORD/NAME to
# "test" before anything imports core.config, and load_dotenv(override=False)
# means those win over .env - which is what keeps the unit tests hermetic, but
# also means db.connect points at a database that does not exist. These tests
# want the real one, so they read .env themselves.
def _make_sessionmaker():
    from dotenv import dotenv_values
    from sqlalchemy import URL, create_engine
    from sqlalchemy.orm import sessionmaker

    env = dotenv_values(pathlib.Path(__file__).resolve().parent.parent / ".env")
    url = URL.create(
        "postgresql+psycopg2",
        username=env["DB_USER"],
        password=env["DB_PASSWORD"],
        host=env.get("DB_HOST", "localhost"),
        port=int(env.get("DB_PORT", 5432)),
        database=env["DB_NAME"],
    )
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return sessionmaker(bind=engine)


try:
    SessionLocal = _make_sessionmaker()
    DB_UP = True
except Exception:  # noqa: BLE001 - any failure to reach it means skip
    SessionLocal = None
    DB_UP = False

pytestmark = pytest.mark.skipif(DB_UP is False, reason="no database reachable")

WINDOW = timedelta(minutes=15)
MAX_IDENTITY = 3
MAX_IP = 10


@pytest.fixture
def ip():
    """A unique address per test, so tests cannot interfere with each other
    through the shared per-address counter."""
    address = f"198.51.100.{uuid.uuid4().int % 250 + 1}-{uuid.uuid4().hex[:8]}"
    yield address
    with SessionLocal() as db:
        db.query(AuthAttempt).filter(AuthAttempt.client_ip == address).delete(
            synchronize_session=False
        )
        db.commit()


def reserve(ip, username="ghost", max_identity=MAX_IDENTITY, max_ip=MAX_IP):
    with SessionLocal() as db:
        return AuthAttemptRepository(db).reserve(
            username, ip, WINDOW, max_identity, max_ip
        )


def test_the_window_sql_actually_counts(ip):
    """If the interval expression were wrong this would never refuse."""
    assert [reserve(ip) for _ in range(MAX_IDENTITY)] == [None] * MAX_IDENTITY

    refused = reserve(ip)
    assert refused is not None, "the fourth attempt must be refused"
    assert 0 < refused <= WINDOW.total_seconds()


def test_thirty_simultaneous_attempts_get_exactly_the_cap(ip):
    """The regression test for the race.

    A Barrier is the point: without it the pool trickles the calls out and the
    earlier ones finish in time to be counted, which hides the bug.
    """
    workers = 30
    barrier = Barrier(workers)

    def go(_):
        barrier.wait()
        return reserve(ip)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(go, range(workers)))

    allowed = sum(1 for r in results if r is None)
    assert allowed == MAX_IDENTITY, (
        f"{allowed} of {workers} simultaneous attempts were allowed; the cap is "
        f"{MAX_IDENTITY}. The count and the insert are not atomic."
    )


def test_the_address_ceiling_also_holds_under_concurrency(ip):
    """Each attempt uses a fresh username, so only the per-address ceiling
    can stop it - and it has to do so atomically too."""
    workers = 25
    barrier = Barrier(workers)

    def go(n):
        barrier.wait()
        return reserve(ip, username=f"victim{n}")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(go, range(workers)))

    assert sum(1 for r in results if r is None) == MAX_IP


def test_a_success_clears_only_that_pair(ip):
    reserve(ip, username="ada")
    reserve(ip, username="bob")

    with SessionLocal() as db:
        AuthAttemptRepository(db).clear_for_identity("ada", ip)

    with SessionLocal() as db:
        remaining = (
            db.query(AuthAttempt).filter(AuthAttempt.client_ip == ip).all()
        )
    assert [r.username for r in remaining] == ["bob"]


def test_expired_rows_are_cleared_for_the_address_being_served(ip):
    reserve(ip)
    with SessionLocal() as db:
        db.query(AuthAttempt).filter(AuthAttempt.client_ip == ip).update(
            {"created_at": text("now() - interval '1 hour'")}, synchronize_session=False
        )
        db.commit()

    # The next attempt sweeps this address's stale rows while it holds the lock.
    reserve(ip)

    with SessionLocal() as db:
        rows = db.query(AuthAttempt).filter(AuthAttempt.client_ip == ip).count()
    assert rows == 1, "the hour-old row should be gone, leaving only the new one"


def test_an_overlong_username_is_truncated_before_storage(ip):
    reserve(ip, username="x" * 5000)
    with SessionLocal() as db:
        stored = db.query(AuthAttempt).filter(AuthAttempt.client_ip == ip).one()
    assert len(stored.username) == 150
