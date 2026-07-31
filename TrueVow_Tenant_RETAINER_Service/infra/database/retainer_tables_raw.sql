BEGIN;

CREATE TABLE retainer.alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001_initial

CREATE SCHEMA IF NOT EXISTS retainer;

CREATE TYPE retainer.engagement_state AS ENUM (
            'NOT_STARTED','ATTORNEY_APPROVAL_RECORDED','CONFLICT_REVIEW_PENDING','CONFLICT_HOLD',
            'PACKAGE_PREPARATION','DELIVERY_AUTHORIZED','DELIVERED','CLIENT_REVIEW','SIGNATURE_PENDING',
            'FULLY_EXECUTED','ACTIVATION_PENDING','ACTIVATED','DECLINED_OR_EXPIRED'
        );

CREATE TABLE retainer.retainer_workflows (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    matter_candidate_id UUID NOT NULL, 
    candidate_version INTEGER NOT NULL, 
    state VARCHAR DEFAULT 'NOT_STARTED' NOT NULL, 
    version INTEGER DEFAULT '1' NOT NULL, 
    representation_decision_id UUID, 
    conflict_review_id UUID, 
    engagement_package_id UUID, 
    activation_checklist_id UUID, 
    activated_matter_id UUID, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    UNIQUE (tenant_id, matter_candidate_id, candidate_version), 
    CHECK (version > 0)
);

CREATE INDEX ix_retainer_workflows_tenant_state ON retainer.retainer_workflows (tenant_id, state);

CREATE TABLE retainer.representation_decisions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    matter_candidate_id UUID NOT NULL, 
    outcome VARCHAR NOT NULL, 
    scope_json JSON DEFAULT '{}' NOT NULL, 
    attorney_actor_id TEXT NOT NULL, 
    authority_record_id UUID NOT NULL, 
    supersedes_id UUID, 
    decided_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(supersedes_id) REFERENCES retainer.representation_decisions (id)
);

CREATE INDEX ix_rep_decisions_tenant_candidate ON retainer.representation_decisions (tenant_id, matter_candidate_id);

