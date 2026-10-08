"""Registration, login and token checks against a real Postgres."""

from datetime import datetime, timedelta, timezone

import jwt

from tests.helpers import register


def test_register_then_me(client):
    headers = register(client, "Ann@Example.com")
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "ann@example.com"  # stored lowercase


def test_duplicate_email_any_case(client):
    register(client, "ann@example.com")
    res = client.post("/auth/register", json={"email": "ANN@example.com", "password": "another-pass"})
    assert res.status_code == 409 and res.json()["error"]["code"] == "EMAIL_TAKEN"


def test_login(client):
    register(client, "ann@example.com", "correct-horse")
    res = client.post("/auth/login", json={"email": "ann@example.com", "password": "correct-horse"})
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer" and body["expires_in"] == 30 * 60


def test_wrong_password_and_unknown_email_look_the_same(client):
    register(client, "ann@example.com", "correct-horse")
    wrong = client.post("/auth/login", json={"email": "ann@example.com", "password": "wrong-horse"})
    unknown = client.post("/auth/login", json={"email": "bob@example.com", "password": "wrong-horse"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_password_is_hashed(client, db_ready):
    import psycopg
    register(client, "ann@example.com", "correct-horse")
    with psycopg.connect(db_ready) as conn:
        stored = conn.execute("SELECT password_hash FROM rsvp_hosts").fetchone()[0]
    assert stored.startswith("$argon2id$") and "correct-horse" not in stored


def _token(sub: str, minutes: int, secret: str = "test-secret-that-is-long-enough-for-hs256-0123"):
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": sub, "iat": now, "exp": now + timedelta(minutes=minutes)},
                      secret, algorithm="HS256")


def test_expired_token_rejected(client):
    register(client)  # host id 1
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {_token('1', -1)}"})
    assert res.status_code == 401


def test_token_signed_with_other_secret_rejected(client):
    register(client)
    forged = _token("1", 10, secret="someone-elses-secret-that-is-also-long-0000")
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert res.status_code == 401


def test_token_for_missing_host_rejected(client):
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {_token('999', 10)}"})
    assert res.status_code == 401
