"""Create the durable job queue.

Revision ID: 0002_durable_jobs
Revises: 0001_scan_history
Create Date: 2026-07-14
"""

from collections.abc import Sequence

from alembic import op

from ragscanner.storage.schema import jobs

revision: str = "0002_durable_jobs"
down_revision: str | None = "0001_scan_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    jobs.create(op.get_bind())


def downgrade() -> None:
    jobs.drop(op.get_bind())
