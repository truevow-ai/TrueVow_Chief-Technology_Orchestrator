from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    CONFLICT_SEARCH_STARTED = "conflict.search_started"
    CONFLICT_CANDIDATE_DETECTED = "conflict.candidate_detected"
    CONFLICT_REVIEW_REQUESTED = "conflict.review_requested"
    CONFLICT_CLEARED_BY_ATTORNEY = "conflict.cleared_by_attorney"
    CONFLICT_HOLD_APPLIED = "conflict.hold_applied"

    REPRESENTATION_APPROVED_BY_ATTORNEY = "representation.approved_by_attorney"
    REPRESENTATION_DECLINED_BY_ATTORNEY = "representation.declined_by_attorney"

    ENGAGEMENT_WORKFLOW_STARTED = "engagement.workflow_started"
    ENGAGEMENT_CLIENT_REVIEW_STARTED = "engagement.client_review_started"
    ENGAGEMENT_QUESTION_RECEIVED = "engagement.question_received"
    ENGAGEMENT_QUESTION_ESCALATED = "engagement.question_escalated"
    ENGAGEMENT_DECLINED_BY_CLIENT = "engagement.declined_by_client"
    ENGAGEMENT_AUTHORIZATION_WITHDRAWN = "engagement.authorization_withdrawn"
    ENGAGEMENT_DELIVERY_FAILED = "engagement.delivery_failed"
    ENGAGEMENT_REMINDER_SENT = "engagement.reminder_sent"
    ENGAGEMENT_REMINDER_SUPPRESSED = "engagement.reminder_suppressed"
    ENGAGEMENT_RECONCILIATION_REQUIRED = "engagement.reconciliation_required"
    ENGAGEMENT_EXPIRED = "engagement.expired"

    TEMPLATE_RESOLVED = "template.resolved"

    PACKAGE_GENERATED = "package.generated"
    PACKAGE_DELIVERY_AUTHORIZED = "package.delivery_authorized"
    PACKAGE_DELIVERED = "package.delivered"
    PACKAGE_FULLY_EXECUTED = "package.fully_executed"

    ESIGN_CONSENT_GRANTED = "esign.consent_granted"

    SIGNATURE_APPLIED = "signature.applied"
    SIGNATURE_INVALIDATED = "signature.invalidated"
    SIGNATURE_REQUESTED = "signature.requested"

    COMPLETED_COPY_DELIVERED = "completed_copy.delivered"

    MATTER_ACTIVATION_AUTHORIZED = "matter.activation_authorized"
    MATTER_ACTIVATED = "matter.activated"

    CANDIDATE_SUBMITTED_FOR_REPRESENTATION_REVIEW = "candidate.submitted_for_representation_review"


CANONICAL_EVENTS: set[EventType] = {
    EventType.CONFLICT_SEARCH_STARTED,
    EventType.CONFLICT_CANDIDATE_DETECTED,
    EventType.CONFLICT_REVIEW_REQUESTED,
    EventType.CONFLICT_CLEARED_BY_ATTORNEY,
    EventType.CONFLICT_HOLD_APPLIED,
    EventType.REPRESENTATION_APPROVED_BY_ATTORNEY,
    EventType.REPRESENTATION_DECLINED_BY_ATTORNEY,
    EventType.ENGAGEMENT_WORKFLOW_STARTED,
    EventType.TEMPLATE_RESOLVED,
    EventType.PACKAGE_GENERATED,
    EventType.PACKAGE_DELIVERY_AUTHORIZED,
    EventType.PACKAGE_DELIVERED,
    EventType.ESIGN_CONSENT_GRANTED,
    EventType.ENGAGEMENT_QUESTION_RECEIVED,
    EventType.ENGAGEMENT_QUESTION_ESCALATED,
    EventType.SIGNATURE_APPLIED,
    EventType.SIGNATURE_INVALIDATED,
    EventType.PACKAGE_FULLY_EXECUTED,
    EventType.COMPLETED_COPY_DELIVERED,
    EventType.MATTER_ACTIVATION_AUTHORIZED,
    EventType.MATTER_ACTIVATED,
    EventType.ENGAGEMENT_EXPIRED,
}

EVENT_SCHEMA_VERSIONS: dict[EventType, str] = dict.fromkeys(EventType, "1.0.1")
