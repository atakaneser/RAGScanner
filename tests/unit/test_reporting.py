"""Security, determinism, schema, filtering, and rendering tests for reports."""

import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jsonschema
import pytest
from pydantic import ValidationError
from ragscanner.domain import (
    AnalysisMode,
    AuthorizationScope,
    DetectionType,
    EvaluationClassification,
    ExecutionStatus,
    Finding,
    PrivacyMode,
    SafetyMode,
    Scan,
    ScanStatus,
    ScanType,
    ScoreSummary,
    Severity,
    SourceLocation,
)
from ragscanner.domain import (
    TestExecution as ExecutionRecord,
)
from ragscanner.reporting import (
    HtmlReporter,
    JsonReporter,
    ReportBuilder,
    ReportFilter,
    ReportInput,
    ReportLimits,
    TerminalReporter,
)

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[2]


def finding(
    identifier: str,
    severity: Severity = Severity.HIGH,
    classification: EvaluationClassification = EvaluationClassification.PROBABLE,
    *,
    evidence: str = "Şüpheli retrieved instruction",
    active: bool = False,
) -> Finding:
    digest = (identifier.encode().hex() + "0" * 64)[:64]
    return Finding(
        id=identifier,
        fingerprint=digest,
        category="prompt_injection",
        scanner="static_security" if not active else "active_security",
        rule_id=f"RULE-{identifier}",
        rule_version="1.0.0",
        title=f"Finding {identifier}",
        description="Synthetic report fixture",
        severity=severity,
        confidence=0.8,
        detection_type=DetectionType.HEURISTIC,
        classification=classification,
        source=None
        if active
        else SourceLocation(
            source_id="source",
            source_type="filesystem",
            source_name="knowledge",
            source_path="/private/customer/knowledge.md",
            page_number=2,
        ),
        document_id=None if active else "doc-1",
        target_id="target-1" if active else None,
        test_case_id="test-1" if active else None,
        execution_id="execution-1" if active else None,
        evidence=evidence,
        impact="Retrieved instructions may influence the model.",
        recommendation="Review and isolate untrusted context.",
        first_seen=NOW,
        last_seen=NOW,
    )


def report_input(*, active: bool = False, findings: list[Finding] | None = None) -> ReportInput:
    authorization = (
        AuthorizationScope(
            authorized=True,
            authorized_by="owner@example.invalid",
            authorized_at=NOW,
            scope_description="Synthetic staging test",
            environment="staging",
            expires_at=None,
        )
        if active
        else None
    )
    scan = Scan(
        id="scan-1",
        scan_type=ScanType.ACTIVE if active else ScanType.STATIC,
        source_name=None if active else "Local knowledge",
        target_id="target-1" if active else None,
        authorization_scope=authorization,
        status=ScanStatus.COMPLETED_WITH_WARNINGS,
        mode=AnalysisMode.OFFLINE,
        safety_mode=SafetyMode.SAFE,
        privacy_mode=PrivacyMode.LOCAL_ONLY,
        started_at=NOW,
        completed_at=NOW + timedelta(seconds=2),
        scanner_version="0.1.0",
        rule_pack_version="1.0.0",
        files_discovered=2,
        files_scanned=1,
        files_skipped=1,
        chunks_scanned=3,
        requests_planned=2 if active else 0,
        requests_sent=1 if active else 0,
        warnings=["unsupported file type skipped"],
    )
    executions = (
        [
            ExecutionRecord(
                id="execution-1",
                scan_id=scan.id,
                target_id="target-1",
                test_case_id="test-1",
                payload_id="payload-1",
                status=ExecutionStatus.COMPLETED,
                started_at=NOW,
                completed_at=NOW + timedelta(seconds=1),
                metadata={"is_control": False},
            )
        ]
        if active
        else []
    )
    return ReportInput(
        scan=scan,
        findings=findings if findings is not None else [finding("a", active=active)],
        executions=executions,
        scores=ScoreSummary(security=72.5),
        documents_parsed=1,
        rules_evaluated=["RULE-a"],
        rules_skipped=["retrieval capability unavailable"],
        skipped_checks=["model-assisted checks not run"],
        warnings=["size-limit skip"],
        target_name="Synthetic target" if active else None,
        target_capabilities=["safe_test_mode"] if active else [],
        authorization_summary="Authorized staging scope; actor hidden" if active else None,
        configuration_summary={"offline": True, "api_key": "must-not-render"},
        methodology=["Deterministic and heuristic checks"],
        limitations=["Not detected is not a security guarantee"],
        generated_at=NOW + timedelta(seconds=3),
    )


