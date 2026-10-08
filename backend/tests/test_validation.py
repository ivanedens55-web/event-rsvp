"""Boundary validation, error format and headers. No database needed:
these requests are rejected before any query runs."""

import pytest
from pydantic import ValidationError

from app.config import load_settings
from app.schemas import EventCreate, EventUpdate


def assert_error(res, status, code):
    assert res.status_code == status, res.text
    body = res.json()
    assert set(body) == {"error"} and set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code


@pytest.mark.parametrize("body", [
    {"email": "not-an-email", "password": "long-enough"},
    {"email": "a@example.com", "password": "short"},
    {"email": "a@example.com", "password": "x" * 129},
    {"email": "a@example.com", "password": "long-enough", "is_admin": True},  # unknown field
    {"email": "a@example.com"},
])
def test_register_rejects_bad_bodies(plain_client, body):
    assert_error(plain_client.post("/auth/register", json=body), 422, "VALIDATION_ERROR")


GOOD_RSVP = {"name": "Ann", "email": "ann@example.com", "response": "yes"}


@pytest.mark.parametrize("changes", [
    {"response": "perhaps"},
    {"party_size": 0},
    {"party_size": 11},
    {"name": "   "},  # blank after trimming
    {"name": "x" * 101},
    {"note": "x" * 501},
    {"email": "nope"},
])
def test_rsvp_rejects_bad_bodies(plain_client, changes):
    res = plain_client.post("/public/events/abcdefgh12/rsvps", json={**GOOD_RSVP, **changes})
    assert_error(res, 422, "VALIDATION_ERROR")


def test_bad_slug_rejected_before_database(plain_client):
    assert_error(plain_client.get("/public/events/bad slug!"), 422, "VALIDATION_ERROR")
    assert_error(plain_client.get("/public/events/short"), 422, "VALIDATION_ERROR")


def test_validation_message_names_field_without_echoing_input(plain_client):
    res = plain_client.post("/public/events/abcdefgh12/rsvps",
                            json={**GOOD_RSVP, "note": "<script>" * 100})
    msg = res.json()["error"]["message"]
    assert msg.startswith("note:") and "<script>" not in msg


def test_protected_routes_need_a_token(plain_client):
    assert_error(plain_client.get("/events"), 401, "UNAUTHORIZED")
    assert_error(plain_client.get("/events", headers={"Authorization": "Bearer junk"}),
                 401, "UNAUTHORIZED")


def test_unknown_route_and_method(plain_client):
    assert_error(plain_client.get("/nope"), 404, "NOT_FOUND")
    assert_error(plain_client.delete("/health"), 405, "METHOD_NOT_ALLOWED")


def test_security_headers(plain_client):
    h = plain_client.get("/health").headers
    assert h["X-Content-Type-Options"] == "nosniff"
    assert h["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in h["Content-Security-Policy"]
    assert h["Referrer-Policy"] == "no-referrer"
    assert "Strict-Transport-Security" not in h  # HSTS only in production


def test_cors_allows_only_configured_origin(plain_client):
    ok = plain_client.options("/events", headers={
        "Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = plain_client.options("/events", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_cors_wildcard_refused(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError):
        load_settings()


def test_event_needs_timezone_and_future_date():
    with pytest.raises(ValidationError):
        EventCreate(title="x", starts_at="2030-01-01T18:00:00")  # no timezone
    with pytest.raises(ValidationError):
        EventCreate(title="x", starts_at="2020-01-01T18:00:00Z")  # past


def test_event_update_rules():
    assert EventUpdate(capacity=None).changes() == {"capacity": None}  # remove the limit
    with pytest.raises(ValidationError):
        EventUpdate(title=None)  # only capacity may be null
    with pytest.raises(ValidationError):
        EventUpdate()  # nothing to change


def test_broken_json_gets_friendly_message(plain_client):
    res = plain_client.post("/auth/login", content="{bad json",
                            headers={"Content-Type": "application/json"})
    assert_error(res, 422, "VALIDATION_ERROR")
    assert res.json()["error"]["message"] == "Request body is not valid JSON."
