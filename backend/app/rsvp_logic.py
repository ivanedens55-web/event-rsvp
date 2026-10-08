"""Business rules for RSVPs. Pure functions (no database, no web), so they are
easy to unit test. The routes call these; the frontend never re-implements them."""

from datetime import datetime


def spots_left(capacity: int | None, attending: int) -> int | None:
    """People who can still say yes. None means unlimited."""
    if capacity is None:
        return None
    return max(capacity - attending, 0)


def is_accepting_rsvps(
    rsvp_open: bool, starts_at: datetime, capacity: int | None, attending: int, now: datetime
) -> bool:
    """Open for RSVPs only if the host left it open, it hasn't started, and it isn't full."""
    if not rsvp_open or starts_at <= now:
        return False
    return spots_left(capacity, attending) != 0


def rsvp_rejection(
    *,
    rsvp_open: bool,
    starts_at: datetime,
    capacity: int | None,
    attending: int,
    response: str,
    party_size: int,
    now: datetime,
) -> tuple[str, str] | None:
    """Return (error_code, message) if this RSVP must be refused, else None.

    "No" and "maybe" answers are always allowed while RSVPs are open: they
    don't take a spot. A "yes" must fit in the spots left.
    """
    if not rsvp_open or starts_at <= now:
        return ("RSVP_CLOSED", "RSVPs for this event are closed.")
    if response == "yes":
        left = spots_left(capacity, attending)
        if left is not None and party_size > left:
            if left == 0:
                return ("EVENT_FULL", "This event is full.")
            return ("EVENT_FULL", f"Only {left} spot(s) left. Reduce your party size.")
    return None


def normalise_party_size(response: str, party_size: int) -> int:
    """A guest who says no isn't bringing anyone, so store 1."""
    return 1 if response == "no" else party_size


def capacity_too_low(new_capacity: int | None, attending: int) -> bool:
    """The host can't set capacity below the number of people already confirmed."""
    return new_capacity is not None and new_capacity < attending
