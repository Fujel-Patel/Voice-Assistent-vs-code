from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.logger import get_logger
from core.orchestrator import get_orchestrator
from fastapi import WebSocket, WebSocketDisconnect
from voice.state_machine import VoiceState

from api.schemas import WebSocketMessage

logger = get_logger(__name__)


def _message(
    msg_type: str, payload: dict[str, Any], request_id: str | None = None
) -> dict[str, Any]:
    return {
        "type": msg_type,
        "payload": payload,
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id or str(uuid4()),
    }


async def handle_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    backend = get_orchestrator()

    backend.clients.add(websocket)
    logger.info(f"Client connected. count={len(backend.clients)}")

    await websocket.send_text(
        json.dumps(
            _message(
                msg_type="health_status",
                payload=backend.latest_health_status,
            )
        )
    )
    await websocket.send_text(
        json.dumps(
            _message(
                msg_type="auth_result",
                payload=backend.latest_auth_result,
            )
        )
    )
    await websocket.send_text(
        json.dumps(
            _message(
                msg_type="voice_state_change",
                payload={
                    "state": backend.state_machine.state.value,
                    "previous_state": backend.state_machine.state.value,
                    "source": "snapshot",
                },
            )
        )
    )

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                ws_msg = WebSocketMessage(**data)
            except Exception as e:
                await websocket.send_text(
                    json.dumps(
                        _message(
                            msg_type="error",
                            payload={
                                "code": "INVALID_FORMAT",
                                "message": f"Invalid message format: {e}",
                                "recoverable": True,
                            },
                        )
                    )
                )
                continue

            message_type = ws_msg.type
            payload = ws_msg.payload
            req_id = ws_msg.request_id

            try:
                if message_type == "ping":
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="pong",
                                payload={"timestamp": datetime.now(UTC).isoformat()},
                                request_id=req_id,
                            )
                        )
                    )
                elif message_type == "start_listening":
                    if backend.state_machine.state != VoiceState.IDLE:
                        logger.info(
                            f"Interrupting {backend.state_machine.state.value} for manual start_listening"
                        )
                        backend.recorder.cancel_recording()
                        await backend.state_machine.reset()

                    backend.wake_queue.put_nowait(
                        {
                            "ts": datetime.now(UTC).isoformat(),
                            "source": "manual",
                        }
                    )
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="voice_state_change",
                                payload={
                                    "state": "wake_detected",
                                    "previous_state": backend.state_machine.state.value,
                                    "source": "manual",
                                },
                                request_id=req_id,
                            )
                        )
                    )
                elif message_type == "interrupt":
                    if backend.state_machine.state in {
                        VoiceState.WAKE_DETECTED,
                        VoiceState.LISTENING,
                        VoiceState.TRANSCRIBING,
                        VoiceState.VERIFYING,
                        VoiceState.THINKING,
                    }:
                        backend.recorder.cancel_recording()
                        await backend.state_machine.reset()
                    else:
                        await backend.state_machine.handle_interrupt()
                elif message_type == "user_command":
                    text = str(payload.get("text") or "").strip()
                    if not text:
                        await websocket.send_text(
                            json.dumps(
                                _message(
                                    msg_type="error",
                                    payload={
                                        "code": "EMPTY_COMMAND",
                                        "message": "user_command payload.text is required",
                                        "recoverable": True,
                                    },
                                    request_id=req_id,
                                )
                            )
                        )
                        continue

                    await backend._process_text_command(
                        user_text=text,
                        request_id=req_id or str(uuid4()),
                    )
                elif message_type in {
                    "get_settings",
                    "update_setting",
                    "update_settings_bulk",
                    "validate_api_key",
                    "reset_settings",
                    "export_settings",
                    "import_settings",
                }:
                    handled = await backend.settings_handler.handle(
                        message_type, payload
                    )
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type=handled["type"],
                                payload=handled["payload"],
                                request_id=req_id,
                            )
                        )
                    )

                    if handled["type"] == "settings_updated" and handled["payload"].get(
                        "ok"
                    ):
                        settings_payload = handled["payload"].get("settings", {})
                        threshold_level = settings_payload.get("auth.threshold")
                        if isinstance(threshold_level, str):
                            backend.speaker_verifier.set_threshold(threshold_level)

                        await backend.broadcast(
                            _message(
                                msg_type="settings_sync", payload=handled["payload"]
                            )
                        )
                elif message_type == "verify_pin":
                    pin = str(payload.get("pin") or "")
                    ok = backend.access_controller.verify_pin(pin)
                    if ok:
                        backend.speaker_verifier.mark_pin_verified(
                            backend.config.auth.default_user_id
                        )
                        backend.latest_auth_result = {
                            "verified": True,
                            "confidence": 0.99,
                            "user_id": backend.config.auth.default_user_id,
                            "mode": "pin",
                            "threshold_used": backend.speaker_verifier.current_threshold,
                            "pin_required": False,
                        }
                        await backend.broadcast(
                            _message(
                                msg_type="auth_result",
                                payload=backend.latest_auth_result,
                            )
                        )

                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="pin_result",
                                payload={
                                    "ok": ok,
                                    "message": "PIN verified" if ok else "Invalid PIN",
                                },
                                request_id=req_id,
                            )
                        )
                    )
                elif message_type == "start_voice_enrollment":
                    user_id = str(
                        payload.get("user_id") or backend.config.auth.default_user_id
                    )
                    response = await backend.enrollment.start_enrollment(user_id)
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="enrollment_status",
                                payload=response,
                                request_id=req_id,
                            )
                        )
                    )
                elif message_type == "submit_voice_sample":
                    user_id = str(
                        payload.get("user_id") or backend.config.auth.default_user_id
                    )
                    step = int(payload.get("step") or 1)
                    int(payload.get("sample_rate") or 16000)
                    transcript_text = payload.get("transcript_text")
                    capture_duration_ms = payload.get("capture_duration_ms")
                    if capture_duration_ms is not None:
                        try:
                            capture_duration_ms = int(capture_duration_ms)
                        except (TypeError, ValueError):
                            capture_duration_ms = None

                    audio_b64 = payload.get("audio_base64")
                    if not isinstance(audio_b64, str) or not audio_b64:
                        await websocket.send_text(
                            json.dumps(
                                _message(
                                    msg_type="enrollment_status",
                                    payload={
                                        "ok": False,
                                        "error": "Missing audio_base64",
                                    },
                                    request_id=req_id,
                                )
                            )
                        )
                        continue

                    audio = backend._decode_audio_payload(audio_b64)
                    response = await backend.enrollment.process_sample(
                        user_id=user_id,
                        audio=audio,
                        step=step,
                        transcript_text=transcript_text,
                        capture_duration_ms=capture_duration_ms,
                    )
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="enrollment_status",
                                payload=response,
                                request_id=req_id,
                            )
                        )
                    )
                elif message_type == "complete_voice_enrollment":
                    user_id = str(
                        payload.get("user_id") or backend.config.auth.default_user_id
                    )
                    response = await backend.enrollment.complete_enrollment(user_id)
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="enrollment_status",
                                payload=response,
                                request_id=req_id,
                            )
                        )
                    )
                elif message_type == "set_always_on":
                    backend.always_on_enabled = bool(payload.get("enabled", False))
                    logger.info(f"Always-on speaker set to {backend.always_on_enabled}")
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="settings_sync",
                                payload={
                                    "ok": True,
                                    "settings": {
                                        "always_on": backend.always_on_enabled
                                    },
                                },
                                request_id=req_id,
                            )
                        )
                    )
                else:
                    await websocket.send_text(
                        json.dumps(
                            _message(
                                msg_type="error",
                                payload={
                                    "code": "UNKNOWN_MESSAGE_TYPE",
                                    "message": f"Unsupported message type: {message_type}",
                                    "recoverable": True,
                                },
                                request_id=req_id,
                            )
                        )
                    )
            except Exception as exc:
                logger.exception(f"Failed handling message type={message_type}: {exc}")
                if backend.state_machine.state != VoiceState.IDLE:
                    await backend.state_machine.reset()
                await websocket.send_text(
                    json.dumps(
                        _message(
                            msg_type="error",
                            payload={
                                "code": "MESSAGE_HANDLER_ERROR",
                                "message": str(exc),
                                "recoverable": True,
                                "message_type": message_type,
                            },
                            request_id=req_id,
                        )
                    )
                )
    except WebSocketDisconnect:
        raise
    except Exception:
        logger.exception("Unhandled error in websocket client handler")
    finally:
        backend.clients.discard(websocket)
        logger.info(f"Client disconnected. count={len(backend.clients)}")
