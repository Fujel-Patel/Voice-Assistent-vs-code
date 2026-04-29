from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from typing import Any

from config.config_loader import (
    ENV_FILE_PATH,
    export_config,
    get_config_dict,
    import_config,
    reset_user_config,
    save_all,
    save_setting,
)
from core.logger import get_logger

from .key_validator import validate_key

logger = get_logger(__name__)

_API_ENV_MAP = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama": "OLLAMA_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
    "brave": "BRAVE_SEARCH_API_KEY",
}


@dataclass
class SettingsHandler:
    """Handles WebSocket CRUD operations for runtime settings and API keys."""

    async def handle(
        self, message_type: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        payload = payload or {}

        if message_type == "get_settings":
            return {
                "type": "settings_response",
                "payload": {
                    "ok": True,
                    "settings": self._frontend_settings(),
                    "system_info": self._system_info(),
                },
            }

        if message_type == "update_setting":
            key = str(payload.get("key") or "").strip()
            if not key:
                return self._error("Missing setting key")
            value = payload.get("value")
            valid = self._validate_setting(key, value)
            if valid is not None:
                return self._error(valid)

            if key.startswith("api."):
                self._store_api_key(key, value)
            else:
                save_setting(key, value)
            return {
                "type": "settings_updated",
                "payload": {
                    "ok": True,
                    "settings": self._frontend_settings(),
                    "updated": {key: value},
                    "restart_required": self._requires_restart(key),
                },
            }

        if message_type == "update_settings_bulk":
            settings = payload.get("settings")
            if not isinstance(settings, dict):
                return self._error("Bulk update requires a settings object")

            for key, value in settings.items():
                problem = self._validate_setting(str(key), value)
                if problem is not None:
                    return self._error(f"{key}: {problem}")

            regular_settings = {
                k: v for k, v in settings.items() if not str(k).startswith("api.")
            }
            key_settings = {
                k: v for k, v in settings.items() if str(k).startswith("api.")
            }

            if regular_settings:
                nested = self._unflatten(regular_settings)
                save_all(nested)

            for key, value in key_settings.items():
                self._store_api_key(str(key), value)

            return {
                "type": "settings_updated",
                "payload": {
                    "ok": True,
                    "settings": self._frontend_settings(),
                    "updated": settings,
                    "restart_required": any(
                        self._requires_restart(str(k)) for k in settings
                    ),
                },
            }

        if message_type == "validate_api_key":
            provider = str(payload.get("provider") or "").strip().lower()
            key = str(payload.get("key") or "")
            result = await validate_key(provider, key)
            return {
                "type": "api_key_validation",
                "payload": {
                    "provider": provider,
                    **result,
                },
            }

        if message_type == "reset_settings":
            reset_user_config()
            return {
                "type": "settings_updated",
                "payload": {
                    "ok": True,
                    "settings": self._frontend_settings(),
                    "reset": True,
                },
            }

        if message_type == "export_settings":
            return {
                "type": "settings_export",
                "payload": {
                    "ok": True,
                    "config_json": export_config(),
                },
            }

        if message_type == "import_settings":
            config_json = payload.get("config_json")
            if not isinstance(config_json, str):
                return self._error("import_settings requires config_json string")
            try:
                import_config(config_json)
            except Exception as exc:
                return self._error(f"Import failed: {exc}")

            return {
                "type": "settings_updated",
                "payload": {
                    "ok": True,
                    "settings": self._frontend_settings(),
                    "imported": True,
                },
            }

        return self._error(f"Unsupported settings message: {message_type}")

    def _frontend_settings(self) -> dict[str, Any]:
        cfg = get_config_dict()
        flat = self._flatten(cfg)

        return {
            "wake_word.engine": flat.get("wake_word.engine", "openwakeword"),
            "wake_word.sensitivity": flat.get("wake_word.sensitivity", 0.5),
            "wake_word.keyword": flat.get("wake_word.keyword", "jarvis"),
            "wake_word.openwakeword_model_path": flat.get(
                "wake_word.openwakeword_model_path", ""
            ),
            "wake_word.openwakeword_vad_threshold": flat.get(
                "wake_word.openwakeword_vad_threshold", 0.0
            ),
            "wake_word.openwakeword_enable_speex": flat.get(
                "wake_word.openwakeword_enable_speex", False
            ),
            "audio.silence_stop_seconds": flat.get("audio.silence_stop_seconds", 2.0),
            "stt.engine": flat.get("stt.engine", "moonshine"),
            "stt.language": flat.get("stt.language", "en-us"),
            "stt.model": flat.get("stt.model", "tiny"),
            "tts.primary": flat.get("tts.primary", "piper"),
            "tts.voice_id": flat.get("tts.voice_id", "jarvis_custom"),
            "tts.speaking_rate": flat.get("tts.speaking_rate", 1.0),
            "tts.volume": flat.get("tts.volume", 0.8),
            "brain.providers.default_provider": flat.get(
                "brain.providers.default_provider", "gemini"
            ),
            "brain.models.claude": flat.get(
                "brain.models.claude", "claude-sonnet-4-20250514"
            ),
            "brain.models.gemini": flat.get("brain.models.gemini", "gemini-2.5-flash"),
            "brain.models.groq": flat.get(
                "brain.models.groq", "llama-3.3-70b-versatile"
            ),
            "brain.models.openrouter": flat.get(
                "brain.models.openrouter", "openai/gpt-4o-mini"
            ),
            "brain.models.ollama": flat.get("brain.models.ollama", "llama3.2"),
            "brain.short_term_turns": flat.get("brain.short_term_turns", 20),
            "brain.token_budget": flat.get("brain.token_budget", 4000),
            "brain.stream_chunks": flat.get("brain.stream_chunks", False),
            "web.search_engine": flat.get("web.search_engine", "brave"),
            "web.max_results": flat.get("web.max_results", 5),
            "ui.theme": flat.get("ui.theme", "dark-sci-fi"),
            "ui.accent": flat.get("ui.accent", "cyan"),
            "ui.reduced_animations": flat.get("ui.reduced_animations", False),
            "window.always_on_top": flat.get("window.always_on_top", False),
            "window.start_minimized": flat.get("window.start_minimized", False),
            "window.opacity": flat.get("window.opacity", 100),
            "window.font_size": flat.get("window.font_size", "normal"),
            "response.style": flat.get("response.style", "professional"),
            "response.length": flat.get("response.length", "normal"),
            "response.custom_prompt": flat.get("response.custom_prompt", ""),
            "auth.enabled": flat.get("auth.enabled", False),
            "auth.mode": flat.get("auth.mode", "passive"),
            "auth.threshold": flat.get("auth.threshold", "medium"),
            "auth.liveness": flat.get("auth.liveness", "sensitive_only"),
            "auth.pin_fallback": flat.get("auth.pin_fallback", True),
            "auth.session_timeout_minutes": flat.get(
                "auth.session_timeout_minutes", 30
            ),
            "api.anthropic": os.getenv("ANTHROPIC_API_KEY", ""),
            "api.gemini": os.getenv("GEMINI_API_KEY", ""),
            "api.groq": os.getenv("GROQ_API_KEY", ""),
            "api.openrouter": os.getenv("OPENROUTER_API_KEY", ""),
            "api.ollama": os.getenv("OLLAMA_API_KEY", ""),
            "api.elevenlabs": os.getenv("ELEVENLABS_API_KEY", ""),
            "api.brave": os.getenv("BRAVE_SEARCH_API_KEY", ""),
        }

    def _validate_setting(self, key: str, value: Any) -> str | None:
        if key == "wake_word.engine" and value not in {"openwakeword"}:
            return "must be openwakeword"
        if key == "wake_word.sensitivity":
            if not isinstance(value, (int, float)) or not (0.1 <= float(value) <= 1.0):
                return "must be between 0.1 and 1.0"
        if key == "wake_word.openwakeword_vad_threshold":
            if not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
                return "must be between 0.0 and 1.0"
        if key == "tts.volume":
            if not isinstance(value, (int, float)) or not (0.0 <= float(value) <= 1.0):
                return "must be between 0.0 and 1.0"
        if key == "brain.token_budget":
            if not isinstance(value, int) or not (1000 <= value <= 16000):
                return "must be between 1000 and 16000"
        if key == "brain.short_term_turns":
            if not isinstance(value, int) or not (5 <= value <= 200):
                return "must be between 5 and 200"
        if key == "stt.engine" and value not in {"moonshine"}:
            return "must be moonshine"
        if key == "tts.primary" and value not in {
            "piper",
            "local",
            "kokoro",
            "edge",
            "elevenlabs",
        }:
            return "must be one of piper, local, kokoro, edge, elevenlabs"
        if key == "brain.providers.default_provider" and value not in {
            "claude",
            "gemini",
            "groq",
            "openrouter",
            "ollama",
        }:
            return "must be one of claude, gemini, groq, openrouter, ollama"
        if key == "window.opacity":
            if not isinstance(value, (int, float)) or not (50 <= float(value) <= 100):
                return "must be between 50 and 100"
        if key == "auth.threshold" and value not in {"low", "medium", "high"}:
            return "must be one of low, medium, high"
        if key == "auth.mode" and value not in {"passive", "challenge", "off"}:
            return "must be one of passive, challenge, off"
        if key == "auth.liveness" and value not in {
            "always",
            "sensitive_only",
            "never",
        }:
            return "must be one of always, sensitive_only, never"
        if key == "auth.session_timeout_minutes":
            if not isinstance(value, int) or not (5 <= value <= 180):
                return "must be between 5 and 180"
        return None

    def _requires_restart(self, key: str) -> bool:
        return key in {"server.port", "stt.engine", "stt.model", "audio.sample_rate"}

    def _flatten(self, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in data.items():
            full = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten(value, full))
            else:
                result[full] = value
        return result

    def _unflatten(self, data: dict[str, Any]) -> dict[str, Any]:
        nested: dict[str, Any] = {}
        for key, value in data.items():
            parts = [part for part in key.split(".") if part]
            current = nested
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value
        return nested

    def _system_info(self) -> dict[str, Any]:
        return {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "node": os.getenv("NODE_VERSION"),
            "app_version": "1.0.0",
        }

    def _store_api_key(self, key: str, value: Any) -> None:
        provider = key.split(".", 1)[1] if "." in key else key
        env_name = _API_ENV_MAP.get(provider)
        if not env_name:
            raise ValueError(f"Unsupported API key provider: {provider}")

        text_value = "" if value is None else str(value)
        os.environ[env_name] = text_value
        self._upsert_env_file(env_name, text_value)

    def _upsert_env_file(self, key: str, value: str) -> None:
        ENV_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        if ENV_FILE_PATH.exists():
            lines = ENV_FILE_PATH.read_text(encoding="utf-8").splitlines()

        replaced = False
        for index, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[index] = f"{key}={value}"
                replaced = True
                break

        if not replaced:
            lines.append(f"{key}={value}")

        ENV_FILE_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    def _error(self, message: str) -> dict[str, Any]:
        return {
            "type": "settings_response",
            "payload": {
                "ok": False,
                "error": message,
            },
        }
