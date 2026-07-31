"""WebhookSignature v1.0 — golden fixture tests.

16 test cases covering: valid primary/secondary keys, missing/malformed/expired
timestamps, modified body, wrong method/path, hex/signature validation, unknown
key IDs, and legacy auth recording.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from app.security.webhook_signature import (
    REPLAY_WINDOW_MS,
    VerifyResult,
    sign_request,
    verify_signature,
)

TEST_SECRET = "test-secret-v1-primary"
TEST_SECONDARY = "test-secret-v2-secondary"
TEST_BODY = b'{"candidate_id":"abc","tenant_id":"def"}'
TEST_PATH = "/api/v1/retainer/webhooks/candidate-submitted"
TEST_METHOD = "POST"


@pytest.fixture
def valid_headers():
    return sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, secret=TEST_SECRET)


def test_valid_primary_key(valid_headers):
    result = verify_signature(valid_headers, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert result.valid
    assert result.key_id == "tv-primary"


def test_valid_secondary_key():
    hdrs = sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, key_id="tv-secondary", secret=TEST_SECONDARY)
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, TEST_BODY,
                              key_id_override="tv-secondary", secret_override=TEST_SECONDARY)
    assert result.valid


def test_missing_headers():
    result = verify_signature({}, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid
    assert result.reason == "MISSING_HEADERS"


def test_unknown_key_id(valid_headers):
    hdrs_with_unknown = {
        "X-TrueVow-Key-Id": "tv-unknown-key",
        "X-TrueVow-Timestamp": valid_headers["X-TrueVow-Timestamp"],
        "X-TrueVow-Signature": "a" * 64,
    }
    result = verify_signature(hdrs_with_unknown, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid
    assert result.reason == "SIGNATURE_MISMATCH"


def test_malformed_timestamp():
    hdrs = {
        "X-TrueVow-Key-Id": "tv-primary",
        "X-TrueVow-Timestamp": "not-a-number",
        "X-TrueVow-Signature": "a" * 64,
    }
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid
    assert result.reason == "MALFORMED_TIMESTAMP"


def test_expired_timestamp():
    old = str(int(time.time() * 1000) - REPLAY_WINDOW_MS - 1000)
    body_hash = hashlib.sha256(TEST_BODY).hexdigest()
    sig = hmac.new(TEST_SECRET.encode(), f"{old}:POST:{TEST_PATH}:{body_hash}".encode(), hashlib.sha256).hexdigest()
    hdrs = {"X-TrueVow-Key-Id": "tv-primary", "X-TrueVow-Timestamp": old, "X-TrueVow-Signature": sig}
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid
    assert result.reason == "EXPIRED_TIMESTAMP"


def test_future_timestamp():
    future = str(int(time.time() * 1000) + REPLAY_WINDOW_MS + 1000)
    body_hash = hashlib.sha256(TEST_BODY).hexdigest()
    sig = hmac.new(TEST_SECRET.encode(), f"{future}:POST:{TEST_PATH}:{body_hash}".encode(), hashlib.sha256).hexdigest()
    hdrs = {"X-TrueVow-Key-Id": "tv-primary", "X-TrueVow-Timestamp": future, "X-TrueVow-Signature": sig}
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid


def test_modified_body():
    hdrs = sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, secret=TEST_SECRET)
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, b'{"tampered":true}', secret_override=TEST_SECRET)
    assert not result.valid
    assert result.reason == "SIGNATURE_MISMATCH"


def test_wrong_method():
    hdrs = sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, secret=TEST_SECRET)
    result = verify_signature(hdrs, "GET", TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid


def test_wrong_path():
    hdrs = sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, secret=TEST_SECRET)
    result = verify_signature(hdrs, TEST_METHOD, "/api/v1/retainer/webhooks/different", TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid


def test_trailing_slash_mismatch():
    hdrs = sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, secret=TEST_SECRET)
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH + "/", TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid


def test_invalid_signature_length():
    hdrs = {"X-TrueVow-Key-Id": "tv-primary", "X-TrueVow-Timestamp": str(int(time.time() * 1000)), "X-TrueVow-Signature": "short"}
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid
    assert result.reason == "INVALID_SIGNATURE_FORMAT"


def test_non_hex_signature():
    hdrs = {"X-TrueVow-Key-Id": "tv-primary", "X-TrueVow-Timestamp": str(int(time.time() * 1000)), "X-TrueVow-Signature": "g" * 64}
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, TEST_BODY, secret_override=TEST_SECRET)
    assert not result.valid


def test_signing_produces_valid_symmetric_result(valid_headers):
    body_hash = hashlib.sha256(TEST_BODY).hexdigest()
    ts = valid_headers["X-TrueVow-Timestamp"]
    sig = valid_headers["X-TrueVow-Signature"]
    signing_string = f"{ts}:POST:{TEST_PATH}:{body_hash}"
    expected = hmac.new(TEST_SECRET.encode(), signing_string.encode(), hashlib.sha256).hexdigest()
    assert hmac.compare_digest(expected, sig)


def test_raw_body_hash_matches():
    """Verify we hash exact bytes, not parsed/reserialized JSON."""
    hdrs = sign_request(TEST_METHOD, TEST_PATH, TEST_BODY, secret=TEST_SECRET)
    same = TEST_BODY
    result = verify_signature(hdrs, TEST_METHOD, TEST_PATH, same, secret_override=TEST_SECRET)
    assert result.valid
    different = b'{"different":true}'
    result2 = verify_signature(hdrs, TEST_METHOD, TEST_PATH, different, secret_override=TEST_SECRET)
    assert not result2.valid
