"""Shared fixtures for the service-layer unit tests.

These tests never touch Postgres: the repositories are patched out at their
import site in ``services.mes_service``, so a ``MessageService`` built here
talks to mocks only. ``autospec=True`` keeps the mocks honest -- calling a repo
method that doesn't exist, or with the wrong signature, fails the test.
"""

import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

# core.config validates these at import time, and importing the service pulls it
# in. These are set before that import and core.config loads .env with
# override=False, so THESE win, not .env - which is what keeps the unit tests
# off any real database. Tests that do want one build their own engine from
# .env; see tests/test_auth_attempt_repo.py.
os.environ.setdefault("SECRET_KEY", "test-secret-never-used")
os.environ.setdefault("CORS_ORIGINS", '["http://testserver"]')
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "test")

from services.mes_service import MessageService  # noqa: E402

SENDER_ID = 1
RECEIVER_ID = 2
OUTSIDER_ID = 3

# A fixed "now" so boundary tests can land on the exact microsecond.
FROZEN_NOW = datetime(2026, 9, 25, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def message_repo(mocker):
    """The MessageRepository instance the service will build for itself."""
    return mocker.patch("services.mes_service.MessageRepository", autospec=True).return_value


@pytest.fixture
def user_repo(mocker):
    """The UserRepository instance the service will build for itself."""
    return mocker.patch("services.mes_service.UserRepository", autospec=True).return_value


@pytest.fixture
def service(message_repo, user_repo):
    # db=None is deliberate: both repos are mocks, so nothing may dereference it.
    return MessageService(db=None)


@pytest.fixture
def frozen_now(mocker):
    """Pin datetime.now() inside the service so elapsed time is exact."""
    fake_datetime = mocker.patch("services.mes_service.datetime")
    fake_datetime.now.return_value = FROZEN_NOW
    return FROZEN_NOW


@pytest.fixture
def existing_receiver():
    """Whatever UserRepository.get_by_id returns; the service only null-checks it."""
    return SimpleNamespace(id=RECEIVER_ID, username="receiver")


@pytest.fixture
def make_message():
    """Build a stand-in for a persisted Message row.

    ``sent_ago`` is measured back from FROZEN_NOW. Pass ``naive=True`` to mimic a
    column read that lost its tzinfo.
    """

    def _make(
        *,
        message_id=101,
        sender_id=SENDER_ID,
        receiver_id=RECEIVER_ID,
        content="original content",
        sent_ago=timedelta(minutes=1),
        naive=False,
    ):
        timestamp = FROZEN_NOW - sent_ago
        if naive:
            timestamp = timestamp.replace(tzinfo=None)
        return SimpleNamespace(
            id=message_id,
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            timestamp=timestamp,
        )

    return _make
