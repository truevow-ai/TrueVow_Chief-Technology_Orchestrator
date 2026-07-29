from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    RET_AUTHORITY_MISSING = "RET_AUTHORITY_MISSING"
    RET_POLICY_INACTIVE = "RET_POLICY_INACTIVE"
    RET_STATE_CONFLICT = "RET_STATE_CONFLICT"
    RET_TENANT_MISMATCH = "RET_TENANT_MISMATCH"
    RET_TEMPLATE_UNRESOLVED = "RET_TEMPLATE_UNRESOLVED"
    RET_PREFLIGHT_FAILED = "RET_PREFLIGHT_FAILED"
    RET_DOCUMENT_HASH_MISMATCH = "RET_DOCUMENT_HASH_MISMATCH"
    RET_CONSENT_NOT_EFFECTIVE = "RET_CONSENT_NOT_EFFECTIVE"
    RET_SIGNATURE_INVALID = "RET_SIGNATURE_INVALID"
    RET_ACTIVATION_UNKNOWN = "RET_ACTIVATION_UNKNOWN"
    RET_IDEMPOTENCY_CONFLICT = "RET_IDEMPOTENCY_CONFLICT"
    RET_CANDIDATE_VERSION_CONFLICT = "RET_CANDIDATE_VERSION_CONFLICT"


ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.RET_AUTHORITY_MISSING: "Required authority or evidence is absent.",
    ErrorCode.RET_POLICY_INACTIVE: "No effective policy is configured for this tenant.",
    ErrorCode.RET_STATE_CONFLICT: "This action is not allowed from the current state.",
    ErrorCode.RET_TENANT_MISMATCH: "The resource does not belong to your tenant.",
    ErrorCode.RET_TEMPLATE_UNRESOLVED: "No effective approved template is available.",
    ErrorCode.RET_PREFLIGHT_FAILED: "Required package data or controls are missing.",
    ErrorCode.RET_DOCUMENT_HASH_MISMATCH: "Document bytes differ from the locked version.",
    ErrorCode.RET_CONSENT_NOT_EFFECTIVE: "Required consent is absent or has been revoked.",
    ErrorCode.RET_SIGNATURE_INVALID: "Signature evidence is invalid or mismatched.",
    ErrorCode.RET_ACTIVATION_UNKNOWN: "Activation result is uncertain; reconciliation required.",
    ErrorCode.RET_IDEMPOTENCY_CONFLICT: (
        "A conflicting request with the same idempotency key was detected."
    ),
    ErrorCode.RET_CANDIDATE_VERSION_CONFLICT: "A conflicting candidate version already exists.",
}
