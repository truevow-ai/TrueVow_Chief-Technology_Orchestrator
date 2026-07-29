-- TrueVow RETAINER operational schema seed v1.0
-- Shared canonical records are referenced by ID and remain owned by their shared/canonical services.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE SCHEMA IF NOT EXISTS retainer;

CREATE TYPE retainer.engagement_state AS ENUM (
  'NOT_STARTED','ATTORNEY_APPROVAL_RECORDED','CONFLICT_REVIEW_PENDING','CONFLICT_HOLD',
  'PACKAGE_PREPARATION','DELIVERY_AUTHORIZED','DELIVERED','CLIENT_REVIEW','SIGNATURE_PENDING',
  'FULLY_EXECUTED','ACTIVATION_PENDING','ACTIVATED','DECLINED_OR_EXPIRED'
);

CREATE TABLE retainer.retainer_workflows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  matter_candidate_id uuid NOT NULL,
  candidate_version integer NOT NULL,
  state retainer.engagement_state NOT NULL DEFAULT 'NOT_STARTED',
  version integer NOT NULL DEFAULT 1,
  representation_decision_id uuid,
  conflict_review_id uuid,
  engagement_package_id uuid,
  activation_checklist_id uuid,
  activated_matter_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, matter_candidate_id, candidate_version),
  CHECK (version > 0)
);
CREATE INDEX ix_retainer_workflows_tenant_state
  ON retainer.retainer_workflows(tenant_id, state);

CREATE TABLE retainer.representation_decisions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  matter_candidate_id uuid NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('APPROVED','DECLINED','DEFERRED')),
  scope_json jsonb NOT NULL,
  attorney_actor_id text NOT NULL,
  authority_record_id uuid NOT NULL,
  supersedes_id uuid REFERENCES retainer.representation_decisions(id),
  decided_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_rep_decisions_tenant_candidate
  ON retainer.representation_decisions(tenant_id, matter_candidate_id);

CREATE TABLE retainer.conflict_searches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  workflow_id uuid NOT NULL REFERENCES retainer.retainer_workflows(id),
  party_set_version integer NOT NULL,
  algorithm_version text NOT NULL,
  scope_json jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('PENDING','COMPLETED','FAILED')),
  started_at timestamptz NOT NULL,
  completed_at timestamptz
);
CREATE TABLE retainer.conflict_candidates (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  search_id uuid NOT NULL REFERENCES retainer.conflict_searches(id),
  matched_party_ref text NOT NULL,
  match_basis_json jsonb NOT NULL,
  rule_or_score text,
  disposition text NOT NULL DEFAULT 'UNREVIEWED'
);
CREATE TABLE retainer.conflict_reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  search_id uuid NOT NULL REFERENCES retainer.conflict_searches(id),
  outcome text NOT NULL CHECK (outcome IN ('CLEARED','HOLD','APPROVED_EXCEPTION')),
  attorney_actor_id text NOT NULL,
  authority_record_id uuid NOT NULL,
  rationale_ref text,
  decided_at timestamptz NOT NULL
);

CREATE TABLE retainer.template_resolutions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  workflow_id uuid NOT NULL REFERENCES retainer.retainer_workflows(id),
  template_definition_id uuid NOT NULL,
  template_version text NOT NULL,
  template_hash char(64) NOT NULL,
  policy_version_id uuid NOT NULL,
  inputs_json jsonb NOT NULL,
  resolved_at timestamptz NOT NULL,
  UNIQUE(tenant_id, workflow_id, template_definition_id, template_version)
);
CREATE TABLE retainer.engagement_packages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  workflow_id uuid NOT NULL REFERENCES retainer.retainer_workflows(id),
  template_resolution_id uuid NOT NULL REFERENCES retainer.template_resolutions(id),
  manifest_json jsonb NOT NULL,
  status text NOT NULL CHECK (status IN ('DRAFT','LOCKED','DELIVERED','FULLY_EXECUTED','SUPERSEDED','VOID')),
  package_hash char(64) NOT NULL,
  generated_at timestamptz NOT NULL,
  locked_at timestamptz
);
CREATE TABLE retainer.package_documents (
  tenant_id uuid NOT NULL,
  package_id uuid NOT NULL REFERENCES retainer.engagement_packages(id),
  document_version_id uuid NOT NULL,
  document_role text NOT NULL,
  required boolean NOT NULL DEFAULT true,
  sequence integer NOT NULL,
  document_hash char(64) NOT NULL,
  PRIMARY KEY(package_id, document_version_id)
);

