from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import numpy as np

from core.logger import get_logger

logger = get_logger(__name__)

try:
    from kittentts import KittenTTS as _KittenEngine
except ImportError:
    _KittenEngine = None


class KittenTTS:
    """Optional KittenTTS backend with streaming PCM output."""

    def __init__(self, config) -> None:
        self.config = config
        self._cancelled = False
        self.available = _KittenEngine is not None
        self.voice = (getattr(config.tts, "kitten_voice", "alloy") or "alloy").strip()
        self.model_name = (getattr(config.tts, "kitten_model", "kitten-1") or "kitten-1").strip()
        self.sample_rate = int(config.tts.sample_rate)

        self._engine = None
        if self.available:
            try:
                self._engine = _KittenEngine(model=self.model_name)
            except Exception as exc:
                logger.warning(f"KittenTTS initialization failed: {exc}")
                self.available = False

    def cancel(self) -> None:
        self._cancelled = True

    async def synthesize(self, text: str) -> np.ndarray:
        if not self.available or self._engine is None:
            raise RuntimeError("KittenTTS backend unavailable")

        self._cancelled = False
        chunks: list[np.ndarray] = []

        for chunk in self._engine.synthesize_streaming(text, voice=self.voice):
            if self._cancelled:
                break
            if not chunk:
                continue
            pcm = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767.0
            chunks.append(pcm)

        if not chunks:
            return np.zeros(1, dtype=np.float32)

        return np.concatenate(chunks).astype(np.float32)

    async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
        if not self.available or self._engine is None:
            raise RuntimeError("KittenTTS backend unavailable")

        self._cancelled = False
        for chunk in self._engine.synthesize_streaming(text, voice=self.voice):
            if self._cancelled:
                break
            if not chunk:
                continue
            yield chunk
            await asyncio.sleep(0)
