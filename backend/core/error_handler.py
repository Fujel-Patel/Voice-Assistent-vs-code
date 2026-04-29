from __future__ import annotations

import sys
import traceback
from dataclasses import dataclass
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class JarvisError(Exception):
    code = "JARVIS_ERROR"


class MicrophoneError(JarvisError):
    code = "MICROPHONE_ERROR"


class ModelError(JarvisError):
    code = "MODEL_ERROR"


class APIError(JarvisError):
    code = "API_ERROR"


class ConfigError(JarvisError):
    code = "CONFIG_ERROR"


@dataclass
class ErrorPayload:
    code: str
    message: str
    recoverable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "recoverable": self.recoverable,
        }


def to_user_error(exc: Exception) -> ErrorPayload:
    if isinstance(exc, MicrophoneError):
        return ErrorPayload(code=exc.code, message="Microphone is unavailable.")
    if isinstance(exc, ModelError):
        return ErrorPayload(code=exc.code, message="Speech model is unavailable.")
    if isinstance(exc, APIError):
        return ErrorPayload(code=exc.code, message="External service request failed.")
    if isinstance(exc, ConfigError):
        return ErrorPayload(
            code=exc.code, message="Configuration is invalid.", recoverable=False
        )
    return ErrorPayload(code="UNKNOWN_ERROR", message="An unexpected error occurred.")


def setup_global_error_handler() -> None:
    def _handle_uncaught(
        exc_type: type[BaseException],
        exc_value: BaseException,
        exc_tb: Any,
    ) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error(f"Uncaught exception: {exc_value}")
        logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

    sys.excepthook = _handle_uncaught
