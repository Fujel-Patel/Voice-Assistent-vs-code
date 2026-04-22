from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import numpy as np

from core.event_bus import EventBus
from core.logger import get_logger
from voice.audio_queue import AudioQueue

logger = get_logger(__name__)


class AudioPlayer:
    def __init__(self, event_bus: EventBus, volume: float = 0.8, sample_rate: int = 22050) -> None:
        self.event_bus = event_bus
        self.volume = max(0.0, min(1.0, volume))
        self.sample_rate = sample_rate
        self.queue = AudioQueue()
        self._stop = asyncio.Event()

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))

    async def play(self, audio_data: np.ndarray, sample_rate: int | None = None) -> None:
        await self.event_bus.publish("audio_playback_started", {})
        sr = sample_rate or self.sample_rate
        try:
            import sounddevice as sd

            data = (audio_data.astype(np.float32) * self.volume).astype(np.float32)
            await asyncio.to_thread(sd.play, data, sr)
            await asyncio.to_thread(sd.wait)
            await self.event_bus.publish("audio_playback_completed", {})
        except Exception as exc:
            logger.warning(f"Audio playback failed or unavailable: {exc}")
            await self.event_bus.publish("audio_playback_completed", {"simulated": True})

    async def play_stream(self, audio_stream: AsyncIterator[bytes], sample_rate: int | None = None) -> None:
        self._stop.clear()
        sr = sample_rate or self.sample_rate
        await self.event_bus.publish("audio_playback_started", {})

        try:
            import sounddevice as sd

            async for chunk in audio_stream:
                if self._stop.is_set():
                    break
                if not chunk:
                    continue
                pcm = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767.0
                pcm = (pcm * self.volume).astype(np.float32)
                await asyncio.to_thread(sd.play, pcm, sr)
                await asyncio.to_thread(sd.wait)
            if self._stop.is_set():
                await self.event_bus.publish("audio_playback_interrupted", {})
            else:
                await self.event_bus.publish("audio_playback_completed", {})
        except Exception as exc:
            logger.warning(f"Streaming playback fallback path: {exc}")
            async for _chunk in audio_stream:
                if self._stop.is_set():
                    break
                await asyncio.sleep(0)
            if self._stop.is_set():
                await self.event_bus.publish("audio_playback_interrupted", {})
            else:
                await self.event_bus.publish("audio_playback_completed", {"simulated": True})

    async def stop(self) -> None:
        self._stop.set()
        await self.queue.clear()
        try:
            import sounddevice as sd

            await asyncio.to_thread(sd.stop)
        except Exception:
            pass
