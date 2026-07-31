"""Add TemplateMergeField and PackagePreflightResult tables.

Revision ID: 0004_template_package_tables
Revises: 0003_conflict_search_extensions
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_template_package_tables"
down_revision: str | None = "0003_conflict_search_extensions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "template_merge_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("template_resolution_id", sa.Uuid(), sa.ForeignKey("retainer.template_resolutions.id"), nullable=False),
        sa.Column("field_name", sa.Text(), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_resolution_id", "field_name"),
        schema="retainer",
    )
    op.create_index("ix_template_merge_fields_tenant_id", "template_merge_fields", ["tenant_id"], schema="retainer")

    op.create_table(
        "package_preflight_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("package_id", sa.Uuid(), sa.ForeignKey("retainer.engagement_packages.id"), nullable=False),
        sa.Column("control_id", sa.Text(), nullable=False),
        sa.Column("control_name", sa.Text(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        schema="retainer",
    )
    op.create_index("ix_package_preflight_results_tenant_id", "package_preflight_results", ["tenant_id"], schema="retainer")


def downgrade() -> None:
    op.drop_table("package_preflight_results", schema="retainer")
    op.drop_table("template_merge_fields", schema="retainer")
