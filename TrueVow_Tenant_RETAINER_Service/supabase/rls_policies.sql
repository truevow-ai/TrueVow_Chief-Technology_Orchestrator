-- Supabase Row-Level Security policies for RETAINER service
-- All tables live in the `retainer` schema.
-- RLS enforces: tenant_id = current_setting('app.current_tenant_id')::uuid OR role = 'service'

-- Enable RLS on all retainer tables
ALTER TABLE retainer.retainer_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.representation_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.conflict_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.conflict_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.conflict_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.template_resolutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.engagement_packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.package_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.engagement_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.signature_ceremonies ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.signer_requirements ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.signature_evidence_refs ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.activation_checklists ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.activation_checklist_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.reminder_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.reminder_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.retainer_inbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.retainer_outbox_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.retainer_idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.retainer_projection_checkpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.candidate_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.review_work_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.missing_information_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.authority_evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.configuration_resolution_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE retainer.retainer_audit_events ENABLE ROW LEVEL SECURITY;

-- Tenant-scoped select policy (firm users see only their own tenant data)
CREATE POLICY tenant_isolation_select ON retainer.retainer_workflows
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_select ON retainer.representation_decisions
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_select ON retainer.candidate_reviews
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_select ON retainer.review_work_items
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_select ON retainer.retainer_audit_events
    FOR SELECT USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Tenant-scoped insert policy
CREATE POLICY tenant_isolation_insert ON retainer.retainer_workflows
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_insert ON retainer.representation_decisions
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_insert ON retainer.candidate_reviews
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_insert ON retainer.retainer_audit_events
    FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant_id')::uuid);
