"""Safe, deterministic active black-box scan orchestration without persistence."""

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from time import monotonic
from typing import Any, Protocol, runtime_checkable

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from ragscanner.domain import (
    AnalysisMode,
    AuthorizationScope,
    EvaluationClassification,
    ExecutionStatus,
    Finding,
    PayloadVariant,
    SafetyMode,
    Scan,
    ScanStatus,
    ScanType,
    ScoreSummary,
    SecurityTestCase,
    Severity,
    SideEffectRisk,
    TargetAdapter,
    TargetError,
    TargetObservation,
    TestExecution,
)
from ragscanner.domain.helpers import (
    contains_unreferenced_secret,
    finding_fingerprint,
    mask_secret_like_values,
    test_execution_fingerprint,
    truncate_evidence,
)
from ragscanner.evaluation import CompositeResponseEvaluator
from ragscanner.security import ActiveTestLibrary, render_payload
from ragscanner.version import __version__


class ActiveScanEventType(StrEnum):
    SCAN_STARTED = "scan_started"
    TEST_SELECTED = "test_selected"
    TEST_SKIPPED = "test_skipped"
    CONTROL_STARTED = "control_started"
    CONTROL_COMPLETED = "control_completed"
    INVOCATION_STARTED = "invocation_started"
    INVOCATION_COMPLETED = "invocation_completed"
    EVALUATION_COMPLETED = "evaluation_completed"
    FINDING_CREATED = "finding_created"
    SCAN_WARNING = "scan_warning"
    SCAN_CANCELLED = "scan_cancelled"
    SCAN_COMPLETED = "scan_completed"


class ActiveScanEvent(BaseModel):
    event_type: ActiveScanEventType
    scan_id: str
    occurred_at: AwareDatetime
    test_case_id: str | None = None
    payload_id: str | None = None
    execution_id: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata")
    @classmethod
    def reject_secret_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        if contains_unreferenced_secret(value):
            raise ValueError("event metadata cannot contain secrets")
        return value


@runtime_checkable
class ActiveScanEventSink(Protocol):
    async def emit(self, event: ActiveScanEvent) -> None: ...


class NoOpActiveScanEventSink:
    async def emit(self, event: ActiveScanEvent) -> None:
        return None


@runtime_checkable
class ResponseEvaluator(Protocol):
    def evaluate(
        self,
        test_case: SecurityTestCase,
        payload: PayloadVariant,
        observation: TargetObservation,
        control_observation: TargetObservation | None = None,
    ) -> Any: ...


class ActiveScanPlan(BaseModel):
    scan_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    test_case_ids: set[str] = Field(default_factory=set)
    categories: set[str] = Field(default_factory=set)
    languages: set[str] = Field(default_factory=set)
    tags: set[str] = Field(default_factory=set)
    safety_mode: SafetyMode = SafetyMode.SAFE
    analysis_mode: AnalysisMode = AnalysisMode.OFFLINE
    request_budget: int = Field(default=100, gt=0)
    duration_budget_seconds: float = Field(default=300, gt=0)
    concurrency: int = Field(default=1, ge=1, le=1)
    run_controls: bool = True
    retain_ambiguous_findings: bool = True
    stop_on_critical: bool = False
    stop_on_failure_threshold: int = Field(default=5, gt=0)
    canary_token: str = Field(default="RAGSCANNER-CANARY", min_length=1, max_length=128)
    authorization_scope: AuthorizationScope
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_plan(self) -> "ActiveScanPlan":
        if not self.authorization_scope.is_valid():
            raise ValueError("active scan requires valid, unexpired authorization")
        if contains_unreferenced_secret(self.metadata) or contains_unreferenced_secret(
            self.canary_token
        ):
            raise ValueError("scan plan cannot contain credentials")
        return self


class ActiveScanResult(BaseModel):
    scan: Scan
    executions: list[TestExecution] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    score_summary: ScoreSummary | None = None
    started_at: AwareDatetime
    completed_at: AwareDatetime
    cancelled: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class _SelectedPayload(BaseModel):
    test_case: SecurityTestCase
    payload: PayloadVariant


