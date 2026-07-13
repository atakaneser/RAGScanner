"""Unified static scan pipeline public API."""

from ragscanner.pipeline.config import LocalScanFileConfig, load_local_scan_config
from ragscanner.pipeline.models import (
    AssessmentCoverage,
    AssessmentStatus,
    OutputFormat,
    ProgressMode,
    SkippedItem,
    StageError,
    StageName,
    StaticPipelineConfig,
    StaticPipelineResult,
    StaticScanEvent,
    StaticScanEventType,
)
from ragscanner.pipeline.registry import ParserRegistry
from ragscanner.pipeline.service import (
    NoOpStaticScanEventSink,
    StaticScanEventSink,
    StaticScanPipeline,
    TerminalStaticScanEventSink,
    run_static_pipeline,
)

__all__ = [
    "AssessmentCoverage",
    "AssessmentStatus",
    "LocalScanFileConfig",
    "NoOpStaticScanEventSink",
    "OutputFormat",
    "ParserRegistry",
    "ProgressMode",
    "SkippedItem",
    "StageError",
    "StageName",
    "StaticPipelineConfig",
    "StaticPipelineResult",
    "StaticScanEvent",
    "StaticScanEventSink",
    "StaticScanEventType",
    "StaticScanPipeline",
    "TerminalStaticScanEventSink",
    "load_local_scan_config",
    "run_static_pipeline",
]
