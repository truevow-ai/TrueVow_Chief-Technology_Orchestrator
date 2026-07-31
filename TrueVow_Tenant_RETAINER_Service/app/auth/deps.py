"""Authenticated request context + FastAPI dependency."""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
import logging
import time
from dataclasses import dataclass, field

import jwt
from fastapi import HTTPException, Request, status

from app.auth.clerk import verify_token

logger = logging.getLogger("retainer.auth")


@dataclass
class AuthContext:
    user_id: str
    firm_id: str
    role: str | None = None
    mfa: bool = False
    claims: dict = field(default_factory=dict)


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def get_current_context(request: Request) -> AuthContext:
    token = _extract_bearer(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )

    try:
        claims = verify_token(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session."
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication could not be verified."
        ) from None

    user_id = claims.get("sub")
    firm_id = claims.get("org_id") or claims.get("firm_id")
    if not user_id or not firm_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is missing the required firm or user identity.",
        )

    ctx = AuthContext(
        user_id=str(user_id),
        firm_id=str(firm_id),
        role=claims.get("role") or claims.get("org_role"),
        mfa=bool(claims.get("two_factor_enabled") or claims.get("mfa", False)),
        claims=claims,
    )
    request.state.auth = ctx
    return ctx


async def get_optional_context(request: Request) -> AuthContext | None:
    try:
        return await get_current_context(request)
    except HTTPException:
        return None


async def get_webhook_context(request: Request) -> AuthContext:
    """Authenticate a service-to-service webhook call.

    HMAC (WebhookSignature v1.0) is preferred. Falls back to legacy Bearer/API-Key
    during migration with deprecation warnings.
    """
    from app.core.config import settings

    # Try HMAC signature first (WebhookSignature v1.0)
    hmac_result = await _verify_hmac_signature(request)
    if hmac_result:
        tenant_id = request.headers.get("X-Tenant-Id")
        actor_id = request.headers.get("X-Actor-Id", "system")
        if not tenant_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="X-Tenant-Id required")
        ctx = AuthContext(user_id=actor_id, firm_id=tenant_id, role="SYSTEM_WEBHOOK",
                          claims={"auth_method": "hmac", "key_id": hmac_result})
        request.state.auth = ctx
        return ctx

    # Legacy: Bearer or X-API-Key
    api_key = _extract_bearer(request) or request.headers.get("X-API-Key")
    if api_key:
        allowed = {settings.service_api_key}
        if settings.intake_webhook_secret:
            allowed.add(settings.intake_webhook_secret)
        if api_key in allowed:
            logger.warning("Legacy webhook auth used (Bearer/API-Key). Migrate to HMAC WebhookSignature v1.0.")
            tenant_id = request.headers.get("X-Tenant-Id")
            if not tenant_id:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="X-Tenant-Id required")
            ctx = AuthContext(user_id=request.headers.get("X-Actor-Id", "system"), firm_id=tenant_id,
                              role="SYSTEM_WEBHOOK", claims={"auth_method": "legacy_bearer"})
            request.state.auth = ctx
            return ctx

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Webhook authentication required.")


async def _verify_hmac_signature(request: Request) -> str | None:
    """Verify WebhookSignature v1.0 HMAC. Returns key_id if valid, None otherwise."""
    from app.core.config import settings

    key_id = request.headers.get("X-TrueVow-Key-Id")
    timestamp_str = request.headers.get("X-TrueVow-Timestamp")
    signature = request.headers.get("X-TrueVow-Signature")

    if not key_id or not timestamp_str or not signature:
        return None

    try:
        timestamp_ms = int(timestamp_str)
    except ValueError:
        return None

    if abs(int(time.time() * 1000) - timestamp_ms) > 300_000:
        return None

    secret = _resolve_webhook_secret(key_id)
    if not secret:
        return None

    body_bytes = await request.body()
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    path = request.url.path
    method = request.method
    signing_string = f"{timestamp_ms}:{method}:{path}:{body_hash}"

    expected = hmac_module.new(secret.encode(), signing_string.encode(), hashlib.sha256).hexdigest()

    if not hmac_module.compare_digest(expected, signature):
        return None

    return key_id


def _resolve_webhook_secret(key_id: str) -> str | None:
    """Resolve the HMAC secret for a given key_id."""
    from app.core.config import settings

    if key_id == "tv-primary":
        return settings.intake_webhook_secret or settings.service_api_key

    if settings.intake_webhook_secret:
        try:
            secondary = json.loads(settings.intake_webhook_secret)
            for key in secondary if isinstance(secondary, list) else []:
                if isinstance(key, dict) and key.get("key_id") == key_id:
                    return key.get("secret")
        except (json.JSONDecodeError, TypeError):
            pass

    return None
