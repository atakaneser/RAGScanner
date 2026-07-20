"""Add recurring scan schedules.

Revision ID: 0005_scan_schedules
Revises: 0004_public_ids
Create Date: 2026-07-20
"""

from collections.abc import Sequence

from alembic import op

from ragscanner.storage.schema import schedules

revision: str = "0005_scan_schedules"
down_revision: str | None = "0004_public_ids"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    schedules.create(op.get_bind())


def downgrade() -> None:
    schedules.drop(op.get_bind())
