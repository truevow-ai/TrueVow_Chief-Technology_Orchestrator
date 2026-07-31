"""v1.1 Addendum — Add scopes to ClientPortalAccess, add PortalInvitation table.

Revision ID: 0007_scopes_and_invitations
Revises: 0006_v11_addendum
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_scopes_and_invitations"
down_revision: str | None = "0006_v11_addendum"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("client_portal_access", sa.Column("scopes", sa.JSON(), nullable=False, server_default="[]"), schema="retainer")
    op.alter_column("client_portal_access", "state", server_default="PENDING_INVITATION", existing_type=sa.String(), schema="retainer")

    op.create_table(
        "portal_invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("access_grant_id", sa.Uuid(), sa.ForeignKey("retainer.client_portal_access.id"), nullable=False),
        sa.Column("invitation_token_hash", sa.String(64), nullable=False),
        sa.Column("channel", sa.String(), nullable=False, server_default="email"),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column("state", sa.String(), nullable=False, server_default="ISSUED"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invitation_token_hash"),
        schema="retainer",
    )
    op.create_index("ix_portal_invitations_tenant_id", "portal_invitations", ["tenant_id"], schema="retainer")


def downgrade() -> None:
    op.drop_table("portal_invitations", schema="retainer")
    op.drop_column("client_portal_access", "scopes", schema="retainer")
