"""Validated, display-safe model output contracts."""

from datetime import UTC, datetime
from typing import Literal

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


class AIFindingAction(BaseModel):
    """Advisory remediation tied to one deterministic finding."""

    finding_id: str = Field(min_length=1, max_length=512)
    remediation: str = Field(min_length=1, max_length=1_500)
    verification_steps: list[str] = Field(default_factory=list, max_length=6)


class AIRootCause(BaseModel):
    """Evidence-bound root-cause pattern returned by the analysis provider."""

    pattern: Literal["P1", "P2", "P3", "P4", "other"]
    label: str = Field(min_length=1, max_length=240)
    finding_rules: list[str] = Field(min_length=1, max_length=20)
    example_files: list[str] = Field(min_length=1, max_length=20)
    explanation: str = Field(min_length=1, max_length=1_500)
    confidence: Literal["confirmed", "likely"]


class AIPriorityAction(BaseModel):
    """One ordered, concrete remediation derived from supplied findings."""

    order: int = Field(ge=1, le=20)
    action: str = Field(min_length=1, max_length=1_500)
    target: Literal["ingestion", "chunking", "corpus", "configuration"]
    addresses: list[str] = Field(default_factory=list, max_length=20)
    expected_effect: str = Field(min_length=1, max_length=1_500)
    effort: Literal["low", "medium", "high"]


class AIReviewQuestion(BaseModel):
    """A decision-oriented question that cannot be answered from scan data."""

    question: str = Field(min_length=1, max_length=1_000)
    informs: str = Field(min_length=1, max_length=1_000)


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
    timeout_seconds: float = Field(default=180, ge=30, le=600)

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

    model_config = ConfigDict(extra="forbid")

    ai_analysis: str = Field(min_length=1, max_length=2_000)
    root_causes: list[AIRootCause] = Field(default_factory=list, max_length=8)
    priority_actions: list[AIPriorityAction] = Field(default_factory=list, max_length=8)
    review_questions: list[AIReviewQuestion] = Field(default_factory=list, max_length=8)
    score_commentary: str = Field(min_length=1, max_length=2_000)
    coverage_caveat: str | None = Field(default=None, max_length=1_500)


class AIReportAnalysis(AIAnalysisContent):
    """Provenance added locally after validated provider output."""

    schema_version: str = "2.0.0"
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=240)
    remote: bool
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_version: str = "2.0.0"
    executive_summary: str = Field(default="", max_length=2_000)
    risk_interpretation: str = Field(default="", max_length=2_000)
    verification_steps: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=8)
    finding_ids: list[str] = Field(default_factory=list, max_length=25)
    finding_actions: list[AIFindingAction] = Field(default_factory=list, max_length=25)
    ignored_finding_ids: list[str] = Field(default_factory=list, max_length=25)
    disclaimer: str = (
        "AI-generated analysis is advisory. Verify it against the deterministic findings "
        "and underlying evidence before acting."
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_v1_analysis(cls, value: object) -> object:
        """Keep persisted v1 advisory sections readable after the v2 prompt rewrite."""

        if not isinstance(value, dict):
            return value
        migrated = dict(value)
        summary = migrated.get("ai_analysis") or migrated.get("executive_summary")
        if isinstance(summary, str):
            migrated["ai_analysis"] = summary
        migrated.setdefault(
            "score_commentary",
            migrated.get("risk_interpretation") or summary or "No score commentary was provided.",
        )
        old_actions = migrated.get("priority_actions")
        if isinstance(old_actions, list):
            migrated["priority_actions"] = [
                (
                    {
                        "order": index,
                        "action": item,
                        "target": "configuration",
                        "addresses": [],
                        "expected_effect": "Review the deterministic findings after applying this action.",
                        "effort": "medium",
                    }
                    if isinstance(item, str)
                    else item
                )
                for index, item in enumerate(old_actions, start=1)
            ]
        old_questions = migrated.get("review_questions")
        if isinstance(old_questions, list):
            migrated["review_questions"] = [
                (
                    {
                        "question": item,
                        "informs": "The related remediation decision.",
                    }
                    if isinstance(item, str)
                    else item
                )
                for item in old_questions
            ]
        return migrated

    @model_validator(mode="after")
    def mirror_summary(self) -> "AIReportAnalysis":
        if not self.executive_summary:
            self.executive_summary = self.ai_analysis
        return self
