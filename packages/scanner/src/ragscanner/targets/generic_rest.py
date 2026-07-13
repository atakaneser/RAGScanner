"""Provider-neutral JSON REST TargetAdapter with strict destination controls."""

import asyncio
import ipaddress
import json
import re
import socket
from collections.abc import Mapping
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import BaseModel, Field, field_validator, model_validator

from ragscanner.domain import (
    AuthorizationScope,
    HttpMethod,
    PayloadVariant,
    SafetyMode,
    SecurityTestCase,
    TargetBudget,
    TargetCapabilities,
    TargetCitation,
    TargetDescriptor,
    TargetError,
    TargetErrorCategory,
    TargetErrorDetail,
    TargetFunctionCall,
    TargetHealth,
    TargetHealthStatus,
    TargetInvocation,
    TargetObservation,
    TargetSession,
    TargetSourceDocument,
    TargetToolCall,
    TargetType,
)
from ragscanner.domain.helpers import contains_unreferenced_secret, is_secure_secret_reference
from ragscanner.secrets import SecretResolver
from ragscanner.version import __version__

_TEMPLATE = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
_ALLOWED_TEMPLATE_FIELDS = {"PAYLOAD", "SESSION_ID", "CANARY_TOKEN", "TEST_CASE_ID", "PAYLOAD_ID"}
_METADATA_IPS = {ipaddress.ip_address("169.254.169.254"), ipaddress.ip_address("100.100.100.200")}
_SENSITIVE_HEADERS = {"authorization", "cookie", "proxy-authorization", "x-api-key", "api-key"}


class GenericRestResponseMapping(BaseModel):
    response_text: str = Field(min_length=1)
    citations: str | None = None
    source_documents: str | None = None
    tool_calls: str | None = None
    function_calls: str | None = None
    model_name: str | None = None
    finish_reason: str | None = None
    external_session_id: str | None = None

    @field_validator(
        "response_text",
        "citations",
        "source_documents",
        "tool_calls",
        "function_calls",
        "model_name",
        "finish_reason",
        "external_session_id",
    )
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*", value):
            raise ValueError("response mappings must use restricted dotted paths")
        return value


