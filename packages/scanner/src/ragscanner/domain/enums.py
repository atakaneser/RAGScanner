"""Framework-independent domain enumerations."""

from enum import StrEnum


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DetectionType(StrEnum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    LLM_ASSISTED = "llm_assisted"
    MANUAL = "manual"


class TargetType(StrEnum):
    GENERIC_REST = "generic_rest"
    OPENAI_COMPATIBLE = "openai_compatible"
    HUGGINGFACE_INFERENCE = "huggingface_inference"
    OPENWEBUI = "openwebui"
    CUSTOM = "custom"


class SafetyMode(StrEnum):
    SAFE = "safe"
    CONTROLLED = "controlled"
    DESTRUCTIVE = "destructive"  # Must never be selected implicitly.


class SideEffectRisk(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DESTRUCTIVE = "destructive"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class EvaluationClassification(StrEnum):
    CONFIRMED = "confirmed"
    PROBABLE = "probable"
    AMBIGUOUS = "ambiguous"
    NOT_DETECTED = "not_detected"
    INCONCLUSIVE = "inconclusive"


class EvaluatorType(StrEnum):
    DETERMINISTIC = "deterministic"
    HEURISTIC = "heuristic"
    LLM_ASSISTED = "llm_assisted"
    MANUAL = "manual"


class ScanType(StrEnum):
    STATIC = "static"
    ACTIVE = "active"
    COMBINED = "combined"


class AnalysisMode(StrEnum):
    OFFLINE = "offline"
    BALANCED = "balanced"
    DEEP = "deep"


class ScanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PrivacyMode(StrEnum):
    LOCAL_ONLY = "local_only"
    REDACTED_REMOTE = "redacted_remote"


class HttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
