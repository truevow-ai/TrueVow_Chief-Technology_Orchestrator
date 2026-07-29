"""Plain-English error handling.

Every failure returns a short human message plus a correlation id
and support contact. Stack traces are never exposed.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger("retainer.errors")

SUPPORT_CONTACT = "support@truevow.law"


class RetainerError(Exception):
    def __init__(
        self, message: str, *, status_code: int = 400, code: str = "retainer_error"
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def _body(message: str, code: str, request: Request) -> dict:
    return {
        "error": code,
        "message": message,
        "correlation_id": _correlation_id(request),
        "support": SUPPORT_CONTACT,
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RetainerError)
    async def _handle_retainer_error(request: Request, exc: RetainerError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content=_body(exc.message, exc.code, request)
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_body(
                "Some of the information provided was not valid.", "invalid_request", request
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request could not be completed."
        return JSONResponse(
            status_code=exc.status_code, content=_body(message, "http_error", request)
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content=_body(
                "Something went wrong on our end. Please try again or contact support.",
                "internal_error",
                request,
            ),
        )
