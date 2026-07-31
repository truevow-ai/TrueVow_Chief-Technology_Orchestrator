"""Add ConflictSearchParty, ConflictSearchSource, ConflictHold, ConflictEvidenceSnapshot.

Revision ID: 0003_conflict_search_extensions
Revises: 0002_remaining_tables
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_conflict_search_extensions"
down_revision: str | None = "0002_remaining_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conflict_search_parties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_searches.id"), nullable=False),
        sa.Column("party_type", sa.String(), nullable=False),
        sa.Column("canonical_ref", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.Text(), nullable=False),
        sa.Column("prior_names", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("aliases", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("normalized_name", sa.Text(), nullable=True),
        sa.Column("date_of_birth", sa.Text(), nullable=True),
        sa.Column("organization_identifiers", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("relationship_to_candidate", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(), nullable=True),
        sa.Column("candidate_version", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("search_id", "canonical_ref"),
        schema="retainer",
    )
    op.create_index("ix_conflict_search_parties_tenant_id", "conflict_search_parties", ["tenant_id"], schema="retainer")

    op.create_table(
        "conflict_search_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_searches.id"), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_identifier", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("coverage_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_conflict_search_sources_tenant_id", "conflict_search_sources", ["tenant_id"], schema="retainer")

    op.create_table(
        "conflict_holds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_searches.id"), nullable=False),
        sa.Column("attorney_actor_id", sa.Text(), nullable=False),
        sa.Column("authority_record_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("affected_candidate_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_candidates.id"), nullable=True),
        sa.Column("supporting_evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("required_followup", sa.Text(), nullable=True),
        sa.Column("review_owner", sa.Text(), nullable=True),
        sa.Column("policy_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("held_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_conflict_holds_tenant_id", "conflict_holds", ["tenant_id"], schema="retainer")

    op.create_table(
        "conflict_evidence_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("search_id", sa.Uuid(), sa.ForeignKey("retainer.conflict_searches.id"), nullable=False),
        sa.Column("snapshot_type", sa.String(), nullable=False),
        sa.Column("party_set_hash", sa.String(64), nullable=False),
        sa.Column("source_set_hash", sa.String(64), nullable=False),
        sa.Column("candidate_version", sa.Integer(), nullable=False),
        sa.Column("policy_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("snapped_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_conflict_evidence_snapshots_tenant_id", "conflict_evidence_snapshots", ["tenant_id"], schema="retainer")


def downgrade() -> None:
    op.drop_table("conflict_evidence_snapshots", schema="retainer")
    op.drop_table("conflict_holds", schema="retainer")
    op.drop_table("conflict_search_sources", schema="retainer")
    op.drop_table("conflict_search_parties", schema="retainer")
