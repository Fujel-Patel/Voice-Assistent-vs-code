from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable


class ShortTermMemory:
    def __init__(
        self,
        max_turns: int = 20,
        on_rollover: Callable[[list[dict[str, Any]]], Awaitable[None]] | None = None,
    ) -> None:
        self.max_turns = max_turns
        self._turns: deque[dict[str, Any]] = deque()
        self._lock = asyncio.Lock()
        self._on_rollover = on_rollover

    async def add_turn(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        metadata = metadata or {}
        turn = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "intent": metadata.get("intent"),
            "tokens": int(metadata.get("tokens", max(1, len(content) // 4))),
        }

        rolled: list[dict[str, Any]] = []
        async with self._lock:
            self._turns.append(turn)
            while len(self._turns) > self.max_turns:
                rolled.append(self._turns.popleft())

        if rolled and self._on_rollover is not None:
            await self._on_rollover(rolled)

    async def get_history(self, max_turns: int = 10) -> list[dict[str, Any]]:
        async with self._lock:
            turns = list(self._turns)
        if max_turns <= 0:
            return []
        return turns[-max_turns:]

    async def get_token_count(self) -> int:
        async with self._lock:
            return sum(int(t.get("tokens", 0)) for t in self._turns)

    async def clear(self) -> None:
        async with self._lock:
            self._turns.clear()

    async def trim_to_budget(self, max_tokens: int) -> list[dict[str, Any]]:
        removed: list[dict[str, Any]] = []
        async with self._lock:
            token_count = sum(int(t.get("tokens", 0)) for t in self._turns)
            while self._turns and token_count > max_tokens:
                dropped = self._turns.popleft()
                removed.append(dropped)
                token_count -= int(dropped.get("tokens", 0))
        return removed