CREATE TABLE retainer.conflict_searches (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    party_set_version INTEGER NOT NULL, 
    algorithm_version TEXT NOT NULL, 
    scope_json JSON DEFAULT '{}' NOT NULL, 
    status VARCHAR DEFAULT 'PENDING' NOT NULL, 
    started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE TABLE retainer.conflict_candidates (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    search_id UUID NOT NULL, 
    matched_party_ref TEXT NOT NULL, 
    match_basis_json JSON DEFAULT '{}' NOT NULL, 
    rule_or_score TEXT, 
    disposition VARCHAR DEFAULT 'UNREVIEWED' NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(search_id) REFERENCES retainer.conflict_searches (id)
);

CREATE TABLE retainer.conflict_reviews (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    search_id UUID NOT NULL, 
    outcome VARCHAR NOT NULL, 
    attorney_actor_id TEXT NOT NULL, 
    authority_record_id UUID NOT NULL, 
    rationale_ref TEXT, 
    decided_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(search_id) REFERENCES retainer.conflict_searches (id)
);

CREATE TABLE retainer.candidate_reviews (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    review_state VARCHAR DEFAULT 'UNREVIEWED' NOT NULL, 
    prepared_by_actor_id TEXT, 
    prepared_at TIMESTAMP WITH TIME ZONE, 
    attorney_assigned_at TIMESTAMP WITH TIME ZONE, 
    responsible_attorney_actor_id TEXT, 
    candidate_version_reviewed INTEGER, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE INDEX ix_candidate_reviews_tenant ON retainer.candidate_reviews (tenant_id);

CREATE TABLE retainer.review_work_items (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    work_type VARCHAR NOT NULL, 
    assigned_actor_id TEXT, 
    state VARCHAR DEFAULT 'PENDING' NOT NULL, 
    due_at TIMESTAMP WITH TIME ZONE, 
    completed_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE INDEX ix_review_work_items_tenant ON retainer.review_work_items (tenant_id);

CREATE TABLE retainer.missing_information_requests (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    requested_by_actor_id TEXT NOT NULL, 
    reason TEXT NOT NULL, 
    fields_required JSON DEFAULT '[]' NOT NULL, 
    state VARCHAR DEFAULT 'OPEN' NOT NULL, 
    requested_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    resolved_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE INDEX ix_missing_info_requests_tenant ON retainer.missing_information_requests (tenant_id);

CREATE TABLE retainer.authority_evaluations (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID, 
    action TEXT NOT NULL, 
    actor_id TEXT NOT NULL, 
    authority_class VARCHAR NOT NULL, 
    result VARCHAR NOT NULL, 
    policy_snapshot_id UUID, 
    reason TEXT, 
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE INDEX ix_auth_evaluations_tenant ON retainer.authority_evaluations (tenant_id);

CREATE TABLE retainer.configuration_resolution_snapshots (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    resolution_type TEXT NOT NULL, 
    policy_version_id UUID, 
    jurisdiction_profile_version_id UUID, 
    resolution_data JSON DEFAULT '{}' NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE INDEX ix_config_res_snapshots_tenant ON retainer.configuration_resolution_snapshots (tenant_id);

CREATE TABLE retainer.retainer_audit_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID, 
    event_type TEXT NOT NULL, 
    actor_id TEXT NOT NULL, 
    actor_role TEXT, 
    authority_class VARCHAR, 
    action TEXT NOT NULL, 
    result VARCHAR NOT NULL, 
    details JSON DEFAULT '{}' NOT NULL, 
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    PRIMARY KEY (id)
);

CREATE INDEX ix_audit_events_tenant ON retainer.retainer_audit_events (tenant_id);

CREATE TABLE retainer.retainer_inbox_events (
    event_id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    event_type TEXT NOT NULL, 
    schema_version TEXT NOT NULL, 
    received_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    processed_at TIMESTAMP WITH TIME ZONE, 
    payload_hash VARCHAR(64) NOT NULL, 
    result TEXT, 
    error_code TEXT, 
    PRIMARY KEY (event_id)
);

CREATE INDEX ix_retainer_inbox_tenant_received ON retainer.retainer_inbox_events (tenant_id, received_at);

CREATE TABLE retainer.retainer_outbox_events (
    event_id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    aggregate_id UUID NOT NULL, 
    event_type TEXT NOT NULL, 
    schema_version TEXT NOT NULL, 
    payload_json JSON DEFAULT '{}' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    published_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (event_id)
);

CREATE INDEX ix_retainer_outbox_unpublished ON retainer.retainer_outbox_events (created_at) WHERE published_at IS NULL;

CREATE TABLE retainer.retainer_idempotency_keys (
    tenant_id UUID NOT NULL, 
    idempotency_key TEXT NOT NULL, 
    command_type TEXT NOT NULL, 
    request_hash VARCHAR(64) NOT NULL, 
    result_ref TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    expires_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (tenant_id, idempotency_key)
);

CREATE TABLE retainer.retainer_projection_checkpoints (
    projection_name TEXT NOT NULL, 
    tenant_id UUID NOT NULL, 
    last_event_position INTEGER DEFAULT '0' NOT NULL, 
    rebuilt_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (projection_name, tenant_id)
);

INSERT INTO retainer.alembic_version (version_num) VALUES ('0001_initial') RETURNING retainer.alembic_version.version_num;

-- Running upgrade 0001_initial -> 0002_remaining_tables

CREATE TABLE retainer.template_resolutions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    template_definition_id UUID NOT NULL, 
    template_version TEXT NOT NULL, 
    template_hash VARCHAR(64) NOT NULL, 
    policy_version_id UUID NOT NULL, 
    inputs_json JSON DEFAULT '{}' NOT NULL, 
    resolved_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (tenant_id, workflow_id, template_definition_id, template_version), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE TABLE retainer.engagement_packages (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    template_resolution_id UUID NOT NULL, 
    manifest_json JSON DEFAULT '{}' NOT NULL, 
    status VARCHAR DEFAULT 'DRAFT' NOT NULL, 
    package_hash VARCHAR(64) NOT NULL, 
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    locked_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id), 
    FOREIGN KEY(template_resolution_id) REFERENCES retainer.template_resolutions (id)
);

CREATE TABLE retainer.package_documents (
    tenant_id UUID NOT NULL, 
    package_id UUID NOT NULL, 
    document_version_id UUID NOT NULL, 
    document_role TEXT NOT NULL, 
    required BOOLEAN DEFAULT true NOT NULL, 
    sequence INTEGER NOT NULL, 
    document_hash VARCHAR(64) NOT NULL, 
    PRIMARY KEY (tenant_id, package_id, document_version_id), 
    FOREIGN KEY(package_id) REFERENCES retainer.engagement_packages (id)
);

CREATE TABLE retainer.engagement_questions (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    document_version_id UUID, 
    page_or_clause_ref TEXT, 
    question_text TEXT NOT NULL, 
    classification VARCHAR NOT NULL, 
    state VARCHAR DEFAULT 'RECEIVED' NOT NULL, 
    submitted_by_actor_id TEXT NOT NULL, 
    assigned_actor_id TEXT, 
    response_ref TEXT, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    answered_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE TABLE retainer.signature_ceremonies (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    package_id UUID NOT NULL, 
    provider_type TEXT NOT NULL, 
    provider_ref TEXT, 
    state VARCHAR NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(), 
    expires_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(package_id) REFERENCES retainer.engagement_packages (id)
);

CREATE TABLE retainer.signer_requirements (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    ceremony_id UUID NOT NULL, 
    party_role_id UUID NOT NULL, 
    signer_role TEXT NOT NULL, 
    authority_scope TEXT, 
    required BOOLEAN DEFAULT true NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ceremony_id) REFERENCES retainer.signature_ceremonies (id)
);

CREATE TABLE retainer.signature_evidence_refs (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    ceremony_id UUID NOT NULL, 
    signer_requirement_id UUID NOT NULL, 
    shared_signature_evidence_id UUID NOT NULL, 
    validity_state VARCHAR DEFAULT 'VALID' NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (tenant_id, shared_signature_evidence_id), 
    FOREIGN KEY(ceremony_id) REFERENCES retainer.signature_ceremonies (id), 
    FOREIGN KEY(signer_requirement_id) REFERENCES retainer.signer_requirements (id)
);

CREATE TABLE retainer.activation_checklists (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    policy_version_id UUID NOT NULL, 
    state VARCHAR DEFAULT 'PENDING' NOT NULL, 
    version INTEGER DEFAULT '1' NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE TABLE retainer.activation_checklist_items (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    checklist_id UUID NOT NULL, 
    control_id TEXT NOT NULL, 
    required BOOLEAN DEFAULT true NOT NULL, 
    result VARCHAR DEFAULT 'PENDING' NOT NULL, 
    evidence_refs_json JSON DEFAULT '[]' NOT NULL, 
    evaluated_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (checklist_id, control_id), 
    FOREIGN KEY(checklist_id) REFERENCES retainer.activation_checklists (id)
);

CREATE TABLE retainer.reminder_schedules (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    policy_version_id UUID NOT NULL, 
    next_due_at TIMESTAMP WITH TIME ZONE, 
    max_attempts INTEGER NOT NULL, 
    state VARCHAR DEFAULT 'ACTIVE' NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE TABLE retainer.reminder_attempts (
    id UUID DEFAULT gen_random_uuid() NOT NULL, 
    tenant_id UUID NOT NULL, 
    schedule_id UUID NOT NULL, 
    communication_id UUID, 
    attempt_no INTEGER NOT NULL, 
    result TEXT NOT NULL, 
    attempted_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (schedule_id, attempt_no), 
    FOREIGN KEY(schedule_id) REFERENCES retainer.reminder_schedules (id)
);

UPDATE retainer.alembic_version SET version_num='0002_remaining_tables' WHERE retainer.alembic_version.version_num = '0001_initial';

-- Running upgrade 0002_remaining_tables -> 0003_conflict_search_extensions

CREATE TABLE retainer.conflict_search_parties (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    search_id UUID NOT NULL, 
    party_type VARCHAR NOT NULL, 
    canonical_ref UUID NOT NULL, 
    legal_name TEXT NOT NULL, 
    prior_names JSON DEFAULT '[]' NOT NULL, 
    aliases JSON DEFAULT '[]' NOT NULL, 
    normalized_name TEXT, 
    date_of_birth TEXT, 
    organization_identifiers JSON DEFAULT '[]' NOT NULL, 
    relationship_to_candidate TEXT, 
    source TEXT, 
    confidence VARCHAR, 
    candidate_version INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (search_id, canonical_ref), 
    FOREIGN KEY(search_id) REFERENCES retainer.conflict_searches (id)
);

CREATE INDEX ix_conflict_search_parties_tenant_id ON retainer.conflict_search_parties (tenant_id);

CREATE TABLE retainer.conflict_search_sources (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    search_id UUID NOT NULL, 
    source_type VARCHAR NOT NULL, 
    source_identifier TEXT NOT NULL, 
    algorithm_version TEXT NOT NULL, 
    coverage_data JSON DEFAULT '{}' NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(search_id) REFERENCES retainer.conflict_searches (id)
);

CREATE INDEX ix_conflict_search_sources_tenant_id ON retainer.conflict_search_sources (tenant_id);

CREATE TABLE retainer.conflict_holds (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    search_id UUID NOT NULL, 
    attorney_actor_id TEXT NOT NULL, 
    authority_record_id UUID NOT NULL, 
    reason TEXT NOT NULL, 
    affected_candidate_id UUID, 
    supporting_evidence JSON DEFAULT '{}' NOT NULL, 
    required_followup TEXT, 
    review_owner TEXT, 
    policy_snapshot_id UUID, 
    held_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    released_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(search_id) REFERENCES retainer.conflict_searches (id), 
    FOREIGN KEY(affected_candidate_id) REFERENCES retainer.conflict_candidates (id)
);

CREATE INDEX ix_conflict_holds_tenant_id ON retainer.conflict_holds (tenant_id);

CREATE TABLE retainer.conflict_evidence_snapshots (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    search_id UUID NOT NULL, 
    snapshot_type VARCHAR NOT NULL, 
    party_set_hash VARCHAR(64) NOT NULL, 
    source_set_hash VARCHAR(64) NOT NULL, 
    candidate_version INTEGER NOT NULL, 
    policy_snapshot_id UUID, 
    snapshot_data JSON DEFAULT '{}' NOT NULL, 
    snapped_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(search_id) REFERENCES retainer.conflict_searches (id)
);

CREATE INDEX ix_conflict_evidence_snapshots_tenant_id ON retainer.conflict_evidence_snapshots (tenant_id);

UPDATE retainer.alembic_version SET version_num='0003_conflict_search_extensions' WHERE retainer.alembic_version.version_num = '0002_remaining_tables';

-- Running upgrade 0003_conflict_search_extensions -> 0004_template_package_tables

CREATE TABLE retainer.template_merge_fields (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    template_resolution_id UUID NOT NULL, 
    field_name TEXT NOT NULL, 
    field_value TEXT NOT NULL, 
    source VARCHAR NOT NULL, 
    validated BOOLEAN DEFAULT 'true' NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (template_resolution_id, field_name), 
    FOREIGN KEY(template_resolution_id) REFERENCES retainer.template_resolutions (id)
);

CREATE INDEX ix_template_merge_fields_tenant_id ON retainer.template_merge_fields (tenant_id);

CREATE TABLE retainer.package_preflight_results (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    package_id UUID NOT NULL, 
    control_id TEXT NOT NULL, 
    control_name TEXT NOT NULL, 
    passed BOOLEAN DEFAULT 'false' NOT NULL, 
    detail TEXT, 
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(package_id) REFERENCES retainer.engagement_packages (id)
);

CREATE INDEX ix_package_preflight_results_tenant_id ON retainer.package_preflight_results (tenant_id);

UPDATE retainer.alembic_version SET version_num='0004_template_package_tables' WHERE retainer.alembic_version.version_num = '0003_conflict_search_extensions';

-- Running upgrade 0004_template_package_tables -> 0005_portal_and_delivery

CREATE TABLE retainer.delivery_authorizations (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    package_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    authorized_by_actor_id TEXT NOT NULL, 
    authority_record_id UUID NOT NULL, 
    channel VARCHAR DEFAULT 'portal' NOT NULL, 
    recipient_verified BOOLEAN DEFAULT 'false' NOT NULL, 
    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(package_id) REFERENCES retainer.engagement_packages (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id)
);

CREATE INDEX ix_delivery_authorizations_tenant_id ON retainer.delivery_authorizations (tenant_id);

CREATE TABLE retainer.client_portal_access (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    access_token_hash VARCHAR(64) NOT NULL, 
    package_id UUID NOT NULL, 
    prospect_party_role_id UUID NOT NULL, 
    state VARCHAR DEFAULT 'ISSUED' NOT NULL, 
    issued_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE, 
    first_accessed_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    UNIQUE (access_token_hash), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id), 
    FOREIGN KEY(package_id) REFERENCES retainer.engagement_packages (id)
);

CREATE INDEX ix_client_portal_access_tenant_id ON retainer.client_portal_access (tenant_id);

CREATE TABLE retainer.esign_consent_records (
    id UUID NOT NULL, 
    tenant_id UUID NOT NULL, 
    workflow_id UUID NOT NULL, 
    portal_access_id UUID NOT NULL, 
    prospect_party_role_id UUID NOT NULL, 
    state VARCHAR DEFAULT 'GRANTED' NOT NULL, 
    ip_address TEXT, 
    user_agent TEXT, 
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    revoked_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(workflow_id) REFERENCES retainer.retainer_workflows (id), 
    FOREIGN KEY(portal_access_id) REFERENCES retainer.client_portal_access (id)
);

CREATE INDEX ix_esign_consent_records_tenant_id ON retainer.esign_consent_records (tenant_id);

UPDATE retainer.alembic_version SET version_num='0005_portal_and_delivery' WHERE retainer.alembic_version.version_num = '0004_template_package_tables';

COMMIT;

