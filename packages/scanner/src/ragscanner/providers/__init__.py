"""Optional model-provider adapters; never imported by Core scanning code."""

from ragscanner.providers.adapters import (
    ModelProviderError,
    OllamaAnalysisProvider,
    OpenAICompatibleAnalysisProvider,
)

__all__ = ["ModelProviderError", "OllamaAnalysisProvider", "OpenAICompatibleAnalysisProvider"]
