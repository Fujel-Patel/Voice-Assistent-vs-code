from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

CONFIG_DIR = Path(__file__).parent
DEFAULT_CONFIG_PATH = CONFIG_DIR / "default.yaml"
USER_CONFIG_PATH = CONFIG_DIR / "user_config.yaml"
ENV_FILE_PATH = CONFIG_DIR.parent.parent / ".env"


class WakeWordConfig(BaseModel):
    engine: str = "openwakeword"
    sensitivity: float = 0.5
    keyword: str = "jarvis"
    openwakeword_model_path: str = ""
    openwakeword_vad_threshold: float = 0.0
    openwakeword_enable_speex: bool = False


class AudioConfig(BaseModel):
    sample_rate: int = 16000
    channels: int = 1
    silence_threshold: float = 2.0
    max_recording_duration: float = 30.0
    min_recording_duration: float = 0.5
    no_speech_timeout: float = 5.0
    silence_stop_seconds: float = 2.0


class STTConfig(BaseModel):
    engine: str = "moonshine"
    model: str = "tiny"
    language: str = "en-us"
    compute_type: str = "int8"
    vosk_model_path: str = ""


class LoggingConfig(BaseModel):
    level: str = "INFO"
    file: str = "logs/jarvis.log"


class TTSConfig(BaseModel):
    primary: str = "edge"
    fallback: str = "local"
    voice_id: str = "jarvis_custom"
    model_id: str = "eleven_turbo_v2"
    stability: float = 0.5
    similarity_boost: float = 0.8
    speaking_rate: float = 1.0
    volume: float = 0.8
    local_voice: str = "en_US-lessac-medium"
    piper_model: str = "en_US-lessac-medium.onnx"
    piper_speaker_id: int | None = None
    piper_noise_scale: float = 0.667
    piper_noise_w: float = 0.8
    piper_sentence_silence: float = 0.0
    edge_voice: str = "jarvis"
    kitten_model: str = "kitten-1"
    kitten_voice: str = "alloy"
    sample_rate: int = 22050


class BrainProviderConfig(BaseModel):
    default_provider: str = "gemini"
    fallback_order: list[str] = Field(
        default_factory=lambda: ["claude", "gemini", "groq", "openrouter", "ollama"]
    )


class BrainModelConfig(BaseModel):
    claude: str = "claude-sonnet-4-20250514"
    gemini: str = "gemini-2.5-flash"
    groq: str = "llama-3.3-70b-versatile"
    openrouter: str = "openai/gpt-4o-mini"
    ollama: str = "llama3.2"
    summary_model: str = "claude-3-5-haiku-20241022"


class BrainConfig(BaseModel):
    providers: BrainProviderConfig = Field(default_factory=BrainProviderConfig)
    models: BrainModelConfig = Field(default_factory=BrainModelConfig)
    token_budget: int = 4000
    short_term_turns: int = 20
    long_term_top_k: int = 3
    stream_chunks: bool = True


class WebConfig(BaseModel):
    search_engine: str = "brave"
    max_results: int = 5
    safe_search: str = "moderate"
    country: str = "US"
    language: str = "en"
    search_cache_ttl_seconds: int = 300
    summary_cache_ttl_seconds: int = 3600


class AuthConfig(BaseModel):
    enabled: bool = False
    mode: str = "passive"
    threshold: str = "medium"
    liveness: str = "sensitive_only"
    pin_fallback: bool = True
    session_timeout_minutes: int = 30
    reverify_minutes: int = 5
    default_user_id: str = "default_user"
    pin_code: str = "1234"


class ProviderAPIKeys(BaseModel):
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None
    ollama_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"


