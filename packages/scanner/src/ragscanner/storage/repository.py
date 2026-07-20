"""SQLAlchemy-backed local implementation of the scan-history port."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Integer, cast, delete, func, insert, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ragscanner.domain.helpers import contains_unreferenced_secret
from ragscanner.history.models import ScanHistoryPage, ScanHistorySummary
from ragscanner.reporting.models import ReportDocument
from ragscanner.storage.database import StorageError, create_sqlite_engine
from ragscanner.storage.schema import finding_occurrences, findings, scans


class SQLiteScanHistoryRepository:
    """Persist redacted report snapshots with immutable scan identities."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.expanduser().resolve()
        self.engine = create_sqlite_engine(self.database_path)

    def close(self) -> None:
        self.engine.dispose()

    def save(self, report: ReportDocument) -> str:
        report_data = report.model_dump(mode="json")
        if contains_unreferenced_secret(report_data):
            raise StorageError("The report contains a credential-like value and was not persisted.")
        payload = json.dumps(report_data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        scan_id = str(report.scan["id"])
        history_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(scans.c.id).where(scans.c.report_sha256 == checksum)
            ).scalar_one_or_none()
            if existing is not None:
                return str(existing)
            sequence = connection.execute(
                select(func.max(cast(func.substr(scans.c.display_id, 9), Integer)))
            ).scalar_one_or_none()
            connection.execute(
                insert(scans).values(
                    id=history_id,
                    display_id=f"RAGREP-{(sequence or 0) + 1:04d}",
                    scan_id=scan_id,
                    scan_type=str(report.scan["type"]),
                    status=str(report.scan["status"]),
                    source_name=report.scan.get("source_name"),
                    started_at=report.scan.get("started_at"),
                    completed_at=report.scan.get("completed_at"),
                    overall_score=report.scores.get("overall"),
                    finding_count=len(report.findings),
                    report_schema_version=report.schema_version,
                    report_json=payload,
                    report_sha256=checksum,
                    created_at=created_at,
                )
            )
            for finding in report.findings:
                connection.execute(
                    sqlite_insert(findings)
                    .values(
                        fingerprint=finding.fingerprint,
                        fingerprint_version="1",
                        rule_id=finding.rule_id,
                        first_observed_at=finding.first_seen.isoformat(),
                    )
                    .on_conflict_do_nothing(index_elements=[findings.c.fingerprint])
                )
                connection.execute(
                    insert(finding_occurrences).values(
                        history_id=history_id,
                        fingerprint=finding.fingerprint,
                        finding_id=finding.id,
                        severity=finding.severity.value,
                        classification=(
                            finding.classification.value if finding.classification else None
                        ),
                        observed_at=finding.last_seen.isoformat(),
                    )
                )
        return history_id

    def get(self, history_id: str) -> ReportDocument | None:
        with self.engine.connect() as connection:
            payload = connection.execute(
                select(scans.c.report_json).where(scans.c.id == history_id)
            ).scalar_one_or_none()
        return ReportDocument.model_validate_json(payload) if payload is not None else None

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        source: str | None = None,
    ) -> ScanHistoryPage:
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be non-negative")
        conditions = []
        if created_after is not None:
            conditions.append(scans.c.created_at >= created_after.isoformat())
        if created_before is not None:
            conditions.append(scans.c.created_at <= created_before.isoformat())
        if source:
            conditions.append(scans.c.source_name == source)
        with self.engine.connect() as connection:
            count_query = select(func.count()).select_from(scans)
            rows_query = select(
                scans.c.id,
                scans.c.display_id,
                scans.c.scan_id,
                scans.c.scan_type,
                scans.c.status,
                scans.c.source_name,
                scans.c.started_at,
                scans.c.completed_at,
                scans.c.overall_score,
                scans.c.finding_count,
                scans.c.report_schema_version,
                scans.c.created_at,
            )
            if conditions:
                count_query = count_query.where(*conditions)
                rows_query = rows_query.where(*conditions)
            total = connection.execute(count_query).scalar_one()
            rows = connection.execute(
                rows_query.order_by(scans.c.created_at.desc(), scans.c.id.desc())
                .limit(limit)
                .offset(offset)
            ).mappings()
            items = [
                ScanHistorySummary(
                    history_id=row["id"],
                    display_id=row["display_id"],
                    scan_id=row["scan_id"],
                    scan_type=row["scan_type"],
                    status=row["status"],
                    source_name=row["source_name"],
                    started_at=row["started_at"],
                    completed_at=row["completed_at"],
                    overall_score=row["overall_score"],
                    finding_count=row["finding_count"],
                    schema_version=row["report_schema_version"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]
        return ScanHistoryPage(items=items, total=total, limit=limit, offset=offset)

    def delete(self, history_id: str) -> bool:
        with self.engine.begin() as connection:
            result = connection.execute(delete(scans).where(scans.c.id == history_id))
        return bool(result.rowcount)
