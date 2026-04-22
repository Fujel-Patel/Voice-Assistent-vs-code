from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from core.event_bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)

Probe = Callable[[], Awaitable[tuple[bool, str]]]


@dataclass
class HealthChecker:
    event_bus: EventBus
    microphone_probe: Probe
    model_probe: Probe
    websocket_probe: Probe
    interval_seconds: float = 30.0

    def __post_init__(self) -> None:
        self._task: asyncio.Task | None = None

    async def run_once(self) -> dict:
        mic_ok, mic_msg = await self.microphone_probe()
        model_ok, model_msg = await self.model_probe()
        ws_ok, ws_msg = await self.websocket_probe()

        payload = {
            "microphone": mic_ok,
            "model_loaded": model_ok,
            "websocket": ws_ok,
            "apis": {
                "claude": False,
                "gemini": False,
                "groq": False,
                "openrouter": False,
                "ollama": False,
                "elevenlabs": False,
            },
            "details": {
                "microphone": mic_msg,
                "model": model_msg,
                "websocket": ws_msg,
            },
        }
        await self.event_bus.publish("health_check", payload)
        return payload

    async def start_periodic(self) -> None:
        if self._task and not self._task.done():
            return

        async def _loop() -> None:
            while True:
                try:
                    await self.run_once()
                except Exception as exc:  # pragma: no cover - defensive path
                    logger.error(f"Health check failed: {exc}")
                await asyncio.sleep(self.interval_seconds)

        self._task = asyncio.create_task(_loop(), name="health-check-loop")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
