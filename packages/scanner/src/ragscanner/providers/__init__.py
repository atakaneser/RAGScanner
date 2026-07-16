"""Optional model-provider adapters; never imported by Core scanning code."""

from ragscanner.providers.adapters import (
    PROVIDER_CATALOG,
    AnthropicAnalysisProvider,
    GeminiAnalysisProvider,
    ModelProviderError,
    OllamaAnalysisProvider,
    OpenAICompatibleAnalysisProvider,
    create_analysis_provider,
    discover_provider_models,
)

__all__ = [
    "PROVIDER_CATALOG",
    "AnthropicAnalysisProvider",
    "GeminiAnalysisProvider",
    "ModelProviderError",
    "OllamaAnalysisProvider",
    "OpenAICompatibleAnalysisProvider",
    "create_analysis_provider",
    "discover_provider_models",
]
