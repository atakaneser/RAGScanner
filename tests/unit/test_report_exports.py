"""Standalone dashboard report export tests."""

from io import BytesIO

import pytest
from openpyxl import load_workbook
from pypdf import PdfReader
from ragscanner.reporting import export_report, report_export_filename


def test_html_export_is_localized_standalone_and_escaped(report, finding) -> None:  # type: ignore[no-untyped-def]
    unsafe = finding("html")
    unsafe.title = "<script>alert(1)</script>"
    unsafe.source = "politika-tr.md"
    unsafe.page = 2
    unsafe.evidence_highlight = "MFA'yı devre dışı bırak"
    exported = export_report(report("scan-html", findings=[unsafe]), "html", locale="tr")
    text = exported.content.decode("utf-8")

    assert exported.media_type == "text/html"
    assert exported.extension == "html"
    assert '<html lang="tr">' in text
    assert "Yönetici özeti" in text
    assert "Sorunlu metin" in text
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in text
    assert "connect-src 'none'" in text
    assert "<script" not in text.casefold()


def test_xlsx_export_has_structured_sheets_and_blocks_formulas(report, finding) -> None:  # type: ignore[no-untyped-def]
    suspicious = finding("xlsx")
    suspicious.title = '=HYPERLINK("https://example.invalid","open")'
    suspicious.source = "+SUM(A1:A2)"
    suspicious.evidence_highlight = "Şüpheli metin"
    exported = export_report(report("scan-xlsx", findings=[suspicious]), "xlsx", locale="tr")
    workbook = load_workbook(BytesIO(exported.content), data_only=False)

    assert exported.extension == "xlsx"
    assert workbook.sheetnames[:4] == ["Özet", "Bulgular", "Kapsam", "Veri alımı sorunları"]
    findings_sheet = workbook["Bulgular"]
    assert findings_sheet.freeze_panes == "A2"
    assert findings_sheet.auto_filter.ref
    assert findings_sheet["C2"].data_type == "s"
    assert str(findings_sheet["C2"].value).startswith("'=")
    assert str(findings_sheet["F2"].value).startswith("'+")
    assert findings_sheet["I2"].value == "Şüpheli metin"


@pytest.mark.parametrize("locale", ["en", "tr", "de", "fr", "zh-CN", "it"])
def test_pdf_export_is_readable_in_every_supported_locale(locale, report, finding) -> None:  # type: ignore[no-untyped-def]
    located = finding("pdf")
    located.source = "güvenlik-政策.pdf"
    located.page = 3
    located.evidence_highlight = "MFA güvenlik kontrolü"
    exported = export_report(report("scan-pdf", findings=[located]), "pdf", locale=locale)
    reader = PdfReader(BytesIO(exported.content))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert exported.content.startswith(b"%PDF-")
    assert exported.media_type == "application/pdf"
    assert len(reader.pages) >= 1
    assert "RAGScanner" in extracted
    assert "scan-pdf" not in extracted  # exports do not expose an internal scan id as a heading


def test_pdf_groups_repeated_findings_and_bounds_occurrence_details(report, finding) -> None:  # type: ignore[no-untyped-def]
    repeated = []
    for index in range(80):
        item = finding("a")
        item.id = f"finding-{index}"
        item.fingerprint = f"{index:064x}"
        item.title = "Excessive Overlap"
        item.rule_id = "QUALITY-CHUNK-EXCESSIVE-OVERLAP"
        item.source = f"support-{index:02}.md"
        item.impact = "Poor chunk quality can reduce retrieval precision, waste context, or hide source structure."
        item.recommendation = (
            "Reduce bounded overlap without crossing unrelated structural boundaries."
        )
        repeated.append(item)
    exported = export_report(report("scan-grouped", findings=repeated), "pdf", locale="tr")
    reader = PdfReader(BytesIO(exported.content))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert "Aşırı bindirme" in extracted
    assert "Tekrarlar: 80" in extracted
    assert "60 tekrar daha PDF özetinden çıkarıldı" in extracted
    assert len(reader.pages) < 10


def test_pdf_renders_plain_source_apostrophes_instead_of_html_entities(report, finding) -> None:  # type: ignore[no-untyped-def]
    item = finding("apostrophe")
    item.evidence = "## VPN'e bağlanma\nVPN'e bağlanmak için ',,sms' ekleyin."
    item.evidence_highlight = "VPN'e bağlanmak"
    exported = export_report(report("scan-apostrophe", findings=[item]), "pdf", locale="tr")
    extracted = "\n".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(exported.content)).pages
    )

    assert "VPN'e" in extracted
    assert "&#x27;" not in extracted


def test_report_export_filename_is_bounded_and_safe(report) -> None:  # type: ignore[no-untyped-def]
    value = report("scan-name", source_name="Policy / ../../ unsafe")
    filename = report_export_filename(value, "abcdef0123456789", "xlsx")

    assert filename == "ragscanner-policy-unsafe-abcdef012345.xlsx"
    assert "/" not in filename


def test_unknown_export_format_is_rejected(report) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="unsupported report export format"):
        export_report(report("scan-invalid"), "csv")  # type: ignore[arg-type]
