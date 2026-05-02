from __future__ import annotations

from collections.abc import AsyncIterator

import numpy as np

try:
    import soundfile as sf
    from kokoro import KPipeline
except ImportError:
    KPipeline = None
    sf = None
from io import BytesIO
from typing import TYPE_CHECKING

from core.logger import get_logger

if TYPE_CHECKING:
    from core.config import JarvisConfig

logger = get_logger(__name__)


class KokoroTTS:
    """TTS via Kokoro for extremely fast local generation."""

    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        # initialize pipeline
        # Assuming English ('a' = American, 'b' = British)
        if KPipeline:
            self.pipeline = KPipeline(lang_code="a")
        else:
            self.pipeline = None
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def synthesize(self, text: str) -> bytes:
        if self.pipeline is None:
            raise RuntimeError(
                "KokoroTTS is not available (kokoro package not installed)"
            )
        self._cancelled = False
        # Default voice to use
        voice = "af_bella"  # one of the smaller/popular

        # Generator for chunks
        generator = self.pipeline(text, voice=voice, speed=1, split_pattern=r"\n+")

        audio_chunks = []
        for _i, (_gs, _ps, audio) in enumerate(generator):
            if self._cancelled:
                break
            audio_chunks.append(audio)

        if not audio_chunks:
            return b""

        full_audio = np.concatenate(audio_chunks)
        # convert float output to bytes
        full_audio = (full_audio * 32767.0).astype(np.int16)

        out = BytesIO()
        sf.write(out, full_audio, samplerate=24000, format="WAV")
        return out.getvalue()

    async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
        if self.pipeline is None:
            raise RuntimeError(
                "KokoroTTS is not available (kokoro package not installed)"
            )
        self._cancelled = False
        voice = "af_bella"
        generator = self.pipeline(text, voice=voice, speed=1)

        for _i, (_gs, _ps, audio) in enumerate(generator):
            if self._cancelled:
                break

            pcm = (audio * 32767.0).astype(np.int16).tobytes()
            yield pcm
