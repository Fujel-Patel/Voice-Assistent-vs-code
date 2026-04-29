from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from voice.stt import SpeechToText as SpeechToTextWhisper
from config.config_loader import JarvisConfig
from core.event_bus import EventBus
from core.logger import get_logger

from voice.stt import SpeechToText as SpeechToTextWhisper
from voice.stt_moonshine import SpeechToTextMoonshine
from voice.stt_vosk import SpeechToTextVosk

logger = get_logger(__name__)


class STTStream:
    """A handle to an active STT stream for real-time processing."""

    def __init__(
        self,
        engine: Any,
        on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.engine = engine
        self.on_chunk = on_chunk
        self._is_vosk = isinstance(engine, SpeechToTextVosk)
        self._audio_buffer: list[NDArray[Any]] = []
        self._started_at = time.perf_counter()

    async def process_audio(self, chunk: NDArray[Any]) -> None:
        if self._is_vosk:
            # Vosk supports incremental processing via the same transcribe call pattern
            # but we need to feed it 30ms-sized chunks usually.
            await self.engine.transcribe(chunk, on_chunk=self.on_chunk, finalize=False)
        else:
            # Moonshine/Whisper don't support streaming well, so we just buffer.
            self._audio_buffer.append(chunk)

    async def finalize(self) -> dict[str, Any]:
        if self._is_vosk:
            # Vosk already processed chunks via AcceptWaveform during process_audio.
            # Just get the final result without passing empty audio.
            result = await self.engine.transcribe(
                np.array([], dtype=np.int16), on_chunk=self.on_chunk, finalize=True
            )
            return dict(result)

        # For non-streaming engines, process the whole buffer at the end.
        if not self._audio_buffer:
            return {"text": "", "confidence": 0.0, "language": "en"}

        full_audio = np.concatenate(self._audio_buffer)
        result = await self.engine.transcribe(
            full_audio, on_chunk=self.on_chunk, finalize=True
        )
        return dict(result)


class STTManager:
    """Manages multiple STT backends with fallback logic and streaming support."""

    def __init__(self, config: JarvisConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus

        # Primary engine from config
        self.primary_engine_name = (config.stt.engine or "moonshine").lower()

        self._moonshine: SpeechToTextMoonshine | None = None
        self._whisper: SpeechToTextWhisper | None = None
        self._vosk: SpeechToTextVosk | None = None

    def _get_engine(self, name: str) -> Any:
        logger.debug(f"Getting STT engine: {name}")
        if name == "moonshine":
            if self._moonshine is None:
                logger.info("Initializing Moonshine STT")
                self._moonshine = SpeechToTextMoonshine(self.config)
            return self._moonshine
        elif name == "whisper":
            if self._whisper is None:
                logger.info("Initializing Whisper STT")
                self._whisper = SpeechToTextWhisper(self.config)
            return self._whisper
        elif name == "vosk":
            if self._vosk is None:
                try:
                    logger.info("Initializing Vosk STT")
                    self._vosk = SpeechToTextVosk(self.config)
                except Exception as exc:
                    logger.warning(f"Failed to initialize Vosk: {exc}")
                    return None
            return self._vosk
        return None

    def open_stream(
        self, on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    ) -> STTStream:
        """Opens a new transcription stream using the best available streaming-capable engine."""
        # Prefer Vosk for real-time streaming if available
        engine = self._get_engine("vosk") or self._get_engine(self.primary_engine_name)
        logger.info(f"Opening STT stream with engine: {type(engine).__name__}")
        return STTStream(engine, on_chunk=on_chunk)

    async def transcribe(
        self,
        audio_data: NDArray[Any],
        on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> dict[str, Any]:
        engines_to_try = [self.primary_engine_name]

        # Add fallbacks
        for fallback in ["whisper", "vosk"]:
            if fallback not in engines_to_try:
                engines_to_try.append(fallback)

        last_error = None
        for engine_name in engines_to_try:
            engine = self._get_engine(engine_name)
            if not engine:
                continue

            try:
                logger.info(f"Attempting transcription with engine: {engine_name}")
                result = await engine.transcribe(audio_data, on_chunk=on_chunk)

                # If we got text, or if it's just silence (and engine didn't error), we accept it
                if result.get("text") or result.get("duration_seconds", 0) > 0:
                    return dict(result)
            except Exception as exc:
                logger.error(f"STT engine '{engine_name}' failed: {exc}")
                last_error = exc
                continue

        if last_error:
            raise last_error

        return {
            "text": "",
            "confidence": 0.0,
            "language": "unknown",
            "error": "All STT engines failed or were unavailable",
        }
