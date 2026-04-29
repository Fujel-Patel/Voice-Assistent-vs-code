from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from numpy.typing import NDArray

import moonshine
import numpy as np
from config.config_loader import JarvisConfig
from core.logger import get_logger

logger = get_logger(__name__)


class SpeechToTextMoonshine:
    """Moonshine-tiny transcription service."""

    def __init__(self, config: JarvisConfig) -> None:
        self._config = config
        self._model_name = "moonshine/tiny"
        self._sample_rate = 16000

    async def transcribe(
        self,
        audio_data: NDArray[Any] | bytes,
        on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
        finalize: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()

        if isinstance(audio_data, bytes):
            audio = np.frombuffer(audio_data, dtype=np.int16)
        else:
            audio = audio_data

        peak_volume = float(np.max(np.abs(audio))) if audio.size > 0 else 0.0
        if audio.size == 0 or peak_volume < 100.0:
            return {
                "text": "",
                "confidence": 0.05,
                "language": "en",
                "duration_seconds": round(time.perf_counter() - started_at, 3),
            }

        audio_int16 = audio.astype(np.int16)
        if audio_int16.ndim == 1:
            audio_int16 = audio_int16.reshape(1, -1)

        try:
            loop = asyncio.get_running_loop()
            tokens = await loop.run_in_executor(
                None, moonshine.transcribe, audio_int16, self._model_name
            )
            text = (
                " ".join(tokens).strip()
                if isinstance(tokens, (list, tuple))
                else str(tokens or "").strip()
            )
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
            await on_chunk(
                {
                    "text": text,
                    "chunk": text,
                    "is_final": True,
                }
            )

        return {
            "text": text,
            "confidence": 0.9,
            "language": "en",
            "duration_seconds": round(duration, 3),
        }