CREATE TABLE retainer.engagement_questions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  workflow_id uuid NOT NULL REFERENCES retainer.retainer_workflows(id),
  document_version_id uuid,
  page_or_clause_ref text,
  question_text text NOT NULL,
  classification text NOT NULL CHECK (classification IN ('LOGISTICAL','LEGAL_OR_UNCERTAIN')),
  state text NOT NULL CHECK (state IN ('RECEIVED','ESCALATED','ANSWERED','CLOSED')),
  submitted_by_actor_id text NOT NULL,
  assigned_actor_id text,
  response_ref text,
  created_at timestamptz NOT NULL DEFAULT now(),
  answered_at timestamptz
);

CREATE TABLE retainer.signature_ceremonies (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  package_id uuid NOT NULL REFERENCES retainer.engagement_packages(id),
  provider_type text NOT NULL,
  provider_ref text,
  state text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz
);
CREATE TABLE retainer.signer_requirements (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  ceremony_id uuid NOT NULL REFERENCES retainer.signature_ceremonies(id),
  party_role_id uuid NOT NULL,
  signer_role text NOT NULL,
  authority_scope text,
  required boolean NOT NULL DEFAULT true
);
CREATE TABLE retainer.signature_evidence_refs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  ceremony_id uuid NOT NULL REFERENCES retainer.signature_ceremonies(id),
  signer_requirement_id uuid NOT NULL REFERENCES retainer.signer_requirements(id),
  shared_signature_evidence_id uuid NOT NULL,
  validity_state text NOT NULL CHECK (validity_state IN ('VALID','INVALID','SUPERSEDED')),
  UNIQUE(tenant_id, shared_signature_evidence_id)
);

CREATE TABLE retainer.activation_checklists (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  workflow_id uuid NOT NULL REFERENCES retainer.retainer_workflows(id),
  policy_version_id uuid NOT NULL,
  state text NOT NULL CHECK (state IN ('PENDING','PASS','FAIL','STALE')),
  version integer NOT NULL DEFAULT 1
);
CREATE TABLE retainer.activation_checklist_items (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  checklist_id uuid NOT NULL REFERENCES retainer.activation_checklists(id),
  control_id text NOT NULL,
  required boolean NOT NULL DEFAULT true,
  result text NOT NULL CHECK (result IN ('PENDING','PASS','FAIL','WAIVED')),
  evidence_refs_json jsonb NOT NULL DEFAULT '[]'::jsonb,
  evaluated_at timestamptz,
  UNIQUE(checklist_id, control_id)
);

CREATE TABLE retainer.reminder_schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  workflow_id uuid NOT NULL REFERENCES retainer.retainer_workflows(id),
  policy_version_id uuid NOT NULL,
  next_due_at timestamptz,
  max_attempts integer NOT NULL,
  state text NOT NULL CHECK (state IN ('ACTIVE','PAUSED','COMPLETED','SUPPRESSED','EXPIRED'))
);
CREATE TABLE retainer.reminder_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id uuid NOT NULL,
  schedule_id uuid NOT NULL REFERENCES retainer.reminder_schedules(id),
  communication_id uuid,
  attempt_no integer NOT NULL,
  result text NOT NULL,
  attempted_at timestamptz NOT NULL,
  UNIQUE(schedule_id, attempt_no)
);

CREATE TABLE retainer.retainer_inbox_events (
  event_id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  event_type text NOT NULL,
  schema_version text NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  processed_at timestamptz,
  payload_hash char(64) NOT NULL,
  result text,
  error_code text
);
CREATE INDEX ix_retainer_inbox_tenant_received
  ON retainer.retainer_inbox_events(tenant_id, received_at);

CREATE TABLE retainer.retainer_outbox_events (
  event_id uuid PRIMARY KEY,
  tenant_id uuid NOT NULL,
  aggregate_id uuid NOT NULL,
  event_type text NOT NULL,
  schema_version text NOT NULL,
  payload_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);
CREATE INDEX ix_retainer_outbox_unpublished
  ON retainer.retainer_outbox_events(created_at) WHERE published_at IS NULL;

CREATE TABLE retainer.retainer_idempotency_keys (
  tenant_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  command_type text NOT NULL,
  request_hash char(64) NOT NULL,
  result_ref text,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz,
  PRIMARY KEY(tenant_id, idempotency_key)
);
CREATE TABLE retainer.retainer_projection_checkpoints (
  projection_name text NOT NULL,
  tenant_id uuid NOT NULL,
  last_event_position bigint NOT NULL DEFAULT 0,
  rebuilt_at timestamptz,
  PRIMARY KEY(projection_name, tenant_id)
);

-- Apply platform-standard RLS policies and tenant-context enforcement to every table.