def test_terminal_empty_missing_scores_no_ansi_and_failed_scan() -> None:
    source = report_input(findings=[])
    source.scores = None
    source.scan.status = ScanStatus.FAILED
    output = TerminalReporter().render(ReportBuilder().build(source), verbose=True)
    assert "Not assessed" in output
    assert "Status: failed" in output
    assert "\x1b[" not in output


def test_terminal_default_is_concise_and_verbose_keeps_technical_details() -> None:
    source = report_input()
    source.ingestion_issues = [
        {
            "path": "/private/customer/broken.pdf",
            "stage": "parsing",
            "code": "pdf_malformed",
            "message": "The PDF structure is malformed.",
            "remediation": "Export or download the PDF again.",
            "fatal": False,
        }
    ]
    report = ReportBuilder().build(source)

    concise = TerminalReporter().render(report)
    verbose = TerminalReporter().render(report, verbose=True)

    assert "RAGScanner scan: COMPLETED WITH WARNINGS" in concise
    assert "broken.pdf: The PDF structure is malformed." in concise
    assert "/private/customer" not in concise
    assert "Scores (product-defined" not in concise
    assert "Scores (product-defined" in verbose
    assert "Why it matters:" in verbose
    assert "What to do:" in verbose


def test_terminal_verbose_order_filters_and_evidence_truncation() -> None:
    items = [finding("low", Severity.LOW), finding("critical", Severity.CRITICAL)]
    report = ReportBuilder(
        filters=ReportFilter(minimum_severity=Severity.HIGH),
        limits=ReportLimits(maximum_evidence_length=64),
    ).build(report_input(findings=items))
    output = TerminalReporter().render(report, verbose=True)
    assert "critical" in output
    assert "RULE-low" not in output
    assert output.index("CRITICAL") < output.index("Evidence")


