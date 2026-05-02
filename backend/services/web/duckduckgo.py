from __future__ import annotations

import asyncio
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class DuckDuckGoSearch:
    def __init__(self) -> None:
        pass

    async def search(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._search_sync, query, count)

    async def search_news(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._search_news_sync, query, count)

    async def instant_answer(self, query: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._instant_answer_sync, query)

    def _search_sync(self, query: str, count: int) -> list[dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
        except Exception:
            logger.warning("duckduckgo_search package unavailable")
            return []

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=count))
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "description": item.get("body", ""),
                    "age": item.get("date", ""),
                }
                for item in results
                if item.get("href")
            ]
        except Exception as exc:
            logger.warning(f"DDG search failed: {exc}")
            return []

    def _search_news_sync(self, query: str, count: int) -> list[dict[str, Any]]:
        try:
            from duckduckgo_search import DDGS
        except Exception:
            logger.warning("duckduckgo_search package unavailable")
            return []

        try:
            with DDGS() as ddgs:
                results = list(ddgs.news(query, max_results=count))
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("body", ""),
                    "age": item.get("date", ""),
                }
                for item in results
                if item.get("url")
            ]
        except Exception as exc:
            logger.warning(f"DDG news search failed: {exc}")
            return []

    def _instant_answer_sync(self, query: str) -> dict[str, Any] | None:
        try:
            from duckduckgo_search import DDGS
        except Exception:
            return None

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=1))
                if not results:
                    return None
                first = results[0]
                return {
                    "answer": first.get("body", ""),
                    "source": first.get("href", "DuckDuckGo"),
                    "type": "search_result",
                }
        except Exception:
            return None
