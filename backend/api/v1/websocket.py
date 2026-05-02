from __future__ import annotations

from api.websocket_handler import handle_websocket
from core.logger import get_logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    try:
        await handle_websocket(websocket)
    except WebSocketDisconnect as exc:
        logger.info(f"WebSocket disconnected with code {exc.code}")
    except Exception as exc:
        logger.exception(f"Unexpected error in websocket connection: {exc}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


@router.websocket("/")
async def websocket_root_endpoint(websocket: WebSocket) -> None:
    try:
        await handle_websocket(websocket)
    except WebSocketDisconnect as exc:
        logger.info(f"WebSocket disconnected with code {exc.code}")
    except Exception as exc:
        logger.exception(f"Unexpected error in websocket connection: {exc}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
