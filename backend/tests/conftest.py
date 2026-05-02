from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from numpy.typing import NDArray

import os
import sys

import numpy as np
import pytest

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from core.config import load_config
from core.event_bus import EventBus


@pytest.fixture
def mock_audio() -> NDArray[np.int16]:
    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    wave = 0.2 * np.sin(2 * np.pi * 440 * t)
    return cast("NDArray[np.int16]", (wave * 32767).astype(np.int16))


@pytest.fixture
def mock_config() -> dict[str, Any]:
    cfg = load_config()
    return cfg.model_dump()


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()
