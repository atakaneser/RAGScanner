"""Create execution history and finding occurrence tables.

Revision ID: 0001_scan_history
Revises:
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op

from ragscanner.storage.schema import finding_occurrences, findings, scans

revision: str = "0001_scan_history"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    scans.create(op.get_bind())
    findings.create(op.get_bind())
    finding_occurrences.create(op.get_bind())


def downgrade() -> None:
    finding_occurrences.drop(op.get_bind())
    findings.drop(op.get_bind())
    scans.drop(op.get_bind())
