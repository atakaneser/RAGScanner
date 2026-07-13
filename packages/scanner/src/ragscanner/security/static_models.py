"""Typed contracts for declarative static security rules and scan results."""

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from ragscanner.domain import DetectionType, Finding, Severity

STATIC_RULE_SCHEMA_VERSION = "1.0.0"
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class StaticScope(StrEnum):
    RAW_DOCUMENT = "raw_document"
    NORMALIZED_DOCUMENT = "normalized_document"
    CHUNK = "chunk"
    TITLE = "title"
    METADATA = "metadata"
    PARSER_WARNING = "parser_warning"
    NORMALIZATION_ANNOTATION = "normalization_annotation"
    HEADING = "heading"
    TABLE_CELL = "table_cell"
    CODE_BLOCK = "code_block"
    URL = "url"


class MatcherType(StrEnum):
    EXACT = "exact"
    SUBSTRING_CI = "substring_ci"
    REGEX = "regex"
    TOKEN_SEQUENCE = "token_sequence"  # noqa: S105 - matcher name, not a credential
    METADATA_FIELD = "metadata_field"
    ANNOTATION_TYPE = "annotation_type"
    WARNING_CODE = "warning_code"
    DECODED_CONTENT = "decoded_content"
    ENTROPY_HEURISTIC = "entropy_heuristic"
    URL_PROPERTY = "url_property"
    SECRET_PATTERN = "secret_pattern"  # noqa: S105 - matcher name, not a credential
    PII_PATTERN = "pii_pattern"


class StaticMatcher(BaseModel):
    type: MatcherType
    patterns: list[str] = Field(default_factory=list, max_length=100)
    flags: list[str] = Field(default_factory=list)
    metadata_fields: list[str] = Field(default_factory=list, max_length=50)
    minimum_length: int = Field(default=0, ge=0, le=1_000_000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("patterns")
    @classmethod
    def validate_patterns(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            if not pattern or len(pattern) > 512:
                raise ValueError("matcher patterns must contain 1-512 characters")
        return patterns


class StaticRule(BaseModel):
    id: str = Field(pattern=r"^STATIC-[A-Z0-9-]+$")
    version: str
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: Severity
    default_confidence: float = Field(ge=0, le=1)
    detection_type: DetectionType
    scope: list[StaticScope] = Field(min_length=1)
    matchers: list[StaticMatcher] = Field(min_length=1)
    exclusions: list[str] = Field(default_factory=list)
    context_requirements: list[str] = Field(default_factory=list)
    evidence_window: int = Field(default=120, ge=20, le=1_024)
    remediation: str = Field(min_length=1)
    references: list[str] = Field(default_factory=list)
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not _SEMVER.fullmatch(value):
            raise ValueError("rule version must use MAJOR.MINOR.PATCH")
        return value


class StaticRulePack(BaseModel):
    schema_version: str
    pack_id: str = Field(min_length=1)
    version: str
    description: str = Field(min_length=1)
    rules: list[StaticRule] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_pack(self) -> "StaticRulePack":
        if self.schema_version != STATIC_RULE_SCHEMA_VERSION:
            raise ValueError("unsupported static rule-pack schema version")
        if not _SEMVER.fullmatch(self.version):
            raise ValueError("pack version must use MAJOR.MINOR.PATCH")
        ids = [rule.id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate static rule ID in pack")
        return self


class StaticRuleSelection(BaseModel):
    rule_ids: set[str] = Field(default_factory=set)
    excluded_rule_ids: set[str] = Field(default_factory=set)
    categories: set[str] = Field(default_factory=set)
    severities: set[Severity] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)
    languages: set[str] = Field(default_factory=set)
    scopes: set[StaticScope] = Field(default_factory=set)
    include_disabled: bool = False
    include_pii: bool = False


class StaticScanConfig(BaseModel):
    selection: StaticRuleSelection = Field(default_factory=StaticRuleSelection)
    maximum_matches_per_rule: int = Field(default=20, gt=0, le=10_000)
    maximum_findings_per_document: int = Field(default=500, gt=0, le=100_000)
    maximum_decoded_payload_size: int = Field(default=4_096, gt=0, le=1_000_000)
    maximum_decoding_depth: int = Field(default=1, ge=0, le=3)
    maximum_evidence_size: int = Field(default=512, ge=64, le=4_096)
    maximum_metadata_fields_scanned: int = Field(default=200, gt=0, le=10_000)
    maximum_regex_input_size: int = Field(default=1_000_000, gt=0, le=10_000_000)
    maximum_total_rules: int = Field(default=1_000, gt=0, le=10_000)
    maximum_scan_seconds: float = Field(default=30, gt=0, le=600)


class StaticScanWarning(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    rule_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StaticScanStatistics(BaseModel):
    rules_evaluated: int = Field(ge=0)
    rules_skipped: int = Field(ge=0)
    matches_evaluated: int = Field(ge=0)
    findings_created: int = Field(ge=0)
    chunks_scanned: int = Field(ge=0)
    metadata_fields_scanned: int = Field(ge=0)
    decoded_payloads_inspected: int = Field(ge=0)


class StaticScanResult(BaseModel):
    document_id: str = Field(min_length=1)
    findings: list[Finding] = Field(default_factory=list)
    rules_evaluated: list[str] = Field(default_factory=list)
    rules_skipped: list[str] = Field(default_factory=list)
    warnings: list[StaticScanWarning] = Field(default_factory=list)
    statistics: StaticScanStatistics
    scanner_name: str = Field(min_length=1)
    scanner_version: str = Field(min_length=1)
    rule_pack_versions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
