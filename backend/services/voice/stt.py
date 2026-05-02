from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import numpy as np
from core.config import JarvisConfig
from core.logger import get_logger

from services.voice.model_manager import ModelManager

if TYPE_CHECKING:
    from numpy.typing import NDArray

logger = get_logger(__name__)


class SpeechToText:
    """faster-whisper transcription service."""

    def __init__(self, config: JarvisConfig, model_manager: ModelManager | None = None):
        self._config = config
        self.model_manager = model_manager or ModelManager(config)

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

        if audio.size == 0:
            return {
                "text": "",
                "confidence": 0.05,
                "language": self._config.stt.language
                if self._config.stt.language != "auto"
                else "unknown",
                "duration_seconds": 0.0,
            }

        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 1.0:
            return {
                "text": "",
                "confidence": 0.05,
                "language": self._config.stt.language
                if self._config.stt.language != "auto"
                else "unknown",
                "duration_seconds": audio.size / float(self._config.audio.sample_rate),
            }

        model = await self.model_manager.ensure_loaded()

        normalized = audio.astype(np.float32) / 32768.0
        lang = (
            None if self._config.stt.language == "auto" else self._config.stt.language
        )

        segments, info = model.transcribe(
            normalized,
            language=lang,
            beam_size=5,
            vad_filter=True,
        )

        collected = []
        probs = []
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                collected.append(text)
                if on_chunk is not None:
                    await on_chunk(
                        {
                            "text": " ".join(collected).strip(),
                            "chunk": text,
                            "is_final": False,
                        }
                    )
            if hasattr(seg, "avg_logprob"):
                probs.append(float(seg.avg_logprob))

        text = " ".join(collected).strip()
        if probs:
            # Map average log-probabilities to [0,1] confidence.
            avg = sum(probs) / len(probs)
            confidence = max(0.0, min(1.0, 1.0 + (avg / 5.0)))
        else:
            confidence = 0.9 if text else 0.05

        duration = time.perf_counter() - started_at
        if on_chunk is not None and text:
            await on_chunk(
                {
                    "text": text,
                    "chunk": "",
                    "is_final": True,
                }
            )
        return {
            "text": text,
            "confidence": round(confidence, 3),
            "language": getattr(info, "language", lang or "unknown"),
            "duration_seconds": round(duration, 3),
        }
