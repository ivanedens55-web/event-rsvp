"""One error shape for every failure: {"error": {"code": ..., "message": ...}}.

Clients get short, safe messages. Full details and stack traces go to the
server log only, so SQL errors and internal paths never reach the browser.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("rsvp")


class APIError(Exception):
    """Raise this from any route to send a clean error to the client."""

    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _describe_validation_error(exc: RequestValidationError) -> str:
    """Turn Pydantic's error list into one readable sentence, without echoing input."""
    first = exc.errors()[0]
    if first["type"] == "json_invalid":
        return "Request body is not valid JSON."
    # loc looks like ("body", "title") or ("path", "event_id")
    field = ".".join(str(part) for part in first["loc"][1:]) or "request"
    return f"{field}: {first['msg']}"


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError):
        return JSONResponse(error_body(exc.code, exc.message), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        return JSONResponse(
            error_body("VALIDATION_ERROR", _describe_validation_error(exc)), status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return JSONResponse(error_body("NOT_FOUND", "Not found."), status_code=404)
        if exc.status_code == 405:
            return JSONResponse(
                error_body("METHOD_NOT_ALLOWED", "Method not allowed."), status_code=405
            )
        return JSONResponse(
            error_body("HTTP_ERROR", "Request could not be processed."),
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            error_body("INTERNAL_ERROR", "Something went wrong on our side. Please try again."),
            status_code=500,
        )
