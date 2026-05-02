from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray
from core.config import JarvisConfig
from core.event_bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RecordingResult:
    audio: NDArray[np.int16]
    sample_rate: int


class AudioRecorder:
    """Microphone recorder with VAD-based auto-stop."""

    def __init__(self, config: JarvisConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._cancel = asyncio.Event()

    def cancel_recording(self) -> None:
        self._cancel.set()

    async def start_recording(
        self,
        on_audio_chunk: Callable[[NDArray[np.int16]], Awaitable[None]] | None = None,
    ) -> RecordingResult | None:
        self._cancel.clear()

        try:
            import sounddevice as sd
        except Exception as exc:  # pragma: no cover - runtime dependency
            await self._event_bus.publish(
                "listener_error", {"message": f"sounddevice unavailable: {exc}"}
            )
            return None

        try:
            import webrtcvad
        except Exception as exc:  # pragma: no cover - runtime dependency
            await self._event_bus.publish(
                "listener_error", {"message": f"webrtcvad unavailable: {exc}"}
            )
            return None

        sample_rate = self._config.audio.sample_rate
        channels = self._config.audio.channels
        max_duration = float(self._config.audio.max_recording_duration)
        no_speech_timeout = float(self._config.audio.no_speech_timeout)
        min_duration = float(self._config.audio.min_recording_duration)
        silence_stop_seconds = float(self._config.audio.silence_stop_seconds)

        vad = webrtcvad.Vad(3)
        frame_ms = 30
        frame_samples = int(sample_rate * frame_ms / 1000)
        silence_frames_limit = int(silence_stop_seconds * 1000 / frame_ms)
        no_speech_frames_limit = int(no_speech_timeout * 1000 / frame_ms)
        max_frames = int(max_duration * 1000 / frame_ms)

        # Calculate RMS threshold from percentage in config (e.g. 2.0 -> 2% of 32768)
        silence_threshold_pct = float(self._config.audio.silence_threshold)
        rms_threshold = int(32768 * (silence_threshold_pct / 100.0))

        frames: list[NDArray[np.int16]] = []
        silence_frames = 0
        no_speech_frames = 0
        detected_speech = False
        last_level_emit = 0.0

        await self._event_bus.publish("recording_started", {})

        try:
            with sd.InputStream(
                samplerate=sample_rate, channels=channels, dtype="int16"
            ) as stream:
                for _ in range(max_frames):
                    if self._cancel.is_set():
                        break

                    audio_chunk, _overflowed = await asyncio.to_thread(
                        stream.read, frame_samples
                    )
                    mono_chunk = (
                        audio_chunk[:, 0] if audio_chunk.ndim > 1 else audio_chunk
                    )
                    mono_int16 = mono_chunk.astype(np.int16)
                    pcm_bytes = mono_int16.tobytes()

                    # Provide real-time audio chunk to STT if needed
                    if on_audio_chunk:
                        await on_audio_chunk(mono_int16)

                    now = time.perf_counter()
                    if (now - last_level_emit) >= 0.05:
                        normalized = np.abs(mono_chunk.astype(np.float32)) / 32768.0
                        bins = 24
                        if normalized.size >= bins:
                            window = max(1, normalized.size // bins)
                            levels = [
                                float(
                                    np.mean(
                                        normalized[
                                            index * window : (index + 1) * window
                                        ]
                                    )
                                )
                                for index in range(bins)
                            ]
                        else:
                            levels = [float(np.mean(normalized))] * bins

                        await self._event_bus.publish("audio_level", {"levels": levels})
                        last_level_emit = now

                    # RMS energy check to supplement VAD
                    rms = np.sqrt(np.mean(mono_int16.astype(np.float32) ** 2))
                    is_speech = vad.is_speech(pcm_bytes, sample_rate)

                    if _ % 30 == 0:
                        logger.info(
                            f"Audio frame RMS: {rms:.2f}, VAD is_speech: {is_speech}, threshold: {rms_threshold}"
                        )

                    if rms < rms_threshold:
                        is_speech = False

                    frames.append(mono_int16)

                    # Grace period: ignore silence-stop for first 500ms
                    grace_frames = int(500 / frame_ms)
                    frame_count = len(frames)

                    if frame_count > grace_frames:
                        if is_speech:
                            detected_speech = True
                            silence_frames = 0
                        else:
                            silence_frames += 1
                            if not detected_speech:
                                no_speech_frames += 1

                        if (
                            not detected_speech
                            and no_speech_frames >= no_speech_frames_limit
                        ):
                            logger.info("Recording timed out: no speech detected")
                            await self._event_bus.publish(
                                "recording_timeout", {"reason": "no_speech"}
                            )
                            return None

                        if detected_speech and silence_frames >= silence_frames_limit:
                            logger.info("Recording finished: silence detected")
                            break
                    else:
                        if is_speech:
                            detected_speech = True
        except Exception as exc:
            logger.exception(f"Recording loop error: {exc}")
            await self._event_bus.publish(
                "listener_error", {"message": f"recording failed: {exc}"}
            )
            return None
        finally:
            await self._event_bus.publish("recording_stopped", {})

        if not frames:
            return None

        audio = np.concatenate(frames).astype(np.int16)
        duration = len(audio) / sample_rate
        if duration < min_duration:
            logger.info("Ignoring short utterance")
            return None

        return RecordingResult(audio=audio, sample_rate=sample_rate)
