"""Allow the implemented website and SharePoint source profile kinds.

Revision ID: 0007_remote_source_profile_kinds
Revises: 0006_source_profile_kinds
Create Date: 2026-07-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_remote_source_profile_kinds"
down_revision: str | None = "0006_source_profile_kinds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KINDS = (
    "kind IN ('openwebui', 'filesystem', 'website', 'sharepoint', 'qdrant', 'chroma', "
    "'weaviate', 'milvus', 'pgvector', 'elasticsearch', 'opensearch', 'pinecone', "
    "'kubernetes', 'generic', 'custom')"
)
_OLD_KINDS = (
    "kind IN ('openwebui', 'filesystem', 'qdrant', 'chroma', 'weaviate', 'milvus', "
    "'pgvector', 'elasticsearch', 'opensearch', 'pinecone', 'kubernetes', 'generic', 'custom')"
)


def upgrade() -> None:
    with op.batch_alter_table("source_profiles") as batch:
        batch.drop_constraint("ck_source_profiles_kind", type_="check")
        batch.create_check_constraint("ck_source_profiles_kind", _KINDS)


def downgrade() -> None:
    with op.batch_alter_table("source_profiles") as batch:
        batch.drop_constraint("ck_source_profiles_kind", type_="check")
        batch.create_check_constraint("ck_source_profiles_kind", _OLD_KINDS)
