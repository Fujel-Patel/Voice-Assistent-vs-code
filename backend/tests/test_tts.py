from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from numpy.typing import NDArray

import numpy as np
import pytest
from core.event_bus import EventBus
from infrastructure.audio.audio_player import AudioPlayer
from services.voice.tts import TTSManager
from services.voice.tts_local import LocalTTS


def _config() -> SimpleNamespace:
    tts = SimpleNamespace(
        primary="elevenlabs",
        fallback="local",
        voice_id="voice_test",
        model_id="eleven_turbo_v2",
        stability=0.5,
        similarity_boost=0.8,
        speaking_rate=1.0,
        volume=0.8,
        local_voice="en_US-lessac-medium",
        sample_rate=22050,
    )
    return SimpleNamespace(tts=tts, elevenlabs_api_key="test-key")


@pytest.mark.asyncio
async def test_elevenlabs_synthesis() -> None:
    cfg = _config()
    bus = EventBus()
    manager = TTSManager(cast(Any, cfg), bus)

    async def fake_backend(backend: str, text: str) -> NDArray[Any]:
        assert backend == "elevenlabs"
        return np.ones(2205, dtype=np.float32) * 0.1

    cast(Any, manager)._synthesize_with_backend = fake_backend

    audio = await manager.synthesize("hello")
    assert isinstance(audio, np.ndarray)
    assert audio.size > 0


@pytest.mark.asyncio
async def test_local_tts_synthesis() -> None:
    local = LocalTTS(cast(Any, _config()))
    audio = await local.synthesize("fallback voice")
    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.float32
    assert audio.size > 0


@pytest.mark.asyncio
async def test_fallback_on_api_error() -> None:
    cfg = _config()
    bus = EventBus()
    manager = TTSManager(cast(Any, cfg), bus)

    async def fake_backend(backend: str, text: str) -> NDArray[Any]:
        if backend == "elevenlabs":
            raise RuntimeError("api failed")
        return np.ones(1024, dtype=np.float32) * 0.05

    cast(Any, manager)._synthesize_with_backend = fake_backend

    audio = await manager.synthesize("fallback please")
    assert audio.size == 1024


@pytest.mark.asyncio
async def test_streaming_synthesis() -> None:
    cfg = _config()
    bus = EventBus()
    manager = TTSManager(cast(Any, cfg), bus)

    async def fake_stream_backend(backend: str, text: str) -> AsyncIterator[bytes]:
        yield b"aaa"
        yield b"bbb"

    cast(Any, manager)._stream_with_backend = fake_stream_backend

    async def chunks() -> AsyncIterator[str]:
        yield "Hello world."
        yield " Next sentence!"

    out = []
    async for part in manager.stream_synthesize(chunks()):
        out.append(part)

    assert out
    assert b"aaa" in out


@pytest.mark.asyncio
async def test_interruption() -> None:
    cfg = _config()
    bus = EventBus()
    manager = TTSManager(cast(Any, cfg), bus)

    async def fake_stream_backend(backend: str, text: str) -> AsyncIterator[bytes]:
        for _ in range(20):
            await asyncio.sleep(0)
            yield b"chunk"

    cast(Any, manager)._stream_with_backend = fake_stream_backend

    async def chunks() -> AsyncIterator[str]:
        yield "Long sentence that keeps generating."

    emitted = 0
    async for _part in manager.stream_synthesize(chunks()):
        emitted += 1
        if emitted == 2:
            manager.cancel()

    assert emitted <= 3


def test_volume_control() -> None:
    player = AudioPlayer(event_bus=EventBus(), volume=0.5)
    player.set_volume(1.2)
    assert player.volume == 1.0
    player.set_volume(-1.0)
    assert player.volume == 0.0


def test_backend_mapping_supports_new_backends() -> None:
    cfg = _config()
    bus = EventBus()
    manager = TTSManager(cast(Any, cfg), bus)

    assert manager._backend("kitten") == "kitten"
    assert manager._backend("edge") == "edge"
    assert manager._backend("unknown") == "local"
