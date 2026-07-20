"""Add stable human-readable identifiers for jobs and reports.

Revision ID: 0004_public_ids
Revises: 0003_source_profiles
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_public_ids"
down_revision: str | None = "0003_source_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    job_columns = {column["name"] for column in inspector.get_columns("jobs")}
    scan_columns = {column["name"] for column in inspector.get_columns("scans")}
    if "display_id" not in job_columns:
        op.add_column("jobs", sa.Column("display_id", sa.String(length=32), nullable=True))
    if "display_id" not in scan_columns:
        op.add_column("scans", sa.Column("display_id", sa.String(length=32), nullable=True))
    jobs = connection.execute(sa.text("SELECT id FROM jobs ORDER BY created_at, id")).fetchall()
    for number, row in enumerate(jobs, start=1):
        connection.execute(
            sa.text("UPDATE jobs SET display_id = :display_id WHERE id = :id"),
            {"display_id": f"RAGSCN-{number:04d}", "id": row.id},
        )
    scans = connection.execute(sa.text("SELECT id FROM scans ORDER BY created_at, id")).fetchall()
    for number, row in enumerate(scans, start=1):
        connection.execute(
            sa.text("UPDATE scans SET display_id = :display_id WHERE id = :id"),
            {"display_id": f"RAGREP-{number:04d}", "id": row.id},
        )
    indexes = {index["name"] for index in inspector.get_indexes("jobs")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("jobs")}
    if "uq_jobs_display_id" not in indexes | constraints:
        op.create_index("uq_jobs_display_id", "jobs", ["display_id"], unique=True)
    indexes = {index["name"] for index in inspector.get_indexes("scans")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("scans")}
    if "uq_scans_display_id" not in indexes | constraints:
        op.create_index("uq_scans_display_id", "scans", ["display_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_scans_display_id", table_name="scans")
    op.drop_index("uq_jobs_display_id", table_name="jobs")
    op.drop_column("scans", "display_id")
    op.drop_column("jobs", "display_id")