class ActiveSecurityScanRunner:
    def __init__(
        self,
        *,
        adapter: TargetAdapter,
        library: ActiveTestLibrary,
        evaluator: ResponseEvaluator | None = None,
        event_sink: ActiveScanEventSink | None = None,
        clock: Callable[[], datetime] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self._adapter = adapter
        self._library = library
        self._evaluator = evaluator or CompositeResponseEvaluator()
        self._event_sink = event_sink or NoOpActiveScanEventSink()
        self._clock = clock or (lambda: datetime.now(UTC))
        self._monotonic = monotonic_clock or monotonic
        self._cancelled = False
        self._current_invocation_id: str | None = None

    async def cancel(self) -> None:
        self._cancelled = True
        if self._current_invocation_id is not None:
            await self._adapter.cancel(self._current_invocation_id)

    async def run(self, plan: ActiveScanPlan) -> ActiveScanResult:
        started_at = self._now()
        started_monotonic = self._monotonic()
        descriptor = await self._adapter.describe()
        if descriptor.id != plan.target_id:
            raise ValueError("scan target does not match adapter target")
        if not plan.authorization_scope.is_valid(started_at):
            raise ValueError("active scan authorization is missing or expired")
        if (
            plan.safety_mode is SafetyMode.DESTRUCTIVE
            and not descriptor.capabilities.destructive_test_mode
        ):
            raise ValueError("target does not declare destructive-test capability")
        if plan.safety_mode is SafetyMode.SAFE and not descriptor.capabilities.safe_test_mode:
            raise ValueError("target does not declare safe-test capability")
        if (plan.authorization_scope.environment or "").casefold() in {
            "production",
            "prod",
        } and plan.safety_mode is not SafetyMode.SAFE:
            raise ValueError("production targets require safe mode")

        warnings: list[str] = []
        errors: list[str] = []
        executions: list[TestExecution] = []
        findings: list[Finding] = []
        await self._emit(plan, ActiveScanEventType.SCAN_STARTED)
        selected = await self._select(plan, descriptor.capabilities, warnings)
        control_case_ids = {
            item.test_case.id
            for item in selected
            if plan.run_controls and item.test_case.control_payload is not None
        }
        planned_requests = len(selected) + len(control_case_ids)
        scan = Scan(
            id=plan.scan_id,
            scan_type=ScanType.ACTIVE,
            target_id=plan.target_id,
            status=ScanStatus.RUNNING,
            mode=plan.analysis_mode,
            safety_mode=plan.safety_mode,
            authorization_scope=plan.authorization_scope,
            started_at=started_at,
            scanner_version=__version__,
            requests_planned=planned_requests,
            metadata={"concurrency": plan.concurrency},
        )
        requests_used = 0
        failures = 0
        control_observations: dict[str, TargetObservation | None] = {}

        for item in selected:
            if self._cancelled:
                break
            if self._duration_exhausted(plan, started_monotonic):
                warnings.append("scan duration budget exhausted")
                break
            await self._emit(
                plan,
                ActiveScanEventType.TEST_SELECTED,
                test_case_id=item.test_case.id,
                payload_id=item.payload.id,
            )
            control_observation = control_observations.get(item.test_case.id)
            if (
                plan.run_controls
                and item.test_case.control_payload is not None
                and item.test_case.id not in control_observations
            ):
                if requests_used >= plan.request_budget:
                    warnings.append("request budget exhausted before control")
                    break
                try:
                    control_payload = self._render(
                        item.test_case.control_payload, plan, descriptor.name
                    )
                except ValueError:
                    failures += 1
                    control_observations[item.test_case.id] = None
                    warnings.append(f"control render failed for {item.test_case.id}")
                    await self._warning(plan, warnings[-1], item.test_case.id)
                else:
                    control_execution, control_observation, failed = await self._execute(
                        plan, item.test_case, control_payload, is_control=True
                    )
                    control_observations[item.test_case.id] = control_observation
                    executions.append(control_execution)
                    requests_used += 1
                    scan.requests_sent += 1
                    if failed:
                        failures += 1
                        scan.requests_failed += 1
                        warnings.append(f"control failed for {item.test_case.id}")
                        await self._warning(plan, warnings[-1], item.test_case.id)
                    if failures >= plan.stop_on_failure_threshold:
                        warnings.append("failure threshold reached")
                        break
            if failures >= plan.stop_on_failure_threshold:
                warnings.append("failure threshold reached")
                break
            if self._cancelled:
                break
            if requests_used >= plan.request_budget:
                warnings.append("request budget exhausted before attack payload")
                break
            if self._duration_exhausted(plan, started_monotonic):
                warnings.append("scan duration budget exhausted before attack payload")
                break
            try:
                rendered = self._render(item.payload, plan, descriptor.name)
            except ValueError:
                failures += 1
                warnings.append(f"payload render failed for {item.test_case.id}/{item.payload.id}")
                await self._warning(plan, warnings[-1], item.test_case.id)
                if failures >= plan.stop_on_failure_threshold:
                    warnings.append("failure threshold reached")
                    break
                continue
            execution, _attack_observation, failed = await self._execute(
                plan,
                item.test_case,
                rendered,
                is_control=False,
                control_observation=control_observation,
            )
            executions.append(execution)
            requests_used += 1
            scan.requests_sent += 1
            if failed:
                failures += 1
                scan.requests_failed += 1
                warnings.append(
                    f"attack execution failed for {item.test_case.id}/{item.payload.id}"
                )
                await self._warning(plan, warnings[-1], item.test_case.id)
            elif execution.evaluation is not None:
                finding = self._finding(plan, item.test_case, execution, self._now())
                if finding is not None and (
                    finding.classification is not EvaluationClassification.AMBIGUOUS
                    or plan.retain_ambiguous_findings
                ):
                    findings.append(finding)
                    await self._emit(
                        plan,
                        ActiveScanEventType.FINDING_CREATED,
                        test_case_id=item.test_case.id,
                        payload_id=item.payload.id,
                        execution_id=execution.id,
                    )
                    if plan.stop_on_critical and finding.severity is Severity.CRITICAL:
                        warnings.append("stopped after critical finding")
                        break
            if self._duration_exhausted(plan, started_monotonic):
                warnings.append("scan duration budget exhausted after request")
                break
            if failures >= plan.stop_on_failure_threshold:
                warnings.append("failure threshold reached")
                break

        completed_at = self._now()
        if self._cancelled:
            status = ScanStatus.CANCELLED
            await self._emit(plan, ActiveScanEventType.SCAN_CANCELLED)
        elif errors or (
            executions and all(item.status is ExecutionStatus.FAILED for item in executions)
        ):
            status = ScanStatus.FAILED
        elif warnings or failures:
            status = ScanStatus.COMPLETED_WITH_WARNINGS
        else:
            status = ScanStatus.COMPLETED
        scan.status = status
        scan.completed_at = completed_at
        scan.warnings = list(warnings)
        scan.errors = list(errors)
        scan.finding_counts = self._finding_counts(findings)
        await self._emit(plan, ActiveScanEventType.SCAN_COMPLETED, message=status.value)
        return ActiveScanResult(
            scan=scan,
            executions=executions,
            findings=findings,
            started_at=started_at,
            completed_at=completed_at,
            cancelled=self._cancelled,
            warnings=warnings,
            errors=errors,
            metadata={"selected_payloads": len(selected), "failures": failures},
        )

    async def _select(
        self, plan: ActiveScanPlan, capabilities: Any, warnings: list[str]
    ) -> list[_SelectedPayload]:
        selected: list[_SelectedPayload] = []
        for test_case in self._library.select(enabled=None):
            reason: str | None = None
            if not test_case.enabled:
                reason = "disabled test case"
            elif plan.test_case_ids and test_case.id not in plan.test_case_ids:
                continue
            elif plan.categories and test_case.category not in plan.categories:
                continue
            elif plan.tags and not (
                plan.tags.intersection(test_case.tags)
                or any(plan.tags.intersection(payload.tags) for payload in test_case.payloads)
            ):
                continue
            elif test_case.requires_retrieval and not capabilities.retrieval_present:
                reason = "retrieval capability not declared"
            elif test_case.requires_tool_access and not (
                capabilities.tool_calls or capabilities.function_calls
            ):
                reason = "tool/function capability not declared"
            elif test_case.side_effect_risk is SideEffectRisk.DESTRUCTIVE and (
                plan.safety_mode is not SafetyMode.DESTRUCTIVE
            ):
                reason = "destructive test excluded by safety mode"
            if reason:
                warning = f"skipped {test_case.id}: {reason}"
                warnings.append(warning)
                await self._emit(
                    plan,
                    ActiveScanEventType.TEST_SKIPPED,
                    test_case_id=test_case.id,
                    message=reason,
                )
                continue
            variants = sorted(test_case.payloads, key=lambda payload: payload.id)
            if plan.languages:
                variants = [payload for payload in variants if payload.language in plan.languages]
            if plan.tags:
                variants = [
                    payload
                    for payload in variants
                    if plan.tags.intersection(payload.tags)
                    or plan.tags.intersection(test_case.tags)
                ]
            variants = [
                payload
                for payload in variants
                if not (plan.safety_mode is SafetyMode.SAFE and not payload.safe_for_production)
            ]
            if not variants:
                reason = "no compatible language/tag/safety payload variant"
                warnings.append(f"skipped {test_case.id}: {reason}")
                await self._emit(
                    plan,
                    ActiveScanEventType.TEST_SKIPPED,
                    test_case_id=test_case.id,
                    message=reason,
                )
                continue
            selected.extend(
                _SelectedPayload(test_case=test_case, payload=payload) for payload in variants
            )
        return sorted(selected, key=lambda item: (item.test_case.id, item.payload.id))

    def _render(
        self, payload: PayloadVariant, plan: ActiveScanPlan, target_name: str
    ) -> PayloadVariant:
        values = {
            "CANARY_TOKEN": plan.canary_token,
            "TEST_SESSION_ID": f"session-{plan.scan_id}",
            "SAFE_TOOL_NAME": "ragscanner_noop",
            "FAKE_DOCUMENT_NAME": "ragscanner-synthetic-document",
            "AUTHORIZED_TEST_USER": "authorized-test-user",
            "TARGET_NAME": target_name,
        }
        required = set(payload.placeholders)
        unknown = required - set(values)
        if unknown:
            raise ValueError(f"unknown runtime placeholders: {', '.join(sorted(unknown))}")
        return render_payload(payload, {name: values[name] for name in required})

    async def _execute(
        self,
        plan: ActiveScanPlan,
        test_case: SecurityTestCase,
        payload: PayloadVariant,
        *,
        is_control: bool,
        control_observation: TargetObservation | None = None,
    ) -> tuple[TestExecution, TargetObservation | None, bool]:
        started = self._now()
        execution_id = test_execution_fingerprint(
            target_id=plan.target_id,
            test_case_id=test_case.id,
            payload_id=payload.id,
            scan_id=plan.scan_id,
        )
        event = (
            ActiveScanEventType.CONTROL_STARTED
            if is_control
            else ActiveScanEventType.INVOCATION_STARTED
        )
        await self._emit(
            plan, event, test_case_id=test_case.id, payload_id=payload.id, execution_id=execution_id
        )
        try:
            invocation = await self._adapter.prepare_invocation(
                test_case, payload, None, plan.safety_mode
            )
            self._current_invocation_id = invocation.id
            if self._cancelled:
                await self._adapter.cancel(invocation.id)
            observation = await self._adapter.invoke(invocation)
            evaluation = (
                None
                if is_control
                else self._evaluator.evaluate(test_case, payload, observation, control_observation)
            )
            execution = TestExecution(
                id=execution_id,
                scan_id=plan.scan_id,
                target_id=plan.target_id,
                test_case_id=test_case.id,
                payload_id=payload.id,
                started_at=started,
                completed_at=self._now(),
                status=ExecutionStatus.COMPLETED,
                request_summary={"invocation_id": invocation.id, "is_control": is_control},
                response_summary={
                    "status_code": observation.status_code,
                    "body_sha256": hashlib.sha256(observation.body.encode()).hexdigest(),
                    "truncated": observation.truncated,
                },
                evaluation=evaluation,
                metadata={"is_control": is_control},
            )
            completed_event = (
                ActiveScanEventType.CONTROL_COMPLETED
                if is_control
                else ActiveScanEventType.INVOCATION_COMPLETED
            )
            await self._emit(
                plan,
                completed_event,
                test_case_id=test_case.id,
                payload_id=payload.id,
                execution_id=execution_id,
            )
            if evaluation is not None:
                await self._emit(
                    plan,
                    ActiveScanEventType.EVALUATION_COMPLETED,
                    test_case_id=test_case.id,
                    payload_id=payload.id,
                    execution_id=execution_id,
                    message=evaluation.classification.value,
                )
            return execution, observation, False
        except TargetError as error:
            safe_error = truncate_evidence(mask_secret_like_values(str(error)), 320)
            execution = TestExecution(
                id=execution_id,
                scan_id=plan.scan_id,
                target_id=plan.target_id,
                test_case_id=test_case.id,
                payload_id=payload.id,
                started_at=started,
                completed_at=self._now(),
                status=ExecutionStatus.FAILED,
                errors=[safe_error],
                metadata={"is_control": is_control, "error_category": error.detail.category.value},
            )
            return execution, None, True
        except Exception as error:
            safe_error = truncate_evidence(mask_secret_like_values(str(error)), 320)
            execution = TestExecution(
                id=execution_id,
                scan_id=plan.scan_id,
                target_id=plan.target_id,
                test_case_id=test_case.id,
                payload_id=payload.id,
                started_at=started,
                completed_at=self._now(),
                status=ExecutionStatus.FAILED,
                errors=[safe_error or "unexpected evaluator or adapter error"],
                metadata={"is_control": is_control, "error_category": "unexpected"},
            )
            return execution, None, True
        finally:
            self._current_invocation_id = None

    def _finding(
        self,
        plan: ActiveScanPlan,
        test_case: SecurityTestCase,
        execution: TestExecution,
        at: datetime,
    ) -> Finding | None:
        evaluation = execution.evaluation
        if evaluation is None or evaluation.classification not in {
            EvaluationClassification.CONFIRMED,
            EvaluationClassification.PROBABLE,
            EvaluationClassification.AMBIGUOUS,
        }:
            return None
        evidence = truncate_evidence(" | ".join(evaluation.evidence) or evaluation.explanation, 512)
        fingerprint = finding_fingerprint(
            rule_id=test_case.id,
            rule_version=test_case.version,
            source_id=None,
            document_id=None,
            chunk_id=None,
            target_id=plan.target_id,
            test_case_id=test_case.id,
            evidence=evidence,
        )
        return Finding(
            id=f"finding-{fingerprint[:16]}",
            fingerprint=fingerprint,
            category=test_case.category,
            scanner="active_response_evaluator",
            rule_id=test_case.id,
            rule_version=test_case.version,
            title=test_case.name,
            description=test_case.description,
            severity=test_case.severity,
            confidence=evaluation.confidence,
            detection_type=test_case.detection_type,
            classification=evaluation.classification,
            target_id=plan.target_id,
            test_case_id=test_case.id,
            execution_id=execution.id,
            evidence=evidence,
            impact=f"The target may not enforce the expected safe behavior: {test_case.expected_safe_behavior}",
            recommendation=test_case.remediation,
            references=test_case.references,
            first_seen=at,
            last_seen=at,
            metadata={"evaluator_type": evaluation.evaluator_type.value},
        )

    def _duration_exhausted(self, plan: ActiveScanPlan, started: float) -> bool:
        return self._monotonic() - started >= plan.duration_budget_seconds

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("runner clock must be timezone-aware")
        return value

    async def _emit(
        self,
        plan: ActiveScanPlan,
        event_type: ActiveScanEventType,
        *,
        test_case_id: str | None = None,
        payload_id: str | None = None,
        execution_id: str | None = None,
        message: str | None = None,
    ) -> None:
        try:
            await self._event_sink.emit(
                ActiveScanEvent(
                    event_type=event_type,
                    scan_id=plan.scan_id,
                    occurred_at=self._now(),
                    test_case_id=test_case_id,
                    payload_id=payload_id,
                    execution_id=execution_id,
                    message=message,
                )
            )
        except Exception:
            return None

    async def _warning(
        self, plan: ActiveScanPlan, message: str, test_case_id: str | None = None
    ) -> None:
        await self._emit(
            plan, ActiveScanEventType.SCAN_WARNING, test_case_id=test_case_id, message=message
        )

    @staticmethod
    def _finding_counts(findings: list[Finding]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for finding in findings:
            key = finding.severity.value
            counts[key] = counts.get(key, 0) + 1
        return counts
