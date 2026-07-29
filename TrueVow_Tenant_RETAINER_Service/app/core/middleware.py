"""HTTP middleware: correlation id + per-request audit logging."""

from __future__ import annotations

import uuid

from fastapi import Request

from app.core.logging import get_logger

logger = get_logger("retainer.middleware")

_API_PREFIX = "/api/v1/retainer/"


async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


async def audit_middleware(request: Request, call_next):
    response = await call_next(request)

    ctx = getattr(request.state, "auth", None)
    if ctx is not None and request.url.path.startswith(_API_PREFIX):
        try:
            logger.info(
                "AUDIT user=%s firm=%s method=%s path=%s status=%s",
                ctx.user_id,
                ctx.firm_id,
                request.method,
                request.url.path,
                response.status_code,
            )
        except Exception:
            logger.exception("Failed to write audit entry")

    return response
