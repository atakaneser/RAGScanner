from ragscanner.application import HistoryApplicationService, HistoryNotFoundError
from ragscanner.history.models import ScanHistoryPage, ScanHistorySummary


class InMemoryHistoryRepository:
    def __init__(self, reports: dict[str, object]) -> None:
        self.reports = reports

    def save(self, report):  # type: ignore[no-untyped-def]
        raise NotImplementedError

    def get(self, history_id):  # type: ignore[no-untyped-def]
        return self.reports.get(history_id)

    def list(self, *, limit: int = 50, offset: int = 0) -> ScanHistoryPage:
        items = [
            ScanHistorySummary(
                history_id=history_id,
                scan_id=str(report.scan["id"]),
                scan_type=str(report.scan["type"]),
                status=str(report.scan["status"]),
                source_name=report.scan.get("source_name"),
                finding_count=len(report.findings),
                schema_version=report.schema_version,
                created_at=report.generated_at,
            )
            for history_id, report in sorted(self.reports.items())
        ]
        return ScanHistoryPage(
            items=items[offset : offset + limit], total=len(items), limit=limit, offset=offset
        )

    def delete(self, history_id: str) -> bool:
        return self.reports.pop(history_id, None) is not None


def test_application_service_coordinates_list_detail_compare_and_delete(report, finding) -> None:  # type: ignore[no-untyped-def]
    baseline_id = "a" * 32
    candidate_id = "b" * 32
    repository = InMemoryHistoryRepository(
        {
            baseline_id: report("scan-1", findings=[finding("a")]),
            candidate_id: report("scan-2", findings=[finding("b")]),
        }
    )
    service = HistoryApplicationService(repository)  # type: ignore[arg-type]

    assert service.list(limit=1).total == 2
    assert service.get(baseline_id).scan["id"] == "scan-1"
    assert service.compare(baseline_id, candidate_id).compatible
    service.delete(baseline_id)

    try:
        service.get(baseline_id)
    except HistoryNotFoundError as error:
        assert error.history_ids == (baseline_id,)
    else:
        raise AssertionError("deleted history must not remain accessible")


def test_application_service_reports_all_missing_comparison_records(report) -> None:  # type: ignore[no-untyped-def]
    service = HistoryApplicationService(InMemoryHistoryRepository({}))  # type: ignore[arg-type]

    try:
        service.compare("a" * 32, "b" * 32)
    except HistoryNotFoundError as error:
        assert error.history_ids == ("a" * 32, "b" * 32)
    else:
        raise AssertionError("missing history must fail")
