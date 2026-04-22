from __future__ import annotations

import json

from fastapi.testclient import TestClient

import api.fastapi_app as fastapi_app


def _install_fake_backend(monkeypatch):
    calls = {"start": 0, "stop": 0, "messages": []}

    class FakeBackend:
        always_on_enabled = False
        latest_health_status = {
            "microphone": True,
            "model_loaded": True,
            "websocket": True,
            "apis": {},
        }

        async def start(self) -> None:
            calls["start"] += 1

        async def stop(self) -> None:
            calls["stop"] += 1

        async def _handle_client(self, adapter) -> None:
            # Send one message so websocket clients can verify end-to-end flow.
            await adapter.send(
                json.dumps(
                    {
                        "type": "health_status",
                        "payload": self.latest_health_status,
                        "timestamp": "2026-01-01T00:00:00Z",
                        "request_id": "transport-test",
                    }
                )
            )

            async for raw in adapter:
                calls["messages"].append(raw)
                await adapter.send(
                    json.dumps(
                        {
                            "type": "pong",
                            "payload": {"echo": "ok"},
                            "timestamp": "2026-01-01T00:00:00Z",
                            "request_id": "transport-test",
                        }
                    )
                )
                break

    backend = FakeBackend()
    monkeypatch.setattr(fastapi_app, "get_backend", lambda: backend)
    return calls


def test_fastapi_health_endpoint(monkeypatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["status"] == "healthy"
    assert payload["backend"]["websocket"] is True


def test_fastapi_health_cors_for_vite_origin(monkeypatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_websocket_transport_ws_path(monkeypatch) -> None:
    calls = _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        with client.websocket_connect("/ws") as ws:
            first = ws.receive_json()
            assert first["type"] == "health_status"

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
            second = ws.receive_json()
            assert second["type"] == "pong"

    assert calls["messages"]


def test_websocket_transport_root_alias(monkeypatch) -> None:
    _install_fake_backend(monkeypatch)

    with TestClient(fastapi_app.app) as client:
        with client.websocket_connect("/") as ws:
            first = ws.receive_json()
            assert first["type"] == "health_status"
