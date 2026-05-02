from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.config import load_config
from core.event_bus import EventBus
from services.voice.stt_manager import STTManager


@pytest.mark.asyncio
async def test_stt_manager_fallback(mock_audio: Any) -> None:
    config = load_config()
    event_bus = EventBus()

    manager = STTManager(config, event_bus)

    # Mock moonshine to fail
    mock_moonshine = MagicMock()
    mock_moonshine.transcribe = AsyncMock(side_effect=Exception("Moonshine failed"))

    # Mock whisper to succeed
    mock_whisper = MagicMock()
    mock_whisper.transcribe = AsyncMock(
        return_value={"text": "Whisper success", "confidence": 0.8}
    )

    def get_engine_mock(name: str) -> Any:
        if name == "moonshine":
            return mock_moonshine
        if name == "whisper":
            return mock_whisper
        return None

    with patch.object(manager, "_get_engine", side_effect=get_engine_mock):
        result = await manager.transcribe(mock_audio)
        assert result["text"] == "Whisper success"
        assert cast(Any, manager._get_engine).call_count >= 2
