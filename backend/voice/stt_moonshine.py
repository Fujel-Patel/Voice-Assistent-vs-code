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
                "Install backend requirements (includes useful-moonshine and tensorflow)."
                f"{detail}"
            )
        
        # Load the moonshine tiny model
        self.model = moonshine.load_model("moonshine/tiny")
        logger.info("Moonshine tiny model loaded.")

    async def transcribe(
        self,
        audio_data: np.ndarray | bytes,
        on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()

        if isinstance(audio_data, bytes):
            audio = np.frombuffer(audio_data, dtype=np.int16)
        else:
            audio = audio_data

        if audio.size == 0 or np.max(np.abs(audio)) < 5.0:
            return {
                "text": "",
                "confidence": 0.05,
                "language": "en",
                "duration_seconds": 0.0,
            }

        # Moonshine usually requires 16000 Hz, float32 audio
        normalized = audio.astype(np.float32) / 32768.0

        # Run model inference in executor so voice loop stays responsive.
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, self.model.transcribe, normalized)
        
        duration = time.perf_counter() - started_at
        
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
