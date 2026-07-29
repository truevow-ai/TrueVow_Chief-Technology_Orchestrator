"""initial retainer schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS retainer")

    op.execute("""
        CREATE TYPE retainer.engagement_state AS ENUM (
            'NOT_STARTED','ATTORNEY_APPROVAL_RECORDED','CONFLICT_REVIEW_PENDING','CONFLICT_HOLD',
            'PACKAGE_PREPARATION','DELIVERY_AUTHORIZED','DELIVERED','CLIENT_REVIEW','SIGNATURE_PENDING',
            'FULLY_EXECUTED','ACTIVATION_PENDING','ACTIVATED','DECLINED_OR_EXPIRED'
        )
    """)

    op.create_table(
        "retainer_workflows",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("matter_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="NOT_STARTED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("representation_decision_id", sa.Uuid(), nullable=True),
        sa.Column("conflict_review_id", sa.Uuid(), nullable=True),
        sa.Column("engagement_package_id", sa.Uuid(), nullable=True),
        sa.Column("activation_checklist_id", sa.Uuid(), nullable=True),
        sa.Column("activated_matter_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "matter_candidate_id", "candidate_version"),
        sa.CheckConstraint("version > 0"),
        schema="retainer",
    )
    op.create_index("ix_retainer_workflows_tenant_state", "retainer_workflows", ["tenant_id", "state"], schema="retainer")

    op.create_table(
        "representation_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("matter_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("attorney_actor_id", sa.Text(), nullable=False),
        sa.Column("authority_record_id", sa.Uuid(), nullable=False),
        sa.Column("supersedes_id", sa.Uuid(), sa.ForeignKey("retainer.representation_decisions.id"), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="retainer",
    )
    op.create_index("ix_rep_decisions_tenant_candidate", "representation_decisions", ["tenant_id", "matter_candidate_id"], schema="retainer")

    op.create_table(
        "conflict_searches",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("party_set_version", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("scope_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )

    op.create_table(
        "conflict_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_searches.id"), nullable=False),
        sa.Column("matched_party_ref", sa.Text(), nullable=False),
        sa.Column("match_basis_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("rule_or_score", sa.Text(), nullable=True),
        sa.Column("disposition", sa.String(), nullable=False, server_default="UNREVIEWED"),
        schema="retainer",
    )

    op.create_table(
        "conflict_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_searches.id"), nullable=False),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("attorney_actor_id", sa.Text(), nullable=False),
        sa.Column("authority_record_id", sa.Uuid(), nullable=False),
        sa.Column("rationale_ref", sa.Text(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        schema="retainer",
    )

    op.create_table(
        "candidate_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("review_state", sa.String(), nullable=False, server_default="UNREVIEWED"),
        sa.Column("prepared_by_actor_id", sa.Text(), nullable=True),
        sa.Column("prepared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attorney_assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsible_attorney_actor_id", sa.Text(), nullable=True),
        sa.Column("candidate_version_reviewed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="retainer",
    )
    op.create_index("ix_candidate_reviews_tenant", "candidate_reviews", ["tenant_id"], schema="retainer")

    op.create_table(
        "review_work_items",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("work_type", sa.String(), nullable=False),
        sa.Column("assigned_actor_id", sa.Text(), nullable=True),
        sa.Column("state", sa.String(), nullable=False, server_default="PENDING"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="retainer",
    )
    op.create_index("ix_review_work_items_tenant", "review_work_items", ["tenant_id"], schema="retainer")

    op.create_table(
        "missing_information_requests",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("requested_by_actor_id", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("fields_required", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("state", sa.String(), nullable=False, server_default="OPEN"),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )
    op.create_index("ix_missing_info_requests_tenant", "missing_information_requests", ["tenant_id"], schema="retainer")

    op.create_table(
        "authority_evaluations",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("authority_class", sa.String(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("policy_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="retainer",
    )
    op.create_index("ix_auth_evaluations_tenant", "authority_evaluations", ["tenant_id"], schema="retainer")

    op.create_table(
        "configuration_resolution_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), sa.ForeignKey("retainer.retainer_workflows.id"), nullable=False),
        sa.Column("resolution_type", sa.Text(), nullable=False),
        sa.Column("policy_version_id", sa.Uuid(), nullable=True),
        sa.Column("jurisdiction_profile_version_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="retainer",
    )
    op.create_index("ix_config_res_snapshots_tenant", "configuration_resolution_snapshots", ["tenant_id"], schema="retainer")

    op.create_table(
        "retainer_audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_id", sa.Text(), nullable=False),
        sa.Column("actor_role", sa.Text(), nullable=True),
        sa.Column("authority_class", sa.String(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema="retainer",
    )
    op.create_index("ix_audit_events_tenant", "retainer_audit_events", ["tenant_id"], schema="retainer")

    op.create_table(
        "retainer_inbox_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        schema="retainer",
    )
    op.create_index("ix_retainer_inbox_tenant_received", "retainer_inbox_events", ["tenant_id", "received_at"], schema="retainer")

    op.create_table(
        "retainer_outbox_events",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )
    op.create_index("ix_retainer_outbox_unpublished", "retainer_outbox_events", ["created_at"], postgresql_where=sa.text("published_at IS NULL"), schema="retainer")

    op.create_table(
        "retainer_idempotency_keys",
        sa.Column("tenant_id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False, primary_key=True),
        sa.Column("command_type", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("result_ref", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )

    op.create_table(
        "retainer_projection_checkpoints",
        sa.Column("projection_name", sa.Text(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=False, primary_key=True),
        sa.Column("last_event_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rebuilt_at", sa.DateTime(timezone=True), nullable=True),
        schema="retainer",
    )


def downgrade() -> None:
    tables = [
        "retainer_projection_checkpoints", "retainer_idempotency_keys",
        "retainer_outbox_events", "retainer_inbox_events", "retainer_audit_events",
        "configuration_resolution_snapshots", "authority_evaluations",
        "missing_information_requests", "review_work_items", "candidate_reviews",
        "conflict_reviews", "conflict_candidates", "conflict_searches",
        "representation_decisions", "retainer_workflows",
    ]
    for t in tables:
        op.execute(f"DROP TABLE IF EXISTS retainer.{t} CASCADE")
    op.execute("DROP TYPE IF EXISTS retainer.engagement_state")
    op.execute("DROP SCHEMA IF EXISTS retainer")
