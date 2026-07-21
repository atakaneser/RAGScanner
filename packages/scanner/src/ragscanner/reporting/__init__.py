"""Public reporting API."""

from ragscanner.reporting.compatibility import without_removed_consistency
from ragscanner.reporting.engine import ReportBuilder
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
    "HtmlReporter",
    "JsonReporter",
    "ReportBuilder",
    "ReportDocument",
    "ReportFilter",
    "ReportInput",
    "ReportLimits",
    "TerminalReporter",
    "without_removed_consistency",
]
