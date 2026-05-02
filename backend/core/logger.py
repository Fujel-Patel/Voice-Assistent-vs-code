from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from loguru import logger as _logger

from core.config import load_config


class _WebSocketNoiseFilter(logging.Filter):
    """Drop common handshake noise that isn't actionable for developers."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if "opening handshake failed" in message:
            return False
        if "no close frame received or sent" in message:
            return False
        return True


def _configure_logger() -> None:
    cfg = load_config()
    log_path = Path(__file__).resolve().parent.parent / cfg.logging.file
    log_path.parent.mkdir(parents=True, exist_ok=True)

    _logger.remove()

    # Keep console logs human readable for local development.
    _logger.add(
        sys.stdout,
        level=cfg.logging.level.upper(),
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level:<8}</level> | "
            "<cyan>{extra[module]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        colorize=True,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )

    # Keep file logs structured for postmortem analysis and tooling.
    _logger.add(
        str(log_path),
        level=cfg.logging.level.upper(),
        serialize=True,
        backtrace=True,
        diagnose=False,
        rotation="10 MB",
        retention="14 days",
        enqueue=True,
    )

    # Reduce third-party websocket traceback noise in stdout while keeping real errors.
    ws_server_logger = logging.getLogger("websockets.server")
    ws_server_logger.setLevel(logging.ERROR)
    ws_server_logger.addFilter(_WebSocketNoiseFilter())


_configured = False


def get_logger(name: str) -> Any:
    global _configured
    if not _configured:
        _configure_logger()
        _configured = True
    return _logger.bind(module=name)
