from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from io import BytesIO

import numpy as np
import soundfile as sf

from core.logger import get_logger

logger = get_logger(__name__)


class PiperTTS:
    def __init__(self, config) -> None:
        self.config = config
        self.sample_rate = int(config.tts.sample_rate)
        self._cancelled = False
        self._voice = None
        self._voice_model_name = ""
        self.available = self._module_available()

    def _module_available(self) -> bool:
        try:
            import piper  # noqa: F401

            return True
        except Exception:
            return False

    def cancel(self) -> None:
        self._cancelled = True

    def _ensure_voice(self):
        if not self.available:
            raise RuntimeError("piper-tts is not installed. Run `pip install piper-tts`")

        model_name = str(getattr(self.config.tts, "piper_model", "") or "en_US-lessac-medium.onnx").strip()
        if not model_name:
            model_name = "en_US-lessac-medium.onnx"

        if self._voice is not None and self._voice_model_name == model_name:
            return self._voice

        from piper import PiperVoice

        logger.info(f"Loading Piper voice model: {model_name}")
        self._voice = PiperVoice.load(model_name, use_cuda=False)
        self._voice_model_name = model_name
        return self._voice

    async def synthesize(self, text: str) -> np.ndarray:
        self._cancelled = False
        if not text.strip():
            return np.zeros(1, dtype=np.float32)

        def _render() -> tuple[np.ndarray, int]:
            voice = self._ensure_voice()
            wav_buffer = BytesIO()
            speaker_id = getattr(self.config.tts, "piper_speaker_id", None)
            length_scale = max(0.5, min(2.0, float(self.config.tts.speaking_rate)))

            import wave

            with wave.open(wav_buffer, "wb") as wav_file:
                voice.synthesize(
                    text=text,
                    wav_file=wav_file,
                    speaker_id=speaker_id,
                    length_scale=length_scale,
                    noise_scale=float(getattr(self.config.tts, "piper_noise_scale", 0.667)),
                    noise_w=float(getattr(self.config.tts, "piper_noise_w", 0.8)),
                    sentence_silence=float(getattr(self.config.tts, "piper_sentence_silence", 0.0)),
                )

            wav_buffer.seek(0)
            audio, sr = sf.read(wav_buffer, dtype="float32")
            if isinstance(audio, np.ndarray) and audio.ndim > 1:
                audio = audio.mean(axis=1)
            return audio.astype(np.float32), int(sr)

        audio, sr = await asyncio.to_thread(_render)
        if sr != self.sample_rate:
            audio = self._resample(audio, sr, self.sample_rate)
        return audio.astype(np.float32)

    async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text)
        pcm = (audio * 32767.0).astype(np.int16).tobytes()
        chunk_size = 4096
        for i in range(0, len(pcm), chunk_size):
            if self._cancelled:
                break
            yield pcm[i : i + chunk_size]
            await asyncio.sleep(0)

    def _resample(self, audio: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        if src_rate == dst_rate or audio.size == 0:
            return audio
        duration = len(audio) / float(src_rate)
        src_time = np.linspace(0, duration, num=len(audio), endpoint=False)
        dst_len = int(duration * dst_rate)
        dst_time = np.linspace(0, duration, num=max(1, dst_len), endpoint=False)
        return np.interp(dst_time, src_time, audio).astype(np.float32)
