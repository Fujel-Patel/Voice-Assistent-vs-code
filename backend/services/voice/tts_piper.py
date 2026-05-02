from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from io import BytesIO
from typing import TYPE_CHECKING, Any

import numpy as np
import soundfile as sf

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from piper import PiperVoice
from core.logger import get_logger

logger = get_logger(__name__)


class PiperTTS:
    def __init__(self, config: Any) -> None:
        self.config = config
        self.sample_rate = int(config.tts.sample_rate)
        self._cancelled = False
        self._voice: PiperVoice | None = None
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

    def _ensure_voice(self) -> PiperVoice:
        if not self.available:
            raise RuntimeError(
                "piper-tts is not installed. Run `pip install piper-tts`"
            )

        import os
        from pathlib import Path

        model_name_cfg = str(
            getattr(self.config.tts, "piper_model", "") or "en_US-lessac-medium.onnx"
        ).strip()

        if self._voice is not None and self._voice_model_name == model_name_cfg:
            return self._voice

        # Search locations in order
        search_paths = [
            Path(model_name_cfg),  # absolute path as given
            Path.home()
            / ".jarvis"
            / "models"
            / "tts"
            / model_name_cfg,  # download_models.py location
            Path.home()
            / ".local"
            / "share"
            / "piper"
            / model_name_cfg,  # piper default
            Path("/usr/share/piper/voices") / model_name_cfg,  # system install
        ]

        resolved_path = None
        for candidate in search_paths:
            if candidate.exists():
                resolved_path = os.fspath(candidate)
                break

        if resolved_path is None:
            raise RuntimeError(
                f"Piper model '{model_name_cfg}' not found. "
                f"Run: python scripts/download_models.py\n"
                f"Searched: {[str(p) for p in search_paths]}"
            )

        from piper import PiperVoice

        logger.info(f"Loading Piper voice model from: {resolved_path}")
        self._voice = PiperVoice.load(resolved_path, use_cuda=False)
        self._voice_model_name = model_name_cfg
        return self._voice

    async def synthesize(self, text: str) -> NDArray[np.float32]:
        self._cancelled = False
        if not text.strip():
            return np.zeros(1, dtype=np.float32)

        def _render() -> tuple[NDArray[np.float32], int]:
            voice = self._ensure_voice()
            wav_buffer = BytesIO()
            speaker_id = getattr(self.config.tts, "piper_speaker_id", None)
            length_scale = max(0.5, min(2.0, float(self.config.tts.speaking_rate)))

            import wave

            with wave.open(wav_buffer, "wb") as wav_file:
                voice_any: Any = voice
                voice_any.synthesize(
                    text=text,
                    wav_file=wav_file,
                    speaker_id=speaker_id,
                    length_scale=length_scale,
                    noise_scale=float(
                        getattr(self.config.tts, "piper_noise_scale", 0.667)
                    ),
                    noise_w=float(getattr(self.config.tts, "piper_noise_w", 0.8)),
                    sentence_silence=float(
                        getattr(self.config.tts, "piper_sentence_silence", 0.0)
                    ),
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
