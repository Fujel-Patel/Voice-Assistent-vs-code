from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from config.config_loader import load_config
from core.logger import get_logger

from services.web_fetcher import WebFetcher

if TYPE_CHECKING:
    from brain.orchestrator import ClaudeAgent

logger = get_logger(__name__)


class URLSummarizer:
    def __init__(
        self, claude_agent: ClaudeAgent | None = None, fetcher: WebFetcher | None = None
    ) -> None:
        self.config = load_config()
        self.claude_agent = claude_agent
        self.fetcher = fetcher or WebFetcher()
        self.cache_ttl = self.config.web.summary_cache_ttl_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def summarize_url(self, url: str, style: str = "brief") -> dict[str, Any]:
        now = time.time()
        cached = self._cache.get(url)
        if cached and now - cached[0] < self.cache_ttl:
            return cached[1]

        page = await self.fetcher.fetch_page(url)
        content = page.get("content", "")
        summary_text = await self.summarize_text(content, style=style)

        payload = {
            "url": page.get("url", url),
            "title": page.get("title", ""),
            "summary": summary_text,
            "key_points": self._key_points_from_summary(summary_text),
            "tokens_used": max(1, len(content) // 4),
        }
        self._cache[url] = (now, payload)
        return payload

    async def summarize_text(self, text: str, style: str = "brief") -> str:
        clean = " ".join((text or "").split())
        if not clean:
            return "No content available to summarize."

        chunks = self._chunk_text(clean, max_chars=12000)
        if self.claude_agent is None:
            return self._fallback_summary(clean, style=style)

        partials: list[str] = []
        preferred_provider = self.config.brain.providers.default_provider
        for chunk in chunks:
            prompt = self._summary_prompt(chunk, style)
            result = await self.claude_agent.process_input(
                prompt,
                {"preferred_provider": preferred_provider},
            )
            partials.append(result.get("response_text", ""))

        merged = "\n".join(partials).strip()
        if len(partials) == 1:
            return merged

        final_prompt = self._summary_prompt(merged, style)
        final = await self.claude_agent.process_input(
            final_prompt,
            {"preferred_provider": preferred_provider},
        )
        return str(final.get("response_text", merged))

    def _summary_prompt(self, text: str, style: str) -> str:
        styles = {
            "brief": "Summarize in 2-3 sentences.",
            "detailed": "Summarize in 2-3 concise paragraphs.",
            "bullet_points": "Summarize into 5-7 bullet points.",
            "eli5": "Explain this in very simple words like I'm 5.",
        }
        instruction = styles.get(style, styles["brief"])
        return f"{instruction}\n\nText:\n{text}"

    def _chunk_text(self, text: str, max_chars: int = 12000) -> list[str]:
        if len(text) <= max_chars:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunks.append(text[start:end])
            start = end
        return chunks

    def _fallback_summary(self, text: str, style: str) -> str:
        if style == "bullet_points":
            sentences = [s.strip() for s in text.split(".") if s.strip()][:6]
            return "\n".join(f"- {sentence}." for sentence in sentences)
        if style == "detailed":
            return text[:1200] + ("..." if len(text) > 1200 else "")
        if style == "eli5":
            return "In simple words: " + text[:400] + ("..." if len(text) > 400 else "")
        return text[:350] + ("..." if len(text) > 350 else "")

    def _key_points_from_summary(self, summary: str) -> list[str]:
        lines = [line.strip(" -") for line in summary.splitlines() if line.strip()]
        if lines:
            return lines[:7]
        sentences = [s.strip() for s in summary.split(".") if s.strip()]
        return [f"{sentence}." for sentence in sentences[:5]]
