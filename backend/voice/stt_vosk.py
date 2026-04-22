from __future__ import annotations

import json
import time
from typing import Any, Awaitable, Callable

import numpy as np

from config.config_loader import JarvisConfig
from core.logger import get_logger

try:
    import vosk
except ImportError:
    vosk = None

logger = get_logger(__name__)


class SpeechToTextVosk:
    """Vosk speech-to-text service with partial transcript callbacks."""

    def __init__(self, config: JarvisConfig):
        self._config = config
        if vosk is None:
            raise RuntimeError("vosk is not installed. Run `pip install vosk`")

        model_path = (config.stt.vosk_model_path or "").strip()
        language = (config.stt.language or "en-us").strip().lower()
        sample_rate = int(config.audio.sample_rate)

        if model_path:
            self.model = vosk.Model(model_path)
        else:
            try:
                self.model = vosk.Model(lang=language)
            except TypeError as exc:
                raise RuntimeError(
                    "This Vosk build requires an explicit model path. "
                    "Set stt.vosk_model_path in config."
                ) from exc

        self.recognizer = vosk.KaldiRecognizer(self.model, sample_rate)
        if hasattr(self.recognizer, "SetWords"):
            self.recognizer.SetWords(True)

    async def transcribe(
        self,
        audio_data: np.ndarray | bytes,
        on_chunk: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
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
                "language": self._config.stt.language if self._config.stt.language != "auto" else "unknown",
                "duration_seconds": 0.0,
            }

        collected_final: list[str] = []
        frame_size = int(self._config.audio.sample_rate * 0.03)  # 30ms frames

        for i in range(0, len(audio), frame_size):
            frame = audio[i : i + frame_size]
            if frame.size == 0:
                continue
            accepted = self.recognizer.AcceptWaveform(frame.astype(np.int16).tobytes())
            if accepted:
                result = json.loads(self.recognizer.Result())
                text = (result.get("text") or "").strip()
                if text and (not collected_final or collected_final[-1] != text):
                    collected_final.append(text)
                    if on_chunk is not None:
                        await on_chunk(
                            {
                                "text": " ".join(collected_final).strip(),
                                "chunk": text,
                                "is_final": False,
                            }
                        )
            elif on_chunk is not None:
                partial = json.loads(self.recognizer.PartialResult())
                partial_text = (partial.get("partial") or "").strip()
                if partial_text:
                    await on_chunk(
                        {
                            "text": (" ".join(collected_final) + " " + partial_text).strip(),
                            "chunk": partial_text,
                            "is_final": False,
                        }
                    )

        final_result = json.loads(self.recognizer.FinalResult())
        final_text = (final_result.get("text") or "").strip()
        if final_text:
            collected_final.append(final_text)

        transcript = " ".join(collected_final).strip()
        duration = time.perf_counter() - started_at

        if on_chunk is not None and transcript:
            await on_chunk({"text": transcript, "chunk": "", "is_final": True})

        return {
            "text": transcript,
            "confidence": 0.82 if transcript else 0.05,
            "language": self._config.stt.language if self._config.stt.language != "auto" else "unknown",
            "duration_seconds": round(duration, 3),
        }
