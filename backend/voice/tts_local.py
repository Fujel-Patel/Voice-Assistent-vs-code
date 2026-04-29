from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import tempfile
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Any

import numpy as np
import soundfile as sf
from core.logger import get_logger

if TYPE_CHECKING:
    from config.config_loader import JarvisConfig
    from numpy.typing import NDArray

logger = get_logger(__name__)


class LocalTTS:
    def __init__(self, config: JarvisConfig) -> None:
        self.config = config
        self.sample_rate = int(config.tts.sample_rate)
        self._cancelled = False
        self.models_dir = Path.home() / ".jarvis" / "models" / "tts"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def cancel(self) -> None:
        self._cancelled = True

    def _jarvis_effect(self, audio: NDArray[np.float32]) -> NDArray[np.float32]:
        if audio.size == 0:
            return audio
        delay = int(0.035 * self.sample_rate)
        if delay <= 0 or delay >= audio.size:
            return audio

        out = audio.astype(np.float32).copy()
        out[delay:] += 0.12 * out[:-delay]
        peak = float(np.max(np.abs(out))) or 1.0
        out = out / peak
        return np.clip(out, -1.0, 1.0)

    async def synthesize(self, text: str) -> NDArray[np.float32]:
        self._cancelled = False
        speech = await self._synthesize_with_espeak(text)
        if speech is not None and speech.size:
            return speech

        speech = await self._synthesize_with_pyttsx3(text)
        if speech is not None and speech.size:
            return speech

        logger.warning(
            "No local speech backend available (espeak/pyttsx3); returning silent fallback audio"
        )
        # Keep pipeline healthy without producing unpleasant tone artifacts.
        duration = max(0.2, min(2.0, len(text) / 24.0))
        n = max(1, int(duration * self.sample_rate))
        return np.zeros(n, dtype=np.float32)

    async def stream_synthesize_sentence(self, text: str) -> AsyncIterator[bytes]:
        audio = await self.synthesize(text)
        pcm = (audio * 32767.0).astype(np.int16).tobytes()
        chunk_size = 4096
        for i in range(0, len(pcm), chunk_size):
            if self._cancelled:
                break
            yield pcm[i : i + chunk_size]
            await asyncio.sleep(0)

    async def _synthesize_with_pyttsx3(self, text: str) -> NDArray[np.float32] | None:
        if not text.strip():
            return np.zeros(1, dtype=np.float32)

        def _render_wav() -> tuple[NDArray[Any], int] | None:
            wav_path = None
            try:
                wav_path = str(
                    Path(tempfile.gettempdir())
                    / f"jarvis_pyttsx3_{uuid.uuid4().hex}.wav"
                )

                scaled_rate = int(
                    175 * max(0.6, min(1.6, float(self.config.tts.speaking_rate)))
                )
                pyttsx3_script = (
                    "import sys\n"
                    "import pyttsx3\n"
                    "out_path = sys.argv[1]\n"
                    "text = sys.argv[2]\n"
                    "rate = int(sys.argv[3])\n"
                    "engine = pyttsx3.init()\n"
                    "engine.setProperty('rate', rate)\n"
                    "engine.save_to_file(text, out_path)\n"
                    "engine.runAndWait()\n"
                    "try:\n"
                    "    engine.stop()\n"
                    "except Exception:\n"
                    "    pass\n"
                )
                subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        pyttsx3_script,
                        wav_path,
                        text,
                        str(scaled_rate),
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                )

                wav_file = Path(wav_path)
                if not wav_file.exists() or wav_file.stat().st_size < 64:
                    return None

                audio, sr = sf.read(wav_path, dtype="float32")
                if isinstance(audio, np.ndarray) and audio.ndim > 1:
                    audio = audio.mean(axis=1)
                if audio.size == 0:
                    return None
                return audio.astype(np.float32), int(sr)
            except Exception as exc:
                logger.warning(f"pyttsx3 synthesis failed: {exc}")
                return None
            finally:
                if wav_path:
                    try:
                        Path(wav_path).unlink(missing_ok=True)
                    except Exception:
                        pass

        rendered = await asyncio.to_thread(_render_wav)
        if rendered is None:
            return None

        audio, sr = rendered
        if sr != self.sample_rate:
            audio = self._resample(audio, sr, self.sample_rate)
        return self._jarvis_effect(audio.astype(np.float32))

    async def _synthesize_with_espeak(self, text: str) -> NDArray[np.float32] | None:
        if not text.strip():
            return np.zeros(1, dtype=np.float32)

        speech_cli = shutil.which("espeak") or shutil.which("espeak-ng")
        if not speech_cli:
            return None

        def _render_wav() -> tuple[NDArray[Any], int] | None:
            wav_path = None
            try:
                with NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    wav_path = tmp.name

                base_speed = 175
                speed = int(
                    base_speed
                    * max(0.6, min(1.6, float(self.config.tts.speaking_rate)))
                )
                cmd = [speech_cli, "-s", str(speed), "-w", wav_path, text]
                subprocess.run(
                    cmd,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                audio, sr = sf.read(wav_path, dtype="float32")
                if isinstance(audio, np.ndarray) and audio.ndim > 1:
                    audio = audio.mean(axis=1)
                return audio.astype(np.float32), int(sr)
            except Exception as exc:
                logger.warning(f"espeak synthesis failed: {exc}")
                return None
            finally:
                if wav_path:
                    try:
                        Path(wav_path).unlink(missing_ok=True)
                    except Exception:
                        pass

        rendered = await asyncio.to_thread(_render_wav)
        if rendered is None:
            return None

        audio, sr = rendered
        if sr != self.sample_rate:
            audio = self._resample(audio, sr, self.sample_rate)
        return self._jarvis_effect(audio.astype(np.float32))

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
