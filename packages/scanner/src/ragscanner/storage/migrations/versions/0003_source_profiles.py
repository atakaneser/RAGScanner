"""Add non-secret source profiles and local setup preferences.

Revision ID: 0003_source_profiles
Revises: 0002_durable_jobs
Create Date: 2026-07-16
"""

from collections.abc import Sequence

from alembic import op

from ragscanner.storage.schema import app_settings, source_profiles

revision: str = "0003_source_profiles"
down_revision: str | None = "0002_durable_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    source_profiles.create(op.get_bind())
    app_settings.create(op.get_bind())


def downgrade() -> None:
    app_settings.drop(op.get_bind())
    source_profiles.drop(op.get_bind())
