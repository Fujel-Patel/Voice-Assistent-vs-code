from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from core.logger import get_logger
from core.orchestrator import get_orchestrator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.v1.health import router as health_router
from api.v1.websocket import router as websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    orchestrator = get_orchestrator()
    await orchestrator.start()
    try:
        yield
    finally:
        await orchestrator.stop()


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

app.include_router(health_router, prefix="/api/v1")
app.include_router(websocket_router)
