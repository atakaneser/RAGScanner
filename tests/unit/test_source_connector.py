"""Contract tests for vendor-neutral static sources."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError
from ragscanner.domain import (
    SourceCapabilities,
    SourceChange,
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
)
from ragscanner.testing import FakeSourceConnector

NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


def descriptor(**changes: Any) -> SourceDescriptor:
    values: dict[str, Any] = {
        "id": "source-1",
        "name": "primary-knowledge",
        "source_type": "knowledge_base",
        "display_name": "Primary knowledge",
        "description": "Synthetic source",
        "capabilities": SourceCapabilities(
            discover_documents=True,
            read_document_content=True,
            read_metadata=True,
            change_detection=True,
            delete_detection=True,
        ),
        "configuration_reference": "env:RAGSCANNER_SOURCE_CONFIG",
    }
    values.update(changes)
    return SourceDescriptor(**values)


def item(number: int) -> SourceItem:
    return SourceItem(
        id=f"item-{number}",
        source_id="source-1",
        external_id=f"external-{number}",
        name=f"Document {number}",
        path=f"collection/document-{number}.txt",
        mime_type="text/plain",
        size_bytes=7,
        modified_at=NOW,
        version=str(number),
        metadata={"classification": "synthetic"},
    )


def content(source_item: SourceItem, data: bytes = b"content") -> SourceContent:
    return SourceContent(
        item=source_item,
        content_bytes=data,
        content_type="text/plain",
        encoding="utf-8",
        retrieved_at=NOW,
        checksum="synthetic-checksum",
    )


def connector(**changes: Any) -> FakeSourceConnector:
    items = [item(1), item(2), item(3)]
    values: dict[str, Any] = {
        "descriptor": descriptor(),
        "health": SourceHealth(status=SourceHealthStatus.HEALTHY, checked_at=NOW, latency_ms=1),
        "items": items,
        "contents": {entry.id: content(entry) for entry in items},
        "changes": [
            SourceChange(
                source_id="source-1",
                item_id="item-1",
                external_id="external-1",
                change_type=SourceChangeType.MODIFIED,
                detected_at=NOW,
                previous_version="0",
                current_version="1",
            ),
            SourceChange(
                source_id="source-1",
                external_id="deleted-external",
                change_type=SourceChangeType.DELETED,
                detected_at=NOW,
                previous_version="1",
            ),
        ],
        "change_page_size": 1,
    }
    values.update(changes)
    return FakeSourceConnector(**values)


def test_descriptor_is_vendor_neutral_and_capabilities_are_explicit() -> None:
    source = descriptor()
    assert source.source_type == "knowledge_base"
    assert source.capabilities.read_only is True
    assert source.capabilities.preserve_page_locations is False
    assert "api_key" not in source.model_dump(mode="json")


def test_source_item_has_no_content_and_serializes_cleanly() -> None:
    payload = item(1).model_dump(mode="json")
    assert "content" not in payload
    assert payload["modified_at"] == "2026-07-12T12:00:00Z"


def test_source_content_tracks_size_and_limit() -> None:
    value = SourceContent(
        item=item(1),
        content_bytes=b"abc",
        content_type="application/octet-stream",
        retrieved_at=NOW,
        truncated=True,
        limit_bytes=3,
    )
    assert value.size_bytes == 3
    assert value.model_dump(mode="json")["size_bytes"] == 3


def test_pagination_uses_opaque_cursor_at_contract_boundary() -> None:
    fake = connector()
    first = asyncio.run(fake.list_items(None, 2))
    second = asyncio.run(fake.list_items(first.next_cursor, 2))
    assert [entry.id for entry in first.items] == ["item-1", "item-2"]
    assert first.has_more and first.next_cursor is not None
    assert [entry.id for entry in second.items] == ["item-3"]
    assert not second.has_more


def test_change_pagination_represents_deletion_without_live_item_id() -> None:
    fake = connector()
    first = asyncio.run(fake.detect_changes(None))
    second = asyncio.run(fake.detect_changes(first.next_cursor))
    assert first.items[0].change_type is SourceChangeType.MODIFIED
    assert second.items[0].change_type is SourceChangeType.DELETED
    assert second.items[0].item_id is None
    assert second.items[0].external_id == "deleted-external"


@pytest.mark.parametrize("status", list(SourceHealthStatus))
def test_all_health_states_are_representable(status: SourceHealthStatus) -> None:
    fake = connector(health=SourceHealth(status=status, checked_at=NOW))
    assert asyncio.run(fake.health_check()).status is status


def test_fake_conforms_to_protocol_and_returns_defensive_copies() -> None:
    fake = connector()
    assert isinstance(fake, SourceConnector)
    returned = asyncio.run(fake.get_item("item-1"))
    returned.metadata["changed"] = True
    assert "changed" not in asyncio.run(fake.get_item("item-1")).metadata


def test_configured_failure_is_typed_and_secret_safe() -> None:
    failure = SourceErrorDetail(
        category=SourceErrorCategory.TIMEOUT,
        message="request failed Bearer abcdefghijklmnop",
        retryable=True,
    )
    fake = connector(failures={"describe": failure})
    with pytest.raises(SourceError) as caught:
        asyncio.run(fake.describe())
    assert caught.value.detail.category is SourceErrorCategory.TIMEOUT
    assert "abcdefghijklmnop" not in str(caught.value)
    assert "abcdefghijklmnop" not in repr(caught.value)


def test_missing_and_oversized_content_have_typed_categories() -> None:
    fake = connector()
    with pytest.raises(SourceError) as missing:
        asyncio.run(fake.get_content("missing", 100))
    with pytest.raises(SourceError) as oversized:
        asyncio.run(fake.get_content("item-1", 2))
    assert missing.value.detail.category is SourceErrorCategory.NOT_FOUND
    assert oversized.value.detail.category is SourceErrorCategory.CONTENT_TOO_LARGE


def test_raw_secrets_are_rejected_but_secure_reference_is_allowed() -> None:
    assert descriptor(configuration_reference="vault:ragscanner/source").configuration_reference
    with pytest.raises(ValidationError):
        descriptor(configuration_reference="plain-secret")
    with pytest.raises(ValidationError):
        descriptor(metadata={"api_key": "super-secret-password"})
    with pytest.raises(ValidationError):
        SourceItem.model_validate({**item(1).model_dump(), "metadata": {"password": "secret"}})


def test_naive_datetimes_and_invalid_cursor_expiry_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SourceHealth(status=SourceHealthStatus.UNKNOWN, checked_at=datetime(2026, 1, 1))
    with pytest.raises(ValidationError):
        SourceCursor(
            source_id="source-1",
            cursor_value="opaque",
            created_at=NOW,
            expires_at=NOW - timedelta(seconds=1),
        )


def test_mutable_defaults_are_isolated() -> None:
    first = SourceItem(id="one", source_id="source-1", external_id="one", name="one")
    second = SourceItem(id="two", source_id="source-1", external_id="two", name="two")
    first.metadata["new"] = "value"
    assert second.metadata == {}


def test_fake_module_has_no_filesystem_or_network_dependencies() -> None:
    module_names = FakeSourceConnector.__init__.__globals__
    assert {"httpx", "requests", "socket", "pathlib", "os"}.isdisjoint(module_names)
