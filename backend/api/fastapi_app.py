from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from main import get_backend


class FastAPIWebSocketAdapter:
    """Adapter to reuse existing websocket business logic with FastAPI transport."""

    def __init__(self, websocket: WebSocket) -> None:
        self._ws = websocket

    async def send(self, payload: str) -> None:
        await self._ws.send_text(payload)

    async def close(self, code: int = 1001, reason: str = "") -> None:
        await self._ws.close(code=code, reason=reason)

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        try:
            return await self._ws.receive_text()
        except WebSocketDisconnect:
            raise StopAsyncIteration


@asynccontextmanager
async def lifespan(_app: FastAPI):
    backend = get_backend()
    await backend.start()
    try:
        yield
    finally:
        await backend.stop()


app = FastAPI(title="Jarvis Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    backend = get_backend()
    return {
        "ok": True,
        "status": "healthy",
        "always_on": backend.always_on_enabled,
        "backend": backend.latest_health_status,
    }


async def _serve_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    backend = get_backend()
    adapter = FastAPIWebSocketAdapter(websocket)
    await backend._handle_client(adapter)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await _serve_websocket(websocket)


@app.websocket("/")
async def websocket_root_endpoint(websocket: WebSocket) -> None:
    await _serve_websocket(websocket)


@app.get("/")
async def root() -> dict:
    return {"service": "jarvis-backend", "transport": "fastapi-websocket", "ws_path": "/ws"}
