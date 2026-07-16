"""Offline terminal, JSON, and standalone HTML report renderers."""

import html
import json
from typing import Any

from ragscanner.reporting.models import ReportDocument, ReportLimits


def _display(value: Any) -> str:
    if value is None:
        return "Not assessed"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


class TerminalReporter:
    def render(self, report: ReportDocument, *, verbose: bool = False) -> str:
        scan = report.scan
        status = str(scan["status"]).replace("_", " ").upper()
        lines = [
            f"RAGScanner scan: {status}",
            (
                f"Files: {report.processing.files_discovered} discovered · "
                f"{report.processing.files_scanned} processed · "
                f"{report.processing.files_skipped} skipped"
            ),
            f"Findings: {len(report.findings)}",
        ]
        critical_or_high = report.severity_summary["critical"] + report.severity_summary["high"]
        if critical_or_high:
            lines.append(
                "Security: "
                f"{report.severity_summary['critical']} critical and "
                f"{report.severity_summary['high']} high-severity finding(s)"
            )
        else:
            lines.append("Security: no critical or high findings in the assessed checks")
        if report.ingestion_issues:
            lines.append("Ingestion issues:")
            lines.extend(
                f"  - {item.path}: {item.message}"
                + (f" Next: {item.remediation}" if item.remediation else "")
                for item in report.ingestion_issues
            )
        if report.filters_active:
            lines.append("Filters active: yes")
        if not verbose:
            if report.warnings or report.skipped_checks or report.errors:
                lines.append(
                    "Run again with --verbose for scores, coverage, and technical details."
                )
            return "\n".join(lines) + "\n"

        lines.extend(
            [
                "",
                f"Report ID: {scan['id']}",
                f"Type: {scan['type']}  Status: {scan['status']}",
                (
                    "Knowledge base mode: "
                    f"{report.knowledge_base_mode} ({report.source_count} source(s))"
                ),
                (
                    f"Source: {_display(scan.get('source_name'))}  "
                    f"Target: {_display(scan.get('target_name'))}"
                ),
                "Scores (product-defined and limited to assessed checks):",
            ]
        )
        labels = {
            "overall": "Overall RAG Health",
            "security": "Security",
            "knowledge_quality": "Knowledge Quality",
            "retrieval_quality": "Retrieval Quality",
            "answer_reliability": "Answer Reliability",
            "freshness": "Freshness",
            "efficiency": "Efficiency",
            "rag_rot": "RAG Rot",
        }
        lines.extend(
            f"  {label}: {_display(report.scores.get(key))}" for key, label in labels.items()
        )
        lines.append(
            "Severity: "
            + "  ".join(
                f"{name}={report.severity_summary[name]}"
                for name in ("critical", "high", "medium", "low", "info")
            )
        )
        if report.truncation_notices:
            lines.extend(f"LIMIT: {item}" for item in report.truncation_notices)
        lines.append(f"Findings: {len(report.findings)}")
        for finding in report.findings:
            classification = (
                finding.classification.value if finding.classification else "unclassified"
            )
            lines.append(
                f"[{finding.severity.value.upper()}] [{classification}] "
                f"{finding.rule_id}: {finding.title} ({finding.confidence:.2f})"
            )
            location = finding.source or finding.target_id or "unknown"
            lines.extend(
                [
                    f"  Location: {location}",
                    f"  Evidence: {finding.evidence}",
                    f"  Why it matters: {finding.impact}",
                    f"  What to do: {finding.recommendation}",
                ]
            )
        if report.duplicate_groups:
            lines.append(
                f"Duplicate groups: {len(report.duplicate_groups)} (token savings are estimates)"
            )
        if report.chunk_quality is not None:
            lines.append("Chunk quality: assessed using product-defined heuristics")
        if report.active_security is not None:
            lines.append(
                f"Active requests: {report.active_security['request_budget_usage']['sent']} sent; "
                f"{report.active_security['transport_failures']} transport failure(s)"
            )
        lines.extend(f"WARNING: {item}" for item in report.warnings)
        lines.extend(f"SKIPPED: {item}" for item in report.skipped_checks)
        lines.extend(f"ERROR: {item}" for item in report.errors)
        for name, assessment in sorted(report.assessment_coverage.items()):
            lines.append(
                f"ASSESSMENT: {name} = {assessment.get('status', 'unknown')}"
                f" ({assessment.get('reason', 'no reason recorded')})"
            )
        return "\n".join(lines) + "\n"


