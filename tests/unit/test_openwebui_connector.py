import httpx
import pytest
from ragscanner.connectors import OpenWebUISourceConfig, OpenWebUISourceConnector
from ragscanner.domain import SourceError, SourceErrorCategory, SourceHealthStatus


@pytest.mark.anyio
async def test_openwebui_connector_lists_and_reads_bounded_knowledge_files() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.headers["authorization"] == "Bearer synthetic-runtime-token"
        if request.url.path == "/api/v1/knowledge/kb-1":
            return httpx.Response(200, json={"id": "kb-1", "name": "Synthetic KB"})
        if request.url.path == "/api/v1/knowledge/kb-1/files":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "file-1",
                            "filename": "Überblick.md",
                            "meta": {
                                "name": "Überblick.md",
                                "content_type": "text/markdown",
                                "size": 28,
                                "file_hash": "abc123",
                            },
                        }
                    ],
                    "total": 1,
                },
            )
        if request.url.path == "/api/v1/files/file-1/content":
            return httpx.Response(
                200,
                content=b"# Synthetic\n\nSafe content.\n",
                headers={"content-type": "text/markdown; charset=utf-8"},
            )
        raise AssertionError(f"unexpected request: {request.url}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = OpenWebUISourceConnector(
        OpenWebUISourceConfig(
            base_url="http://127.0.0.1:3000",
            knowledge_id="kb-1",
            credential_ref="env:OPENWEBUI_API_KEY",
            content_consent=True,
        ),
        api_key="synthetic-runtime-token",
        client=client,
    )
    try:
        descriptor = await connector.describe()
        health = await connector.health_check()
        page = await connector.list_items(None, 100)
        content = await connector.get_content("file-1", 1024)
    finally:
        await client.aclose()

    assert descriptor.capabilities.read_document_content
    assert descriptor.configuration_reference == "env:OPENWEBUI_API_KEY"
    assert health.status is SourceHealthStatus.HEALTHY
    assert [item.name for item in page.items] == ["Überblick.md"]
    assert content.content_bytes.startswith(b"# Synthetic")
    assert content.content_type == "text/markdown"
    assert content.metadata == {"remote_content_consent": True, "upstream": "openwebui"}
    assert all("synthetic-runtime-token" not in str(request.url) for request in requests)


@pytest.mark.anyio
async def test_openwebui_connector_rejects_oversized_content_without_following_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files"):
            return httpx.Response(
                200,
                json={"items": [{"id": "large", "filename": "large.txt"}], "total": 1},
            )
        return httpx.Response(200, content=b"x" * 20, headers={"content-type": "text/plain"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    connector = OpenWebUISourceConnector(
        OpenWebUISourceConfig(
            base_url="https://openwebui.example",
            knowledge_id="kb-1",
            credential_ref="env:OPENWEBUI_API_KEY",
            content_consent=True,
        ),
        api_key="synthetic-runtime-token",
        client=client,
    )
    try:
        await connector.list_items(None, 100)
        with pytest.raises(SourceError) as captured:
            await connector.get_content("large", 10)
    finally:
        await client.aclose()

    assert captured.value.detail.category is SourceErrorCategory.CONTENT_TOO_LARGE


@pytest.mark.parametrize(
    ("base_url", "consent", "message"),
    [
        ("http://openwebui.example", True, "require HTTPS"),
        ("http://127.0.0.1:3000/path", True, "application path"),
        ("http://127.0.0.1:3000", False, "explicit content consent"),
    ],
)
def test_openwebui_connector_configuration_enforces_endpoint_and_consent(
    base_url: str, consent: bool, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        OpenWebUISourceConfig(
            base_url=base_url,
            knowledge_id="kb-1",
            credential_ref="env:OPENWEBUI_API_KEY",
            content_consent=consent,
        )


@pytest.mark.anyio
async def test_openwebui_connector_preserves_items_when_caller_limit_is_smaller_than_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["page"] == "1"
        return httpx.Response(
            200,
            json={
                "items": [
                    {"id": "one", "filename": "one.md"},
                    {"id": "two", "filename": "two.md"},
                    {"id": "three", "filename": "three.md"},
                ],
                "total": 3,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    connector = OpenWebUISourceConnector(
        OpenWebUISourceConfig(
            base_url="http://127.0.0.1:3000",
            knowledge_id="kb-1",
            credential_ref="env:OPENWEBUI_API_KEY",
            content_consent=True,
        ),
        api_key="synthetic-runtime-token",
        client=client,
    )
    try:
        first = await connector.list_items(None, 2)
        second = await connector.list_items(first.next_cursor, 2)
    finally:
        await client.aclose()

    assert [item.id for item in first.items] == ["one", "two"]
    assert first.has_more
    assert [item.id for item in second.items] == ["three"]
    assert not second.has_more