class GenericRestTargetConfig(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    endpoint_path: str = Field(min_length=1)
    method: HttpMethod = HttpMethod.POST
    static_headers: dict[str, str] = Field(default_factory=dict)
    secret_header_references: dict[str, str] = Field(default_factory=dict)
    request_body_template: dict[str, Any]
    response_mapping: GenericRestResponseMapping
    timeout_seconds: float = Field(default=30, gt=0, le=300)
    delay_seconds: float = Field(default=0, ge=0, le=3600)
    maximum_requests: int = Field(default=100, gt=0)
    verify_tls: bool = True
    allowed_hosts: set[str] = Field(min_length=1)
    allowed_ports: set[int] = Field(default_factory=lambda: {443}, min_length=1)
    allow_redirects: bool = False
    max_redirects: int = Field(default=3, ge=0, le=10)
    maximum_response_size: int = Field(default=1_048_576, gt=0, le=50_000_000)
    health_check_path: str | None = None
    allow_private_networks: bool = False
    configuration_reference: str
    retrieval_present: bool = False

    @model_validator(mode="after")
    def validate_configuration(self) -> "GenericRestTargetConfig":
        parsed = urlsplit(self.base_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url must use HTTP or HTTPS")
        if parsed.username or parsed.password:
            raise ValueError("base_url cannot contain embedded credentials")
        if parsed.fragment:
            raise ValueError("base_url cannot contain a fragment")
        if parsed.query:
            raise ValueError("base_url cannot contain query parameters")
        if not parsed.hostname:
            raise ValueError("base_url requires a hostname")
        normalized_hosts = {host.casefold().rstrip(".") for host in self.allowed_hosts}
        if parsed.hostname.casefold().rstrip(".") not in normalized_hosts:
            raise ValueError("base_url host must be explicitly allowed")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in self.allowed_ports:
            raise ValueError("base_url port is not allowed")
        for path in (self.endpoint_path, self.health_check_path):
            if path is not None and (not path.startswith("/") or path.startswith("//")):
                raise ValueError("endpoint paths must be absolute paths on the configured host")
            if path is not None and (urlsplit(path).fragment or contains_unreferenced_secret(path)):
                raise ValueError("endpoint paths cannot contain fragments or secret query values")
        if contains_unreferenced_secret(self.static_headers):
            raise ValueError("static headers cannot contain credentials")
        if any(name.casefold() in _SENSITIVE_HEADERS for name in self.static_headers):
            raise ValueError("sensitive headers must use secret_header_references")
        if any(
            not is_secure_secret_reference(reference)
            for reference in self.secret_header_references.values()
        ):
            raise ValueError("secret headers must use approved external references")
        if not is_secure_secret_reference(self.configuration_reference):
            raise ValueError("configuration_reference must be an approved external reference")
        _validate_template(self.request_body_template)
        return self


@runtime_checkable
class DestinationResolver(Protocol):
    async def resolve(self, hostname: str, port: int) -> list[str]: ...


class SystemDestinationResolver:
    async def resolve(self, hostname: str, port: int) -> list[str]:
        loop = asyncio.get_running_loop()
        records = await loop.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        return sorted({str(record[4][0]) for record in records})


def _validate_template(value: Any) -> None:
    if isinstance(value, str):
        unknown = set(_TEMPLATE.findall(value)) - _ALLOWED_TEMPLATE_FIELDS
        if unknown:
            raise ValueError(f"unknown request-template placeholders: {', '.join(sorted(unknown))}")
        if "${" in value or "{%" in value or "{{ " in value:
            raise ValueError("template expressions and expansion syntax are not allowed")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("request-template keys must be strings")
            _validate_template(item)
    elif isinstance(value, list):
        for item in value:
            _validate_template(item)
    elif value is not None and not isinstance(value, bool | int | float):
        raise ValueError("request template contains an unsupported value")


def render_json_template(template: dict[str, Any], values: Mapping[str, str]) -> dict[str, Any]:
    _validate_template(template)

    def render(value: Any) -> Any:
        if isinstance(value, str):
            exact = _TEMPLATE.fullmatch(value)
            if exact:
                return values[exact.group(1)]
            rendered = value
            for name in sorted(set(_TEMPLATE.findall(value))):
                rendered = rendered.replace(f"{{{{{name}}}}}", values[name])
            if _TEMPLATE.search(rendered):
                raise ValueError("recursive request templates are not allowed")
            return rendered
        if isinstance(value, dict):
            return {key: render(item) for key, item in value.items()}
        if isinstance(value, list):
            return [render(item) for item in value]
        return value

    required = set()
    serialized = json.dumps(template, ensure_ascii=False)
    required.update(_TEMPLATE.findall(serialized))
    if not required.issubset(values):
        raise ValueError("request template is missing placeholder values")
    result = render(template)
    if not isinstance(result, dict):
        raise ValueError("rendered request template must remain a JSON object")
    return result


def _extract(value: Any, path: str | None) -> Any:
    if path is None:
        return None
    current = value
    for part in path.split("."):
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return None
            current = current[index]
        elif isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _target_error(
    category: TargetErrorCategory,
    message: str,
    *,
    target_id: str,
    invocation_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    retryable: bool = False,
) -> TargetError:
    return TargetError(
        TargetErrorDetail(
            category=category,
            message=message,
            target_id=target_id,
            invocation_id=invocation_id,
            metadata=metadata or {},
            retryable=retryable,
        )
    )


class GenericRestTargetAdapter:
    """JSON REST transport only; it intentionally performs no vulnerability evaluation."""

    def __init__(
        self,
        *,
        config: GenericRestTargetConfig,
        authorization: AuthorizationScope | None,
        budget: TargetBudget,
        secret_resolver: SecretResolver,
        destination_resolver: DestinationResolver,
        client: httpx.AsyncClient | None = None,
        clock: datetime | None = None,
        canary_value: str | None = None,
    ) -> None:
        self.config = config
        self._authorization = authorization
        self._budget = budget
        self._secret_resolver = secret_resolver
        self._destination_resolver = destination_resolver
        self._clock = clock
        self._canary_token = canary_value or "RAGSCANNER-CANARY"
        self._client = client or httpx.AsyncClient(
            verify=config.verify_tls,
            follow_redirects=False,
            timeout=httpx.Timeout(config.timeout_seconds),
            headers={"User-Agent": f"RAGScanner/{__version__}"},
        )
        self._owns_client = client is None
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._cancelled: set[str] = set()
        self._invocation_sequence = 0

    def _now(self) -> datetime:
        return self._clock or datetime.now(UTC)

    def _require_authorization(self) -> None:
        if self._authorization is None or not self._authorization.is_valid(self._now()):
            raise _target_error(
                TargetErrorCategory.AUTHORIZATION,
                "active request requires valid, unexpired authorization",
                target_id=self.config.id,
            )

    async def describe(self) -> TargetDescriptor:
        return TargetDescriptor(
            id=self.config.id,
            name=self.config.name,
            target_type=TargetType.GENERIC_REST,
            display_name=self.config.name,
            description="User-configured generic JSON REST target",
            capabilities=TargetCapabilities(
                chat_completion=True,
                retrieval_present=self.config.retrieval_present,
                citations_present=self.config.response_mapping.citations is not None,
                source_documents_present=self.config.response_mapping.source_documents is not None,
                tool_calls=self.config.response_mapping.tool_calls is not None,
                function_calls=self.config.response_mapping.function_calls is not None,
                conversation_state=self.config.response_mapping.external_session_id is not None,
                custom_headers=True,
                structured_output=True,
                request_cancellation=True,
                rate_limit_headers=True,
                safe_test_mode=True,
                remote=True,
            ),
            configuration_reference=self.config.configuration_reference,
            default_timeout_seconds=self.config.timeout_seconds,
            default_delay_seconds=self.config.delay_seconds,
            default_max_requests=self.config.maximum_requests,
            verify_tls=self.config.verify_tls,
        )

    async def health_check(self) -> TargetHealth:
        started = monotonic()
        try:
            url = self._url(self.config.health_check_path or self.config.endpoint_path)
            await self._validate_url(url)
            if self.config.health_check_path is not None:
                response = await self._client.get(
                    url, headers=await self._resolved_headers(), follow_redirects=False
                )
                if response.is_redirect or response.status_code >= 500:
                    raise _target_error(
                        TargetErrorCategory.UNAVAILABLE,
                        "configured health endpoint was unavailable",
                        target_id=self.config.id,
                    )
                if len(response.content) > self.config.maximum_response_size:
                    raise _target_error(
                        TargetErrorCategory.MALFORMED_RESPONSE,
                        "health response exceeded configured size limit",
                        target_id=self.config.id,
                    )
        except TargetError as error:
            return TargetHealth(
                status=TargetHealthStatus.UNAVAILABLE,
                checked_at=self._now(),
                latency_ms=(monotonic() - started) * 1000,
                message=str(error),
            )
        except httpx.HTTPError:
            return TargetHealth(
                status=TargetHealthStatus.UNAVAILABLE,
                checked_at=self._now(),
                latency_ms=(monotonic() - started) * 1000,
                message="configured health endpoint transport failed",
            )
        message = (
            "configured health endpoint reachable"
            if self.config.health_check_path is not None
            else "configuration and destination policy valid; no request sent"
        )
        return TargetHealth(
            status=TargetHealthStatus.HEALTHY,
            checked_at=self._now(),
            latency_ms=(monotonic() - started) * 1000,
            message=message,
        )

    async def prepare_invocation(
        self,
        test_case: SecurityTestCase,
        payload: PayloadVariant,
        session: TargetSession | None,
        safety_mode: SafetyMode = SafetyMode.SAFE,
    ) -> TargetInvocation:
        self._require_authorization()
        if self._budget_exhausted():
            raise _target_error(
                TargetErrorCategory.BUDGET_EXHAUSTED,
                "target budget is exhausted",
                target_id=self.config.id,
            )
        if safety_mode is SafetyMode.DESTRUCTIVE:
            raise _target_error(
                TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                "generic REST adapter does not enable destructive mode",
                target_id=self.config.id,
            )
        if safety_mode is SafetyMode.SAFE and (
            not payload.safe_for_production or test_case.default_safety_mode is not SafetyMode.SAFE
        ):
            raise _target_error(
                TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                "payload is not compatible with safe mode",
                target_id=self.config.id,
            )
        if test_case.requires_tool_access and safety_mode is SafetyMode.SAFE:
            if not {tag.casefold() for tag in payload.tags}.intersection(
                {"canary", "no-op", "noop", "dry-run", "simulated"}
            ):
                raise _target_error(
                    TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    "safe tool tests require canary or no-op behavior",
                    target_id=self.config.id,
                )
        values = {
            "PAYLOAD": payload.content,
            "SESSION_ID": session.external_session_id
            if session and session.external_session_id
            else "",
            "CANARY_TOKEN": self._canary_token,
            "TEST_CASE_ID": test_case.id,
            "PAYLOAD_ID": payload.id,
        }
        try:
            body = render_json_template(self.config.request_body_template, values)
        except (KeyError, ValueError) as error:
            raise _target_error(
                TargetErrorCategory.CONFIGURATION,
                "request template could not be rendered",
                target_id=self.config.id,
            ) from error
        self._invocation_sequence += 1
        return TargetInvocation(
            id=f"generic-rest-{self._invocation_sequence}",
            target_id=self.config.id,
            test_case_id=test_case.id,
            payload_id=payload.id,
            conversation_id=session.id if session else None,
            method=self.config.method,
            path=self.config.endpoint_path,
            headers={**self.config.static_headers, **self.config.secret_header_references},
            body=body,
            timeout_seconds=self.config.timeout_seconds,
            created_at=self._now(),
            safety_mode=safety_mode,
        )

    async def invoke(self, invocation: TargetInvocation) -> TargetObservation:
        self._require_authorization()
        if self._budget_exhausted(invocation.request_budget_cost):
            raise _target_error(
                TargetErrorCategory.BUDGET_EXHAUSTED,
                "target budget is exhausted",
                target_id=self.config.id,
                invocation_id=invocation.id,
            )
        if invocation.id in self._cancelled:
            raise _target_error(
                TargetErrorCategory.CANCELLED,
                "invocation was cancelled",
                target_id=self.config.id,
                invocation_id=invocation.id,
            )
        current = asyncio.current_task()
        if current is not None:
            self._tasks[invocation.id] = current
        try:
            async with asyncio.timeout(invocation.timeout_seconds):
                observation = await self._send(invocation)
        except TimeoutError as error:
            self._budget.failures += 1
            raise _target_error(
                TargetErrorCategory.TIMEOUT,
                "target request timed out",
                target_id=self.config.id,
                invocation_id=invocation.id,
                retryable=True,
            ) from error
        except asyncio.CancelledError as error:
            raise _target_error(
                TargetErrorCategory.CANCELLED,
                "invocation was cancelled",
                target_id=self.config.id,
                invocation_id=invocation.id,
            ) from error
        except TargetError:
            self._budget.failures += 1
            raise
        finally:
            self._tasks.pop(invocation.id, None)
        self._budget.requests_used += invocation.request_budget_cost
        if self.config.delay_seconds:
            await asyncio.sleep(self.config.delay_seconds)
        return observation

    def _budget_exhausted(self, request_cost: int = 1) -> bool:
        return (
            self._budget.is_exhausted(request_cost)
            or self._budget.requests_used + request_cost > self.config.maximum_requests
        )

    async def _send(self, invocation: TargetInvocation) -> TargetObservation:
        started = monotonic()
        url = self._url(invocation.path)
        headers = await self._resolved_headers()
        method = invocation.method.value
        body: dict[str, Any] | str | None = invocation.body
        redirect_count = 0
        while True:
            await self._validate_url(url)
            try:
                request = self._client.build_request(method, url, headers=headers, json=body)
                response = await self._client.send(request, stream=True, follow_redirects=False)
            except httpx.TimeoutException as error:
                raise _target_error(
                    TargetErrorCategory.TIMEOUT,
                    "target request timed out",
                    target_id=self.config.id,
                    invocation_id=invocation.id,
                    retryable=True,
                ) from error
            except httpx.TransportError as error:
                category = (
                    TargetErrorCategory.TLS_ERROR
                    if "ssl" in (type(error).__name__ + repr(error)).casefold()
                    else TargetErrorCategory.UNAVAILABLE
                )
                raise _target_error(
                    category,
                    "target transport failed",
                    target_id=self.config.id,
                    invocation_id=invocation.id,
                    retryable=True,
                ) from error
            if not response.is_redirect:
                break
            location = response.headers.get("location")
            await response.aclose()
            if not self.config.allow_redirects or not location:
                raise _target_error(
                    TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    "target redirect is disabled",
                    target_id=self.config.id,
                    invocation_id=invocation.id,
                )
            redirect_count += 1
            if redirect_count > self.config.max_redirects:
                raise _target_error(
                    TargetErrorCategory.INVALID_REQUEST,
                    "target exceeded configured redirect limit",
                    target_id=self.config.id,
                    invocation_id=invocation.id,
                )
            redirected = urljoin(url, location)
            await self._validate_url(redirected)
            if urlsplit(redirected).hostname != urlsplit(url).hostname:
                raise _target_error(
                    TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    "cross-host redirect is blocked to protect credentials",
                    target_id=self.config.id,
                    invocation_id=invocation.id,
                )
            url = redirected
            if response.status_code == 303:
                method, body = HttpMethod.GET.value, None
        try:
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > self.config.maximum_response_size:
                    raise _target_error(
                        TargetErrorCategory.MALFORMED_RESPONSE,
                        "target response exceeded configured size limit",
                        target_id=self.config.id,
                        invocation_id=invocation.id,
                    )
        finally:
            await response.aclose()
        if response.status_code == 429:
            raise _target_error(
                TargetErrorCategory.RATE_LIMITED,
                "target rate limit reached",
                target_id=self.config.id,
                invocation_id=invocation.id,
                metadata={"status_code": 429},
                retryable=True,
            )
        if response.status_code >= 500:
            raise _target_error(
                TargetErrorCategory.UNAVAILABLE,
                "target service unavailable",
                target_id=self.config.id,
                invocation_id=invocation.id,
                metadata={"status_code": response.status_code},
                retryable=True,
            )
        if response.status_code >= 400:
            raise _target_error(
                TargetErrorCategory.INVALID_REQUEST,
                "target rejected request",
                target_id=self.config.id,
                invocation_id=invocation.id,
                metadata={"status_code": response.status_code},
            )
        try:
            structured = json.loads(bytes(content))
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise _target_error(
                TargetErrorCategory.MALFORMED_RESPONSE,
                "target response was not valid JSON",
                target_id=self.config.id,
                invocation_id=invocation.id,
            ) from error
        return self._normalize(invocation, response, structured, (monotonic() - started) * 1000)

    async def _resolved_headers(self) -> dict[str, str]:
        headers = {"User-Agent": f"RAGScanner/{__version__}", **self.config.static_headers}
        for name, reference in self.config.secret_header_references.items():
            headers[name] = await self._secret_resolver.resolve(reference)
        return headers

    def _normalize(
        self,
        invocation: TargetInvocation,
        response: httpx.Response,
        structured: Any,
        latency_ms: float,
    ) -> TargetObservation:
        mapping = self.config.response_mapping
        text = _extract(structured, mapping.response_text)
        if not isinstance(text, str):
            raise _target_error(
                TargetErrorCategory.MALFORMED_RESPONSE,
                "required response text mapping was missing or not text",
                target_id=self.config.id,
                invocation_id=invocation.id,
            )
        citations = _extract(structured, mapping.citations) or []
        sources = _extract(structured, mapping.source_documents) or []
        tools = _extract(structured, mapping.tool_calls) or []
        functions = _extract(structured, mapping.function_calls) or []
        return TargetObservation(
            invocation_id=invocation.id,
            status_code=response.status_code,
            headers=dict(response.headers),
            body=text,
            structured_body=structured if isinstance(structured, dict | list) else None,
            citations=[
                TargetCitation(
                    reference=str(item.get("reference", item.get("id", "source"))),
                    excerpt=str(item.get("excerpt", "")),
                )
                if isinstance(item, dict)
                else TargetCitation(reference=str(item))
                for item in citations
            ]
            if isinstance(citations, list)
            else [],
            source_documents=[
                TargetSourceDocument(
                    id=str(item.get("id")) if item.get("id") is not None else None,
                    title=str(item.get("title")) if item.get("title") is not None else None,
                    excerpt=str(item.get("excerpt", item.get("content", ""))),
                )
                for item in sources
                if isinstance(item, dict)
            ]
            if isinstance(sources, list)
            else [],
            tool_calls=[
                TargetToolCall(
                    name=str(item.get("name", "tool")),
                    arguments=item.get("arguments", {})
                    if isinstance(item.get("arguments", {}), dict)
                    else {},
                )
                for item in tools
                if isinstance(item, dict)
            ]
            if isinstance(tools, list)
            else [],
            function_calls=[
                TargetFunctionCall(
                    name=str(item.get("name", "function")),
                    arguments=item.get("arguments", {})
                    if isinstance(item.get("arguments", {}), dict)
                    else {},
                )
                for item in functions
                if isinstance(item, dict)
            ]
            if isinstance(functions, list)
            else [],
            model_name=str(value)
            if (value := _extract(structured, mapping.model_name)) is not None
            else None,
            finish_reason=str(value)
            if (value := _extract(structured, mapping.finish_reason)) is not None
            else None,
            external_session_id=str(value)
            if (value := _extract(structured, mapping.external_session_id)) is not None
            else None,
            latency_ms=latency_ms,
            received_at=self._now(),
        )

    def _url(self, path: str) -> str:
        return self.config.base_url.rstrip("/") + path

    async def _validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise _target_error(
                TargetErrorCategory.CONFIGURATION, "target URL is invalid", target_id=self.config.id
            )
        if parsed.username or parsed.password or parsed.fragment:
            raise _target_error(
                TargetErrorCategory.CONFIGURATION,
                "target URL contains forbidden credentials or fragment",
                target_id=self.config.id,
            )
        host = parsed.hostname.casefold().rstrip(".")
        if host not in {item.casefold().rstrip(".") for item in self.config.allowed_hosts}:
            raise _target_error(
                TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                "target host is not allowed",
                target_id=self.config.id,
            )
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port not in self.config.allowed_ports:
            raise _target_error(
                TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                "target port is not allowed",
                target_id=self.config.id,
            )
        addresses = await self._destination_resolver.resolve(host, port)
        if not addresses:
            raise _target_error(
                TargetErrorCategory.UNAVAILABLE,
                "target hostname did not resolve",
                target_id=self.config.id,
                retryable=True,
            )
        for raw_address in addresses:
            try:
                address = ipaddress.ip_address(raw_address)
            except ValueError as error:
                raise _target_error(
                    TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    "target resolved to an invalid address",
                    target_id=self.config.id,
                ) from error
            if (
                address in _METADATA_IPS
                or address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_unspecified
            ):
                raise _target_error(
                    TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    "target resolved to a blocked address",
                    target_id=self.config.id,
                )
            if address.is_private and not self.config.allow_private_networks:
                raise _target_error(
                    TargetErrorCategory.UNSAFE_OPERATION_BLOCKED,
                    "private target requires explicit opt-in",
                    target_id=self.config.id,
                )

    async def create_session(self) -> TargetSession | None:
        return None

    async def close_session(self, session: TargetSession) -> None:
        return None

    async def discover_models(self) -> list[str]:
        raise _target_error(
            TargetErrorCategory.UNSUPPORTED,
            "generic REST model discovery is unsupported",
            target_id=self.config.id,
        )

    async def cancel(self, invocation_id: str) -> bool:
        self._cancelled.add(invocation_id)
        task = self._tasks.get(invocation_id)
        if task is not None:
            task.cancel()
        return True

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
