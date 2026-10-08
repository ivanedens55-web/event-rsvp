"""Every SQL query in the app. All values are passed as parameters (%(name)s),
never formatted into the SQL string, so user input can't change a query."""

from psycopg import Connection
from psycopg.errors import UniqueViolation

# ---------- hosts ----------

def create_host(conn: Connection, email: str, password_hash: str) -> int | None:
    """Return the new host id, or None if the email is already registered."""
    try:
        with conn.transaction():  # savepoint, so a duplicate doesn't break the connection
            row = conn.execute(
                "INSERT INTO rsvp_hosts (email, password_hash) VALUES (%(email)s, %(hash)s) "
                "RETURNING id",
                {"email": email, "hash": password_hash},
            ).fetchone()
        return row["id"]
    except UniqueViolation:
        return None


def get_host_by_email(conn: Connection, email: str) -> dict | None:
    return conn.execute(
        "SELECT id, email, password_hash FROM rsvp_hosts WHERE email = %(email)s",
        {"email": email},
    ).fetchone()


def get_host_by_id(conn: Connection, host_id: int) -> dict | None:
    return conn.execute(
        "SELECT id, email FROM rsvp_hosts WHERE id = %(id)s", {"id": host_id}
    ).fetchone()


# ---------- events ----------

# One event row plus its RSVP counts. "attending" adds up party sizes of yes RSVPs.
_EVENT_WITH_COUNTS = """
    SELECT e.id, e.host_id, e.slug, e.title, e.description, e.location,
           e.starts_at, e.capacity, e.rsvp_open, e.created_at,
           COUNT(r.id) FILTER (WHERE r.response = 'yes')   AS yes,
           COUNT(r.id) FILTER (WHERE r.response = 'no')    AS no,
           COUNT(r.id) FILTER (WHERE r.response = 'maybe') AS maybe,
           COALESCE(SUM(r.party_size) FILTER (WHERE r.response = 'yes'), 0)::int AS attending
    FROM rsvp_events e
    LEFT JOIN rsvp_responses r ON r.event_id = e.id
"""


def create_event(conn: Connection, host_id: int, slug: str, data: dict) -> int:
    row = conn.execute(
        """
        INSERT INTO rsvp_events (host_id, slug, title, description, location, starts_at, capacity)
        VALUES (%(host_id)s, %(slug)s, %(title)s, %(description)s, %(location)s,
                %(starts_at)s, %(capacity)s)
        RETURNING id
        """,
        {**data, "host_id": host_id, "slug": slug},
    ).fetchone()
    return row["id"]


def list_host_events(conn: Connection, host_id: int) -> list[dict]:
    return conn.execute(
        _EVENT_WITH_COUNTS + " WHERE e.host_id = %(host_id)s GROUP BY e.id ORDER BY e.starts_at",
        {"host_id": host_id},
    ).fetchall()


def get_host_event(conn: Connection, host_id: int, event_id: int) -> dict | None:
    """The event only if this host owns it. Ownership is part of the WHERE clause."""
    return conn.execute(
        _EVENT_WITH_COUNTS
        + " WHERE e.id = %(event_id)s AND e.host_id = %(host_id)s GROUP BY e.id",
        {"event_id": event_id, "host_id": host_id},
    ).fetchone()


def get_event_by_slug(conn: Connection, slug: str) -> dict | None:
    return conn.execute(
        _EVENT_WITH_COUNTS + " WHERE e.slug = %(slug)s GROUP BY e.id", {"slug": slug}
    ).fetchone()


def lock_host_event(conn: Connection, host_id: int, event_id: int) -> dict | None:
    """Lock this host's event row until the transaction ends (blocks concurrent RSVPs)."""
    return conn.execute(
        "SELECT id FROM rsvp_events WHERE id = %(event_id)s AND host_id = %(host_id)s FOR UPDATE",
        {"event_id": event_id, "host_id": host_id},
    ).fetchone()


def lock_event_by_slug(conn: Connection, slug: str) -> dict | None:
    """Lock the event row so two guests can't both take the last spot."""
    return conn.execute(
        "SELECT id, starts_at, capacity, rsvp_open FROM rsvp_events "
        "WHERE slug = %(slug)s FOR UPDATE",
        {"slug": slug},
    ).fetchone()


def attending_count(conn: Connection, event_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(party_size), 0)::int AS attending FROM rsvp_responses "
        "WHERE event_id = %(event_id)s AND response = 'yes'",
        {"event_id": event_id},
    ).fetchone()
    return row["attending"]


def update_event(conn: Connection, host_id: int, event_id: int, changes: dict) -> None:
    """Apply only the fields present in `changes`. The SQL text never changes:
    a missing field keeps its current value (COALESCE). capacity can be set
    to NULL on purpose, so it uses an explicit "set_capacity" flag instead."""
    conn.execute(
        """
        UPDATE rsvp_events SET
            title       = COALESCE(%(title)s, title),
            description = COALESCE(%(description)s, description),
            location    = COALESCE(%(location)s, location),
            starts_at   = COALESCE(%(starts_at)s, starts_at),
            rsvp_open   = COALESCE(%(rsvp_open)s, rsvp_open),
            capacity    = CASE WHEN %(set_capacity)s THEN %(capacity)s ELSE capacity END
        WHERE id = %(event_id)s AND host_id = %(host_id)s
        """,
        {
            "title": changes.get("title"),
            "description": changes.get("description"),
            "location": changes.get("location"),
            "starts_at": changes.get("starts_at"),
            "rsvp_open": changes.get("rsvp_open"),
            "set_capacity": "capacity" in changes,
            "capacity": changes.get("capacity"),
            "event_id": event_id,
            "host_id": host_id,
        },
    )


def delete_event(conn: Connection, host_id: int, event_id: int) -> bool:
    cur = conn.execute(
        "DELETE FROM rsvp_events WHERE id = %(event_id)s AND host_id = %(host_id)s",
        {"event_id": event_id, "host_id": host_id},
    )
    return cur.rowcount == 1


# ---------- responses ----------

def list_rsvps(conn: Connection, event_id: int) -> list[dict]:
    return conn.execute(
        "SELECT id, name, email, response, party_size, note, created_at "
        "FROM rsvp_responses WHERE event_id = %(event_id)s ORDER BY created_at DESC, id DESC",
        {"event_id": event_id},
    ).fetchall()


def create_rsvp(conn: Connection, event_id: int, data: dict) -> bool:
    """Return False if this email already replied to this event."""
    try:
        with conn.transaction():
            conn.execute(
                """
                INSERT INTO rsvp_responses (event_id, name, email, response, party_size, note)
                VALUES (%(event_id)s, %(name)s, %(email)s, %(response)s, %(party_size)s, %(note)s)
                """,
                {**data, "event_id": event_id},
            )
        return True
    except UniqueViolation:
        return False
