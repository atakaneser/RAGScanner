"""Consent-gated OpenWebUI knowledge-base content connector."""

import hashlib
import ipaddress
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ragscanner.domain import (
    SourceCapabilities,
    SourceChangePage,
    SourceConnector,
    SourceContent,
    SourceCursor,
    SourceDescriptor,
    SourceError,
    SourceErrorCategory,
    SourceErrorDetail,
    SourceHealth,
    SourceHealthStatus,
    SourceItem,
    SourcePage,
)
from ragscanner.domain.helpers import is_secure_secret_reference, normalize_control_characters


class OpenWebUISourceConfig(BaseModel):
    """Non-secret connector configuration with explicit remote-content consent."""

    model_config = ConfigDict(extra="forbid")

    base_url: str = Field(min_length=1, max_length=2048)
    knowledge_id: str = Field(min_length=1, max_length=240)
    credential_ref: str = Field(min_length=1, max_length=500)
    content_consent: bool
    maximum_file_size: int = Field(default=25 * 1024 * 1024, gt=0, le=1024 * 1024 * 1024)
    maximum_discovered_files: int = Field(default=10_000, gt=0, le=100_000)
    timeout_seconds: float = Field(default=15, gt=0, le=120)
    page_size: int = Field(default=30, ge=1, le=200)

    @field_validator("credential_ref")
    @classmethod
    def validate_credential_ref(cls, value: str) -> str:
        if not is_secure_secret_reference(value):
            raise ValueError("credential_ref must be an approved external secret reference")
        return value

    @model_validator(mode="after")
    def validate_endpoint_and_consent(self) -> "OpenWebUISourceConfig":
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an absolute HTTP or HTTPS endpoint")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("base_url cannot contain credentials, query, or fragment")
        if parsed.path not in {"", "/"}:
            raise ValueError("base_url cannot contain an application path")
        loopback = parsed.hostname.casefold() == "localhost"
        try:
            loopback = loopback or ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            pass
        if parsed.scheme == "http" and not loopback:
            raise ValueError("non-loopback OpenWebUI endpoints require HTTPS")
        if not self.content_consent:
            raise ValueError("OpenWebUI document retrieval requires explicit content consent")
        return self


