"""Use cases for scan history, detail, deletion, and comparison."""

from datetime import datetime

from ragscanner.history import ScanComparison, ScanHistoryPage, ScanHistoryRepository, compare_scans
from ragscanner.reporting.models import ReportDocument


class HistoryNotFoundError(LookupError):
    """A requested local execution-history record does not exist."""

    def __init__(self, history_ids: list[str]) -> None:
        self.history_ids = tuple(history_ids)
        super().__init__("One or more scan history records were not found.")


class HistoryApplicationService:
    """Coordinate history use cases without knowing the database or delivery framework."""

    def __init__(self, repository: ScanHistoryRepository) -> None:
        self.repository = repository

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        source: str | None = None,
    ) -> ScanHistoryPage:
        for name, value in (("created_after", created_after), ("created_before", created_before)):
            if value is not None and value.utcoffset() is None:
                raise ValueError(f"{name} must include a UTC offset")
        if created_after is not None and created_before is not None:
            if created_after > created_before:
                raise ValueError("created_after must not be later than created_before")
        if created_after is None and created_before is None and source is None:
            return self.repository.list(limit=limit, offset=offset)
        return self.repository.list(
            limit=limit,
            offset=offset,
            created_after=created_after,
            created_before=created_before,
            source=source,
        )

    def get(self, history_id: str) -> ReportDocument:
        report = self.repository.get(history_id)
        if report is None:
            raise HistoryNotFoundError([history_id])
        return report

    def compare(self, baseline_history_id: str, candidate_history_id: str) -> ScanComparison:
        baseline = self.repository.get(baseline_history_id)
        candidate = self.repository.get(candidate_history_id)
        missing = [
            history_id
            for history_id, report in (
                (baseline_history_id, baseline),
                (candidate_history_id, candidate),
            )
            if report is None
        ]
        if missing:
            raise HistoryNotFoundError(missing)
        assert baseline is not None and candidate is not None
        return compare_scans(baseline, candidate)

    def delete(self, history_id: str) -> None:
        if not self.repository.delete(history_id):
            raise HistoryNotFoundError([history_id])
