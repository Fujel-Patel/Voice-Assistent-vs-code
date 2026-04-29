from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import voice.stt_vosk as stt_vosk_module
from config.config_loader import JarvisConfig
from voice.stt_vosk import SpeechToTextVosk


class _FakeRecognizer:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self._calls = 0

    def SetWords(self, _enabled: bool) -> None:
        return None

    def AcceptWaveform(self, _frame_bytes: bytes) -> bool:
        self._calls += 1
        return self._calls % 2 == 0

    def Result(self) -> str:
        return '{"text":"hello"}'

    def PartialResult(self) -> str:
        return '{"partial":"hel"}'

    def FinalResult(self) -> str:
        return '{"text":"world"}'


class _FakeVosk:
    class Model:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    KaldiRecognizer = _FakeRecognizer


@pytest.mark.asyncio
async def test_vosk_transcribe_emits_chunks(monkeypatch: Any) -> None:
    monkeypatch.setattr(stt_vosk_module, "vosk", _FakeVosk)

    cfg = JarvisConfig()
    cfg.stt.engine = "vosk"
    cfg.stt.language = "en-us"
    cfg.stt.vosk_model_path = ""

    stt = SpeechToTextVosk(cfg)
    seen = []

    async def _on_chunk(payload: dict[str, Any]) -> None:
        seen.append(payload)

    audio = (np.sin(np.linspace(0, 2.0, 16000)) * 32767).astype(np.int16)
    result = await stt.transcribe(audio, on_chunk=_on_chunk)

    assert result["text"] == "hello world"
    assert result["confidence"] > 0
    assert seen
    assert seen[-1]["is_final"] is True