class JsonReporter:
    def render(self, report: ReportDocument, *, limits: ReportLimits | None = None) -> str:
        value = json.dumps(
            report.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        maximum = (limits or ReportLimits()).maximum_json_size
        if len(value.encode("utf-8")) > maximum:
            raise ValueError(f"JSON report exceeds configured maximum of {maximum} bytes")
        return value + "\n"


class HtmlReporter:
    """Render semantic HTML; all dynamic values are escaped at interpolation."""

    def render(self, report: ReportDocument, *, limits: ReportLimits | None = None) -> str:
        def esc(value: Any) -> str:
            return html.escape(_display(value), quote=True)

        score_cards = "".join(
            f'<article class="card"><h3>{esc(name.replace("_", " ").title())}</h3>'
            f"<p>{esc(value)}</p><small>Product-defined</small></article>"
            for name, value in report.scores.items()
        )
        finding_rows = "".join(self._finding(item) for item in report.findings)
        top_finding_rows = "".join(self._finding(item) for item in report.findings[:5])
        priority_actions = (
            "".join(
                f"<li><strong>{esc(item.severity.value.title())}:</strong> {esc(item.recommendation)}</li>"
                for item in report.findings[:3]
            )
            or "<li>No remediation actions were generated by the assessed checks.</li>"
        )
        duplicate_rows = (
            "".join(
                "<tr>"
                f"<td>{esc(item.category)}</td><td>{esc(item.canonical_item_id)}</td>"
                f"<td>{esc(len(item.related_item_ids))}</td><td>{item.similarity:.2f}</td>"
                f"<td>{item.estimated_redundant_tokens} (estimate)</td></tr>"
                for item in report.duplicate_groups
            )
            or '<tr><td colspan="5">No duplicate groups reported.</td></tr>'
        )

        def messages(values: list[str]) -> str:
            return "".join(f"<li>{esc(item)}</li>" for item in values) or "<li>None</li>"

        status = str(report.scan["status"])
        status_label = status.replace("_", " ").title()
        ingestion_rows = "".join(
            "<tr>"
            f"<td>{esc(item.path)}</td><td>{esc(item.stage)}</td>"
            f"<td>{esc(item.message)}</td><td>{esc(item.remediation)}</td></tr>"
            for item in report.ingestion_issues
        )
        if not ingestion_rows:
            if report.processing.files_skipped:
                ingestion_rows = (
                    '<tr><td colspan="4">'
                    f"{report.processing.files_skipped} file(s) were skipped, but this report "
                    "input did not record per-file details.</td></tr>"
                )
            else:
                ingestion_rows = (
                    '<tr><td colspan="4">All discovered files completed ingestion.</td></tr>'
                )
        assessed = sum(
            value.get("status") == "assessed" for value in report.assessment_coverage.values()
        )
        coverage_total = len(report.assessment_coverage)
        coverage_notice = (
            f"{assessed} of {coverage_total} assessment areas completed. "
            "Scores describe assessed checks only and are not a security guarantee."
        )
        ai_analysis = report.ai_analysis
        ai_section = ""
        if ai_analysis is not None:
            risk_interpretation = (
                f"<h3>Risk interpretation</h3><p>{esc(ai_analysis.risk_interpretation)}</p>"
                if ai_analysis.risk_interpretation
                else ""
            )
            ai_section = (
                '<section aria-labelledby="ai-analysis"><h2 id="ai-analysis">AI analysis</h2>'
                f"<p>{esc(ai_analysis.executive_summary)}</p>"
                f"{risk_interpretation}"
                f"<h3>Priority actions</h3><ul>{messages(ai_analysis.priority_actions)}</ul>"
                f"<h3>Questions for review</h3><ul>{messages(ai_analysis.review_questions)}</ul>"
                f"<h3>Verification steps</h3><ul>{messages(ai_analysis.verification_steps)}</ul>"
                f"<h3>Limitations</h3><ul>{messages(ai_analysis.limitations)}</ul>"
                f'<p class="muted">Provider: {esc(ai_analysis.provider)} · Model: '
                f"{esc(ai_analysis.model)} · Remote: {esc(ai_analysis.remote)} · "
                f"{esc(ai_analysis.disclaimer)}</p></section>"
            )
        elif report.ai_analysis_error:
            ai_section = (
                '<section aria-labelledby="ai-analysis"><h2 id="ai-analysis">'
                "AI analysis unavailable</h2>"
                f"<p>{esc(report.ai_analysis_error)}</p></section>"
            )

        html_value = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src 'none'; script-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'none'">
<title>RAGScanner report {esc(report.scan["id"])}</title><style>
:root{{--bg:#f6f7f9;--panel:#fff;--text:#17202a;--muted:#586474;--line:#d8dee6;--critical:#8b1e2d;--high:#a34710;--medium:#766000;--low:#285c85;--info:#4d5968;--accent:#176b5b}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif}}header,main,footer{{max-width:1180px;margin:auto;padding:1.25rem}}header{{background:#17202a;color:#fff;max-width:none}}header>div{{max-width:1140px;margin:auto}}h1,h2,h3{{line-height:1.2}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem}}.card,section{{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:1rem;margin:1rem 0}}.card{{margin:0}}.summary{{border-left:5px solid var(--accent)}}.metric{{font-size:1.6rem;font-weight:750;margin:.25rem 0}}.notice{{background:#eef7f5;border:1px solid #b8d9d2;border-radius:6px;padding:.75rem}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;padding:.6rem;border-bottom:1px solid var(--line);vertical-align:top}}.badge{{display:inline-block;border:1px solid currentColor;border-radius:99px;padding:.1rem .5rem;font-weight:700}}.critical{{color:var(--critical)}}.high{{color:var(--high)}}.medium{{color:var(--medium)}}.low{{color:var(--low)}}.info{{color:var(--info)}}code,pre{{white-space:pre-wrap;overflow-wrap:anywhere}}summary{{cursor:pointer;font-weight:700}}.muted{{color:var(--muted)}}@media(max-width:650px){{table{{display:block;overflow-x:auto}}header,main,footer{{padding:.8rem}}}}@media print{{body{{background:#fff}}header{{color:#000;background:#fff;border-bottom:2px solid #000}}section,.card{{break-inside:avoid;box-shadow:none}}details{{display:block}}details>*{{display:block}}}}
</style></head><body><header role="banner"><div><h1>RAGScanner report</h1><p>{esc(report.scan["id"])} · {esc(report.scan["type"])} · {esc(report.scan["status"])}</p></div></header>
<main id="main-content"><section class="summary" aria-labelledby="summary"><h2 id="summary">Executive summary</h2><p class="metric">{esc(status_label)}</p><div class="grid"><div><strong>Discovered</strong><p class="metric">{report.processing.files_discovered}</p></div><div><strong>Processed</strong><p class="metric">{report.processing.files_scanned}</p></div><div><strong>Skipped</strong><p class="metric">{report.processing.files_skipped}</p></div><div><strong>Findings</strong><p class="metric">{len(report.findings)}</p></div></div><p class="notice">{esc(coverage_notice)}</p><h3>What to do next</h3><ol>{priority_actions}</ol></section>
{ai_section}
<section aria-labelledby="ingestion"><h2 id="ingestion">File ingestion</h2><p>Files that could not be processed are listed separately from security and quality findings.</p><table><thead><tr><th>File</th><th>Stage</th><th>What happened</th><th>What to do</th></tr></thead><tbody>{ingestion_rows}</tbody></table></section>
<section aria-labelledby="scores"><h2 id="scores">Scores</h2><p class="muted">Product-defined scores. Missing values are Not assessed, never zero.</p><div class="grid">{score_cards}</div></section>
<section aria-labelledby="severity"><h2 id="severity">Severity distribution</h2><div class="grid">{"".join(f'<div class="card {esc(k)}"><strong>{esc(k.title())}</strong><p>{v}</p></div>' for k, v in report.severity_summary.items())}</div></section>
<section aria-labelledby="statistics"><h2 id="statistics">Scan statistics</h2><pre>{esc(json.dumps(report.processing.model_dump(), ensure_ascii=False, sort_keys=True, indent=2))}</pre></section>
<section aria-labelledby="top"><h2 id="top">Top findings</h2>{top_finding_rows or "<p>No findings reported.</p>"}</section>
<section aria-labelledby="all"><h2 id="all">All findings</h2>{finding_rows or "<p>No findings reported.</p>"}</section>
<section aria-labelledby="duplicates"><h2 id="duplicates">Duplicate analysis</h2><p>Redundant token and character values are estimates.</p><table><thead><tr><th>Type</th><th>Canonical item</th><th>Related</th><th>Similarity</th><th>Redundant tokens</th></tr></thead><tbody>{duplicate_rows}</tbody></table></section>
<section aria-labelledby="chunks"><h2 id="chunks">Chunk-quality analysis</h2><pre>{esc(json.dumps(report.chunk_quality, ensure_ascii=False, sort_keys=True, indent=2) if report.chunk_quality else "Not assessed")}</pre></section>
<section aria-labelledby="active"><h2 id="active">Active security summary</h2><pre>{esc(json.dumps(report.active_security, ensure_ascii=False, sort_keys=True, indent=2) if report.active_security else "Not assessed")}</pre></section>
<section aria-labelledby="warnings"><h2 id="warnings">Warnings and skipped checks</h2><h3>Warnings</h3><ul>{messages(report.warnings)}</ul><h3>Skipped checks</h3><ul>{messages(report.skipped_checks)}</ul><h3>Errors</h3><ul>{messages(report.errors)}</ul><h3>Limits</h3><ul>{messages(report.truncation_notices)}</ul></section>
<details><summary>Technical details</summary><section aria-labelledby="identity"><h2 id="identity">Scan identity</h2><dl><dt>Source</dt><dd>{esc(report.scan.get("source_name"))}</dd><dt>Target</dt><dd>{esc(report.scan.get("target_name"))}</dd><dt>Generated</dt><dd>{esc(report.generated_at.isoformat())}</dd><dt>Privacy</dt><dd>{esc(report.scan.get("privacy_mode"))}</dd><dt>Safety</dt><dd>{esc(report.scan.get("safety_mode"))}</dd></dl></section><section aria-labelledby="configuration"><h2 id="configuration">Configuration summary</h2><pre>{esc(json.dumps(report.configuration, ensure_ascii=False, sort_keys=True, indent=2))}</pre></section></details>
<section aria-labelledby="methodology"><h2 id="methodology">Methodology and limitations</h2><h3>Methodology</h3><ul>{messages(report.methodology)}</ul><h3>Limitations</h3><ul>{messages(report.limitations)}</ul></section>
<section aria-labelledby="coverage"><h2 id="coverage">Assessment coverage</h2><p>Knowledge base mode: <strong>{esc(report.knowledge_base_mode)}</strong> · Sources: {report.source_count}</p><pre>{esc(json.dumps(report.assessment_coverage, ensure_ascii=False, sort_keys=True, indent=2))}</pre></section>
<section aria-labelledby="metadata"><h2 id="metadata">Report metadata</h2><p>Schema {esc(report.schema_version)} · Reporter {esc(report.reporter_version)}</p><p>Filters active: {esc(report.filters_active)}</p></section></main>
<footer role="contentinfo"><p>Generated locally by RAGScanner. No external assets, analytics, or network requests.</p></footer></body></html>"""
        maximum = (limits or ReportLimits()).maximum_html_size
        if len(html_value.encode("utf-8")) > maximum:
            raise ValueError(f"HTML report exceeds configured maximum of {maximum} bytes")
        return html_value

    @staticmethod
    def _finding(item: Any) -> str:
        def esc(value: Any) -> str:
            return html.escape(_display(value), quote=True)

        classification = item.classification.value if item.classification else "unclassified"
        return (
            f'<details class="finding"><summary><span class="badge {esc(item.severity.value)}">'
            f"{esc(item.severity.value.upper())}</span> {esc(item.title)} · {esc(classification)}</summary>"
            f"<dl><dt>Finding ID</dt><dd>{esc(item.id)}</dd><dt>Category</dt><dd>{esc(item.category)}</dd>"
            f"<dt>Confidence</dt><dd>{item.confidence:.2f}</dd><dt>Rule</dt><dd>{esc(item.rule_id)} / {esc(item.rule_version)}</dd>"
            f"<dt>Source</dt><dd>{esc(item.source)}</dd><dt>Document</dt><dd>{esc(item.document_id)}</dd>"
            f"<dt>Page</dt><dd>{esc(item.page)}</dd><dt>Chunk</dt><dd>{esc(item.chunk_id)}</dd>"
            f"<dt>Target</dt><dd>{esc(item.target_id)}</dd><dt>Test case</dt><dd>{esc(item.test_case_id)}</dd></dl>"
            f"<h3>Evidence</h3><pre>{esc(item.evidence)}</pre><h3>Impact</h3><p>{esc(item.impact)}</p>"
            f'<h3>Recommendation</h3><p>{esc(item.recommendation)}</p><p class="muted">Fingerprint: {esc(item.fingerprint)}</p></details>'
        )
