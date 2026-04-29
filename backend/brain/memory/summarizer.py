from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class Summarizer:
    def __init__(self, brain_agent: Any, long_term_memory: Any) -> None:
        self.brain_agent = brain_agent
        self.long_term_memory = long_term_memory

    async def summarize_turns(
        self, session_id: str, turns: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not turns:
            return {"summary": "", "topics": [], "preferences": {}}

        prompt_lines = [
            "Summarize this conversation in 2-3 sentences.",
            "Extract key topics as a JSON array.",
            "Note any user preferences mentioned as a JSON object.",
            "Return strict JSON with keys: summary, topics, preferences.",
            "Conversation:",
        ]
        prompt_lines.extend(
            f"- {t.get('role', 'user')}: {t.get('content', '')}" for t in turns
        )
        prompt = "\n".join(prompt_lines)

        try:
            preferred_provider = (
                self.brain_agent.config.brain.providers.default_provider
            )
            result = await self.brain_agent.process_input(
                prompt,
                {"preferred_provider": preferred_provider},
            )
            raw = result.get("response_text", "")
            parsed = self._safe_parse_json(raw)
            if parsed is None:
                parsed = self._fallback_summary(turns)
        except Exception as exc:
            logger.warning(f"Summarizer provider call failed: {exc}")
            parsed = self._fallback_summary(turns)

        await self.long_term_memory.store_summary(
            session_id=session_id,
            summary=parsed.get("summary", ""),
            topics=list(parsed.get("topics", [])),
            turn_count=len(turns),
        )

        for key, value in parsed.get("preferences", {}).items():
            await self.long_term_memory.learn_preference(
                str(key), str(value), source="inferred"
            )

        return parsed

    def _safe_parse_json(self, raw: str) -> dict[str, Any] | None:
        import json

        try:
            obj = json.loads(raw)
            if not isinstance(obj, dict):
                return None
            return {
                "summary": str(obj.get("summary", "")),
                "topics": obj.get("topics", [])
                if isinstance(obj.get("topics"), list)
                else [],
                "preferences": obj.get("preferences", {})
                if isinstance(obj.get("preferences"), dict)
                else {},
            }
        except Exception:
            return None

    def _fallback_summary(self, turns: list[dict[str, Any]]) -> dict[str, Any]:
        first = turns[0].get("content", "") if turns else ""
        last = turns[-1].get("content", "") if turns else ""
        summary = (first + " ... " + last).strip(" .")
        return {
            "summary": summary[:500],
            "topics": [],
            "preferences": {},
        }
