"""WebhookSignature v1.0 — HMAC signature verification.

Frozen contract. Every TrueVow service uses this same module.
Copy to: Customer Portal, INTAKE, RETAINER, SaaS Admin.

Env vars (set on every service):
  TRUEVOW_WEBHOOK_KEY_ID=tv-primary
  TRUEVOW_WEBHOOK_SECRET=<shared-secret>
  TRUEVOW_WEBHOOK_SECONDARY_KEYS=[{"key_id":"tv-secondary","secret":"..."}]
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Mapping


# ---------------------------------------------------------------------------
# Key resolution — primary + secondary rotation support
# ---------------------------------------------------------------------------

def _get_secret(key_id: str) -> str:
    primary_key_id = os.getenv("TRUEVOW_WEBHOOK_KEY_ID", "tv-primary")
    if key_id == primary_key_id:
        return os.getenv("TRUEVOW_WEBHOOK_SECRET", "")

    secondary_raw = os.getenv("TRUEVOW_WEBHOOK_SECONDARY_KEYS")
    if secondary_raw:
        try:
            secondary_keys = json.loads(secondary_raw)
            for entry in secondary_keys:
                if entry.get("key_id") == key_id:
                    return entry.get("secret", "")
        except (json.JSONDecodeError, TypeError):
            pass

    return ""


# ---------------------------------------------------------------------------
# Verification — the service receiving the webhook
# ---------------------------------------------------------------------------

def verify_signature(
    headers: Mapping[str, str],
    method: str,
    path: str,
    raw_body: str,
) -> bool:
    """Verify an incoming webhook HMAC signature.

    Rejects signatures older than 5 minutes (replay protection).
    Uses constant-time comparison to prevent timing attacks.
    """
    key_id = headers.get("x-truevow-key-id") or headers.get("X-TrueVow-Key-Id", "")
    timestamp = headers.get("x-truevow-timestamp") or headers.get("X-TrueVow-Timestamp", "")
    signature = headers.get("x-truevow-signature") or headers.get("X-TrueVow-Signature", "")

    if not key_id or not timestamp or not signature:
        return False

    # Replay protection — 5-minute window
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False

    now_ms = int(time.time() * 1000)
    if abs(now_ms - ts) > 300_000:
        return False

    secret = _get_secret(key_id)
    if not secret:
        return False

    body_hash = hashlib.sha256(raw_body.encode()).hexdigest()
    signing_string = f"{timestamp}:{method}:{path}:{body_hash}"
    expected = hmac.new(
        secret.encode(),
        signing_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


# ---------------------------------------------------------------------------
# Dual auth — accept both HMAC and legacy Bearer during migration
# ---------------------------------------------------------------------------

def is_legacy_bearer(method: str, path: str, body: str | None = None) -> bool:
    """Check if this path should fall back to legacy Bearer auth during migration.

    Returns True for internal firm API paths that use Clerk JWT auth.
    Returns False for webhook paths that should use HMAC.
    """
    # Webhook paths must use HMAC — no fallback
    if "/webhooks/" in path:
        return False
    # Internal firm API paths use Clerk (or dev JWT)
    return True
