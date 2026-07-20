import httpx
import pytest
from ragscanner.connectors import WebsiteSourceConfig, WebsiteSourceConnector


@pytest.mark.anyio
async def test_website_connector_reads_bounded_same_origin_sitemap() -> None:
    sitemap = b"""<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://docs.example.test/guide</loc></url><url><loc>https://elsewhere.example.test/nope</loc></url></urlset>"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sitemap.xml":
            return httpx.Response(200, content=sitemap, headers={"content-type": "application/xml"})
        return httpx.Response(200, text="<h1>Guide</h1>", headers={"content-type": "text/html"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    connector = WebsiteSourceConnector(
        WebsiteSourceConfig(
            url="https://docs.example.test/sitemap.xml",
            source_name="Docs",
            content_consent=True,
        ),
        client=client,
    )
    try:
        page = await connector.list_items(None, 100)
        assert [item.external_id for item in page.items] == ["https://docs.example.test/guide"]
        assert page.items[0].path == "guide.html"
        content = await connector.get_content(page.items[0].id, 1024)
        assert content.content_type == "text/html"
        assert content.content_bytes == b"<h1>Guide</h1>"
    finally:
        await client.aclose()


def test_website_connector_requires_https_and_explicit_consent() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        WebsiteSourceConfig(url="http://docs.example.test", content_consent=True)
    with pytest.raises(ValueError, match="explicit content consent"):
        WebsiteSourceConfig(url="https://docs.example.test")


@pytest.mark.anyio
async def test_website_connector_expands_one_level_sitemap_index() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sitemap.xml":
            return httpx.Response(
                200,
                text="<sitemapindex><sitemap><loc>https://docs.example.test/docs.xml</loc></sitemap></sitemapindex>",
            )
        if request.url.path == "/docs.xml":
            return httpx.Response(
                200,
                text="<urlset><url><loc>https://docs.example.test/start</loc></url></urlset>",
            )
        return httpx.Response(200, text="Start")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    connector = WebsiteSourceConnector(
        WebsiteSourceConfig(url="https://docs.example.test/sitemap.xml", content_consent=True),
        client=client,
    )
    try:
        page = await connector.list_items(None, 100)
        assert [item.external_id for item in page.items] == ["https://docs.example.test/start"]
    finally:
        await client.aclose()
