"""Clerk JWT verification.

In production (AUTH_MODE=clerk), tokens are validated against the Clerk JWKS endpoint.
In local/dev mode, tokens are verified with HS256 against LOCAL_JWT_SECRET.
"""

from __future__ import annotations

import jwt
from jwt import PyJWKClient

from app.core.config import settings

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None and settings.clerk_jwks_url:
        _jwks_client = PyJWKClient(settings.clerk_jwks_url, cache_ttl=settings.clerk_jwks_cache_ttl)
    return _jwks_client


def verify_token(token: str) -> dict:
    if settings.auth_mode == "clerk":
        client = _get_jwks_client()
        if not client:
            raise jwt.PyJWTError("Clerk JWKS is not configured.")
        signing_key = client.get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.clerk_audience or None,
            issuer=settings.clerk_issuer or None,
        )
    return jwt.decode(token, settings.local_jwt_secret, algorithms=[settings.local_jwt_algorithm])
