"""Host event routes, including ownership checks."""

from tests.helpers import create_event, future, register, rsvp


def test_create_and_get_event(client):
    h = register(client)
    ev = create_event(client, h, title="  Launch party  ", capacity=20, location="Nairobi")
    assert ev["title"] == "Launch party"  # trimmed
    assert len(ev["slug"]) == 16
    assert ev["accepting_rsvps"] is True
    assert ev["counts"] == {"yes": 0, "no": 0, "maybe": 0, "attending": 0}
    assert client.get(f"/events/{ev['id']}", headers=h).json() == ev


def test_list_is_soonest_first_and_only_mine(client):
    me, other = register(client, "me@example.com"), register(client, "other@example.com")
    later = create_event(client, me, title="Later", starts_at=future(30))
    sooner = create_event(client, me, title="Sooner", starts_at=future(2))
    create_event(client, other, title="Not mine")
    titles = [e["title"] for e in client.get("/events", headers=me).json()]
    assert titles == [sooner["title"], later["title"]]


def test_create_validation(client):
    h = register(client)
    for body in [
        {"title": "", "starts_at": future()},
        {"title": "Past", "starts_at": "2020-01-01T10:00:00Z"},
        {"title": "No tz", "starts_at": "2030-01-01T10:00:00"},
        {"title": "Big", "starts_at": future(), "capacity": 0},
    ]:
        res = client.post("/events", json=body, headers=h)
        assert res.status_code == 422, body


def test_other_hosts_cannot_touch_my_event(client):
    owner, intruder = register(client, "owner@example.com"), register(client, "x@example.com")
    ev = create_event(client, owner)
    url = f"/events/{ev['id']}"
    for res in [
        client.get(url, headers=intruder),
        client.patch(url, json={"title": "Hacked"}, headers=intruder),
        client.delete(url, headers=intruder),
        client.get(url + "/rsvps", headers=intruder),
    ]:
        assert res.status_code == 404  # looks the same as an event that doesn't exist
        assert res.json()["error"]["code"] == "NOT_FOUND"
    assert client.get(url, headers=owner).json()["title"] == "Book club"


def test_patch_changes_only_sent_fields(client):
    h = register(client)
    ev = create_event(client, h, description="Bring a book", capacity=10)
    res = client.patch(f"/events/{ev['id']}", json={"title": "Poetry night"}, headers=h).json()
    assert res["title"] == "Poetry night"
    assert res["description"] == "Bring a book" and res["capacity"] == 10


def test_patch_close_rsvps_and_remove_capacity(client):
    h = register(client)
    ev = create_event(client, h, capacity=10)
    res = client.patch(f"/events/{ev['id']}", json={"rsvp_open": False, "capacity": None},
                       headers=h).json()
    assert res["rsvp_open"] is False and res["capacity"] is None
    assert res["accepting_rsvps"] is False


def test_capacity_cannot_drop_below_people_coming(client):
    h = register(client)
    ev = create_event(client, h, capacity=10)
    assert rsvp(client, ev["slug"], party_size=4).status_code == 201
    res = client.patch(f"/events/{ev['id']}", json={"capacity": 3}, headers=h)
    assert res.status_code == 409 and res.json()["error"]["code"] == "CAPACITY_TOO_LOW"
    assert client.patch(f"/events/{ev['id']}", json={"capacity": 4}, headers=h).status_code == 200


def test_delete_removes_event_and_rsvps(client, db_ready):
    import psycopg
    h = register(client)
    ev = create_event(client, h)
    rsvp(client, ev["slug"])
    assert client.delete(f"/events/{ev['id']}", headers=h).status_code == 204
    assert client.get(f"/events/{ev['id']}", headers=h).status_code == 404
    with psycopg.connect(db_ready) as conn:
        assert conn.execute("SELECT count(*) FROM rsvp_responses").fetchone()[0] == 0


def test_event_id_must_be_positive(client):
    h = register(client)
    assert client.get("/events/0", headers=h).status_code == 422
