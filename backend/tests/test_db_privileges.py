"""The app's database role can use its rows but can't change the schema."""

import psycopg
import pytest

from tests.conftest import APP_URL


@pytest.mark.parametrize("statement", [
    "DROP TABLE rsvp_responses",
    "ALTER TABLE rsvp_events ADD COLUMN x int",
    "TRUNCATE rsvp_hosts",
    "CREATE TABLE rsvp_sneaky (id int)",
])
def test_app_role_cannot_change_schema(db_ready, statement):
    with psycopg.connect(APP_URL) as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute(statement)
