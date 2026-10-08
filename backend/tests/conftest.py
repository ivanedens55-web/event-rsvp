"""Test setup.

Logic, validation and contract tests run anywhere. Database tests need a real,
DISPOSABLE Postgres (never your Supabase project: tables are wiped between tests):

  TEST_ADMIN_DATABASE_URL  owner connection, used to apply db/schema.sql and reset data
  TEST_DATABASE_URL        rsvp_app connection, used by the app under test

If they aren't set, database tests are skipped.
"""

import os
from pathlib import Path

import pytest

ADMIN_URL = os.environ.get("TEST_ADMIN_DATABASE_URL")
APP_URL = os.environ.get("TEST_DATABASE_URL")

# Set before importing the app, so it can never pick up a real DATABASE_URL from .env.
os.environ["DATABASE_URL"] = APP_URL or "postgresql://unused:unused@localhost:1/unused"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-hs256-0123"
os.environ["JWT_EXPIRE_MINUTES"] = "30"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"
os.environ["APP_ENV"] = "test"

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from psycopg.conninfo import conninfo_to_dict  # noqa: E402

from app.main import app  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


@pytest.fixture(scope="session")
def db_ready():
    if not (ADMIN_URL and APP_URL):
        pytest.skip("TEST_ADMIN_DATABASE_URL / TEST_DATABASE_URL not set")
    app_password = conninfo_to_dict(APP_URL).get("password", "")
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute(SCHEMA.read_text())
        # Role passwords can't be bound as parameters; quote it safely instead.
        conn.execute(
            sql.SQL("ALTER ROLE rsvp_app WITH PASSWORD {}").format(
                sql.Literal(app_password)
            )
        )
    return ADMIN_URL


@pytest.fixture(scope="session")
def _app_client(db_ready):
    with TestClient(app) as c:  # runs startup: opens the connection pool
        yield c


@pytest.fixture
def client(_app_client, db_ready):
    """A client with an empty database for each test."""
    with psycopg.connect(db_ready, autocommit=True) as conn:
        conn.execute("TRUNCATE rsvp_responses, rsvp_events, rsvp_hosts RESTART IDENTITY CASCADE")
    return _app_client


@pytest.fixture
def plain_client():
    """No database. For checks that fail before any query runs (validation, 404s)."""
    return TestClient(app)
