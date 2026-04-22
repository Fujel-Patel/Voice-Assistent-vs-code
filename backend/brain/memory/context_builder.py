from __future__ import annotations

import asyncio
from typing import Any

from brain.prompt_templates import JARVIS_SYSTEM_PROMPT
from core.logger import get_logger

logger = get_logger(__name__)


class ContextBuilder:
    def __init__(self, short_term_memory, long_term_memory, token_budget: int = 4000, system_prompt: str | None = None) -> None:
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.token_budget = token_budget
        self.system_prompt = system_prompt or JARVIS_SYSTEM_PROMPT
        self._token_encoder = None

        try:
            import tiktoken

            self._token_encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self._token_encoder = None

    def _estimate_tokens(self, text: str) -> int:
        if self._token_encoder is not None:
            try:
                return len(self._token_encoder.encode(text))
            except Exception:
                pass
        return max(1, len(text) // 4)

    def _truncate_message(self, text: str, max_tokens: int) -> str:
        if self._estimate_tokens(text) <= max_tokens:
            return text
        midpoint = max(20, len(text) // 2)
        first = text[:midpoint].strip()
        last = text[-midpoint:].strip()
        return f"{first} ... {last}"

    async def build_context(self, current_input: str) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        used = self._estimate_tokens(self.system_prompt)

        preferences_task = self.long_term_memory.get_user_preferences()
        relevant_task = self.long_term_memory.search(current_input, top_k=3)
        history_task = self.short_term_memory.get_history(max_turns=20)

        preferences, relevant, history = await asyncio.gather(
            preferences_task,
            relevant_task,
            history_task,
        )

        if preferences:
            pref_blob = "\n".join(f"{k}: {v}" for k, v in preferences.items())
            pref_text = f"Known user preferences:\n{pref_blob}"
            messages.append({"role": "system", "content": pref_text})
            used += self._estimate_tokens(pref_text)

        if relevant:
            context_blob = "\n".join(item["summary"] for item in relevant if item.get("summary"))
            lt_text = f"Relevant past context:\n{context_blob}"
            messages.append({"role": "system", "content": lt_text})
            used += self._estimate_tokens(lt_text)

        recent_anchor = history[-3:] if len(history) >= 3 else history
        older = history[:-3] if len(history) > 3 else []

        for turn in older:
            content = turn.get("content", "")
            token_need = self._estimate_tokens(content)
            if used + token_need > self.token_budget:
                continue
            messages.append({"role": turn.get("role", "user"), "content": content})
            used += token_need

        for turn in recent_anchor:
            content = turn.get("content", "")
            token_need = self._estimate_tokens(content)
            if used + token_need > self.token_budget:
                content = self._truncate_message(content, max_tokens=max(32, self.token_budget - used))
                token_need = self._estimate_tokens(content)
            if used + token_need > self.token_budget:
                break
            messages.append({"role": turn.get("role", "user"), "content": content})
            used += token_need

        user_tokens = self._estimate_tokens(current_input)
        if used + user_tokens > self.token_budget:
            current_input = self._truncate_message(current_input, max_tokens=max(64, self.token_budget - used))
        messages.append({"role": "user", "content": current_input})
        used += self._estimate_tokens(current_input)

        logger.info(f"Context built with ~{used} tokens and {len(messages)} messages")
        return messages
