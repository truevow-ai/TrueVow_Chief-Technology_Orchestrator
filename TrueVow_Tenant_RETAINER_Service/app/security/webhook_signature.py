"""WebhookSignature v1.0 — HMAC-SHA256 signing and verification.

Frozen contract. All TrueVow services use this same module for service-to-service
webhook authentication.

Canonical signing string: {timestamp_ms}:{METHOD}:{path}:{body_sha256}
"""

from __future__ import annotations

import hashlib
import hmac as hmac_module
import json
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger("retainer.webhook_signature")

REPLAY_WINDOW_MS = 300_000
VALID_KEY_IDS = {"tv-primary"}
SIGNATURE_HEX_LENGTH = 64


@dataclass
class VerifyResult:
    valid: bool
    key_id: str | None = None
    reason: str | None = None


def sign_request(
    method: str,
    path: str,
    body: bytes | str,
    key_id: str = "tv-primary",
    secret: str | None = None,
) -> dict[str, str]:
    """Sign a webhook request. Returns headers dict."""
    if secret is None:
        from app.core.config import settings

        secret = settings.intake_webhook_secret or settings.service_api_key

    if isinstance(body, str):
        body = body.encode("utf-8")

    timestamp_ms = str(int(time.time() * 1000))
    body_hash = hashlib.sha256(body).hexdigest()
    signing_string = f"{timestamp_ms}:{method.upper()}:{path}:{body_hash}"
    signature = hmac_module.new(
        secret.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    return {
        "X-TrueVow-Key-Id": key_id,
        "X-TrueVow-Timestamp": timestamp_ms,
        "X-TrueVow-Signature": signature,
    }


def verify_signature(
    headers: dict[str, str],
    method: str,
    path: str,
    raw_body: bytes,
    *,
    key_id_override: str | None = None,
    secret_override: str | None = None,
) -> VerifyResult:
    """Verify a WebhookSignature v1.0 request. Returns VerifyResult."""
    key_id = key_id_override or headers.get("X-TrueVow-Key-Id", "")
    timestamp_str = headers.get("X-TrueVow-Timestamp", "")
    signature = headers.get("X-TrueVow-Signature", "")

    if not key_id or not timestamp_str or not signature:
        return VerifyResult(valid=False, reason="MISSING_HEADERS")

    if not timestamp_str.isdigit():
        return VerifyResult(valid=False, key_id=key_id, reason="MALFORMED_TIMESTAMP")

    if not _valid_hex_signature(signature):
        return VerifyResult(valid=False, key_id=key_id, reason="INVALID_SIGNATURE_FORMAT")

    timestamp_ms = int(timestamp_str)
    now_ms = int(time.time() * 1000)
    if abs(now_ms - timestamp_ms) > REPLAY_WINDOW_MS:
        return VerifyResult(valid=False, key_id=key_id, reason="EXPIRED_TIMESTAMP")

    secret = _resolve_secret(key_id, secret_override)
    if secret is None:
        return VerifyResult(valid=False, key_id=key_id, reason="UNKNOWN_KEY_ID")

    body_hash = hashlib.sha256(raw_body).hexdigest()
    method_upper = method.upper()
    signing_string = f"{timestamp_ms}:{method_upper}:{path}:{body_hash}"
    expected = hmac_module.new(
        secret.encode("utf-8"), signing_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac_module.compare_digest(expected, signature):
        return VerifyResult(valid=False, key_id=key_id, reason="SIGNATURE_MISMATCH")

    return VerifyResult(valid=True, key_id=key_id)


def _resolve_secret(key_id: str, override: str | None = None) -> str | None:
    if override:
        return override
    try:
        from app.core.config import settings

        if key_id == "tv-primary":
            return settings.intake_webhook_secret or settings.service_api_key

        secondary_raw = settings.intake_webhook_secret
        if secondary_raw:
            secondary = json.loads(secondary_raw)
            for key in secondary if isinstance(secondary, list) else []:
                if isinstance(key, dict) and key.get("key_id") == key_id:
                    return key.get("secret")
    except Exception:
        pass
    return None


def _valid_hex_signature(sig: str) -> bool:
    if len(sig) != SIGNATURE_HEX_LENGTH:
        return False
    try:
        int(sig, 16)
        return True
    except ValueError:
        return False
