from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, cast

from core.config import load_config
from core.logger import get_logger
from infrastructure.database.db import get_db

logger = get_logger(__name__)


@dataclass
class StartupDependencies:
    model_ready: Callable[[], Awaitable[None]] | None = None
    voice_init: Callable[[], Awaitable[None]] | None = None
    plugin_discover: Callable[[], None] | None = None
    ws_start: Callable[[], Awaitable[None]] | None = None
    listener_start: Callable[[], Awaitable[None]] | None = None
    health_check: Callable[[], Awaitable[dict[str, Any]]] | None = None
    broadcast: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    listener_stop: Callable[[], Awaitable[None]] | None = None
    voice_cleanup: Callable[[], Awaitable[None]] | None = None
    ws_stop: Callable[[], Awaitable[None]] | None = None


class StartupManager:
    """Orchestrates backend startup and shutdown with health/degraded reporting."""

    def __init__(self, deps: StartupDependencies | None = None) -> None:
        self.deps = deps or StartupDependencies()
        self.health: dict[str, Any] = {}

    async def start(self) -> dict[str, Any]:
        logger.info("Loading configuration...")
        config = load_config()
        if not config:
            raise RuntimeError("Fatal failure: configuration is invalid")

        logger.info("Initializing database...")
        await get_db()

        degraded_reasons: list[str] = []

        await self._best_effort(
            "Checking models...", self.deps.model_ready, degraded_reasons
        )
        await self._best_effort(
            "Starting voice pipeline...", self.deps.voice_init, degraded_reasons
        )
        self._best_effort_sync(
            "Loading plugins...", self.deps.plugin_discover, degraded_reasons
        )
        await self._best_effort(
            "Starting WebSocket server...", self.deps.ws_start, degraded_reasons
        )
        await self._best_effort(
            "Starting wake word listener...", self.deps.listener_start, degraded_reasons
        )

        if self.deps.health_check is not None:
            try:
                self.health = await self.deps.health_check()
            except Exception as exc:
                degraded_reasons.append(f"health_check_failed: {exc}")
                self.health = {"status": "degraded", "details": str(exc)}
        else:
            self.health = {"status": "unknown"}

        status = "ready" if not degraded_reasons else "degraded"
        payload: dict[str, Any] = {
            "type": "system_status",
            "payload": {
                "status": status,
                "health": self.health,
                "degraded_reasons": degraded_reasons,
            },
        }

        if self.deps.broadcast is not None:
            await self.deps.broadcast(payload)

        logger.info(f"Startup complete. status={status}")
        return cast(dict[str, Any], payload["payload"])

    async def shutdown(self) -> None:
        logger.info("Shutting down Jarvis...")
        if self.deps.listener_stop is not None:
            await self._quiet_call(self.deps.listener_stop)
        if self.deps.voice_cleanup is not None:
            await self._quiet_call(self.deps.voice_cleanup)
        if self.deps.ws_stop is not None:
            await self._quiet_call(self.deps.ws_stop)

        db = await get_db()
        await db.close()
        logger.info("Jarvis shutdown complete.")

    async def _best_effort(
        self,
        stage: str,
        callback: Callable[[], Awaitable[None]] | None,
        degraded_reasons: list[str],
    ) -> None:
        if callback is None:
            return
        logger.info(stage)
        try:
            await callback()
        except Exception as exc:
            logger.warning(f"{stage} failed: {exc}")
            degraded_reasons.append(f"{stage} failed: {exc}")

    def _best_effort_sync(
        self,
        stage: str,
        callback: Callable[[], None] | None,
        degraded_reasons: list[str],
    ) -> None:
        if callback is None:
            return
        logger.info(stage)
        try:
            callback()
        except Exception as exc:
            logger.warning(f"{stage} failed: {exc}")
            degraded_reasons.append(f"{stage} failed: {exc}")

    async def _quiet_call(self, callback: Callable[[], Awaitable[None]]) -> None:
        try:
            await callback()
        except Exception as exc:
            logger.warning(f"Shutdown step failed: {exc}")
