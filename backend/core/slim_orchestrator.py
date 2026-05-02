from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from infrastructure.websocket.manager import WSManager

from core.config import load_config
from core.event_bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)


class MessageBuilder(Protocol):
    def __call__(
        self, msg_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]: ...


class SlimOrchestrator:
    """A slim orchestrator that delegates WebSocket management to WSManager"""

    def __init__(self) -> None:
        self.config = load_config()
        self.event_bus = EventBus()

        # Set up message builder
        def _message(
            msg_type: str, payload: dict[str, Any], request_id: str | None = None
        ) -> dict[str, Any]:
            return {
                "type": msg_type,
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id or str(uuid4()),
            }

        self._message = _message
        self.ws_manager = WSManager(
            message_builder=self._message, stop_event=asyncio.Event()
        )

    async def start(self) -> None:
        """Start the orchestrator"""
        pass

    async def stop(self) -> None:
        """Stop the orchestrator"""
        pass
