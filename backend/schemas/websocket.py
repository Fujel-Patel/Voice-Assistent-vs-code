from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool
    status: str
    always_on: bool
    backend: dict[str, Any]


class RootResponse(BaseModel):
    service: str
    transport: str
    ws_path: str


class WebSocketMessage(BaseModel):
    type: str = Field(..., description="The type of the message")
    payload: dict[str, Any] = Field(
        default_factory=dict, description="The message payload"
    )
    request_id: str | None = Field(
        None, description="Optional request ID for request/response tracking"
    )
