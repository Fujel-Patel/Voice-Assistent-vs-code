from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class WSManager:
    def __init__(
        self,
        message_builder: Callable[[str, dict[str, Any], str | None], dict[str, Any]],
        stop_event: asyncio.Event,
    ) -> None:
        self.clients: set[Any] = set()
        self.message_builder: (
            Callable[[str, dict[str, Any], str | None], dict[str, Any]] | None
        ) = message_builder
        self.stop_event: asyncio.Event | None = stop_event

    def set_message_builder(
        self, builder: Callable[[str, dict[str, Any], str | None], dict[str, Any]]
    ) -> None:
        self.message_builder = builder

    def set_stop_event(self, stop_event: asyncio.Event) -> None:
        self.stop_event = stop_event
        self.clients = set()

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self.clients or not payload:
            return

        body = json.dumps(payload)
        tasks = [client.send_text(body) for client in list(self.clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Broadcast failure: {result}")

    async def _broadcast_state(self, payload: dict[str, Any]) -> None:
        if self.message_builder:
            await self.broadcast(
                self.message_builder("voice_state_change", payload, None)
            )

    async def _ws_keepalive_loop(self) -> None:
        if not self.stop_event:
            return

        while not self.stop_event.is_set():
            await asyncio.sleep(30)
            if self.clients and self.message_builder:
                await self.broadcast(
                    self.message_builder(
                        "ping",
                        {"ts": datetime.now(UTC).isoformat()},
                        None,
                    )
                )

    def add_client(self, client: Any) -> None:
        """Add a WebSocket client"""
        self.clients.add(client)

    def remove_client(self, client: Any) -> None:
        """Remove a WebSocket client"""
        self.clients.discard(client)
