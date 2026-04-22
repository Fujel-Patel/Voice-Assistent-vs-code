from __future__ import annotations

import time

import pytest

from plugins.web_search import WebSearchPlugin
from services.brave_search import BraveSearch
from services.duckduckgo import DuckDuckGoSearch
from services.url_summarizer import URLSummarizer
from services.web_fetcher import WebFetcher


@pytest.mark.asyncio
async def test_brave_search(mocker) -> None:
    brave = BraveSearch()
    brave.api_key = "test-key"

    class Resp:
        status_code = 200

        def json(self):
            return {
                "web": {
                    "results": [
                        {
                            "title": "Python 3.13",
                            "url": "https://python.org",
                            "description": "Release notes",
                        }
                    ]
                }
            }

    client = mocker.patch("services.brave_search.httpx.AsyncClient")
    client.return_value.__aenter__.return_value.get = mocker.AsyncMock(return_value=Resp())

    results = await brave.search("python releases", count=1)
    assert results and results[0]["url"] == "https://python.org"


@pytest.mark.asyncio
async def test_duckduckgo_search(mocker) -> None:
    ddg = DuckDuckGoSearch()
    mocker.patch.object(ddg, "_search_sync", return_value=[{"title": "A", "url": "https://a.com", "description": "d", "age": ""}])

    results = await ddg.search("query", count=1)
    assert results[0]["url"] == "https://a.com"


@pytest.mark.asyncio
async def test_fallback_to_duckduckgo(mocker) -> None:
    plugin = WebSearchPlugin()
    mocker.patch.object(plugin.brave, "search", side_effect=RuntimeError("rate limit"))
    mocker.patch.object(plugin.ddg, "search", return_value=[{"title": "B", "url": "https://b.com", "description": "x", "age": ""}])

    result = await plugin.execute(
        {"type": "web-search", "params": {"action": "search", "query": "latest python"}},
        context={},
    )
    assert result.success is True
    assert result.data["source"] == "duckduckgo"


@pytest.mark.asyncio
async def test_web_fetcher(mocker) -> None:
    fetcher = WebFetcher()
    mocker.patch.object(fetcher, "_validate_url", return_value=None)

    class Resp:
        status_code = 200
        text = "<html><head><title>Hello</title></head><body><p>World</p></body></html>"
        url = "https://example.com"

    client = mocker.patch("services.web_fetcher.httpx.AsyncClient")
    client.return_value.__aenter__.return_value.get = mocker.AsyncMock(return_value=Resp())

    page = await fetcher.fetch_page("https://example.com")
    assert page["title"] == "Hello"
    assert "World" in page["content"]


@pytest.mark.asyncio
async def test_url_summarizer(mocker) -> None:
    fetcher = WebFetcher()
    mocker.patch.object(fetcher, "fetch_page", return_value={"url": "https://example.com", "title": "Title", "content": "one two three four five"})

    class FakeClaude:
        async def process_input(self, prompt: str, context: dict):
            return {"response_text": "short summary"}

    summarizer = URLSummarizer(claude_agent=FakeClaude(), fetcher=fetcher)
    data = await summarizer.summarize_url("https://example.com")
    assert data["summary"] == "short summary"


@pytest.mark.asyncio
async def test_search_caching(mocker) -> None:
    brave = BraveSearch()
    brave.api_key = "k"

    class Resp:
        status_code = 200

        def json(self):
            return {"web": {"results": [{"title": "X", "url": "https://x.com", "description": "desc"}]}}

    get_mock = mocker.AsyncMock(return_value=Resp())
    client = mocker.patch("services.brave_search.httpx.AsyncClient")
    client.return_value.__aenter__.return_value.get = get_mock

    first = await brave.search("cache me")
    second = await brave.search("cache me")
    assert first == second
    assert get_mock.await_count == 1


@pytest.mark.asyncio
async def test_ssrf_protection() -> None:
    fetcher = WebFetcher()
    with pytest.raises(ValueError):
        await fetcher._validate_url("http://127.0.0.1/admin")
