from __future__ import annotations

import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

import numpy as np
from core.error_handler import APIError
from core.event_bus import EventBus
from core.logger import get_logger

from services.voice.tts_edge import EdgeTTS
from services.voice.tts_elevenlabs import ElevenLabsTTS
from services.voice.tts_kitten import KittenTTS
from services.voice.tts_kokoro import KokoroTTS
from services.voice.tts_local import LocalTTS
from services.voice.tts_piper import PiperTTS

if TYPE_CHECKING:
    from core.config import JarvisConfig
    from numpy.typing import NDArray

logger = get_logger(__name__)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\n])\s+")


class TTSManager:
    def __init__(self, config: JarvisConfig, event_bus: EventBus) -> None:
        self.config = config
        self.event_bus = event_bus
        preferred_primary = (config.tts.primary or "").strip().lower()
        if preferred_primary == "elevenlabs" and not config.elevenlabs_api_key:
            logger.info("ELEVENLABS_API_KEY missing, using local TTS as primary")
            preferred_primary = "local"

        self.primary_name = preferred_primary or "local"
        self.fallback_name = config.tts.fallback
        self._cancelled = False

        self.eleven = ElevenLabsTTS(config)
        self.edge = EdgeTTS(config)
        self.kokoro = KokoroTTS(config)
        self.local = LocalTTS(config)
        self.kitten = KittenTTS(config)
        self.piper = PiperTTS(config)

        if self.primary_name == "kitten" and not self.kitten.available:
            logger.warning(
                "KittenTTS requested but unavailable, falling back to local TTS"
            )
            self.primary_name = "local"
        if self.primary_name == "piper" and not self.piper.available:
            logger.warning("Piper requested but unavailable, falling back to local TTS")
            self.primary_name = "local"

    def cancel(self) -> None:
        self._cancelled = True
        self.eleven.cancel()
        self.edge.cancel()
        self.kokoro.cancel()
        self.kitten.cancel()
        self.piper.cancel()

    async def synthesize(self, text: str) -> NDArray[np.float32]:
        self._cancelled = False
        await self.event_bus.publish("tts_started", {"text": text})

        engines_to_try = [self.primary_name]
        if self.fallback_name and self.fallback_name not in engines_to_try:
            engines_to_try.append(self.fallback_name)

        # Add all other supported engines as ultimate fallbacks
        for ultimate in ["piper", "edge", "local"]:
            if ultimate not in engines_to_try:
                engines_to_try.append(ultimate)

        audio = None
        last_error = None

        for engine_name in engines_to_try:
            backend = self._backend(engine_name)
            try:
                audio = await self._synthesize_with_backend(backend, text)
                if audio is not None:
                    break
            except Exception as exc:
                last_error = exc
                await self.event_bus.publish(
                    "tts_error", {"provider": engine_name, "error": str(exc)}
                )
                logger.warning(f"TTS engine '{engine_name}' failed, trying next: {exc}")
                continue

        if audio is None:
            if last_error:
                raise last_error
            raise APIError("All TTS engines failed to synthesize audio")

        await self.event_bus.publish(
            "tts_completed",
            {"duration_ms": int(len(audio) / self.config.tts.sample_rate * 1000)},
        )
        return audio

    async def stream_synthesize(
        self, text_chunks: AsyncIterator[str]
    ) -> AsyncIterator[bytes]:
        self._cancelled = False
        buffer = ""
        started_at = datetime.now(UTC).isoformat()
        await self.event_bus.publish(
            "tts_started", {"text": "", "started_at": started_at}
        )

        async for chunk in text_chunks:
            if self._cancelled:
                break
            if not chunk:
                continue
            buffer += chunk
            sentences, buffer = self._pop_sentences(buffer)
            for sentence in sentences:
                async for audio_chunk in self._stream_sentence(sentence):
                    if self._cancelled:
                        break
                    await self.event_bus.publish(
                        "tts_chunk_ready", {"size": len(audio_chunk)}
                    )
                    yield audio_chunk

        if not self._cancelled and buffer.strip():
            async for audio_chunk in self._stream_sentence(buffer.strip()):
                await self.event_bus.publish(
                    "tts_chunk_ready", {"size": len(audio_chunk)}
                )
                yield audio_chunk

        await self.event_bus.publish("tts_completed", {"duration_ms": 0})

    async def _stream_sentence(self, sentence: str) -> AsyncIterator[bytes]:
        engines_to_try = [self.primary_name]
        if self.fallback_name and self.fallback_name not in engines_to_try:
            engines_to_try.append(self.fallback_name)
        for ultimate in ["piper", "edge", "local"]:
            if ultimate not in engines_to_try:
                engines_to_try.append(ultimate)

        for engine_name in engines_to_try:
            backend = self._backend(engine_name)
            yielded = False
            try:
                async for chunk in self._stream_with_backend(backend, sentence):
                    if self._cancelled:
                        return
                    yielded = True
                    yield chunk
                if yielded:
                    return
            except Exception as exc:
                logger.warning(f"TTS '{engine_name}' failed: {exc}")
                continue

        # ALL engines failed — yield silence so pipeline doesn't hang
        logger.error("All TTS engines failed — yielding silence")
        duration = max(0.2, min(3.0, len(sentence) / 20.0))
        silence = np.zeros(int(self.config.tts.sample_rate * duration), dtype=np.int16)
        yield silence.tobytes()

    async def _synthesize_with_backend(
        self, backend: str, text: str
    ) -> NDArray[np.float32]:
        if backend == "elevenlabs":
            mp3_bytes = await self.eleven.synthesize(text)
            try:
                return self._decode_audio_bytes(mp3_bytes)
            except Exception:
                return await self.edge.synthesize(text)

        if backend == "local":
            return await self.local.synthesize(text)

        if backend == "kokoro":
            output = await self.kokoro.synthesize(text)
            if isinstance(output, np.ndarray):
                return output.astype(np.float32)
            if isinstance(output, bytes):
                return self._decode_audio_bytes(output)
            raise APIError("Kokoro returned unsupported audio format")

        if backend == "kitten":
            return await self.kitten.synthesize(text)

        if backend == "piper":
            return await self.piper.synthesize(text)

        if backend == "edge":
            return await self.edge.synthesize(text)

        raise APIError(f"Unsupported TTS backend: {backend}")

    async def _stream_with_backend(
        self, backend: str, text: str
    ) -> AsyncIterator[bytes]:
        if backend == "elevenlabs":
            # ElevenLabs stream endpoint yields encoded bytes (e.g., MP3),
            # while AudioPlayer stream expects int16 PCM chunks.
            # Synthesize first, decode to PCM, then yield fixed-size PCM chunks.
            encoded_audio = await self.eleven.synthesize(text)
            audio = self._decode_audio_bytes(encoded_audio)
            pcm = (audio * 32767.0).astype(np.int16).tobytes()
            chunk_size = 4096
            for i in range(0, len(pcm), chunk_size):
                if self._cancelled:
                    break
                yield pcm[i : i + chunk_size]
            return

        if backend == "local":
            async for chunk in self.local.stream_synthesize_sentence(text):
                if self._cancelled:
                    break
                yield chunk
            return

        if backend == "kokoro":
            async for chunk in self.kokoro.stream_synthesize_sentence(text):
                if self._cancelled:
                    break
                yield chunk
            return

        if backend == "kitten":
            async for chunk in self.kitten.stream_synthesize_sentence(text):
                if self._cancelled:
                    break
                yield chunk
            return

        if backend == "piper":
            async for chunk in self.piper.stream_synthesize_sentence(text):
                if self._cancelled:
                    break
                yield chunk
            return

        if backend == "edge":
            async for chunk in self.edge.stream_synthesize_sentence(text):
                if self._cancelled:
                    break
                yield chunk
            return

        raise APIError(f"Unsupported TTS backend: {backend}")

    def _backend(self, name: str) -> str:
        lowered = (name or "").strip().lower()
        return (
            lowered
            if lowered in {"elevenlabs", "local", "kokoro", "kitten", "edge", "piper"}
            else "local"
        )

    def _pop_sentences(self, text: str) -> tuple[list[str], str]:
        parts = _SENTENCE_SPLIT_RE.split(text)
        if len(parts) <= 1:
            return [], text
        complete = [p.strip() for p in parts[:-1] if p.strip()]
        remaining = parts[-1]
        return complete, remaining

    def _resample(
        self, audio: NDArray[np.float32], src_rate: int, dst_rate: int
    ) -> NDArray[np.float32]:
        if src_rate == dst_rate or audio.size == 0:
            return audio
        duration = len(audio) / float(src_rate)
        src_time = np.linspace(0, duration, num=len(audio), endpoint=False)
        dst_len = int(duration * dst_rate)
        dst_time = np.linspace(0, duration, num=max(1, dst_len), endpoint=False)
        return np.interp(dst_time, src_time, audio).astype(np.float32)

    def _decode_audio_bytes(self, encoded_audio: bytes) -> NDArray[np.float32]:
        import io

        # Try soundfile first (works for WAV/FLAC/OGG)
        try:
            import soundfile as sf

            audio, sr = sf.read(io.BytesIO(encoded_audio), dtype="float32")
            if isinstance(audio, np.ndarray) and audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != self.config.tts.sample_rate:
                audio = self._resample(audio, sr, self.config.tts.sample_rate)
            return cast("NDArray[np.float32]", audio.astype(np.float32))
        except Exception:
            pass
        # Fallback: pydub for MP3 (ElevenLabs output)
        try:
            from pydub import AudioSegment

            segment = AudioSegment.from_file(io.BytesIO(encoded_audio))
            segment = segment.set_frame_rate(self.config.tts.sample_rate).set_channels(
                1
            )
            samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
            # Normalize based on sample width
            max_val = float(2 ** (8 * segment.sample_width - 1))
            return (samples / max_val).astype(np.float32)
        except Exception as exc:
            logger.error(f"Audio decode failed with all backends: {exc}")
            return np.zeros(
                self.config.tts.sample_rate, dtype=np.float32
            )  # 1 second silence
