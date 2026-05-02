"""
Edge-TTS backend — High-quality, free Microsoft neural TTS.

Uses the `edge-tts` package to stream audio from Microsoft's neural voices.
Produces MP3 chunks that are decoded to PCM for the audio pipeline.
No API key required. Requires internet connectivity.
"""

from __future__ import annotations

import asyncio
import io
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, cast

import numpy as np
from core.logger import get_logger

if TYPE_CHECKING:
    from core.config import JarvisConfig
    from numpy.typing import NDArray

logger = get_logger(__name__)

# Microsoft neural voices — high-quality, natural-sounding
VOICE_MAP = {
    "male_us": "en-US-GuyNeural",
    "male_uk": "en-GB-RyanNeural",
    "female_us": "en-US-JennyNeural",
    "female_uk": "en-GB-SoniaNeural",
    "jarvis": "en-US-GuyNeural",  # Deep male voice, good for assistant
    "default": "en-US-GuyNeural",
}


class EdgeTTS:
    """Async TTS using Microsoft Edge neural voices via edge-tts package."""

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self._cancelled = False
        self.sample_rate = int(config.tts.sample_rate)
        # Pick voice from config or default to a deep male voice
        voice_key = (
            (config.tts.edge_voice if hasattr(config.tts, "edge_voice") else "")
            .strip()
            .lower()
        )
        self.voice = VOICE_MAP.get(voice_key, voice_key or VOICE_MAP["jarvis"])

    def cancel(self) -> None:
        self._cancelled = True

    async def synthesize(self, text: str) -> NDArray[np.float32]:
        """Synthesize full text to numpy float32 PCM array."""
        self._cancelled = False
        if not text.strip():
            return np.zeros(1, dtype=np.float32)

        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            audio_chunks: list[bytes] = []

            async for chunk in communicate.stream():
                if self._cancelled:
                    break
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            if not audio_chunks:
                logger.warning("Edge-TTS returned no audio data")
                return np.zeros(1, dtype=np.float32)

            mp3_bytes = b"".join(audio_chunks)
            return self._decode_mp3(mp3_bytes)

        except Exception as exc:
            logger.warning(f"Edge-TTS synthesis failed: {exc}")
            raise

    async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
        """Stream PCM int16 chunks for a sentence."""
        self._cancelled = False
        if not text.strip():
            return

        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            mp3_buffer = bytearray()

            async for chunk in communicate.stream():
                if self._cancelled:
                    break
                if chunk["type"] == "audio" and chunk["data"]:
                    mp3_buffer.extend(chunk["data"])

            if self._cancelled or not mp3_buffer:
                return

            # Decode full MP3 to PCM and yield as one large chunk per sentence
            audio = self._decode_mp3(bytes(mp3_buffer))
            pcm = (audio * 32767.0).astype(np.int16).tobytes()
            yield pcm
            await asyncio.sleep(0)

        except Exception as exc:
            logger.warning(f"Edge-TTS stream failed: {exc}")
            raise

    def _decode_mp3(self, mp3_bytes: bytes) -> NDArray[np.float32]:
        """Decode MP3 bytes to float32 numpy array."""
        try:
            import soundfile as sf

            audio, sr = sf.read(io.BytesIO(mp3_bytes), dtype="float32")
            if isinstance(audio, np.ndarray) and audio.ndim > 1:
                audio = audio.mean(axis=1)
            if sr != self.sample_rate:
                audio = self._resample(audio, sr, self.sample_rate)
            return cast("NDArray[np.float32]", audio.astype(np.float32))
        except Exception:
            # soundfile can't decode MP3 directly on some systems, try pydub fallback
            try:
                from pydub import AudioSegment

                segment = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
                segment = segment.set_frame_rate(self.sample_rate).set_channels(1)
                samples = np.array(segment.get_array_of_samples(), dtype=np.float32)
                return samples / 32768.0
            except Exception as exc2:
                logger.warning(f"MP3 decode failed with both backends: {exc2}")
                return np.zeros(1, dtype=np.float32)

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
