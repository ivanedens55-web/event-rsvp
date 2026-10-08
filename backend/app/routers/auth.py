"""Host sign-up and login."""

from fastapi import APIRouter, Depends

from app import repo
from app.db import get_conn
from app.deps import current_host_id
from app.errors import APIError
from app.schemas import Credentials, Host, Token
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_for(host_id: int) -> Token:
    token, expires_in = create_access_token(host_id)
    return Token(access_token=token, expires_in=expires_in)


@router.post("/register", response_model=Token, status_code=201)
def register(body: Credentials):
    with get_conn() as conn:
        host_id = repo.create_host(conn, body.email, hash_password(body.password))
    if host_id is None:
        raise APIError(409, "EMAIL_TAKEN", "An account with this email already exists. Log in instead.")
    return _token_for(host_id)


@router.post("/login", response_model=Token)
def login(body: Credentials):
    with get_conn() as conn:
        host = repo.get_host_by_email(conn, body.email)
    # Same message whether the email or the password is wrong.
    if not verify_password(body.password, host["password_hash"] if host else None):
        raise APIError(401, "UNAUTHORIZED", "Wrong email or password.")
    return _token_for(host["id"])


@router.get("/me", response_model=Host)
def me(host_id: int = Depends(current_host_id)):
    with get_conn() as conn:
        return repo.get_host_by_id(conn, host_id)
