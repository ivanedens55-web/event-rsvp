"""Shared route dependencies."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import repo
from app.db import get_conn
from app.errors import APIError
from app.security import decode_access_token

_bearer = HTTPBearer(auto_error=False)  # we raise our own error format instead


def current_host_id(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    """Return the logged-in host's id, or reply 401. Protected routes depend on this."""
    host_id = decode_access_token(creds.credentials) if creds else None
    if host_id is None:
        raise APIError(401, "UNAUTHORIZED", "Please log in again.")
    with get_conn() as conn:
        if repo.get_host_by_id(conn, host_id) is None:  # account deleted since token was issued
            raise APIError(401, "UNAUTHORIZED", "Please log in again.")
    return host_id