class JarvisConfig(BaseModel):
    wake_word: WakeWordConfig = Field(default_factory=WakeWordConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    stt: STTConfig = Field(default_factory=STTConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    brain: BrainConfig = Field(default_factory=BrainConfig)
    web: WebConfig = Field(default_factory=WebConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    provider_keys: ProviderAPIKeys = Field(default_factory=ProviderAPIKeys)

    elevenlabs_api_key: str | None = None
    brave_search_api_key: str | None = None


_ENV_TO_CONFIG_MAP: dict[str, tuple[str, ...]] = {
    "JARVIS_WAKE_WORD_ENGINE": ("wake_word", "engine"),
    "JARVIS_WAKE_WORD_SENSITIVITY": ("wake_word", "sensitivity"),
    "JARVIS_WAKE_WORD_KEYWORD": ("wake_word", "keyword"),
    "JARVIS_WAKE_WORD_MODEL_PATH": ("wake_word", "openwakeword_model_path"),
    "JARVIS_WAKE_WORD_VAD_THRESHOLD": ("wake_word", "openwakeword_vad_threshold"),
    "JARVIS_WAKE_WORD_ENABLE_SPEEX": ("wake_word", "openwakeword_enable_speex"),
    "JARVIS_AUDIO_SAMPLE_RATE": ("audio", "sample_rate"),
    "JARVIS_AUDIO_CHANNELS": ("audio", "channels"),
    "JARVIS_AUDIO_SILENCE_THRESHOLD": ("audio", "silence_threshold"),
    "JARVIS_AUDIO_MAX_RECORDING_DURATION": ("audio", "max_recording_duration"),
    "JARVIS_AUDIO_MIN_RECORDING_DURATION": ("audio", "min_recording_duration"),
    "JARVIS_AUDIO_NO_SPEECH_TIMEOUT": ("audio", "no_speech_timeout"),
    "JARVIS_AUDIO_SILENCE_STOP_SECONDS": ("audio", "silence_stop_seconds"),
    "JARVIS_STT_MODEL": ("stt", "model"),
    "JARVIS_STT_ENGINE": ("stt", "engine"),
    "JARVIS_STT_LANGUAGE": ("stt", "language"),
    "JARVIS_STT_COMPUTE_TYPE": ("stt", "compute_type"),
    "JARVIS_STT_VOSK_MODEL_PATH": ("stt", "vosk_model_path"),
    "JARVIS_TTS_PRIMARY": ("tts", "primary"),
    "JARVIS_TTS_FALLBACK": ("tts", "fallback"),
    "JARVIS_TTS_VOICE_ID": ("tts", "voice_id"),
    "JARVIS_TTS_KITTEN_MODEL": ("tts", "kitten_model"),
    "JARVIS_TTS_KITTEN_VOICE": ("tts", "kitten_voice"),
    "JARVIS_TTS_MODEL_ID": ("tts", "model_id"),
    "JARVIS_TTS_SPEAKING_RATE": ("tts", "speaking_rate"),
    "JARVIS_TTS_VOLUME": ("tts", "volume"),
    "JARVIS_TTS_PIPER_MODEL": ("tts", "piper_model"),
    "JARVIS_TTS_PIPER_SPEAKER_ID": ("tts", "piper_speaker_id"),
    "JARVIS_TTS_PIPER_NOISE_SCALE": ("tts", "piper_noise_scale"),
    "JARVIS_TTS_PIPER_NOISE_W": ("tts", "piper_noise_w"),
    "JARVIS_TTS_PIPER_SENTENCE_SILENCE": ("tts", "piper_sentence_silence"),
    "JARVIS_BRAIN_DEFAULT_PROVIDER": ("brain", "providers", "default_provider"),
    "JARVIS_BRAIN_TOKEN_BUDGET": ("brain", "token_budget"),
    "JARVIS_BRAIN_SHORT_TERM_TURNS": ("brain", "short_term_turns"),
    "JARVIS_BRAIN_LONG_TERM_TOP_K": ("brain", "long_term_top_k"),
    "JARVIS_WEB_SEARCH_ENGINE": ("web", "search_engine"),
    "JARVIS_WEB_MAX_RESULTS": ("web", "max_results"),
    "JARVIS_WEB_SAFE_SEARCH": ("web", "safe_search"),
    "JARVIS_WEB_COUNTRY": ("web", "country"),
    "JARVIS_WEB_LANGUAGE": ("web", "language"),
    "JARVIS_WEB_SEARCH_CACHE_TTL": ("web", "search_cache_ttl_seconds"),
    "JARVIS_WEB_SUMMARY_CACHE_TTL": ("web", "summary_cache_ttl_seconds"),
    "JARVIS_AUTH_ENABLED": ("auth", "enabled"),
    "JARVIS_AUTH_MODE": ("auth", "mode"),
    "JARVIS_AUTH_THRESHOLD": ("auth", "threshold"),
    "JARVIS_AUTH_LIVENESS": ("auth", "liveness"),
    "JARVIS_AUTH_PIN_FALLBACK": ("auth", "pin_fallback"),
    "JARVIS_AUTH_SESSION_TIMEOUT_MINUTES": ("auth", "session_timeout_minutes"),
    "JARVIS_AUTH_REVERIFY_MINUTES": ("auth", "reverify_minutes"),
    "JARVIS_AUTH_DEFAULT_USER_ID": ("auth", "default_user_id"),
    "JARVIS_AUTH_PIN_CODE": ("auth", "pin_code"),
    "JARVIS_LOGGING_LEVEL": ("logging", "level"),
    "JARVIS_LOGGING_FILE": ("logging", "file"),
}


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _coerce_value(raw: str) -> Any:
    lowered = raw.strip().lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _set_nested(config: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    target = config
    for key in path[:-1]:
        target = target.setdefault(key, {})
    target[path[-1]] = value


def _get_nested(config: dict[str, Any], path: tuple[str, ...]) -> Any:
    target: Any = config
    for key in path:
        if not isinstance(target, dict) or key not in target:
            raise KeyError(".".join(path))
        target = target[key]
    return target


def _parse_setting_path(key: str) -> tuple[str, ...]:
    key = (key or "").strip()
    if not key:
        raise ValueError("Setting key cannot be empty")
    return tuple(part for part in key.split(".") if part)


@lru_cache(maxsize=1)
def load_config() -> JarvisConfig:
    load_dotenv(ENV_FILE_PATH, override=False)

    merged = _deep_merge(_load_yaml(DEFAULT_CONFIG_PATH), _load_yaml(USER_CONFIG_PATH))

    for env_key, path in _ENV_TO_CONFIG_MAP.items():
        raw_value = os.getenv(env_key)
        if raw_value is None:
            continue
        _set_nested(merged, path, _coerce_value(raw_value))

    merged["elevenlabs_api_key"] = os.getenv("ELEVENLABS_API_KEY")
    merged["brave_search_api_key"] = os.getenv("BRAVE_SEARCH_API_KEY")

    merged.setdefault("provider_keys", {})
    merged["provider_keys"]["anthropic_api_key"] = os.getenv("ANTHROPIC_API_KEY")
    merged["provider_keys"]["gemini_api_key"] = os.getenv("GEMINI_API_KEY")
    merged["provider_keys"]["groq_api_key"] = os.getenv("GROQ_API_KEY")
    merged["provider_keys"]["openrouter_api_key"] = os.getenv("OPENROUTER_API_KEY")
    merged["provider_keys"]["ollama_api_key"] = os.getenv("OLLAMA_API_KEY")
    if os.getenv("OLLAMA_BASE_URL"):
        merged["provider_keys"]["ollama_base_url"] = os.getenv("OLLAMA_BASE_URL")
    if os.getenv("OPENROUTER_BASE_URL"):
        merged["provider_keys"]["openrouter_base_url"] = os.getenv(
            "OPENROUTER_BASE_URL"
        )
    if os.getenv("GROQ_BASE_URL"):
        merged["provider_keys"]["groq_base_url"] = os.getenv("GROQ_BASE_URL")
    if os.getenv("GEMINI_BASE_URL"):
        merged["provider_keys"]["gemini_base_url"] = os.getenv("GEMINI_BASE_URL")

    return JarvisConfig.model_validate(merged)


def get_config_dict() -> dict[str, Any]:
    return load_config().model_dump()


def save_all(settings: dict[str, Any]) -> JarvisConfig:
    if not isinstance(settings, dict):
        raise ValueError("settings must be a dictionary")

    current_user = _load_yaml(USER_CONFIG_PATH)
    merged_user = _deep_merge(current_user, settings)
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_CONFIG_PATH.write_text(
        yaml.safe_dump(merged_user, sort_keys=False), encoding="utf-8"
    )

    load_config.cache_clear()
    return load_config()


def save_setting(key: str, value: Any) -> JarvisConfig:
    path = _parse_setting_path(key)
    user_cfg = _load_yaml(USER_CONFIG_PATH)
    _set_nested(user_cfg, path, value)
    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    USER_CONFIG_PATH.write_text(
        yaml.safe_dump(user_cfg, sort_keys=False), encoding="utf-8"
    )

    load_config.cache_clear()
    return load_config()


def read_setting(key: str) -> Any:
    path = _parse_setting_path(key)
    return _get_nested(get_config_dict(), path)


def export_config() -> str:
    return json.dumps(get_config_dict(), indent=2)


def import_config(json_string: str) -> JarvisConfig:
    payload = json.loads(json_string)
    if not isinstance(payload, dict):
        raise ValueError("Imported config must be an object")

    # Validate by merging into current config model.
    validated = JarvisConfig.model_validate(_deep_merge(get_config_dict(), payload))
    save_all(payload)
    return validated


def reset_user_config() -> JarvisConfig:
    if USER_CONFIG_PATH.exists():
        USER_CONFIG_PATH.unlink()
    load_config.cache_clear()
    return load_config()
