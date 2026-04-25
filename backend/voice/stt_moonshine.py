from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable
import numpy as np

from config.config_loader import JarvisConfig
from core.logger import get_logger

moonshine_import_error: Exception | None = None

try:
    import moonshine
except Exception as exc:
    moonshine = None
    moonshine_import_error = exc

logger = get_logger(__name__)

class SpeechToTextMoonshine:
    """Moonshine-tiny transcription service."""

    def __init__(self, config: JarvisConfig):
        self._config = config
        if moonshine is None:
            detail = f" Original import error: {moonshine_import_error}" if moonshine_import_error else ""
            raise RuntimeError(
                "Moonshine STT dependencies are unavailable. "
                "Install backend requirements (includes useful-moonshine)."
                f"{detail}"
            )

        self._model = None

    async def _ensure_model(self) -> None:
        if self._model is not None:
            return
        logger.info("Downloading/Loading Moonshine tiny model...")
        try:
            self._model = await asyncio.to_thread(moonshine.load_model, "moonshine/tiny")
            logger.info("Moonshine tiny model loaded successfully.")
        except Exception as exc:
            logger.error(f"Failed to load Moonshine STT model: {exc}")
            raise RuntimeError(f"Moonshine model load failed: {exc}")

    async def transcribe(
        self,
        audio_data: np.ndarray | bytes,
        on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        
        try:
            await self._ensure_model()
        except RuntimeError as e:
            return {
                "text": f"[STT Error: {e}]",
                "confidence": 0.0,
                "language": "en",
                "duration_seconds": 0.0,
            }

        if isinstance(audio_data, bytes):
            audio = np.frombuffer(audio_data, dtype=np.int16)
        else:
            audio = audio_data

        peak_volume = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
        # If absolute peak is extremely low, don't pass to model to save CPU
        if audio.size == 0 or peak_volume < 100.0:
            return {
                "text": "",
                "confidence": 0.05,
                "language": "en",
                "duration_seconds": round(time.perf_counter() - started_at, 3),
            }

        # Moonshine usually requires 16000 Hz, float32 audio normalized to [-1.0, 1.0]
        normalized = audio.astype(np.float32) / 32768.0

        try:
            loop = asyncio.get_running_loop()
            tokens = await loop.run_in_executor(None, self._model.transcribe, normalized)
            text = " ".join(tokens).strip() if isinstance(tokens, list) else str(tokens or "").strip()
        except Exception as exc:
            logger.error(f"Moonshine transcribe error: {exc}")
            text = ""

        duration = time.perf_counter() - started_at

        if not text or len(text.strip()) < 2:
            return {
                "text": "",
                "confidence": 0.05,
                "language": "en",
                "duration_seconds": round(duration, 3),
            }
        
        if on_chunk is not None and text:
            await on_chunk({
                "text": text,
                "chunk": text,
                "is_final": True,
            })

        return {
            "text": text,
            "confidence": 0.9,
            "language": "en",
            "duration_seconds": round(duration, 3),
        }
