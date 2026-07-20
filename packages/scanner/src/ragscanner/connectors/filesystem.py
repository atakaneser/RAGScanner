"""Root-confined local filesystem SourceConnector for text and Markdown files."""

import asyncio
import fnmatch
import hashlib
import os
import stat
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from ragscanner.domain import (
    SourceCapabilities,
    SourceChange,
    SourceChangePage,
    SourceChangeType,
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
    SourceWarning,
)
from ragscanner.domain.helpers import contains_unreferenced_secret

MIME_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".epub": "application/epub+zip",
    ".rst": "text/x-rst",
    ".adoc": "text/asciidoc",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".json": "application/json",
    ".jsonl": "application/x-ndjson",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".xml": "application/xml",
    ".html": "text/html",
    ".htm": "text/html",
    ".log": "text/plain",
}


class EncodingStrategy(StrEnum):
    STRICT = "strict"
    FALLBACK = "fallback"
    REPLACE = "replace"


class FilesystemSourceConfig(BaseModel):
    root_path: Path
    source_id: str = Field(default="local-filesystem", min_length=1)
    display_name: str = Field(default="Local filesystem", min_length=1)
    recursive: bool = True
    include_patterns: list[str] = Field(
        default_factory=lambda: [f"*{extension}" for extension in sorted(MIME_TYPES)]
    )
    exclude_patterns: list[str] = Field(default_factory=lambda: [".git/**", "**/.git/**"])
    follow_symlinks: bool = False
    maximum_file_size: int = Field(default=10 * 1024 * 1024, gt=0)
    maximum_discovered_files: int = Field(default=10_000, gt=0)
    allowed_extensions: set[str] = Field(default_factory=lambda: set(MIME_TYPES))
    encoding_strategy: EncodingStrategy = EncodingStrategy.STRICT
    fallback_encodings: list[str] = Field(default_factory=list)
    include_hidden: bool = False
    calculate_checksums: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("root_path")
    @classmethod
    def validate_explicit_root(cls, value: Path) -> Path:
        raw = str(value)
        if not value.is_absolute():
            raise ValueError("root_path must be an explicit absolute path")
        if value == Path(value.anchor):
            raise ValueError("filesystem root cannot be used as an unrestricted scan root")
        if any(marker in raw for marker in ("~", "$", "*", "?", "[", "]")):
            raise ValueError("root_path cannot use shell or environment expansion")
        return value

    @field_validator("allowed_extensions")
    @classmethod
    def validate_extensions(cls, value: set[str]) -> set[str]:
        normalized = {extension.casefold() for extension in value}
        if not normalized or any(extension not in MIME_TYPES for extension in normalized):
            raise ValueError("allowed_extensions contains an unsupported extension")
        return normalized

    @model_validator(mode="after")
    def validate_configuration(self) -> "FilesystemSourceConfig":
        if not self.include_patterns or any(
            "$" in pattern or "~" in pattern
            for pattern in [*self.include_patterns, *self.exclude_patterns]
        ):
            raise ValueError("glob patterns cannot use shell or environment expansion")
        if contains_unreferenced_secret(self.metadata):
            raise ValueError("filesystem metadata cannot contain credentials")
        for encoding in self.fallback_encodings:
            try:
                "".encode(encoding)
            except LookupError as error:
                raise ValueError(f"unknown fallback encoding: {encoding}") from error
        return self


class _DiscoveryResult(BaseModel):
    items: list[SourceItem] = Field(default_factory=list)
    warnings: list[SourceWarning] = Field(default_factory=list)


