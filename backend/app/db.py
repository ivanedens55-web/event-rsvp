"""Postgres connection pool. Every query in the app goes through get_conn()."""

from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import settings

pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=5,  # small: free tiers limit connections
    open=False,  # opened in main.py when the app starts
    kwargs={"row_factory": dict_row},
)


@contextmanager
def get_conn() -> Iterator[Connection]:
    """Borrow a connection. Commits if the block succeeds, rolls back if it raises."""
    with pool.connection() as conn:
        yield conn
