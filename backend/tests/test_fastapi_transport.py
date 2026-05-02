from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import api.fastapi_app as fastapi_app
import pytest
from fastapi.testclient import TestClient


def _install_fake_backend(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    calls: dict[str, Any] = {"start": 0, "stop": 0, "messages": []}

    class FakeBackend:
        always_on_enabled = False
        latest_health_status = {
            "microphone": True,
            "model_loaded": True,
            "websocket": True,
            "apis": {},
        }
        latest_auth_result = {"status": "unverified"}

        def __init__(self):
            self.ws_manager = MagicMock()
            self.ws_manager.clients = set()
            self.state_machine = MagicMock()
            self.state_machine.state.value = "idle"
            self.process_message = AsyncMock(side_effect=self._process)

        async def _process(self, msg: Any, *args: Any, **kwargs: Any) -> None:
            calls["messages"].append(msg)
            # simulate pong message broadcasting back if needed
            # but usually the test client can't intercept ws_manager.broadcast
            # For ping test, the actual handler responds directly
            pass

        async def start(self) -> None:
            calls["start"] += 1

        async def stop(self) -> None:
            calls["stop"] += 1

    backend = FakeBackend()
    import core.orchestrator

    monkeypatch.setattr(core.orchestrator, "get_orchestrator", lambda: backend)
    return calls


def test_fastapi_health_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status"] == "healthy"
    assert payload["backend"]["websocket"] is True


def test_fastapi_health_cors_for_vite_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        response = client.get(
            "/api/v1/health", headers={"Origin": "http://localhost:5173"}
        )

    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    )


def test_websocket_transport_ws_path(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["type"] == "health_status"

            second = ws.receive_json()
            assert second["type"] == "auth_result"

            third = ws.receive_json()
            assert third["type"] == "voice_state_change"

            ws.send_text(
                json.dumps(
                    {
                        "type": "ping",
                        "payload": {},
                        "timestamp": "2026-01-01T00:00:00Z",
                        "request_id": "test-1",
                    }
                )
            )
            fourth = ws.receive_json()
            assert fourth["type"] == "pong"


def test_websocket_transport_root_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        response = client.get("/api/v1/")
        assert response.status_code == 200
        assert response.json()["service"] == "jarvis-backend"
