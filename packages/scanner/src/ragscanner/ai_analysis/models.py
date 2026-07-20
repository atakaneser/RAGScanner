"""Validated, display-safe model output contracts."""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

LOCAL_PROVIDER_IDS = frozenset({"ollama", "lm-studio", "localai", "vllm"})
REMOTE_PROVIDER_IDS = frozenset(
    {
        "openai",
        "openrouter",
        "nvidia-nim",
        "anthropic",
        "google-gemini",
        "groq",
        "mistral",
        "together",
        "custom",
    }
)
PROVIDER_IDS = LOCAL_PROVIDER_IDS | REMOTE_PROVIDER_IDS


class AIProviderConfig(BaseModel):
    """Non-secret, persistable model selection attached to one scan job."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=240)
    base_url: str | None = Field(default=None, max_length=2048)
    credential_ref: str | None = Field(default=None, max_length=500)
    remote_consent: bool = False
    output_language: str = Field(default="en", pattern=r"^(en|tr|de|fr|zh-CN|it)$")

    @model_validator(mode="after")
    def validate_selection(self) -> "AIProviderConfig":
        if not self.enabled:
            return self
        if self.provider not in PROVIDER_IDS:
            raise ValueError("AI analysis requires a supported provider")
        if not self.model or not self.model.strip():
            raise ValueError("AI analysis requires a model")
        if self.provider in REMOTE_PROVIDER_IDS:
            if not self.remote_consent:
                raise ValueError("remote AI analysis requires explicit consent")
            if not self.credential_ref:
                raise ValueError("remote AI analysis requires a credential reference")
        return self


class AIAnalysisContent(BaseModel):
    """The only fields an AI provider may supply."""

    executive_summary: str = Field(min_length=1, max_length=2_000)
    risk_interpretation: str = Field(default="", max_length=2_000)
    priority_actions: list[str] = Field(default_factory=list, max_length=8)
    review_questions: list[str] = Field(default_factory=list, max_length=8)
    verification_steps: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)
    finding_ids: list[str] = Field(default_factory=list, max_length=25)


class AIReportAnalysis(AIAnalysisContent):
    """Provenance added locally after validated provider output."""

    schema_version: str = "1.0.0"
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=240)
    remote: bool
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_version: str = "1.0.0"
    disclaimer: str = (
        "AI-generated analysis is advisory. Verify it against the deterministic findings "
        "and underlying evidence before acting."
    )
