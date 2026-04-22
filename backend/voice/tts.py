from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

import numpy as np

from core.error_handler import APIError
from core.event_bus import EventBus
from core.logger import get_logger
from voice.tts_local import LocalTTS
from voice.tts_elevenlabs import ElevenLabsTTS
from voice.tts_edge import EdgeTTS
from voice.tts_kokoro import KokoroTTS
from voice.tts_kitten import KittenTTS
from voice.tts_piper import PiperTTS

logger = get_logger(__name__)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?\n])\s+")


class TTSManager:
    def __init__(self, config, event_bus: EventBus) -> None:
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
            logger.warning("KittenTTS requested but unavailable, falling back to local TTS")
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

    async def synthesize(self, text: str) -> np.ndarray:
        self._cancelled = False
        await self.event_bus.publish("tts_started", {"text": text})

        backend = self._backend(self.primary_name)
        fallback = self._backend(self.fallback_name)

        try:
            audio = await self._synthesize_with_backend(backend, text)
        except Exception as exc:
            await self.event_bus.publish("tts_error", {"provider": self.primary_name, "error": str(exc)})
            logger.warning(f"Primary TTS failed, falling back: {exc}")
            audio = await self._synthesize_with_backend(fallback, text)

        await self.event_bus.publish("tts_completed", {"duration_ms": int(len(audio) / self.config.tts.sample_rate * 1000)})
        return audio

    async def stream_synthesize(self, text_chunks: AsyncIterator[str]) -> AsyncIterator[bytes]:
        self._cancelled = False
        buffer = ""
        started_at = datetime.now(timezone.utc).isoformat()
        await self.event_bus.publish("tts_started", {"text": "", "started_at": started_at})

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
                    await self.event_bus.publish("tts_chunk_ready", {"size": len(audio_chunk)})
                    yield audio_chunk

        if not self._cancelled and buffer.strip():
            async for audio_chunk in self._stream_sentence(buffer.strip()):
                await self.event_bus.publish("tts_chunk_ready", {"size": len(audio_chunk)})
                yield audio_chunk

        await self.event_bus.publish("tts_completed", {"duration_ms": 0})

    async def _stream_sentence(self, sentence: str) -> AsyncIterator[bytes]:
        backend = self._backend(self.primary_name)
        fallback = self._backend(self.fallback_name)

        try:
            async for chunk in self._stream_with_backend(backend, sentence):
                if self._cancelled:
                    break
                yield chunk
            return
        except Exception as exc:
            await self.event_bus.publish("tts_error", {"provider": self.primary_name, "error": str(exc)})
            logger.warning(f"Primary streaming TTS failed, fallback provider engaged: {exc}")

        async for chunk in self._stream_with_backend(fallback, sentence):
            if self._cancelled:
                break
            yield chunk

    async def _synthesize_with_backend(self, backend: str, text: str) -> np.ndarray:
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

    async def _stream_with_backend(self, backend: str, text: str) -> AsyncIterator[bytes]:
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
        return lowered if lowered in {"elevenlabs", "local", "kokoro", "kitten", "edge", "piper"} else "local"

    def _pop_sentences(self, text: str) -> tuple[list[str], str]:
        parts = _SENTENCE_SPLIT_RE.split(text)
        if len(parts) <= 1:
            return [], text
        complete = [p.strip() for p in parts[:-1] if p.strip()]
        remaining = parts[-1]
        return complete, remaining

    def _resample(self, audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        if src_rate == dst_rate or audio.size == 0:
            return audio
        duration = len(audio) / float(src_rate)
        src_time = np.linspace(0, duration, num=len(audio), endpoint=False)
        dst_len = int(duration * dst_rate)
        dst_time = np.linspace(0, duration, num=max(1, dst_len), endpoint=False)
        return np.interp(dst_time, src_time, audio).astype(np.float32)

    def _decode_audio_bytes(self, encoded_audio: bytes) -> np.ndarray:
        import soundfile as sf
        from io import BytesIO

        audio, sr = sf.read(BytesIO(encoded_audio), dtype="float32")
        if isinstance(audio, np.ndarray) and audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != self.config.tts.sample_rate:
            audio = self._resample(audio, sr, self.config.tts.sample_rate)
        return audio.astype(np.float32)
