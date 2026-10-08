"""Pure business rules: no database, no HTTP."""

from datetime import datetime, timedelta, timezone

from app.rsvp_logic import (
    capacity_too_low,
    is_accepting_rsvps,
    normalise_party_size,
    rsvp_rejection,
    spots_left,
)

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(days=1)
EARLIER = NOW - timedelta(minutes=1)


def reject(**kw):
    base = dict(rsvp_open=True, starts_at=LATER, capacity=None, attending=0,
                response="yes", party_size=1, now=NOW)
    return rsvp_rejection(**{**base, **kw})


def test_spots_left():
    assert spots_left(None, 50) is None
    assert spots_left(10, 4) == 6
    assert spots_left(10, 12) == 0  # never negative


def test_is_accepting_rsvps():
    assert is_accepting_rsvps(True, LATER, None, 0, NOW)
    assert not is_accepting_rsvps(False, LATER, None, 0, NOW)  # host closed it
    assert not is_accepting_rsvps(True, EARLIER, None, 0, NOW)  # already started
    assert not is_accepting_rsvps(True, LATER, 5, 5, NOW)  # full


def test_yes_that_fits_is_allowed():
    assert reject(capacity=5, attending=3, party_size=2) is None


def test_closed_or_started_events_refuse_everything():
    assert reject(rsvp_open=False)[0] == "RSVP_CLOSED"
    assert reject(starts_at=NOW, response="no")[0] == "RSVP_CLOSED"


def test_full_event_refuses_yes():
    code, message = reject(capacity=5, attending=5)
    assert code == "EVENT_FULL" and message == "This event is full."


def test_party_too_big_says_how_many_spots_left():
    code, message = reject(capacity=5, attending=3, party_size=3)
    assert code == "EVENT_FULL" and "Only 2 spot(s) left" in message


def test_no_and_maybe_allowed_when_full():
    assert reject(capacity=5, attending=5, response="no") is None
    assert reject(capacity=5, attending=5, response="maybe", party_size=4) is None


def test_normalise_party_size():
    assert normalise_party_size("no", 4) == 1
    assert normalise_party_size("yes", 4) == 4
    assert normalise_party_size("maybe", 3) == 3


def test_capacity_too_low():
    assert capacity_too_low(3, 4)
    assert not capacity_too_low(4, 4)
    assert not capacity_too_low(None, 100)  # removing the limit is always fine
