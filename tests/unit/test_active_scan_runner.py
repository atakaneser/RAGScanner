"""End-to-end in-memory tests for active scan orchestration."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError
from ragscanner.domain import (
    AuthorizationScope,
    DetectionType,
    EvaluationClassification,
    PayloadVariant,
    SafetyMode,
    ScanStatus,
    SecurityTestCase,
    Severity,
    SideEffectRisk,
    TargetBudget,
    TargetCapabilities,
    TargetDescriptor,
    TargetErrorCategory,
    TargetErrorDetail,
    TargetHealth,
    TargetHealthStatus,
    TargetObservation,
    TargetType,
)
from ragscanner.runner import ActiveScanEvent, ActiveScanPlan, ActiveSecurityScanRunner
from ragscanner.security import ActiveTestLibrary
from ragscanner.testing import FakeTargetAdapter

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def authorization(*, expired: bool = False, environment: str = "test") -> AuthorizationScope:
    return AuthorizationScope(
        authorized=True,
        authorized_by="target-owner",
        authorized_at=NOW - timedelta(hours=1),
        scope_description="Authorized runner test",
        environment=environment,
        expires_at=NOW - timedelta(seconds=1) if expired else datetime(2030, 1, 1, tzinfo=UTC),
    )


def payload(
    identifier: str = "payload-1",
    *,
    language: str = "en",
    safe: bool = True,
    tags: list[str] | None = None,
    content: str = "synthetic attack",
) -> PayloadVariant:
    return PayloadVariant(
        id=identifier,
        content=content,
        language=language,
        safe_for_production=safe,
        expected_behavior="Preserve policy",
        tags=tags or [],
    )


def make_case(identifier: str = "case-1", **changes: Any) -> SecurityTestCase:
    chosen_payloads = changes.pop("payloads", [payload(f"{identifier}-payload")])
    values: dict[str, Any] = {
        "id": identifier,
        "name": identifier,
        "category": "prompt_injection",
        "description": "Synthetic active test",
        "severity": Severity.HIGH,
        "detection_type": DetectionType.DETERMINISTIC,
        "payloads": chosen_payloads,
        "expected_safe_behavior": "Refuse unsafe behavior",
        "unsafe_indicators": ["exact:UNSAFE"],
        "safe_indicators": ["REFUSED"],
        "ambiguous_indicators": ["MAYBE"],
    }
    values.update(changes)
    return SecurityTestCase(**values)


def descriptor(**capability_changes: Any) -> TargetDescriptor:
    capabilities = TargetCapabilities(safe_test_mode=True, **capability_changes)
    return TargetDescriptor(
        id="target-1",
        name="target",
        target_type=TargetType.CUSTOM,
        display_name="Target",
        description="Synthetic target",
        capabilities=capabilities,
        configuration_reference="env:TARGET_CONFIG",
    )


def observation(body: str, **changes: Any) -> TargetObservation:
    values: dict[str, Any] = {
        "invocation_id": "placeholder",
        "status_code": 200,
        "body": body,
        "received_at": NOW,
    }
    values.update(changes)
    return TargetObservation(**values)


def fake_adapter(
    observations: list[TargetObservation],
    *,
    selected_descriptor: TargetDescriptor | None = None,
    failures: dict[str, TargetErrorDetail] | None = None,
) -> FakeTargetAdapter:
    return FakeTargetAdapter(
        descriptor=selected_descriptor or descriptor(),
        health=TargetHealth(status=TargetHealthStatus.HEALTHY, checked_at=NOW),
        authorization=authorization(),
        budget=TargetBudget(max_requests=100, max_duration_seconds=600, max_failures=100),
        clock=NOW,
        observations=observations,
        failures=failures,
    )


def plan(**changes: Any) -> ActiveScanPlan:
    values: dict[str, Any] = {
        "scan_id": "scan-1",
        "target_id": "target-1",
        "authorization_scope": authorization(),
        "run_controls": False,
    }
    values.update(changes)
    return ActiveScanPlan(**values)


def run(
    cases: list[SecurityTestCase],
    observations: list[TargetObservation],
    *,
    selected_plan: ActiveScanPlan | None = None,
    selected_descriptor: TargetDescriptor | None = None,
    evaluator: Any = None,
    event_sink: Any = None,
    monotonic_clock: Any = None,
    failures: dict[str, TargetErrorDetail] | None = None,
) -> Any:
    runner = ActiveSecurityScanRunner(
        adapter=fake_adapter(
            observations, selected_descriptor=selected_descriptor, failures=failures
        ),
        library=ActiveTestLibrary(cases),
        evaluator=evaluator,
        event_sink=event_sink,
        clock=lambda: NOW,
        monotonic_clock=monotonic_clock or (lambda: 0.0),
    )
    return asyncio.run(runner.run(selected_plan or plan()))


def test_successful_safe_scan_finding_counters_and_stable_fingerprint() -> None:
    selected_case = make_case()
    first = run([selected_case], [observation("UNSAFE")])
    second = run([selected_case], [observation("UNSAFE")])
    assert first.scan.status is ScanStatus.COMPLETED
    assert first.scan.safety_mode is SafetyMode.SAFE
    assert first.scan.requests_planned == first.scan.requests_sent == 1
    assert first.scan.requests_failed == 0
    assert len(first.executions) == len(first.findings) == 1
    assert first.findings[0].classification is EvaluationClassification.CONFIRMED
    assert first.findings[0].fingerprint == second.findings[0].fingerprint
    assert first.scan.finding_counts == {"high": 1}


def test_authorization_required_expired_and_production_restriction() -> None:
    with pytest.raises(ValidationError):
        plan(authorization_scope=AuthorizationScope())
    with pytest.raises(ValidationError):
        plan(authorization_scope=authorization(expired=True))
    with pytest.raises(ValueError, match="production targets require safe mode"):
        run(
            [make_case()],
            [],
            selected_plan=plan(
                authorization_scope=authorization(environment="production"),
                safety_mode=SafetyMode.CONTROLLED,
            ),
        )


def test_destructive_mode_and_capability_gates() -> None:
    destructive = make_case(
        side_effect_risk=SideEffectRisk.DESTRUCTIVE, default_safety_mode=SafetyMode.CONTROLLED
    )
    safe_result = run([destructive], [], selected_plan=plan())
    assert safe_result.scan.status is ScanStatus.COMPLETED_WITH_WARNINGS
    assert "destructive" in safe_result.warnings[0]
    with pytest.raises(ValueError, match="destructive-test capability"):
        run([destructive], [], selected_plan=plan(safety_mode=SafetyMode.DESTRUCTIVE))


def test_retrieval_tool_disabled_and_unsafe_tests_are_skipped() -> None:
    retrieval = make_case("retrieval", requires_retrieval=True)
    tool = make_case(
        "tool", requires_tool_access=True, payloads=[payload("tool-payload", tags=["canary"])]
    )
    disabled = make_case("disabled", enabled=False)
    unsafe = make_case(
        "unsafe",
        payloads=[payload("unsafe-payload", safe=False)],
        default_safety_mode=SafetyMode.CONTROLLED,
    )
    result = run([retrieval, tool, disabled, unsafe], [])
    assert result.executions == []
    assert len(result.warnings) == 4
    assert result.scan.status is ScanStatus.COMPLETED_WITH_WARNINGS


def test_deterministic_selection_category_language_and_tag_filters() -> None:
    first = make_case(
        "b-case", category="other", payloads=[payload("tr", language="tr", tags=["beta"])]
    )
    second = make_case(
        "a-case",
        payloads=[
            payload("en", language="en", tags=["alpha"]),
            payload("tr-2", language="tr", tags=["alpha"]),
        ],
    )
    result = run(
        [first, second],
        [observation("REFUSED")],
        selected_plan=plan(categories={"prompt_injection"}, languages={"tr"}, tags={"alpha"}),
    )
    assert [(item.test_case_id, item.payload_id) for item in result.executions] == [
        ("a-case", "tr-2")
    ]


def test_control_and_attack_execution_and_failed_control_behavior() -> None:
    selected_case = make_case(control_payload=payload("control"))
    result = run(
        [selected_case],
        [observation("generic"), observation("UNSAFE")],
        selected_plan=plan(run_controls=True),
    )
    assert [item.metadata["is_control"] for item in result.executions] == [True, False]
    assert len(result.findings) == 1
    failed_control = TargetErrorDetail(category=TargetErrorCategory.TIMEOUT, message="timed out")
    failed = run(
        [selected_case],
        [],
        selected_plan=plan(run_controls=True),
        failures={"invoke": failed_control},
    )
    assert failed.findings == []
    assert failed.scan.requests_failed >= 1
    assert "control failed" in failed.warnings[0]


@pytest.mark.parametrize(
    ("body", "classification", "finding_count"),
    [
        ("UNSAFE", EvaluationClassification.CONFIRMED, 1),
        ("prefix UNSAFE suffix", EvaluationClassification.PROBABLE, 0),
        ("MAYBE", EvaluationClassification.AMBIGUOUS, 1),
        ("REFUSED", EvaluationClassification.NOT_DETECTED, 0),
        ("", EvaluationClassification.INCONCLUSIVE, 0),
    ],
)
def test_finding_policy(
    body: str, classification: EvaluationClassification, finding_count: int
) -> None:
    selected_case = make_case(
        unsafe_indicators=["UNSAFE"] if "prefix" in body else ["exact:UNSAFE"]
    )
    result = run([selected_case], [observation(body)])
    assert result.executions[0].evaluation is not None
    assert result.executions[0].evaluation.classification is classification
    expected = 1 if classification is EvaluationClassification.PROBABLE else finding_count
    assert len(result.findings) == expected


def test_ambiguous_retention_policy() -> None:
    result = run(
        [make_case()], [observation("MAYBE")], selected_plan=plan(retain_ambiguous_findings=False)
    )
    assert result.executions[0].evaluation.classification is EvaluationClassification.AMBIGUOUS
    assert result.findings == []


def test_request_and_duration_budgets() -> None:
    controlled = make_case(control_payload=payload("control"))
    request_limited = run(
        [controlled],
        [observation("control")],
        selected_plan=plan(run_controls=True, request_budget=1),
    )
    assert len(request_limited.executions) == 1
    assert "request budget exhausted" in request_limited.warnings[-1]
    ticks = iter([0.0, 10.0])
    duration_limited = run(
        [make_case()],
        [],
        selected_plan=plan(duration_budget_seconds=1),
        monotonic_clock=lambda: next(ticks),
    )
    assert duration_limited.executions == []
    assert "duration budget exhausted" in duration_limited.warnings[0]


@pytest.mark.parametrize(
    "category",
    [
        TargetErrorCategory.TIMEOUT,
        TargetErrorCategory.RATE_LIMITED,
        TargetErrorCategory.MALFORMED_RESPONSE,
    ],
)
def test_target_failures_are_isolated_and_warn(category: TargetErrorCategory) -> None:
    result = run(
        [make_case()],
        [],
        failures={
            "invoke": TargetErrorDetail(category=category, message=f"{category.value} synthetic")
        },
    )
    assert result.executions[0].status.value == "failed"
    assert result.findings == []
    assert result.scan.status is ScanStatus.FAILED
    assert result.scan.requests_failed == 1


class RaisingEvaluator:
    def evaluate(self, *_: Any, **__: Any) -> Any:
        raise RuntimeError("synthetic evaluator failure")


class FailOnceEvaluator:
    def __init__(self) -> None:
        from ragscanner.evaluation import CompositeResponseEvaluator

        self._delegate = CompositeResponseEvaluator()
        self._calls = 0

    def evaluate(self, *args: Any, **kwargs: Any) -> Any:
        self._calls += 1
        if self._calls == 1:
            raise RuntimeError("first synthetic evaluator failure")
        return self._delegate.evaluate(*args, **kwargs)


def test_evaluator_failure_threshold_partial_failure_and_status() -> None:
    failed = run(
        [make_case()],
        [observation("UNSAFE")],
        evaluator=RaisingEvaluator(),
        selected_plan=plan(stop_on_failure_threshold=1),
    )
    assert failed.scan.status is ScanStatus.FAILED
    assert failed.executions[0].metadata["error_category"] == "unexpected"
    partial = run(
        [make_case("a"), make_case("b")],
        [observation("UNSAFE"), observation("REFUSED")],
        evaluator=FailOnceEvaluator(),
    )
    assert partial.scan.status is ScanStatus.COMPLETED_WITH_WARNINGS
    assert len(partial.executions) == 2
    assert partial.scan.requests_failed == 1


def test_stop_on_critical() -> None:
    critical = make_case("a-critical", severity=Severity.CRITICAL)
    later = make_case("b-later")
    result = run(
        [later, critical], [observation("UNSAFE")], selected_plan=plan(stop_on_critical=True)
    )
    assert len(result.executions) == 1
    assert "critical" in result.warnings[-1]


class CollectingSink:
    def __init__(self) -> None:
        self.events: list[ActiveScanEvent] = []

    async def emit(self, event: ActiveScanEvent) -> None:
        self.events.append(event)


def test_event_order_and_multilingual_payloads() -> None:
    sink = CollectingSink()
    cases = [make_case(payloads=[payload("en", language="en"), payload("tr", language="tr")])]
    result = run(cases, [observation("REFUSED"), observation("REFUSED")], event_sink=sink)
    assert [item.payload_id for item in result.executions] == ["en", "tr"]
    event_types = [event.event_type.value for event in sink.events]
    assert event_types[0] == "scan_started"
    assert event_types[-1] == "scan_completed"
    assert event_types.count("evaluation_completed") == 2


def test_control_runs_once_for_multiple_variants_and_render_failure_is_isolated() -> None:
    controlled = make_case(
        payloads=[payload("attack-a"), payload("attack-b")],
        control_payload=payload("control"),
    )
    result = run(
        [controlled],
        [observation("control"), observation("REFUSED"), observation("REFUSED")],
        selected_plan=plan(run_controls=True),
    )
    assert result.scan.requests_planned == result.scan.requests_sent == 3
    assert sum(bool(item.metadata["is_control"]) for item in result.executions) == 1

    invalid = payload("invalid", content="{{UNKNOWN_RUNTIME_VALUE}}")
    invalid.placeholders = ["UNKNOWN_RUNTIME_VALUE"]
    isolated = run([make_case(payloads=[invalid])], [])
    assert isolated.executions == []
    assert isolated.scan.status is ScanStatus.COMPLETED_WITH_WARNINGS
    assert "render failed" in isolated.warnings[0]


def test_cancellation_before_and_during_execution() -> None:
    async def before() -> Any:
        runner = ActiveSecurityScanRunner(
            adapter=fake_adapter([]),
            library=ActiveTestLibrary([make_case()]),
            clock=lambda: NOW,
            monotonic_clock=lambda: 0.0,
        )
        await runner.cancel()
        return await runner.run(plan())

    assert asyncio.run(before()).scan.status is ScanStatus.CANCELLED

    class CancellingSink:
        runner: ActiveSecurityScanRunner | None = None

        async def emit(self, event: ActiveScanEvent) -> None:
            if event.event_type.value == "invocation_started" and self.runner:
                await self.runner.cancel()

    async def during() -> Any:
        sink = CancellingSink()
        runner = ActiveSecurityScanRunner(
            adapter=fake_adapter([observation("UNSAFE")]),
            library=ActiveTestLibrary([make_case()]),
            event_sink=sink,
            clock=lambda: NOW,
            monotonic_clock=lambda: 0.0,
        )
        sink.runner = runner
        return await runner.run(plan())

    assert asyncio.run(during()).scan.status is ScanStatus.CANCELLED


def test_secret_redaction_and_no_io_dependencies() -> None:
    failure = TargetErrorDetail(
        category=TargetErrorCategory.UNKNOWN,
        message="Bearer synthetic-secret-token-value",
    )
    result = run([make_case()], [], failures={"invoke": failure})
    assert "synthetic-secret" not in result.model_dump_json()
    forbidden = {"httpx", "requests", "socket", "pathlib", "subprocess", "sqlalchemy"}
    assert forbidden.isdisjoint(ActiveSecurityScanRunner.__init__.__globals__)
