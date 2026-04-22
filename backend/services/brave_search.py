from __future__ import annotations

import time
from typing import Any

import httpx

from config.config_loader import load_config
from core.logger import get_logger
from core.retry import retry

logger = get_logger(__name__)


class BraveSearch:
    def __init__(self) -> None:
        self.config = load_config()
        self.api_key = self.config.brave_search_api_key
        self.max_results = self.config.web.max_results
        self.safe_search = self.config.web.safe_search
        self.country = self.config.web.country
        self.language = self.config.web.language
        self.cache_ttl = self.config.web.search_cache_ttl_seconds
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}

    async def search(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        return await self._search_endpoint("web/search", query, count=count)

    async def search_news(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        return await self._search_endpoint("news/search", query, count=count)

    async def search_images(self, query: str, count: int = 5) -> list[dict[str, Any]]:
        return await self._search_endpoint("images/search", query, count=count)

    @retry(max_retries=2, base_delay=0.5)
    async def _search_endpoint(self, endpoint: str, query: str, count: int = 5) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []

        if not self.api_key:
            raise RuntimeError("BRAVE_SEARCH_API_KEY missing")

        key = f"{endpoint}:{query.lower()}:{count}"
        cached = self._cache.get(key)
        now = time.time()
        if cached and now - cached[0] < self.cache_ttl:
            return cached[1]

        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": min(max(1, count), self.max_results),
            "safesearch": self.safe_search,
            "country": self.country,
            "search_lang": self.language,
        }

        url = f"https://api.search.brave.com/res/v1/{endpoint}"
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, headers=headers, params=params)

        if response.status_code == 429:
            raise RuntimeError("brave_rate_limited")
        if response.status_code >= 400:
            raise RuntimeError(f"brave_http_{response.status_code}")

        data = response.json()
        results = self._normalize_results(endpoint, data)
        self._cache[key] = (now, results)
        return results

    def _normalize_results(self, endpoint: str, data: dict[str, Any]) -> list[dict[str, Any]]:
        if endpoint == "images/search":
            items = data.get("results", []) or data.get("images", {}).get("results", [])
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "thumbnail": item.get("thumbnail", {}).get("src") if isinstance(item.get("thumbnail"), dict) else item.get("thumbnail"),
                    "age": item.get("age", ""),
                }
                for item in items
                if item.get("url")
            ]

        if endpoint == "news/search":
            items = data.get("results", []) or data.get("news", {}).get("results", [])
            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("description", ""),
                    "age": item.get("age", ""),
                }
                for item in items
                if item.get("url")
            ]

        items = data.get("web", {}).get("results", []) or data.get("results", [])
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "description": item.get("description", item.get("snippet", "")),
                "age": item.get("age", ""),
            }
            for item in items
            if item.get("url")
        ]
