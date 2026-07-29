from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator

from retainer_contracts.authority import AuthorityClass


class EventEnvelope(BaseModel):
    event_id: uuid.UUID
    event_type: str = Field(pattern=r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
    occurred_at: datetime
    recorded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: uuid.UUID
    aggregate_type: str = Field(min_length=1)
    aggregate_id: uuid.UUID
    aggregate_version: int = Field(ge=1)
    actor_type: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    authority_class: AuthorityClass
    authority_record_id: uuid.UUID | None = None
    policy_version_id: uuid.UUID | None = None
    correlation_id: uuid.UUID
    causation_id: uuid.UUID | None = None
    payload: dict = Field(default_factory=dict)
    sensitivity_class: str = Field(min_length=1)
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")

    @field_validator("sensitivity_class")
    @classmethod
    def sensitivity_class_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("sensitivity_class must not be empty")
        return v

    model_config = {"extra": "forbid"}
