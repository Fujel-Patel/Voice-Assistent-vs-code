from __future__ import annotations

# We cannot easily import get_backend from main.py if we are moving things to core.
# We will use a dependency or direct import from the new core.orchestrator
from core.orchestrator import get_orchestrator
from fastapi import APIRouter

from api.schemas import HealthResponse, RootResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Check health status",
)
async def health() -> HealthResponse:
    orchestrator = get_orchestrator()
    return HealthResponse(
        ok=True,
        status="healthy",
        always_on=orchestrator.always_on_enabled,
        backend=orchestrator.latest_health_status,
    )


@router.get("/", response_model=RootResponse, status_code=200, summary="Root endpoint")
async def root() -> RootResponse:
    return RootResponse(
        service="jarvis-backend",
        transport="fastapi-websocket",
        ws_path="/ws",
    )
