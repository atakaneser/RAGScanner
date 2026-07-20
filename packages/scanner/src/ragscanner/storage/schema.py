"""SQLAlchemy schema owned by the storage adapter, not scanner Core."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

scans = Table(
    "scans",
    metadata,
    Column("id", String(160), primary_key=True),
    Column("display_id", String(32), nullable=False),
    Column("scan_id", String(160), nullable=False),
    Column("scan_type", String(40), nullable=False),
    Column("status", String(40), nullable=False),
    Column("source_name", String(500)),
    Column("started_at", String(40)),
    Column("completed_at", String(40)),
    Column("overall_score", Float),
    Column("finding_count", Integer, nullable=False),
    Column("report_schema_version", String(40), nullable=False),
    Column("report_json", Text, nullable=False),
    Column("report_sha256", String(64), nullable=False),
    Column("created_at", String(40), nullable=False),
    CheckConstraint("length(report_sha256) = 64", name="ck_scans_report_sha256"),
    UniqueConstraint("report_sha256", name="uq_scans_report_sha256"),
    UniqueConstraint("display_id", name="uq_scans_display_id"),
)
Index("ix_scans_created_at", scans.c.created_at)
Index("ix_scans_scan_id", scans.c.scan_id)
Index("ix_scans_source_created", scans.c.source_name, scans.c.created_at)

findings = Table(
    "findings",
    metadata,
    Column("fingerprint", String(64), primary_key=True),
    Column("fingerprint_version", String(20), nullable=False),
    Column("rule_id", String(240), nullable=False),
    Column("first_observed_at", String(40), nullable=False),
    CheckConstraint("length(fingerprint) = 64", name="ck_findings_fingerprint"),
)

finding_occurrences = Table(
    "finding_occurrences",
    metadata,
    Column("history_id", String(160), ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "fingerprint",
        String(64),
        ForeignKey("findings.fingerprint", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Column("finding_id", String(160), nullable=False),
    Column("severity", String(20), nullable=False),
    Column("classification", String(40)),
    Column("observed_at", String(40), nullable=False),
)
Index("ix_occurrences_fingerprint", finding_occurrences.c.fingerprint)

jobs = Table(
    "jobs",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("display_id", String(32), nullable=False),
    Column("kind", String(40), nullable=False),
    Column("status", String(40), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("idempotency_key", String(160)),
    Column("attempt_count", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("available_at", String(40), nullable=False),
    Column("started_at", String(40)),
    Column("completed_at", String(40)),
    Column("lease_owner", String(160)),
    Column("lease_expires_at", String(40)),
    Column("heartbeat_at", String(40)),
    Column("progress", Float, nullable=False, default=0),
    Column("result_ref", String(500)),
    Column("error_code", String(80)),
    Column("error_message", String(500)),
    CheckConstraint("attempt_count >= 0", name="ck_jobs_attempt_count"),
    CheckConstraint("max_attempts BETWEEN 1 AND 10", name="ck_jobs_max_attempts"),
    CheckConstraint("progress BETWEEN 0 AND 1", name="ck_jobs_progress"),
    CheckConstraint(
        "status IN ('queued', 'running', 'cancel_requested', 'succeeded', 'failed', 'cancelled')",
        name="ck_jobs_status",
    ),
    UniqueConstraint("kind", "idempotency_key", name="uq_jobs_kind_idempotency"),
    UniqueConstraint("display_id", name="uq_jobs_display_id"),
)
Index("ix_jobs_claim", jobs.c.status, jobs.c.available_at, jobs.c.lease_expires_at)
Index("ix_jobs_created_at", jobs.c.created_at)

schedules = Table(
    "schedules",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("display_id", String(32), nullable=False),
    Column("name", String(160), nullable=False),
    Column("payload_json", Text, nullable=False),
    Column("interval_minutes", Integer, nullable=False),
    Column("enabled", Boolean, nullable=False, default=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    Column("next_run_at", String(40), nullable=False),
    Column("last_run_at", String(40)),
    CheckConstraint("interval_minutes BETWEEN 15 AND 525600", name="ck_schedules_interval"),
    UniqueConstraint("display_id", name="uq_schedules_display_id"),
)
Index("ix_schedules_due", schedules.c.enabled, schedules.c.next_run_at)

source_profiles = Table(
    "source_profiles",
    metadata,
    Column("id", String(32), primary_key=True),
    Column("name", String(160), nullable=False),
    Column("kind", String(40), nullable=False),
    Column("base_url", String(2048)),
    Column("local_path", String(4096)),
    Column("credential_ref", String(500)),
    Column("discovery_origin", String(80), nullable=False),
    Column("capability_status", String(40), nullable=False),
    Column("enabled", Boolean, nullable=False, default=True),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
    CheckConstraint(
        "kind IN ('openwebui', 'filesystem', 'qdrant', 'chroma', 'weaviate', "
        "'milvus', 'pgvector', 'elasticsearch', 'opensearch', 'pinecone', 'kubernetes', "
        "'generic', 'custom')",
        name="ck_source_profiles_kind",
    ),
    CheckConstraint(
        "capability_status IN ('scan_ready', 'metadata_only', 'connection_required')",
        name="ck_source_profiles_capability_status",
    ),
)
Index("ix_source_profiles_kind", source_profiles.c.kind)
Index("ix_source_profiles_updated_at", source_profiles.c.updated_at)

app_settings = Table(
    "app_settings",
    metadata,
    Column("key", String(120), primary_key=True),
    Column("value", String(2048), nullable=False),
    Column("updated_at", String(40), nullable=False),
)
