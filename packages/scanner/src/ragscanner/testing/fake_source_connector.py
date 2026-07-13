"""Deterministic in-memory SourceConnector for contract tests."""

from ragscanner.domain.source import (
    SourceChange,
    SourceChangePage,
    SourceConnector,
    SourceContent,
    SourceCursor,
    SourceDescriptor,
    SourceError,
    SourceErrorCategory,
    SourceErrorDetail,
    SourceHealth,
    SourceItem,
    SourcePage,
)


class FakeSourceConnector(SourceConnector):
    def __init__(
        self,
        *,
        descriptor: SourceDescriptor,
        health: SourceHealth,
        items: list[SourceItem] | None = None,
        contents: dict[str, SourceContent] | None = None,
        changes: list[SourceChange] | None = None,
        failures: dict[str, SourceErrorDetail] | None = None,
        change_page_size: int = 100,
    ) -> None:
        if change_page_size < 1:
            raise ValueError("change_page_size must be positive")
        self._descriptor = descriptor
        self._health = health
        self._items = sorted(items or [], key=lambda item: item.id)
        self._items_by_id = {item.id: item for item in self._items}
        self._contents = dict(contents or {})
        self._changes = list(changes or [])
        self._failures = dict(failures or {})
        self._change_page_size = change_page_size

    def _fail_if_configured(self, operation: str) -> None:
        if detail := self._failures.get(operation):
            raise SourceError(detail)

    def _offset(self, cursor: SourceCursor | None) -> int:
        if cursor is None:
            return 0
        if cursor.source_id != self._descriptor.id:
            raise SourceError(
                SourceErrorDetail(
                    category=SourceErrorCategory.MALFORMED_RESPONSE,
                    message="cursor belongs to another source",
                    source_id=self._descriptor.id,
                )
            )
        try:
            return int(cursor.cursor_value)
        except ValueError as error:
            raise SourceError(
                SourceErrorDetail(
                    category=SourceErrorCategory.MALFORMED_RESPONSE,
                    message="invalid test cursor",
                    source_id=self._descriptor.id,
                )
            ) from error

    def _cursor(self, offset: int) -> SourceCursor:
        return SourceCursor(
            source_id=self._descriptor.id,
            cursor_value=str(offset),
            created_at=self._health.checked_at,
        )

    async def describe(self) -> SourceDescriptor:
        self._fail_if_configured("describe")
        return self._descriptor.model_copy(deep=True)

    async def health_check(self) -> SourceHealth:
        self._fail_if_configured("health_check")
        return self._health.model_copy(deep=True)

    async def list_items(self, cursor: SourceCursor | None, limit: int) -> SourcePage:
        self._fail_if_configured("list_items")
        if limit < 1:
            raise ValueError("limit must be positive")
        offset = self._offset(cursor)
        page_items = self._items[offset : offset + limit]
        next_offset = offset + len(page_items)
        has_more = next_offset < len(self._items)
        return SourcePage(
            items=[item.model_copy(deep=True) for item in page_items],
            next_cursor=self._cursor(next_offset) if has_more else None,
            has_more=has_more,
        )

    async def get_item(self, item_id: str) -> SourceItem:
        self._fail_if_configured("get_item")
        if item := self._items_by_id.get(item_id):
            return item.model_copy(deep=True)
        raise SourceError(
            SourceErrorDetail(
                category=SourceErrorCategory.NOT_FOUND,
                message="source item not found",
                source_id=self._descriptor.id,
                item_id=item_id,
            )
        )

    async def get_content(self, item_id: str, max_bytes: int) -> SourceContent:
        self._fail_if_configured("get_content")
        if max_bytes < 1:
            raise ValueError("max_bytes must be positive")
        content = self._contents.get(item_id)
        if content is None:
            raise SourceError(
                SourceErrorDetail(
                    category=SourceErrorCategory.NOT_FOUND,
                    message="source content not found",
                    source_id=self._descriptor.id,
                    item_id=item_id,
                )
            )
        if content.size_bytes > max_bytes:
            raise SourceError(
                SourceErrorDetail(
                    category=SourceErrorCategory.CONTENT_TOO_LARGE,
                    message="source content exceeds the requested byte limit",
                    source_id=self._descriptor.id,
                    item_id=item_id,
                )
            )
        return content.model_copy(deep=True, update={"limit_bytes": max_bytes})

    async def detect_changes(self, cursor: SourceCursor | None) -> SourceChangePage:
        self._fail_if_configured("detect_changes")
        offset = self._offset(cursor)
        page_items = self._changes[offset : offset + self._change_page_size]
        next_offset = offset + len(page_items)
        has_more = next_offset < len(self._changes)
        return SourceChangePage(
            items=[item.model_copy(deep=True) for item in page_items],
            next_cursor=self._cursor(next_offset) if has_more else None,
            has_more=has_more,
        )