class OpenWebUISourceConnector(SourceConnector):
    """Read accessible OpenWebUI knowledge files without mutating the upstream service."""

    def __init__(
        self,
        config: OpenWebUISourceConfig,
        *,
        api_key: str,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenWebUI API key is required")
        self.config = config
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout_seconds),
            follow_redirects=False,
            trust_env=False,
        )
        self._owns_client = client is None
        self._items: dict[str, SourceItem] = {}

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def describe(self) -> SourceDescriptor:
        return SourceDescriptor(
            id=self._source_id,
            name="openwebui",
            source_type="openwebui.knowledge",
            display_name="OpenWebUI knowledge base",
            description="Consent-gated OpenWebUI knowledge-base files",
            capabilities=SourceCapabilities(
                discover_documents=True,
                read_document_content=True,
                read_metadata=True,
                incremental_sync=False,
                change_detection=False,
                delete_detection=False,
                remote=True,
                read_only=True,
            ),
            configuration_reference=self.config.credential_ref,
            metadata={
                "knowledge_id": self.config.knowledge_id,
                "loopback_endpoint": self._is_loopback,
            },
        )

    async def health_check(self) -> SourceHealth:
        started = datetime.now(UTC)
        try:
            await self._request_json(
                "GET",
                f"/api/v1/knowledge/{quote(self.config.knowledge_id, safe='')}",
                maximum_bytes=1_000_000,
            )
        except SourceError as error:
            return SourceHealth(
                status=SourceHealthStatus.UNAVAILABLE,
                checked_at=started,
                message=str(error),
                details={"category": error.detail.category.value},
            )
        latency = (datetime.now(UTC) - started).total_seconds() * 1000
        return SourceHealth(
            status=SourceHealthStatus.HEALTHY,
            checked_at=started,
            latency_ms=latency,
            message="OpenWebUI knowledge base is accessible",
        )

    async def list_items(self, cursor: SourceCursor | None, limit: int) -> SourcePage:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        page = 1
        offset = 0
        if cursor is not None:
            if cursor.source_id != self._source_id or not cursor.cursor_value.startswith("page:"):
                raise self._error(SourceErrorCategory.MALFORMED_RESPONSE, "invalid source cursor")
            try:
                cursor_parts = cursor.cursor_value.split(":")
                page = int(cursor_parts[1])
                offset = int(cursor_parts[2]) if len(cursor_parts) == 3 else 0
                if len(cursor_parts) not in {2, 3} or page < 1 or offset < 0:
                    raise ValueError
            except ValueError as error:
                raise self._error(
                    SourceErrorCategory.MALFORMED_RESPONSE, "invalid source cursor"
                ) from error
        payload = await self._request_json(
            "GET",
            f"/api/v1/knowledge/{quote(self.config.knowledge_id, safe='')}/files",
            params={"page": page, "include_content": "false"},
            maximum_bytes=2_000_000,
        )
        raw_items, total = self._page_items(payload)
        items: list[SourceItem] = []
        selected_items = raw_items[offset : offset + limit]
        for raw in selected_items:
            item = self._item(raw)
            if item is not None:
                items.append(item)
        for item in items:
            self._items[item.id] = item
        consumed = offset + len(selected_items)
        page_has_more = consumed < len(raw_items)
        seen = (page - 1) * self.config.page_size + len(raw_items)
        upstream_has_more = bool(raw_items) and (total is None or seen < total)
        has_more = page_has_more or upstream_has_more
        next_value = f"page:{page}:{consumed}" if page_has_more else f"page:{page + 1}:0"
        next_cursor = (
            SourceCursor(
                source_id=self._source_id,
                cursor_value=next_value,
                created_at=datetime.now(UTC),
            )
            if has_more
            else None
        )
        return SourcePage(items=items, next_cursor=next_cursor, has_more=has_more)

    async def get_item(self, item_id: str) -> SourceItem:
        if item_id in self._items:
            return self._items[item_id]
        payload = await self._request_json(
            "GET",
            f"/api/v1/files/{quote(item_id, safe='')}",
            maximum_bytes=1_000_000,
        )
        item = self._item(payload)
        if item is None:
            raise self._error(SourceErrorCategory.MALFORMED_RESPONSE, "invalid file metadata")
        self._items[item.id] = item
        return item

    async def get_content(self, item_id: str, max_bytes: int) -> SourceContent:
        item = await self.get_item(item_id)
        limit = min(max_bytes, self.config.maximum_file_size)
        request = self._client.build_request(
            "GET",
            self._url(f"/api/v1/files/{quote(item_id, safe='')}/content"),
            headers=self._headers,
        )
        try:
            response = await self._client.send(request, stream=True)
        except httpx.TimeoutException as error:
            raise self._error(
                SourceErrorCategory.TIMEOUT, "OpenWebUI content request timed out"
            ) from error
        except httpx.HTTPError as error:
            raise self._error(
                SourceErrorCategory.UNAVAILABLE, "OpenWebUI content request failed"
            ) from error
        try:
            self._raise_for_status(response)
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > limit:
                    raise self._error(
                        SourceErrorCategory.CONTENT_TOO_LARGE,
                        "OpenWebUI file exceeds the configured content limit",
                        item_id=item_id,
                    )
        finally:
            await response.aclose()
        data = bytes(content)
        content_type = response.headers.get(
            "content-type", item.mime_type or "application/octet-stream"
        )
        content_type = content_type.split(";", 1)[0].strip()
        return SourceContent(
            item=item,
            content_bytes=data,
            content_type=content_type,
            encoding="utf-8" if content_type.startswith("text/") else None,
            retrieved_at=datetime.now(UTC),
            checksum=hashlib.sha256(data).hexdigest(),
            limit_bytes=limit,
            metadata={"remote_content_consent": True, "upstream": "openwebui"},
        )

    async def detect_changes(self, cursor: SourceCursor | None) -> SourceChangePage:
        del cursor
        return SourceChangePage()

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        maximum_bytes: int,
    ) -> Any:
        try:
            response = await self._client.request(
                method,
                self._url(path),
                headers=self._headers,
                params=params,
            )
        except httpx.TimeoutException as error:
            raise self._error(SourceErrorCategory.TIMEOUT, "OpenWebUI request timed out") from error
        except httpx.HTTPError as error:
            raise self._error(
                SourceErrorCategory.UNAVAILABLE, "OpenWebUI request failed"
            ) from error
        self._raise_for_status(response)
        if len(response.content) > maximum_bytes:
            raise self._error(
                SourceErrorCategory.CONTENT_TOO_LARGE, "OpenWebUI response is too large"
            )
        try:
            return response.json()
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise self._error(
                SourceErrorCategory.MALFORMED_RESPONSE, "OpenWebUI returned malformed JSON"
            ) from error

    def _item(self, raw: Any) -> SourceItem | None:
        if not isinstance(raw, dict):
            return None
        if isinstance(raw.get("file"), dict):
            raw = raw["file"]
        item_id = self._safe_text(raw.get("id"), 160)
        meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        name = self._safe_text(meta.get("name") or raw.get("filename") or raw.get("name"), 500)
        if not item_id or not name:
            return None
        size = meta.get("size")
        return SourceItem(
            id=item_id,
            source_id=self._source_id,
            external_id=item_id,
            name=name,
            path=name,
            mime_type=self._safe_text(meta.get("content_type"), 200) or None,
            size_bytes=size if isinstance(size, int) and size >= 0 else None,
            version=self._safe_text(meta.get("file_hash") or raw.get("hash"), 200) or None,
            metadata={"knowledge_id": self.config.knowledge_id},
        )

    @staticmethod
    def _page_items(payload: Any) -> tuple[list[Any], int | None]:
        if isinstance(payload, list):
            return payload, None
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise SourceError(
                SourceErrorDetail(
                    category=SourceErrorCategory.MALFORMED_RESPONSE,
                    message="OpenWebUI returned an unsupported file-list schema",
                    source_id="openwebui",
                )
            )
        total = payload.get("total")
        return payload["items"], total if isinstance(total, int) else None

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code == 401:
            raise self._error(
                SourceErrorCategory.AUTHENTICATION, "OpenWebUI rejected the credential"
            )
        if response.status_code == 403:
            raise self._error(SourceErrorCategory.AUTHORIZATION, "OpenWebUI denied source access")
        if response.status_code == 404:
            raise self._error(SourceErrorCategory.NOT_FOUND, "OpenWebUI source was not found")
        if response.status_code == 429:
            raise self._error(SourceErrorCategory.RATE_LIMITED, "OpenWebUI rate limit was reached")
        if response.status_code < 200 or response.status_code >= 300:
            raise self._error(
                SourceErrorCategory.UNAVAILABLE, "OpenWebUI returned an unsuccessful response"
            )

    def _error(
        self,
        category: SourceErrorCategory,
        message: str,
        *,
        item_id: str | None = None,
    ) -> SourceError:
        return SourceError(
            SourceErrorDetail(
                category=category,
                message=message,
                retryable=category
                in {
                    SourceErrorCategory.TIMEOUT,
                    SourceErrorCategory.UNAVAILABLE,
                    SourceErrorCategory.RATE_LIMITED,
                },
                source_id=self._source_id,
                item_id=item_id,
            )
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}

    @property
    def _source_id(self) -> str:
        return f"openwebui:{self.config.knowledge_id}"

    @property
    def _is_loopback(self) -> bool:
        hostname = urlparse(self.config.base_url).hostname or ""
        if hostname.casefold() == "localhost":
            return True
        try:
            return ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            return False

    def _url(self, path: str) -> str:
        return f"{self.config.base_url.rstrip('/')}{path}"

    @staticmethod
    def _safe_text(value: Any, limit: int) -> str:
        return normalize_control_characters(value)[:limit] if isinstance(value, str) else ""
