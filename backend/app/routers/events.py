"""Private host routes. Every query includes host_id, so a host can only ever
see or change their own events. Someone else's event looks exactly like a
missing one (404), so ids can't be probed."""

import secrets
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response

from app import repo
from app.db import get_conn
from app.deps import current_host_id
from app.errors import APIError
from app.rsvp_logic import capacity_too_low, is_accepting_rsvps
from app.schemas import Counts, EventCreate, EventUpdate, HostEvent, Rsvp

router = APIRouter(prefix="/events", tags=["events"])

EventId = Annotated[int, Path(ge=1, le=2**63 - 1)]


def not_found() -> APIError:
    return APIError(404, "NOT_FOUND", "Event not found.")


def to_host_event(row: dict) -> HostEvent:
    """Build the API shape from a database row (event + counts)."""
    return HostEvent(
        **{k: row[k] for k in ("id", "slug", "title", "description", "location",
                               "starts_at", "capacity", "rsvp_open", "created_at")},
        accepting_rsvps=is_accepting_rsvps(
            row["rsvp_open"], row["starts_at"], row["capacity"], row["attending"],
            datetime.now(timezone.utc),
        ),
        counts=Counts(yes=row["yes"], no=row["no"], maybe=row["maybe"], attending=row["attending"]),
    )


@router.get("", response_model=list[HostEvent])
def list_events(host_id: int = Depends(current_host_id)):
    with get_conn() as conn:
        return [to_host_event(row) for row in repo.list_host_events(conn, host_id)]


@router.post("", response_model=HostEvent, status_code=201)
def create_event(body: EventCreate, host_id: int = Depends(current_host_id)):
    slug = secrets.token_urlsafe(12)  # 16 random URL-safe characters
    with get_conn() as conn:
        event_id = repo.create_event(conn, host_id, slug, body.model_dump())
        return to_host_event(repo.get_host_event(conn, host_id, event_id))


@router.get("/{event_id}", response_model=HostEvent)
def get_event(event_id: EventId, host_id: int = Depends(current_host_id)):
    with get_conn() as conn:
        row = repo.get_host_event(conn, host_id, event_id)
    if row is None:
        raise not_found()
    return to_host_event(row)


@router.patch("/{event_id}", response_model=HostEvent)
def update_event(event_id: EventId, body: EventUpdate, host_id: int = Depends(current_host_id)):
    changes = body.changes()
    with get_conn() as conn:
        # Lock the row so no RSVP can sneak in between the capacity check and the update.
        if repo.lock_host_event(conn, host_id, event_id) is None:
            raise not_found()
        if "capacity" in changes and capacity_too_low(
            changes["capacity"], repo.attending_count(conn, event_id)
        ):
            raise APIError(
                409, "CAPACITY_TOO_LOW",
                "Capacity can't be lower than the number of people already coming.",
            )
        repo.update_event(conn, host_id, event_id, changes)
        return to_host_event(repo.get_host_event(conn, host_id, event_id))


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: EventId, host_id: int = Depends(current_host_id)):
    with get_conn() as conn:
        if not repo.delete_event(conn, host_id, event_id):
            raise not_found()
    return Response(status_code=204)


@router.get("/{event_id}/rsvps", response_model=list[Rsvp])
def list_rsvps(event_id: EventId, host_id: int = Depends(current_host_id)):
    with get_conn() as conn:
        if repo.get_host_event(conn, host_id, event_id) is None:  # ownership check first
            raise not_found()
        return repo.list_rsvps(conn, event_id)
