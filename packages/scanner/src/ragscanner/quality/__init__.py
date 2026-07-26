"""Deterministic offline duplicate and chunk-quality analysis."""

from ragscanner.quality.models import (
    ChunkQualityConfig,
    ChunkQualityResult,
    ChunkQualityScore,
    DuplicateGroup,
    DuplicateScanConfig,
    DuplicateScanResult,
    NearDuplicateConfig,
    QualityWarning,
)
from ragscanner.quality.recommendations import (
    RAGConfigurationAdvice,
    RAGConfigurationAdvisor,
    RAGConfigurationConfig,
    RAGProfile,
)
from ragscanner.quality.scanners import (
    ChunkQualityScanner,
    ExactDuplicateScanner,
    NearDuplicateScanner,
)

__all__ = [
    "ChunkQualityConfig",
    "ChunkQualityResult",
    "ChunkQualityScanner",
    "ChunkQualityScore",
    "DuplicateGroup",
    "DuplicateScanConfig",
    "DuplicateScanResult",
    "ExactDuplicateScanner",
    "NearDuplicateConfig",
    "NearDuplicateScanner",
    "QualityWarning",
    "RAGConfigurationAdvice",
    "RAGConfigurationAdvisor",
    "RAGConfigurationConfig",
    "RAGProfile",
]