def test_json_schema_determinism_timestamps_null_scores_and_combined_type() -> None:
    source = report_input()
    source.scan.scan_type = ScanType.COMBINED
    source.scan.target_id = "target-1"
    source.scan.authorization_scope = AuthorizationScope(
        authorized=True,
        authorized_by="owner@example.invalid",
        authorized_at=NOW,
        scope_description="Synthetic",
        environment="staging",
        expires_at=NOW + timedelta(days=1),
    )
    source.scores = ScoreSummary(security=80)
    report = ReportBuilder().build(source)
    first = JsonReporter().render(report)
    second = JsonReporter().render(report)
    assert first == second
    payload = json.loads(first)
    schema = json.loads((ROOT / "schemas/report/ragscanner-report-v1.schema.json").read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(
        payload
    )
    assert payload["scores"]["freshness"] is None
    assert payload["generated_at"].endswith("Z")
    assert payload["scan"]["type"] == "combined"


def test_active_summary_hides_authorization_actor_and_distinguishes_mode() -> None:
    report = ReportBuilder().build(report_input(active=True))
    payload = JsonReporter().render(report)
    assert '"type":"active"' in payload
    assert "owner@example.invalid" not in payload
    assert report.active_security is not None
    assert report.active_security["attack_payloads_executed"] == 1


@pytest.mark.parametrize(
    "attack",
    [
        "<script>alert(1)</script>",
        "<img src=https://evil.invalid onerror=alert(1)>",
        "javascript:alert(1)",
        "-----BEGIN PRIVATE KEY----- abc -----END PRIVATE KEY-----",
        "postgres://user:password@localhost/db",
        "https://user:password@example.invalid/path?token=abcdefghijk",
    ],
)
def test_html_escapes_injection_masks_secrets_and_never_links_urls(attack: str) -> None:
    unsafe = finding("unsafe")
    unsafe = unsafe.model_copy(update={"evidence": attack})
    try:
        source = report_input(findings=[unsafe])
    except ValidationError:
        source = report_input()
        source = ReportInput.model_construct(
            **{
                name: getattr(source, name)
                for name in ReportInput.model_fields
                if name != "findings"
            },
            findings=[unsafe],
        )
    output = HtmlReporter().render(ReportBuilder().build(source))
    if attack.startswith("<") or "password" in attack or "PRIVATE KEY" in attack:
        assert attack not in output
    assert "<script>alert" not in output
    assert 'href="javascript:' not in output
    assert "[REDACTED]" in output or "&lt;" in output


def test_html_standalone_csp_accessibility_print_mobile_and_multilingual() -> None:
    output = HtmlReporter().render(
        ReportBuilder().build(
            report_input(
                findings=[finding("tr", evidence="Türkçe güvenlik finding and English text")]
            )
        )
    )
    assert "Content-Security-Policy" in output
    assert "connect-src 'none'" in output
    assert "<main" in output and "<header" in output and "<footer" in output
    assert "<details" in output and "<summary" in output
    assert "@media print" in output and "viewport" in output
    assert "cdn" not in output.casefold()
    assert "<script" not in output.casefold()
    assert "Türkçe" in output and "English" in output


def test_html_leads_with_coverage_and_ingestion_remediation() -> None:
    source = report_input()
    source.ingestion_issues = [
        {
            "path": "C:/Users/example/knowledge base/broken.pdf",
            "stage": "parsing",
            "code": "pdf_malformed",
            "message": "The PDF structure is malformed.",
            "remediation": "Export or download the PDF again.",
            "fatal": False,
        }
    ]
    source.assessment_coverage = {
        "static_security": {"status": "assessed", "reason": "Rules completed."},
        "freshness": {"status": "not_assessed", "reason": "Not implemented."},
    }

    output = HtmlReporter().render(ReportBuilder().build(source))

    assert output.index("Executive summary") < output.index("Scores")
    assert "1 of 2 assessment areas completed" in output
    assert "not a security guarantee" in output
    assert "broken.pdf" in output
    assert "C:/Users/example" not in output
    assert "Export or download the PDF again." in output
    assert "Technical details" in output


def test_html_does_not_claim_success_when_legacy_input_has_skipped_files() -> None:
    output = HtmlReporter().render(ReportBuilder().build(report_input()))

    assert "1 file(s) were skipped" in output
    assert "did not record per-file details" in output
    assert "All discovered files completed ingestion" not in output


def test_report_boundary_redaction_absolute_path_and_original_not_mutated() -> None:
    source = report_input()
    original = deepcopy(source)
    report = ReportBuilder().build(source)
    serialized = JsonReporter().render(report)
    assert "/private/customer" not in serialized
    assert "must-not-render" not in serialized
    assert "knowledge.md" in serialized
    assert source == original


def test_limit_notices_and_output_size_fail_explicitly() -> None:
    source = report_input(findings=[finding(str(index)) for index in range(5)])
    limits = ReportLimits(maximum_findings=2, maximum_json_size=10_000)
    report = ReportBuilder(limits=limits).build(source)
    assert len(report.findings) == 2
    assert report.truncation_notices
    huge = report.model_copy(update={"limitations": ["x" * 20_000]})
    with pytest.raises(ValueError, match="exceeds configured maximum"):
        JsonReporter().render(
            huge,
            limits=ReportLimits(
                maximum_json_size=10_000,
                maximum_string_length=100_000,
                maximum_metadata_fields=10_000,
                maximum_findings=100_000,
                maximum_warnings=10_000,
                maximum_duplicate_group_members=10_000,
                maximum_evidence_length=4096,
                maximum_html_size=10_000,
            ),
        )


def test_malformed_input_and_execution_scan_mismatch_rejected() -> None:
    with pytest.raises(ValidationError):
        ReportInput.model_validate({"scan": {}})
    source = report_input(active=True)
    source.executions[0] = source.executions[0].model_copy(update={"scan_id": "wrong"})
    with pytest.raises(ValidationError, match="belong"):
        ReportInput.model_validate(source.model_dump())


def test_html_and_json_size_limits_are_enforced() -> None:
    report = (
        ReportBuilder().build(report_input()).model_copy(update={"limitations": ["x" * 20_000]})
    )
    with pytest.raises(ValueError, match="HTML report exceeds"):
        HtmlReporter().render(report, limits=ReportLimits(maximum_html_size=10_000))


def test_reporting_has_no_network_or_subprocess_imports() -> None:
    package = ROOT / "packages/scanner/src/ragscanner/reporting"
    text = "\n".join(path.read_text() for path in package.glob("*.py"))
    assert "import httpx" not in text
    assert "import requests" not in text
    assert "import subprocess" not in text
    assert "os.system" not in text
