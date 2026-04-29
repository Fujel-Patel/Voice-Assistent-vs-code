from __future__ import annotations

from typing import Any

from core.logger import get_logger
from services.brave_search import BraveSearch
from services.duckduckgo import DuckDuckGoSearch
from services.url_summarizer import URLSummarizer
from services.web_fetcher import WebFetcher

from plugins.base import JarvisPlugin, PluginResult

logger = get_logger(__name__)


class WebSearchPlugin(JarvisPlugin):
    name = "web_search"
    description = "Search the web and fetch information"
    intents = ["web-search", "look-up", "find-info", "current-events"]

    def __init__(self) -> None:
        self.brave = BraveSearch()
        self.ddg = DuckDuckGoSearch()
        self.fetcher = WebFetcher()
        self.summarizer = URLSummarizer(claude_agent=None, fetcher=self.fetcher)

    async def execute(
        self, intent: dict[str, Any], context: dict[str, Any]
    ) -> PluginResult:
        params = (
            intent.get("params", {}) if isinstance(intent.get("params"), dict) else {}
        )
        action = str(params.get("action") or "search").strip().lower()
        query = str(params.get("query") or "").strip()
        url = str(params.get("url") or "").strip()
        deep_search = bool(params.get("deep_search", False))

        if action == "search":
            if not query:
                return PluginResult(
                    success=False,
                    output="Please provide a search query.",
                    error="missing_query",
                )
            return await self._handle_search(
                query, deep_search=deep_search, context=context
            )

        if action == "search_news":
            if not query:
                return PluginResult(
                    success=False,
                    output="Please provide a news query.",
                    error="missing_query",
                )
            return await self._handle_search(
                query, deep_search=deep_search, context=context, mode="news"
            )

        if action == "summarize_url":
            if not url:
                return PluginResult(
                    success=False,
                    output="Please provide a URL to summarize.",
                    error="missing_url",
                )
            summary = await self._build_summarizer(context).summarize_url(url)
            return PluginResult(
                success=True, output=summary.get("summary", ""), data=summary
            )

        if action == "fetch":
            if not url:
                return PluginResult(
                    success=False,
                    output="Please provide a URL to fetch.",
                    error="missing_url",
                )
            page = await self.fetcher.fetch_page(url)
            content = page.get("content", "")
            preview = (
                content[:2000]
                if content
                else page.get("error", "No readable content found.")
            )
            return PluginResult(success=True, output=preview, data=page)

        return PluginResult(
            success=False,
            output=f"Unsupported web action: {action}",
            error="unsupported_action",
        )

    async def _handle_search(
        self,
        query: str,
        deep_search: bool,
        context: dict[str, Any],
        mode: str = "web",
    ) -> PluginResult:
        source = "brave"
        try:
            if mode == "news":
                results = await self.brave.search_news(query)
            else:
                results = await self.brave.search(query)
        except Exception as exc:
            logger.warning(f"Brave search failed, using DuckDuckGo fallback: {exc}")
            source = "duckduckgo"
            if mode == "news":
                results = await self.ddg.search_news(query)
            else:
                results = await self.ddg.search(query)

        if not results:
            instant = await self.ddg.instant_answer(query)
            if instant and instant.get("answer"):
                return PluginResult(
                    success=True,
                    output=f"{instant['answer']} (source: {instant.get('source', 'DuckDuckGo')})",
                    data={
                        "results": [],
                        "instant_answer": instant,
                        "source": "duckduckgo",
                    },
                )
            return PluginResult(
                success=True,
                output="I couldn't find live results for that query.",
                data={"results": []},
            )

        pages = []
        if deep_search:
            top_urls = [item.get("url", "") for item in results[:2] if item.get("url")]
            pages = await self.fetcher.fetch_multiple(top_urls)

        brain_agent = context.get("brain_agent")
        if brain_agent is not None and hasattr(brain_agent, "process_with_context"):
            response = await brain_agent.process_with_context(
                query, results, pages=pages or None
            )
            message = (
                response.get("response_text", "") or "Here are the top search results."
            )
        else:
            message = self._format_results(query, results)

        payload = {
            "query": query,
            "results": results,
            "source": source,
            "deep_search": deep_search,
        }
        if pages:
            payload["pages"] = pages

        return PluginResult(success=True, output=message, data=payload)

    def _build_summarizer(self, context: dict[str, Any]) -> URLSummarizer:
        brain_agent = context.get("brain_agent")
        if brain_agent is self.summarizer.claude_agent:
            return self.summarizer
        return URLSummarizer(claude_agent=brain_agent, fetcher=self.fetcher)

    def _format_results(self, query: str, results: list[dict[str, Any]]) -> str:
        lines = [f"Top web results for '{query}':"]
        for idx, item in enumerate(results[:5], start=1):
            lines.append(
                f"{idx}. {item.get('title', 'Untitled')} - {item.get('url', '')}"
            )
        return "\n".join(lines)

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "intent": "web-search",
                "description": "search: run live web search with Brave + DDG fallback",
            },
            {
                "intent": "web-search",
                "description": "search_news: fetch latest news results",
            },
            {
                "intent": "web-search",
                "description": "fetch: download and extract readable page text",
            },
            {
                "intent": "web-search",
                "description": "summarize_url: summarize a URL with chunk-aware summarization",
            },
        ]
