from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from numpy.typing import NDArray

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from core.config import JarvisConfig
from services.voice.stt import SpeechToText


@pytest.mark.asyncio
async def test_transcribe_valid_audio(mock_audio: NDArray[Any]) -> None:
    cfg = JarvisConfig()

    segment = SimpleNamespace(text="open visual studio code", avg_logprob=-0.2)
    info = SimpleNamespace(language="en")

    model = MagicMock()
    model.transcribe.return_value = ([segment], info)

    manager = MagicMock()
    manager.ensure_loaded = AsyncMock(return_value=model)

    stt = SpeechToText(config=cfg, model_manager=manager)
    result = await stt.transcribe(mock_audio)

    assert result["text"] == "open visual studio code"
    assert 0.0 <= result["confidence"] <= 1.0
    assert result["language"] == "en"


@pytest.mark.asyncio
async def test_transcribe_empty_audio() -> None:
    cfg = JarvisConfig()
    manager = MagicMock()
    manager.ensure_loaded = AsyncMock()

    stt = SpeechToText(config=cfg, model_manager=manager)
    result = await stt.transcribe(np.array([], dtype=np.int16))

    assert result["text"] == ""
    assert result["confidence"] <= 0.1
    manager.ensure_loaded.assert_not_called()


@pytest.mark.asyncio
async def test_model_not_loaded_triggers_download(mock_audio: NDArray[Any]) -> None:
    cfg = JarvisConfig()

    segment = SimpleNamespace(text="turn on bluetooth", avg_logprob=-0.5)
    info = SimpleNamespace(language="en")

    model = MagicMock()
    model.transcribe.return_value = ([segment], info)

    manager = MagicMock()
    manager.ensure_loaded = AsyncMock(return_value=model)

    stt = SpeechToText(config=cfg, model_manager=manager)
    _ = await stt.transcribe(mock_audio)

    manager.ensure_loaded.assert_awaited_once()


@pytest.mark.asyncio
async def test_language_detection(mock_audio: NDArray[Any]) -> None:
    cfg = JarvisConfig()

    segment = SimpleNamespace(text="hola mundo", avg_logprob=-0.3)
    info = SimpleNamespace(language="es")

    model = MagicMock()
    model.transcribe.return_value = ([segment], info)

    manager = MagicMock()
    manager.ensure_loaded = AsyncMock(return_value=model)

    stt = SpeechToText(config=cfg, model_manager=manager)
    result = await stt.transcribe(mock_audio)

    assert result["language"] == "es"
