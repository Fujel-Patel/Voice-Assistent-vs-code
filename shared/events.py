"""
Jarvis Shared — Event Type Enums
==================================
Python enum mirror of all IPC event types defined in ipc_protocol.json.
This file should stay in sync with:
  - shared/ipc_protocol.json
  - shared/events.ts (TypeScript mirror for frontend)

Usage:
    from shared.events import BackendEvent, FrontendEvent

    await ws.send_json({
        "type": BackendEvent.VOICE_STATE_CHANGE,
        "payload": {"state": "listening"},
    })
"""

from enum import StrEnum


class BackendEvent(StrEnum):
    """Events sent FROM the Python backend TO the Electron frontend."""

    SERVER_READY = "server_ready"

    # Voice pipeline states
    VOICE_STATE_CHANGE = "voice_state_change"
    TRANSCRIPTION_RESULT = "transcription_result"
    TRANSCRIPT_CHUNK = "transcript_chunk"

    # AI responses
    ASSISTANT_RESPONSE = "assistant_response"
    ASSISTANT_RESPONSE_CHUNK = "assistant_response_chunk"
    RESPONSE_START = "response_start"

    # TTS
    TTS_AUDIO = "tts_audio"
    TTS_START = "tts_start"
    TTS_CHUNK = "tts_chunk"
    TTS_END = "tts_end"
    TTS_STARTED_LEGACY = "tts_started"
    TTS_COMPLETED_LEGACY = "tts_completed"
    AUDIO_LEVEL = "audio_level"

    # System
    HEALTH_STATUS = "health_status"
    SETTINGS_RESPONSE = "settings_response"
    SETTINGS_UPDATED = "settings_updated"
    SETTINGS_SYNC = "settings_sync"
    API_KEY_VALIDATION = "api_key_validation"
    AUTH_RESULT = "auth_result"
    AUTH_CHALLENGE = "auth_challenge"
    AUTH_CHALLENGE_RESULT = "auth_challenge_result"
    ENROLLMENT_STATUS = "enrollment_status"
    PIN_RESULT = "pin_result"
    ERROR = "error"
    PONG = "pong"


class FrontendEvent(StrEnum):
    """Events sent FROM the Electron frontend TO the Python backend."""

    USER_COMMAND = "user_command"
    INTERRUPT = "interrupt"
    CONFIG_UPDATE = "config_update"
    GET_SETTINGS = "get_settings"
    UPDATE_SETTING = "update_setting"
    UPDATE_SETTINGS_BULK = "update_settings_bulk"
    VALIDATE_API_KEY = "validate_api_key"
    START_VOICE_ENROLLMENT = "start_voice_enrollment"
    SUBMIT_VOICE_SAMPLE = "submit_voice_sample"
    COMPLETE_VOICE_ENROLLMENT = "complete_voice_enrollment"
    START_LISTENING = "start_listening"
    SET_ALWAYS_ON = "set_always_on"
    VERIFY_PIN = "verify_pin"
    PING = "ping"


class VoiceState(StrEnum):
    """All valid voice pipeline states (used in voice_state_change payload)."""

    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    VERIFYING = "verifying"
    THINKING = "thinking"
    SPEAKING = "speaking"


class TTSState(StrEnum):
    """TTS playback states (used in tts_state payload)."""

    STARTED = "started"
    PLAYING = "playing"
    DONE = "done"
    ERROR = "error"


class HealthStatus(StrEnum):
    """System health statuses."""

    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class CommandSource(StrEnum):
    """How a user command was triggered."""

    VOICE = "voice"
    KEYBOARD = "keyboard"
