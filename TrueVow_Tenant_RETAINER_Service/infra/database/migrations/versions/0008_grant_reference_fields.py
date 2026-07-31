"""v1.1 Addendum — Add canonical grant reference fields to ClientPortalAccess.

Revision ID: 0008_grant_reference_fields
Revises: 0007_scopes_and_invitations
Create Date: 2026-07-30
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_grant_reference_fields"
down_revision: str | None = "0007_scopes_and_invitations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("client_portal_access", sa.Column("canonical_access_grant_id", sa.Uuid(), nullable=True), schema="retainer")
    op.add_column("client_portal_access", sa.Column("source_event_id", sa.Uuid(), nullable=True), schema="retainer")
    op.add_column("client_portal_access", sa.Column("last_synchronized_at", sa.DateTime(timezone=True), nullable=True), schema="retainer")


def downgrade() -> None:
    op.drop_column("client_portal_access", "last_synchronized_at", schema="retainer")
    op.drop_column("client_portal_access", "source_event_id", schema="retainer")
    op.drop_column("client_portal_access", "canonical_access_grant_id", schema="retainer")
