"""Guest-facing routes: public view and RSVP rules."""

from concurrent.futures import ThreadPoolExecutor

from tests.helpers import create_event, register, rsvp


def test_public_view_has_no_guest_details(client):
    h = register(client)
    ev = create_event(client, h, capacity=10)
    rsvp(client, ev["slug"], email="secret@example.com", name="Secret Sam", party_size=3)
    res = client.get(f"/public/events/{ev['slug']}")
    body = res.json()
    assert res.status_code == 200
    assert set(body) == {"slug", "title", "description", "location", "starts_at",
                         "accepting_rsvps", "spots_left"}
    assert body["spots_left"] == 7
    assert "secret" not in res.text.lower() and "Secret Sam" not in res.text


def test_unknown_slug(client):
    res = client.get("/public/events/doesnotexist1")
    assert res.status_code == 404 and res.json()["error"]["code"] == "NOT_FOUND"
    assert rsvp(client, "doesnotexist1").status_code == 404


def test_rsvp_counts_show_on_host_dashboard(client):
    h = register(client)
    ev = create_event(client, h)
    rsvp(client, ev["slug"], email="a@example.com", party_size=2)
    rsvp(client, ev["slug"], email="b@example.com", response="maybe")
    rsvp(client, ev["slug"], email="c@example.com", response="no", party_size=5)
    counts = client.get(f"/events/{ev['id']}", headers=h).json()["counts"]
    assert counts == {"yes": 1, "no": 1, "maybe": 1, "attending": 2}
    guests = client.get(f"/events/{ev['id']}/rsvps", headers=h).json()
    assert [g["email"] for g in guests] == ["c@example.com", "b@example.com", "a@example.com"]
    assert guests[0]["party_size"] == 1  # a "no" never brings anyone


def test_one_rsvp_per_email_any_case(client):
    h = register(client)
    ev = create_event(client, h)
    assert rsvp(client, ev["slug"], email="ann@example.com").status_code == 201
    res = rsvp(client, ev["slug"], email="ANN@example.com", response="no")
    assert res.status_code == 409 and res.json()["error"]["code"] == "ALREADY_RESPONDED"


def test_full_event(client):
    h = register(client)
    ev = create_event(client, h, capacity=3)
    assert rsvp(client, ev["slug"], email="a@example.com", party_size=2).status_code == 201
    too_many = rsvp(client, ev["slug"], email="b@example.com", party_size=2)
    assert too_many.status_code == 409 and "Only 1 spot(s) left" in too_many.json()["error"]["message"]
    assert rsvp(client, ev["slug"], email="b@example.com").status_code == 201
    assert rsvp(client, ev["slug"], email="c@example.com").json()["error"]["code"] == "EVENT_FULL"
    assert rsvp(client, ev["slug"], email="c@example.com", response="maybe").status_code == 201
    assert client.get(f"/public/events/{ev['slug']}").json()["accepting_rsvps"] is False


def test_closed_event(client):
    h = register(client)
    ev = create_event(client, h)
    client.patch(f"/events/{ev['id']}", json={"rsvp_open": False}, headers=h)
    res = rsvp(client, ev["slug"])
    assert res.status_code == 409 and res.json()["error"]["code"] == "RSVP_CLOSED"


def test_started_event_is_closed(client, db_ready):
    import psycopg
    h = register(client)
    ev = create_event(client, h)
    with psycopg.connect(db_ready) as conn:  # move it into the past directly
        conn.execute("UPDATE rsvp_events SET starts_at = now() - interval '1 hour'")
    assert rsvp(client, ev["slug"]).json()["error"]["code"] == "RSVP_CLOSED"


def test_last_spot_goes_to_exactly_one_guest(client):
    """Ten guests race for one spot. The row lock means exactly one wins."""
    h = register(client)
    ev = create_event(client, h, capacity=1)
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(lambda i: rsvp(client, ev["slug"], email=f"g{i}@example.com"),
                                range(10)))
    codes = sorted(r.status_code for r in results)
    assert codes == [201] + [409] * 9
    assert client.get(f"/events/{ev['id']}", headers=h).json()["counts"]["attending"] == 1
