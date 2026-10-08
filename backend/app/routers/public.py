"""Open routes for guests: view an event by its public link and RSVP.
These never return guest names or emails."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Path

from app import repo
from app.db import get_conn
from app.errors import APIError
from app.rsvp_logic import is_accepting_rsvps, normalise_party_size, rsvp_rejection, spots_left
from app.schemas import PublicEvent, RsvpConfirmation, RsvpCreate

router = APIRouter(prefix="/public", tags=["public"])

Slug = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{8,32}$")]


def not_found() -> APIError:
    return APIError(404, "NOT_FOUND", "This event link doesn't exist. Check it with the host.")


@router.get("/events/{slug}", response_model=PublicEvent)
def get_public_event(slug: Slug):
    with get_conn() as conn:
        row = repo.get_event_by_slug(conn, slug)
    if row is None:
        raise not_found()
    return PublicEvent(
        slug=row["slug"],
        title=row["title"],
        description=row["description"],
        location=row["location"],
        starts_at=row["starts_at"],
        accepting_rsvps=is_accepting_rsvps(
            row["rsvp_open"], row["starts_at"], row["capacity"], row["attending"],
            datetime.now(timezone.utc),
        ),
        spots_left=spots_left(row["capacity"], row["attending"]),
    )


@router.post("/events/{slug}/rsvps", response_model=RsvpConfirmation, status_code=201)
def create_rsvp(slug: Slug, body: RsvpCreate):
    party_size = normalise_party_size(body.response, body.party_size)
    with get_conn() as conn:
        # Lock the event row: if two guests try for the last spot at once,
        # the second waits, then sees the updated count.
        event = repo.lock_event_by_slug(conn, slug)
        if event is None:
            raise not_found()
        rejection = rsvp_rejection(
            rsvp_open=event["rsvp_open"],
            starts_at=event["starts_at"],
            capacity=event["capacity"],
            attending=repo.attending_count(conn, event["id"]),
            response=body.response,
            party_size=party_size,
            now=datetime.now(timezone.utc),
        )
        if rejection:
            raise APIError(409, *rejection)
        data = {**body.model_dump(), "party_size": party_size}
        if not repo.create_rsvp(conn, event["id"], data):
            raise APIError(
                409, "ALREADY_RESPONDED",
                "This email has already replied. Contact the host to change your answer.",
            )
    return RsvpConfirmation(name=body.name, response=body.response, party_size=party_size)
