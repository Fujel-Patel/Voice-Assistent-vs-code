from __future__ import annotations

from typing import Any

import pytest
from services.startup import StartupDependencies, StartupManager


@pytest.mark.asyncio
async def test_startup_manager_ready() -> None:
    called = {"broadcast": False}

    async def noop_async() -> None:
        return None

    def noop_sync() -> None:
        return None

    async def health() -> dict[str, Any]:
        return {"ok": True}

    async def broadcast(_payload: Any) -> None:
        called["broadcast"] = True

    manager = StartupManager(
        StartupDependencies(
            model_ready=noop_async,
            voice_init=noop_async,
            plugin_discover=noop_sync,
            ws_start=noop_async,
            listener_start=noop_async,
            health_check=health,
            broadcast=broadcast,
        )
    )

    result = await manager.start()
    assert result["status"] == "ready"
    assert called["broadcast"] is True


@pytest.mark.asyncio
async def test_startup_manager_degraded() -> None:
    async def fail_step() -> None:
        raise RuntimeError("microphone unavailable")

    manager = StartupManager(
        StartupDependencies(
            listener_start=fail_step,
            health_check=lambda: _health(),
        )
    )

    result = await manager.start()
    assert result["status"] == "degraded"
    assert result["degraded_reasons"]


async def _health() -> dict[str, Any]:
    return {"ok": False}
