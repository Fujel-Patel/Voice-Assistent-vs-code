from __future__ import annotations

import numpy as np
import pytest

from config.config_loader import load_config
from core.event_bus import EventBus


@pytest.fixture
def mock_audio() -> np.ndarray:
    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = 0.2 * np.sin(2 * np.pi * 440 * t)
    return (wave * 32767).astype(np.int16)


@pytest.fixture
def mock_config() -> dict:
    cfg = load_config()
    return cfg.model_dump()


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()
