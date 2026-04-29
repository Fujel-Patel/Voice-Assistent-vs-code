from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from numpy.typing import NDArray

import numpy as np
import pytest
from auth.access_control import AccessController
from auth.embeddings import SpeakerEmbeddingEngine
from auth.enrollment import VoiceEnrollment
from auth.liveness import LivenessDetector
from auth.speaker_verify import SpeakerVerifier


def _tone(freq: float, seconds: float = 3.0, sample_rate: int = 16000) -> NDArray[Any]:
    t = np.linspace(0, seconds, int(sample_rate * seconds), endpoint=False)
    wave = 0.25 * np.sin(2 * np.pi * freq * t)
    return cast("NDArray[Any]", (wave * 32767).astype(np.int16))


class DummyDB:
    def __init__(self) -> None:
        self.commands: list[tuple[str, dict[str, Any] | None]] = []

    async def execute(self, query: str, params: dict[str, Any] | None = None) -> None:
        self.commands.append((query, params))

    async def commit(self) -> None:
        return None

    async def fetch_all(
        self, _query: str, _params: dict[str, Any] | None = None
    ) -> list[Any]:
        return []


@pytest.mark.asyncio
async def test_enrollment_3_samples(monkeypatch: Any) -> None:
    enrollment = VoiceEnrollment()
    user_id = "default_user"

    dummy_db = DummyDB()

    async def fake_get_db() -> DummyDB:
        return dummy_db

    monkeypatch.setattr("auth.enrollment.get_db", fake_get_db)
    monkeypatch.setattr(enrollment, "_encrypt_embedding", lambda emb: emb.tobytes())

    start = await enrollment.start_enrollment(user_id)
    assert start["step"] == 1

    phrases = [
        "Jarvis activate all systems",
        "Good morning Jarvis",
        "Run a full diagnostic",
    ]
    for index, phrase in enumerate(phrases, start=1):
        result = await enrollment.process_sample(
            user_id, _tone(210 + (index * 40)), index, transcript_text=phrase
        )
        assert "error" not in result

    complete = await enrollment.complete_enrollment(user_id)
    assert complete["success"] is True
    assert complete["profile_strength"] > 0
    assert len(dummy_db.commands) >= 1


@pytest.mark.asyncio
async def test_verification_same_speaker(monkeypatch: Any) -> None:
    engine = SpeakerEmbeddingEngine()
    enrollment = VoiceEnrollment(embedding_engine=engine)
    verifier = SpeakerVerifier(
        enrollment=enrollment, embedding_engine=engine, threshold="medium"
    )

    sample = _tone(240)
    profile = engine.create_embedding(sample)

    async def fake_profile(_user_id: str) -> NDArray[Any]:
        return profile

    async def fake_log_attempt(**_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(enrollment, "get_profile_embedding", fake_profile)
    monkeypatch.setattr(verifier, "_log_attempt", fake_log_attempt)

    result = await verifier.verify(sample)
    assert result["verified"] is True
    assert result["confidence"] >= 0.8


@pytest.mark.asyncio
async def test_verification_different_speaker(monkeypatch: Any) -> None:
    engine = SpeakerEmbeddingEngine()
    enrollment = VoiceEnrollment(embedding_engine=engine)
    verifier = SpeakerVerifier(
        enrollment=enrollment, embedding_engine=engine, threshold="high"
    )

    profile = engine.create_embedding(_tone(160))

    async def fake_profile(_user_id: str) -> NDArray[Any]:
        return profile

    async def fake_log_attempt(**_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(enrollment, "get_profile_embedding", fake_profile)
    monkeypatch.setattr(verifier, "_log_attempt", fake_log_attempt)

    result = await verifier.verify(_tone(680))
    assert result["verified"] is False
    assert result["confidence"] < 0.9


def test_liveness_challenge() -> None:
    detector = LivenessDetector()
    challenge = detector.generate_challenge()
    audio = _tone(330, seconds=2.2)

    result = detector.verify_challenge(
        audio,
        expected_phrase=challenge["phrase"],
        transcript_text=challenge["phrase"],
        response_latency_seconds=1.8,
    )

    assert result["passed"] is True
    assert result["phrase_matched"] is True


def test_liveness_replay() -> None:
    detector = LivenessDetector()
    challenge = detector.generate_challenge()
    audio = _tone(330, seconds=0.4)

    result = detector.verify_challenge(
        audio,
        expected_phrase=challenge["phrase"],
        transcript_text=challenge["phrase"],
        response_latency_seconds=0.2,
    )

    assert result["passed"] is False
    assert result["timing_natural"] is False


@pytest.mark.asyncio
async def test_access_control_full() -> None:
    controller = AccessController(pin_code="2468")
    allowed = await controller.check_access({"intent": "open-app"}, {"verified": True})
    assert allowed is True


@pytest.mark.asyncio
async def test_access_control_limited() -> None:
    controller = AccessController(pin_code="2468")
    denied = await controller.check_access(
        {"intent": "file-operation"}, {"verified": False}
    )
    query_allowed = await controller.check_access(
        {"intent": "web-search"}, {"verified": False}
    )
    assert denied is False
    assert query_allowed is True


@pytest.mark.asyncio
async def test_pin_fallback(monkeypatch: Any) -> None:
    engine = SpeakerEmbeddingEngine()
    enrollment = VoiceEnrollment(embedding_engine=engine)
    verifier = SpeakerVerifier(
        enrollment=enrollment, embedding_engine=engine, threshold="high"
    )
    access = AccessController(pin_code="2468")

    profile = engine.create_embedding(_tone(120))

    async def fake_profile(_user_id: str) -> NDArray[Any]:
        return profile

    async def fake_log_attempt(**_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(enrollment, "get_profile_embedding", fake_profile)
    monkeypatch.setattr(verifier, "_log_attempt", fake_log_attempt)

    for _ in range(3):
        result = await verifier.verify(_tone(820))

    assert result["pin_required"] is True
    assert access.verify_pin("2468") is True