class LocalFilesystemConnector(SourceConnector):
    def __init__(self, config: FilesystemSourceConfig) -> None:
        self.config = config
        self._root = config.root_path.resolve(strict=False)
        self._item_paths: dict[str, Path] = {}
        self._page_snapshots: dict[str, list[SourceItem]] = {}
        self._change_snapshots: dict[str, dict[str, tuple[str, str]]] = {}

    async def describe(self) -> SourceDescriptor:
        return SourceDescriptor(
            id=self.config.source_id,
            name="filesystem",
            source_type="filesystem",
            display_name=self.config.display_name,
            description="Root-confined local document source",
            capabilities=SourceCapabilities(
                discover_documents=True,
                read_document_content=True,
                read_metadata=True,
                incremental_sync=True,
                change_detection=True,
                delete_detection=True,
                remote=False,
                read_only=True,
            ),
            metadata={"supported_extensions": sorted(self.config.allowed_extensions)},
        )

    async def health_check(self) -> SourceHealth:
        checked_at = datetime.now(UTC)
        try:
            self._validate_root()
        except SourceError as error:
            return SourceHealth(
                status=SourceHealthStatus.UNAVAILABLE,
                checked_at=checked_at,
                message=str(error),
            )
        return SourceHealth(
            status=SourceHealthStatus.HEALTHY,
            checked_at=checked_at,
            message="configured root is available",
        )

    async def list_items(self, cursor: SourceCursor | None, limit: int) -> SourcePage:
        if limit < 1:
            raise ValueError("limit must be positive")
        if cursor is None:
            result = await asyncio.to_thread(self._discover)
            snapshot_id = self._snapshot_id(result.items)
            self._page_snapshots[snapshot_id] = [
                item.model_copy(deep=True) for item in result.items
            ]
            items, offset, warnings = result.items, 0, result.warnings
        else:
            self._validate_cursor_source(cursor)
            parts = cursor.cursor_value.split(":", 2)
            if len(parts) != 3 or parts[0] != "page":
                raise self._error(
                    SourceErrorCategory.MALFORMED_RESPONSE, "invalid pagination cursor"
                )
            try:
                offset = int(parts[1])
            except ValueError as error:
                raise self._error(
                    SourceErrorCategory.MALFORMED_RESPONSE, "invalid pagination cursor"
                ) from error
            items = self._page_snapshots.get(parts[2], [])
            if not items:
                raise self._error(
                    SourceErrorCategory.MALFORMED_RESPONSE, "pagination snapshot is unavailable"
                )
            snapshot_id, warnings = parts[2], []
        page_items = items[offset : offset + limit]
        next_offset = offset + len(page_items)
        has_more = next_offset < len(items)
        return SourcePage(
            items=[item.model_copy(deep=True) for item in page_items],
            next_cursor=self._cursor(f"page:{next_offset}:{snapshot_id}") if has_more else None,
            has_more=has_more,
            warnings=warnings,
        )

    async def get_item(self, item_id: str) -> SourceItem:
        result = await asyncio.to_thread(self._discover)
        for item in result.items:
            if item.id == item_id:
                return item
        raise self._error(SourceErrorCategory.NOT_FOUND, "source item not found", item_id=item_id)

    async def get_content(self, item_id: str, max_bytes: int) -> SourceContent:
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        item = await self.get_item(item_id)
        path = self._item_paths.get(item_id)
        if path is None:
            raise self._error(
                SourceErrorCategory.NOT_FOUND, "source item path is unavailable", item_id=item_id
            )
        limit = min(max_bytes, self.config.maximum_file_size)
        data = await asyncio.to_thread(self._read_regular_file, path, limit, item_id)
        if (item.mime_type or "").startswith("text/") and self._binary_looking(data):
            raise self._error(
                SourceErrorCategory.MALFORMED_RESPONSE,
                "source content appears to be binary",
                item_id=item_id,
            )
        if (item.mime_type or "").startswith("text/"):
            encoding, warnings = self._select_encoding(data, item_id)
        else:
            encoding, warnings = None, []
        return SourceContent(
            item=item,
            content_bytes=data,
            content_type=item.mime_type or "application/octet-stream",
            encoding=encoding,
            retrieved_at=datetime.now(UTC),
            checksum=hashlib.sha256(data).hexdigest(),
            limit_bytes=limit,
            warnings=warnings,
            metadata={"raw_bytes_preserved": True},
        )

    async def detect_changes(self, cursor: SourceCursor | None) -> SourceChangePage:
        result = await asyncio.to_thread(self._discover)
        current = {item.external_id: (item.id, item.version or "") for item in result.items}
        previous: dict[str, tuple[str, str]] = {}
        if cursor is not None:
            self._validate_cursor_source(cursor)
            if not cursor.cursor_value.startswith("snapshot:"):
                raise self._error(SourceErrorCategory.MALFORMED_RESPONSE, "invalid change cursor")
            snapshot_id = cursor.cursor_value.removeprefix("snapshot:")
            if snapshot_id not in self._change_snapshots:
                raise self._error(
                    SourceErrorCategory.MALFORMED_RESPONSE, "change snapshot is unavailable"
                )
            previous = self._change_snapshots[snapshot_id]
        detected_at = datetime.now(UTC)
        changes: list[SourceChange] = []
        for external_id in sorted(current.keys() | previous.keys()):
            old = previous.get(external_id)
            new = current.get(external_id)
            if old is None and new is not None:
                change_type = SourceChangeType.ADDED
            elif new is None and old is not None:
                change_type = SourceChangeType.DELETED
            elif old != new:
                change_type = SourceChangeType.MODIFIED
            else:
                continue
            changes.append(
                SourceChange(
                    source_id=self.config.source_id,
                    item_id=(new or old or (None, ""))[0],
                    external_id=external_id,
                    change_type=change_type,
                    detected_at=detected_at,
                    previous_version=old[1] if old else None,
                    current_version=new[1] if new else None,
                )
            )
        snapshot_id = self._change_snapshot_id(current)
        self._change_snapshots[snapshot_id] = dict(current)
        return SourceChangePage(
            items=changes,
            next_cursor=self._cursor(f"snapshot:{snapshot_id}"),
            has_more=False,
            warnings=result.warnings,
        )

    def _discover(self) -> _DiscoveryResult:
        self._validate_root()
        warnings: list[SourceWarning] = []
        discovered: list[tuple[str, Path, os.stat_result]] = []
        stack = [self._root]
        visited: set[Path] = set()
        while stack:
            directory = stack.pop()
            try:
                resolved_directory = directory.resolve(strict=True)
            except OSError as error:
                raise self._error(
                    SourceErrorCategory.UNAVAILABLE,
                    "configured root or discovered directory disappeared",
                    retryable=True,
                ) from error
            if resolved_directory in visited:
                continue
            visited.add(resolved_directory)
            try:
                entries = sorted(os.scandir(directory), key=lambda entry: entry.name.casefold())
            except OSError:
                warnings.append(
                    SourceWarning(
                        code="directory_inaccessible",
                        message="A directory could not be read and was skipped.",
                    )
                )
                continue
            for entry in entries:
                logical_path = Path(entry.path)
                path = logical_path
                try:
                    if entry.is_symlink():
                        if not self.config.follow_symlinks:
                            warnings.append(
                                SourceWarning(
                                    code="symlink_skipped",
                                    message="A symbolic link was skipped by policy.",
                                )
                            )
                            continue
                        try:
                            resolved = path.resolve(strict=True)
                        except OSError:
                            warnings.append(
                                SourceWarning(
                                    code="broken_symlink",
                                    message="A broken symbolic link was skipped.",
                                )
                            )
                            continue
                        self._ensure_within_root(resolved)
                        path = resolved
                    info = path.stat(follow_symlinks=self.config.follow_symlinks)
                except SourceError:
                    raise
                except OSError:
                    warnings.append(
                        SourceWarning(
                            code="entry_inaccessible",
                            message="A filesystem entry could not be inspected and was skipped.",
                        )
                    )
                    continue
                mode = info.st_mode
                if stat.S_ISDIR(mode):
                    if self.config.recursive:
                        stack.append(path)
                    continue
                if not stat.S_ISREG(mode):
                    warnings.append(
                        SourceWarning(
                            code="special_file_skipped",
                            message="A non-regular filesystem entry was skipped.",
                        )
                    )
                    continue
                relative = logical_path.relative_to(self._root).as_posix()
                if not self.config.include_hidden and any(
                    part.startswith(".") for part in Path(relative).parts
                ):
                    continue
                extension = logical_path.suffix.casefold()
                if extension not in MIME_TYPES:
                    warnings.append(
                        SourceWarning(
                            code="unsupported_file_type",
                            message=f"Unsupported file extension {extension or '<none>'} was skipped.",
                        )
                    )
                    continue
                if extension not in self.config.allowed_extensions:
                    continue
                if not self._matches(relative):
                    continue
                discovered.append((relative, path, info))
                if len(discovered) >= self.config.maximum_discovered_files:
                    warnings.append(
                        SourceWarning(
                            code="discovery_limit_reached",
                            message="The configured discovery limit was reached.",
                        )
                    )
                    stack.clear()
                    break
        discovered.sort(key=lambda value: value[0].casefold())
        items = [self._item(relative, path, info) for relative, path, info in discovered]
        self._item_paths = {
            item.id: path for item, (_, path, _) in zip(items, discovered, strict=True)
        }
        return _DiscoveryResult(items=items, warnings=warnings)

    def _item(self, relative: str, path: Path, info: os.stat_result) -> SourceItem:
        external_id = relative
        item_id = hashlib.sha256(
            f"filesystem:v1:{self.config.source_id}:{relative}".encode()
        ).hexdigest()
        checksum: str | None = None
        if self.config.calculate_checksums and info.st_size <= self.config.maximum_file_size:
            checksum = hashlib.sha256(
                self._read_regular_file(path, self.config.maximum_file_size, item_id)
            ).hexdigest()
        version = f"{info.st_mtime_ns}:{info.st_size}:{checksum or '-'}"
        created_timestamp = getattr(info, "st_birthtime", None)
        return SourceItem(
            id=item_id,
            source_id=self.config.source_id,
            external_id=external_id,
            name=Path(relative).name,
            path=relative,
            mime_type=MIME_TYPES[Path(relative).suffix.casefold()],
            size_bytes=info.st_size,
            created_at=datetime.fromtimestamp(created_timestamp, UTC)
            if created_timestamp is not None
            else None,
            modified_at=datetime.fromtimestamp(info.st_mtime, UTC),
            version=version,
            checksum=checksum,
            metadata={"extension": Path(relative).suffix.casefold()},
        )

    def _read_regular_file(self, path: Path, limit: int, item_id: str) -> bytes:
        try:
            resolved = path.resolve(strict=True)
            self._ensure_within_root(resolved)
            flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
            if not self.config.follow_symlinks:
                flags |= getattr(os, "O_NOFOLLOW", 0)
                open_path = path
            else:
                open_path = resolved
            descriptor = os.open(open_path, flags)
            try:
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode):
                    raise self._error(
                        SourceErrorCategory.UNSUPPORTED,
                        "source item is not a regular file",
                        item_id=item_id,
                    )
                if info.st_size > limit:
                    raise self._error(
                        SourceErrorCategory.CONTENT_TOO_LARGE,
                        "source item exceeds the configured byte limit",
                        item_id=item_id,
                    )
                data = os.read(descriptor, limit + 1)
            finally:
                os.close(descriptor)
        except SourceError:
            raise
        except FileNotFoundError as error:
            raise self._error(
                SourceErrorCategory.NOT_FOUND,
                "source item disappeared before it could be read",
                item_id=item_id,
                retryable=True,
            ) from error
        except PermissionError as error:
            raise self._error(
                SourceErrorCategory.AUTHORIZATION, "source item is not readable", item_id=item_id
            ) from error
        except OSError as error:
            raise self._error(
                SourceErrorCategory.UNAVAILABLE,
                "source item could not be read",
                item_id=item_id,
                retryable=True,
            ) from error
        if len(data) > limit:
            raise self._error(
                SourceErrorCategory.CONTENT_TOO_LARGE,
                "source item exceeds the configured byte limit",
                item_id=item_id,
            )
        return data

    def _select_encoding(self, data: bytes, item_id: str) -> tuple[str, list[SourceWarning]]:
        if data.startswith(b"\xef\xbb\xbf"):
            return "utf-8-sig", []
        try:
            data.decode("utf-8")
            return "utf-8", []
        except UnicodeDecodeError:
            pass
        if self.config.encoding_strategy is EncodingStrategy.FALLBACK:
            for encoding in self.config.fallback_encodings:
                try:
                    data.decode(encoding)
                    return encoding, [
                        SourceWarning(
                            code="fallback_encoding",
                            message="Content required a configured fallback encoding.",
                            item_id=item_id,
                        )
                    ]
                except UnicodeDecodeError:
                    continue
        if self.config.encoding_strategy is EncodingStrategy.REPLACE:
            return "utf-8", [
                SourceWarning(
                    code="decoding_replacement_required",
                    message="Invalid UTF-8 will be replaced during parsing.",
                    item_id=item_id,
                )
            ]
        raise self._error(
            SourceErrorCategory.MALFORMED_RESPONSE,
            "source content is not valid text in configured encodings",
            item_id=item_id,
        )

    @staticmethod
    def _binary_looking(data: bytes) -> bool:
        sample = data[:4096]
        if b"\x00" in sample:
            return True
        if not sample:
            return False
        controls = sum(byte < 32 and byte not in {9, 10, 12, 13} for byte in sample)
        return controls / len(sample) > 0.3

    def _matches(self, relative: str) -> bool:
        included = any(
            fnmatch.fnmatchcase(relative, pattern)
            or fnmatch.fnmatchcase(relative, pattern.removeprefix("**/"))
            for pattern in self.config.include_patterns
        )
        excluded = any(
            fnmatch.fnmatchcase(relative, pattern)
            or fnmatch.fnmatchcase(relative, pattern.removeprefix("**/"))
            for pattern in self.config.exclude_patterns
        )
        return included and not excluded

    def _validate_root(self) -> None:
        if not self._root.exists():
            raise self._error(SourceErrorCategory.NOT_FOUND, "configured root does not exist")
        if not self._root.is_dir():
            raise self._error(
                SourceErrorCategory.CONFIGURATION, "configured root is not a directory"
            )

    def _ensure_within_root(self, path: Path) -> None:
        try:
            path.relative_to(self._root)
        except ValueError as error:
            raise self._error(
                SourceErrorCategory.AUTHORIZATION, "filesystem path escapes the configured root"
            ) from error

    def _validate_cursor_source(self, cursor: SourceCursor) -> None:
        if cursor.source_id != self.config.source_id:
            raise self._error(
                SourceErrorCategory.MALFORMED_RESPONSE, "cursor belongs to another source"
            )

    def _cursor(self, value: str) -> SourceCursor:
        return SourceCursor(
            source_id=self.config.source_id, cursor_value=value, created_at=datetime.now(UTC)
        )

    @staticmethod
    def _snapshot_id(items: list[SourceItem]) -> str:
        payload = "\n".join(f"{item.external_id}:{item.version}" for item in items)
        return hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _change_snapshot_id(snapshot: dict[str, tuple[str, str]]) -> str:
        payload = "\n".join(f"{key}:{value[1]}" for key, value in sorted(snapshot.items()))
        return hashlib.sha256(payload.encode()).hexdigest()

    def _error(
        self,
        category: SourceErrorCategory,
        message: str,
        *,
        item_id: str | None = None,
        retryable: bool = False,
    ) -> SourceError:
        return SourceError(
            SourceErrorDetail(
                category=category,
                message=message,
                source_id=self.config.source_id,
                item_id=item_id,
                retryable=retryable,
            )
        )
