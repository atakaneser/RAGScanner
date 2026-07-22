"""Public reporting API."""

from ragscanner.reporting.compatibility import without_removed_consistency
from ragscanner.reporting.engine import ReportBuilder
from ragscanner.reporting.exports import (
    SUPPORTED_REPORT_EXPORTS,
    ReportExport,
    ReportExportFormat,
    export_report,
    report_export_filename,
)
from ragscanner.reporting.models import (
    REPORT_SCHEMA_VERSION,
    REPORTER_VERSION,
    ReportDocument,
    ReportFilter,
    ReportInput,
    ReportLimits,
)
from ragscanner.reporting.reporters import HtmlReporter, JsonReporter, TerminalReporter

__all__ = [
    "REPORTER_VERSION",
    "REPORT_SCHEMA_VERSION",
    "SUPPORTED_REPORT_EXPORTS",
    "HtmlReporter",
    "JsonReporter",
    "ReportBuilder",
    "ReportDocument",
    "ReportExport",
    "ReportExportFormat",
    "ReportFilter",
    "ReportInput",
    "ReportLimits",
    "TerminalReporter",
    "export_report",
    "report_export_filename",
    "without_removed_consistency",
]
