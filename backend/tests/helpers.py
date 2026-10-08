from datetime import datetime, timedelta, timezone


def future(days: int = 7) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def register(client, email: str = "host@example.com", password: str = "correct-horse") -> dict:
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def create_event(client, headers: dict, **overrides) -> dict:
    body = {"title": "Book club", "starts_at": future(), **overrides}
    res = client.post("/events", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


def rsvp(client, slug: str, email: str = "guest@example.com", **overrides):
    body = {"name": "Guest", "email": email, "response": "yes", **overrides}
    return client.post(f"/public/events/{slug}/rsvps", json=body)
