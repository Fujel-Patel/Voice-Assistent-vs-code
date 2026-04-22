export enum BackendEvent {
  SERVER_READY = "server_ready",
  VOICE_STATE_CHANGE = "voice_state_change",
  TRANSCRIPTION_RESULT = "transcription_result",
  TRANSCRIPT_CHUNK = "transcript_chunk",
  ASSISTANT_RESPONSE = "assistant_response",
  ASSISTANT_RESPONSE_CHUNK = "assistant_response_chunk",
  RESPONSE_START = "response_start",
  TTS_AUDIO = "tts_audio",
  TTS_START = "tts_start",
  TTS_CHUNK = "tts_chunk",
  TTS_END = "tts_end",
  TTS_STARTED_LEGACY = "tts_started",
  TTS_COMPLETED_LEGACY = "tts_completed",
  AUDIO_LEVEL = "audio_level",
  HEALTH_STATUS = "health_status",
  SETTINGS_RESPONSE = "settings_response",
  SETTINGS_UPDATED = "settings_updated",
  SETTINGS_SYNC = "settings_sync",
  API_KEY_VALIDATION = "api_key_validation",
  AUTH_RESULT = "auth_result",
  AUTH_CHALLENGE = "auth_challenge",
  AUTH_CHALLENGE_RESULT = "auth_challenge_result",
  ENROLLMENT_STATUS = "enrollment_status",
  PIN_RESULT = "pin_result",
  ERROR = "error",
  PONG = "pong",
}

export enum FrontendEvent {
  USER_COMMAND = "user_command",
  INTERRUPT = "interrupt",
  CONFIG_UPDATE = "config_update",
  GET_SETTINGS = "get_settings",
  UPDATE_SETTING = "update_setting",
  UPDATE_SETTINGS_BULK = "update_settings_bulk",
  VALIDATE_API_KEY = "validate_api_key",
  START_VOICE_ENROLLMENT = "start_voice_enrollment",
  SUBMIT_VOICE_SAMPLE = "submit_voice_sample",
  COMPLETE_VOICE_ENROLLMENT = "complete_voice_enrollment",
  START_LISTENING = "start_listening",
  SET_ALWAYS_ON = "set_always_on",
  VERIFY_PIN = "verify_pin",
  PING = "ping",
}

export enum VoiceState {
  IDLE = "idle",
  WAKE_DETECTED = "wake_detected",
  LISTENING = "listening",
  TRANSCRIBING = "transcribing",
  VERIFYING = "verifying",
  THINKING = "thinking",
  SPEAKING = "speaking",
}

export enum TTSState {
  STARTED = "started",
  PLAYING = "playing",
  DONE = "done",
  ERROR = "error",
}

export enum HealthStatus {
  OK = "ok",
  DEGRADED = "degraded",
  FAILED = "failed",
  UNKNOWN = "unknown",
}

export enum CommandSource {
  VOICE = "voice",
  KEYBOARD = "keyboard",
}
