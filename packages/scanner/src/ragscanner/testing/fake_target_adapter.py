"""Deterministic in-memory TargetAdapter for contract tests only."""

from datetime import datetime

from ragscanner.domain.active import AuthorizationScope, PayloadVariant, SecurityTestCase
from ragscanner.domain.enums import HttpMethod, SafetyMode
from ragscanner.domain.target import (
    TargetAdapter,
    TargetBudget,
    TargetDescriptor,
    TargetError,
    TargetErrorCategory,
    TargetErrorDetail,
    TargetHealth,
    TargetInvocation,
    TargetObservation,
    TargetSession,
)


class FakeTargetAdapter(TargetAdapter):
    def __init__(
        self,
        *,
        descriptor: TargetDescriptor,
        health: TargetHealth,
        authorization: AuthorizationScope | None,
        budget: TargetBudget,
        clock: datetime,
        observations: list[TargetObservation] | None = None,
        failures: dict[str, TargetErrorDetail] | None = None,
        models: list[str] | None = None,
    ) -> None:
        if clock.tzinfo is None:
            raise ValueError("clock must be timezone-aware")
        self._descriptor = descriptor
        self._health = health
        self._authorization = authorization
        self._budget = budget
        self._clock = clock
        self._observations = list(observations or [])
        self._failures = dict(failures or {})
        self._models = list(models or [])
        self._cancelled: set[str] = set()
        self.invocation_count = 0
        self._session_count = 0

    def _fail_if_configured(self, operation: str) -> None:
        if detail := self._failures.get(operation):
            if operation == "invoke":
                self._budget.failures += 1
            raise TargetError(detail)

    def _require_authorization(self) -> None:
        if self._authorization is None or not self._authorization.is_valid(self._clock):
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.AUTHORIZATION,
                    message="active invocation requires valid, unexpired authorization",
                    target_id=self._descriptor.id,
                )
            )

    async def describe(self) -> TargetDescriptor:
        self._fail_if_configured("describe")
        return self._descriptor.model_copy(deep=True)

    async def health_check(self) -> TargetHealth:
        self._fail_if_configured("health_check")
        return self._health.model_copy(deep=True)

    async def prepare_invocation(
        self,
        test_case: SecurityTestCase,
        payload: PayloadVariant,
        session: TargetSession | None,
        safety_mode: SafetyMode = SafetyMode.SAFE,
    ) -> TargetInvocation:
        self._fail_if_configured("prepare_invocation")
        self._require_authorization()
        capabilities = self._descriptor.capabilities
        if safety_mode is SafetyMode.SAFE and not capabilities.safe_test_mode:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.UNSUPPORTED,
                    message="target does not declare safe-test support",
                    target_id=self._descriptor.id,
                )
            )
        if safety_mode is SafetyMode.DESTRUCTIVE and not capabilities.destructive_test_mode:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    message="target does not declare destructive-test support",
                    target_id=self._descriptor.id,
                )
            )
        if safety_mode is SafetyMode.SAFE and not payload.safe_for_production:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    message="payload is not allowed in safe mode",
                    target_id=self._descriptor.id,
                )
            )
        if test_case.requires_tool_access and safety_mode is SafetyMode.SAFE:
            safe_tags = {tag.casefold() for tag in payload.tags}
            if not safe_tags.intersection({"canary", "no-op", "noop", "dry-run"}):
                raise TargetError(
                    TargetErrorDetail(
                        category=TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                        message="safe tool tests require canary or no-op behavior",
                        target_id=self._descriptor.id,
                    )
                )
        if session is not None and not capabilities.conversation_state:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.UNSUPPORTED,
                    message="target does not support conversational sessions",
                    target_id=self._descriptor.id,
                )
            )
        if self._budget.is_exhausted():
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.BUDGET_EXHAUSTED,
                    message="target request budget is exhausted",
                    target_id=self._descriptor.id,
                )
            )
        return TargetInvocation(
            id=f"invocation-{self.invocation_count + 1}",
            target_id=self._descriptor.id,
            test_case_id=test_case.id,
            payload_id=payload.id,
            conversation_id=session.id if session else None,
            method=HttpMethod.POST,
            path="/test",
            body={"input": payload.content},
            timeout_seconds=self._descriptor.default_timeout_seconds,
            created_at=self._clock,
            safety_mode=safety_mode,
        )

    async def invoke(self, invocation: TargetInvocation) -> TargetObservation:
        self._fail_if_configured("invoke")
        self._require_authorization()
        if invocation.id in self._cancelled:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.CANCELLED,
                    message="invocation was cancelled",
                    target_id=self._descriptor.id,
                    invocation_id=invocation.id,
                )
            )
        if self._budget.is_exhausted(invocation.request_budget_cost):
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.BUDGET_EXHAUSTED,
                    message="target request budget is exhausted",
                    target_id=self._descriptor.id,
                    invocation_id=invocation.id,
                )
            )
        if self.invocation_count >= len(self._observations):
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.MALFORMED_RESPONSE,
                    message="no predefined observation exists",
                    target_id=self._descriptor.id,
                    invocation_id=invocation.id,
                )
            )
        observation = self._observations[self.invocation_count].model_copy(
            deep=True, update={"invocation_id": invocation.id}
        )
        self.invocation_count += 1
        self._budget.requests_used += invocation.request_budget_cost
        return observation

    async def create_session(self) -> TargetSession | None:
        self._fail_if_configured("create_session")
        if not self._descriptor.capabilities.conversation_state:
            return None
        self._session_count += 1
        return TargetSession(
            id=f"session-{self._session_count}",
            target_id=self._descriptor.id,
            external_session_id=f"external-session-{self._session_count}",
            created_at=self._clock,
        )

    async def close_session(self, session: TargetSession) -> None:
        self._fail_if_configured("close_session")
        if not self._descriptor.capabilities.conversation_state:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.UNSUPPORTED,
                    message="target does not support conversational sessions",
                    target_id=self._descriptor.id,
                )
            )

    async def discover_models(self) -> list[str]:
        self._fail_if_configured("discover_models")
        if not self._descriptor.capabilities.model_discovery:
            raise TargetError(
                TargetErrorDetail(
                    category=TargetErrorCategory.UNSUPPORTED,
                    message="target does not support model discovery",
                    target_id=self._descriptor.id,
                )
            )
        return list(self._models)

    async def cancel(self, invocation_id: str) -> bool:
        self._fail_if_configured("cancel")
        if not self._descriptor.capabilities.request_cancellation:
            return False
        self._cancelled.add(invocation_id)
        return True
