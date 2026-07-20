"""Consent-gated website, sitemap, and accessible SharePoint content connector."""

import hashlib
import ipaddress
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse

import httpx
from defusedxml import ElementTree
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
from ragscanner.domain.helpers import is_secure_secret_reference


class WebsiteSourceConfig(BaseModel):
    """Bounded read-only web inventory configuration without raw credentials."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, max_length=4096)
    source_name: str = Field(default="Website", min_length=1, max_length=160)
    credential_ref: str | None = Field(default=None, max_length=500)
    content_consent: bool = False
    maximum_pages: int = Field(default=250, ge=1, le=2_000)
    maximum_file_size: int = Field(default=25 * 1024 * 1024, gt=0, le=100 * 1024 * 1024)
    timeout_seconds: float = Field(default=20, gt=0, le=120)

    @field_validator("credential_ref")
    @classmethod
    def validate_credential_ref(cls, value: str | None) -> str | None:
        if value is not None and not is_secure_secret_reference(value):
            raise ValueError("credential_ref must be an approved external secret reference")
        return value

    @model_validator(mode="after")
    def validate_url_and_consent(self) -> "WebsiteSourceConfig":
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("website URL must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("website URL cannot contain credentials or a fragment")
        loopback = parsed.hostname.casefold() == "localhost"
        try:
            address = ipaddress.ip_address(parsed.hostname)
            loopback = loopback or address.is_loopback
            if not loopback and (address.is_private or address.is_link_local):
                raise ValueError("private network website addresses are not supported")
        except ValueError as error:
            if "private network" in str(error):
                raise
        if not loopback and parsed.scheme != "https":
            raise ValueError("remote website scans require HTTPS")
        if not self.content_consent:
            raise ValueError("website content scans require explicit content consent")
        return self


class WebsiteSourceConnector(SourceConnector):
    """Read a single URL or same-origin sitemap without executing page content."""

    def __init__(
        self,
        config: WebsiteSourceConfig,
        *,
        bearer_token: str = "",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self._bearer_token = bearer_token.strip()
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(config.timeout_seconds), follow_redirects=False, trust_env=False
        )
        self._owns_client = client is None
        self._items: dict[str, SourceItem] = {}
        self._inventory_loaded = False

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def describe(self) -> SourceDescriptor:
        return SourceDescriptor(
            id=self._source_id,
            name="website",
            source_type="website.sitemap",
            display_name=self.config.source_name,
            description="Consent-gated website, sitemap, or accessible SharePoint content",
            capabilities=SourceCapabilities(
                discover_documents=True,
                read_document_content=True,
                read_metadata=True,
                remote=True,
                read_only=True,
            ),
            configuration_reference=self.config.credential_ref,
            metadata={"same_origin_only": True, "maximum_pages": self.config.maximum_pages},
        )

    async def health_check(self) -> SourceHealth:
        started = datetime.now(UTC)
        try:
            await self._request(self.config.url, maximum_bytes=64 * 1024)
        except SourceError as error:
            return SourceHealth(
                status=SourceHealthStatus.UNAVAILABLE,
                checked_at=started,
                message=str(error),
                details={"category": error.detail.category.value},
            )
        return SourceHealth(
            status=SourceHealthStatus.HEALTHY,
            checked_at=started,
            latency_ms=(datetime.now(UTC) - started).total_seconds() * 1000,
            message="Website source is accessible",
        )

    async def list_items(self, cursor: SourceCursor | None, limit: int) -> SourcePage:
        if not 1 <= limit <= 500:
            raise ValueError("limit must be between 1 and 500")
        if not self._inventory_loaded:
            await self._load_inventory()
        offset = 0
        if cursor is not None:
            if cursor.source_id != self._source_id or not cursor.cursor_value.startswith("offset:"):
                raise self._error(SourceErrorCategory.MALFORMED_RESPONSE, "invalid source cursor")
            try:
                offset = int(cursor.cursor_value.removeprefix("offset:"))
            except ValueError as error:
                raise self._error(
                    SourceErrorCategory.MALFORMED_RESPONSE, "invalid source cursor"
                ) from error
        inventory = list(self._items.values())
        items = inventory[offset : offset + limit]
        next_offset = offset + len(items)
        has_more = next_offset < len(inventory)
        next_cursor = (
            SourceCursor(
                source_id=self._source_id,
                cursor_value=f"offset:{next_offset}",
                created_at=datetime.now(UTC),
            )
            if has_more
            else None
        )
        return SourcePage(items=items, next_cursor=next_cursor, has_more=has_more)

    async def get_item(self, item_id: str) -> SourceItem:
        if not self._inventory_loaded:
            await self._load_inventory()
        item = self._items.get(item_id)
        if item is None:
            raise self._error(SourceErrorCategory.NOT_FOUND, "website item was not found")
        return item

    async def get_content(self, item_id: str, max_bytes: int) -> SourceContent:
        item = await self.get_item(item_id)
        url = str(item.metadata["url"])
        response = await self._request(
            url, maximum_bytes=min(max_bytes, self.config.maximum_file_size)
        )
        content_type = response.headers.get("content-type", item.mime_type or "text/html")
        content_type = content_type.split(";", 1)[0].strip().casefold()
        data = response.content
        return SourceContent(
            item=item.model_copy(update={"mime_type": content_type}),
            content_bytes=data,
            content_type=content_type,
            encoding="utf-8" if content_type.startswith("text/") else None,
            retrieved_at=datetime.now(UTC),
            checksum=hashlib.sha256(data).hexdigest(),
            limit_bytes=min(max_bytes, self.config.maximum_file_size),
            metadata={"remote_content_consent": True, "upstream": "website"},
        )

    async def detect_changes(self, cursor: SourceCursor | None) -> SourceChangePage:
        del cursor
        return SourceChangePage()

    async def _load_inventory(self) -> None:
        parsed = urlparse(self.config.url)
        looks_like_sitemap = (
            parsed.path.casefold().endswith(".xml") or "sitemap" in parsed.path.casefold()
        )
        urls = [self.config.url]
        if looks_like_sitemap:
            response = await self._request(self.config.url, maximum_bytes=2 * 1024 * 1024)
            is_index, urls = self._sitemap_urls(response.content)
            if is_index:
                nested_urls: list[str] = []
                for sitemap_url in urls[:20]:
                    nested = await self._request(sitemap_url, maximum_bytes=2 * 1024 * 1024)
                    nested_is_index, discovered = self._sitemap_urls(nested.content)
                    if not nested_is_index:
                        nested_urls.extend(discovered)
                    if len(nested_urls) >= self.config.maximum_pages:
                        break
                urls = nested_urls
        for url in urls[: self.config.maximum_pages]:
            if not self._same_origin(url):
                continue
            item = self._item(url)
            self._items[item.id] = item
        self._inventory_loaded = True

    def _sitemap_urls(self, content: bytes) -> tuple[bool, list[str]]:
        try:
            root = ElementTree.fromstring(content)
        except (ElementTree.ParseError, ValueError) as error:
            raise self._error(
                SourceErrorCategory.MALFORMED_RESPONSE, "website sitemap is not valid XML"
            ) from error
        urls: list[str] = []
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1].casefold() == "loc" and element.text:
                value = element.text.strip()
                if value and self._same_origin(value):
                    urls.append(value)
                if len(urls) >= self.config.maximum_pages:
                    break
        root_name = root.tag.rsplit("}", 1)[-1].casefold()
        return root_name == "sitemapindex", list(dict.fromkeys(urls))

    def _item(self, url: str) -> SourceItem:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        name = PurePosixPath(path).name or parsed.hostname or "index"
        if not PurePosixPath(name).suffix:
            name += ".html"
        item_id = hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]
        return SourceItem(
            id=item_id,
            source_id=self._source_id,
            external_id=url,
            name=name[:500],
            path=name[:500],
            mime_type=self._mime_type(name),
            metadata={"url": url},
        )

    async def _request(self, url: str, *, maximum_bytes: int) -> httpx.Response:
        if not self._same_origin(url):
            raise self._error(SourceErrorCategory.AUTHORIZATION, "cross-origin URL was rejected")
        headers = {"Accept": "text/html,application/xml,text/plain,application/pdf,*/*;q=0.2"}
        if self._bearer_token:
            headers["Authorization"] = f"Bearer {self._bearer_token}"
        try:
            response = await self._client.get(url, headers=headers)
        except httpx.TimeoutException as error:
            raise self._error(SourceErrorCategory.TIMEOUT, "website request timed out") from error
        except httpx.HTTPError as error:
            raise self._error(SourceErrorCategory.UNAVAILABLE, "website request failed") from error
        if response.status_code in {401, 403}:
            raise self._error(SourceErrorCategory.AUTHORIZATION, "website access was denied")
        if response.status_code == 404:
            raise self._error(SourceErrorCategory.NOT_FOUND, "website content was not found")
        if not 200 <= response.status_code < 300:
            raise self._error(
                SourceErrorCategory.UNAVAILABLE, "website returned an unsuccessful response"
            )
        if len(response.content) > maximum_bytes:
            raise self._error(SourceErrorCategory.CONTENT_TOO_LARGE, "website content is too large")
        return response

    def _same_origin(self, url: str) -> bool:
        expected = urlparse(self.config.url)
        candidate = urlparse(url)
        return (
            candidate.scheme == expected.scheme
            and (candidate.hostname or "").casefold() == (expected.hostname or "").casefold()
            and candidate.port == expected.port
            and not candidate.username
            and not candidate.password
            and not candidate.fragment
        )

    def _error(self, category: SourceErrorCategory, message: str) -> SourceError:
        return SourceError(
            SourceErrorDetail(
                category=category,
                message=message,
                retryable=category
                in {SourceErrorCategory.TIMEOUT, SourceErrorCategory.UNAVAILABLE},
                source_id=self._source_id,
            )
        )

    @property
    def _source_id(self) -> str:
        return f"website:{hashlib.sha256(self.config.url.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def _mime_type(name: str) -> str:
        extension = PurePosixPath(name).suffix.casefold()
        return {
            ".html": "text/html",
            ".htm": "text/html",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".pdf": "application/pdf",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }.get(extension, "text/html")
