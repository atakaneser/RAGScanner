"""Validated, display-safe model output contracts."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class AIAnalysisContent(BaseModel):
    """The only fields an AI provider may supply."""

    executive_summary: str = Field(min_length=1, max_length=2_000)
    priority_actions: list[str] = Field(default_factory=list, max_length=8)
    review_questions: list[str] = Field(default_factory=list, max_length=8)
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
