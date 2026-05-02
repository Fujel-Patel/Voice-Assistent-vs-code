from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from numpy.typing import NDArray

import numpy as np
from core.logger import get_logger
from infrastructure.database.db import get_db

from .embeddings import SpeakerEmbeddingEngine
from .enrollment import VoiceEnrollment

logger = get_logger(__name__)


@dataclass
class VerificationCache:
    verified: bool
    confidence: float
    created_at: datetime
    expires_at: datetime


class SpeakerVerifier:
    THRESHOLDS = {
        "low": 0.70,
        "medium": 0.80,
        "high": 0.90,
    }

    def __init__(
        self,
        enrollment: VoiceEnrollment | None = None,
        embedding_engine: SpeakerEmbeddingEngine | None = None,
        threshold: str = "medium",
        reverify_minutes: int = 5,
        session_timeout_minutes: int = 30,
    ) -> None:
        self.embedding_engine = embedding_engine or SpeakerEmbeddingEngine()
        self.enrollment = enrollment or VoiceEnrollment(self.embedding_engine)
        self._threshold_level = "medium"
        self.set_threshold(threshold)
        self._reverify_minutes = reverify_minutes
        self._session_timeout_minutes = max(1, int(session_timeout_minutes))
        self._session_cache: dict[str, VerificationCache] = {}
        self._failure_count: dict[str, int] = {}

    async def verify(
        self,
        audio: NDArray[np.float32],
        user_id: str = "default_user",
        sample_rate: int = 16000,
    ) -> dict[str, Any]:
        cached = self._session_cache.get(user_id)
        now = datetime.now(UTC)
        if (
            cached
            and cached.verified
            and cached.expires_at > now
            and (now - cached.created_at)
            <= timedelta(minutes=self._session_timeout_minutes)
        ):
            return {
                "verified": cached.verified,
                "confidence": round(cached.confidence, 3),
                "user_id": user_id,
                "threshold_used": self.current_threshold,
                "cached": True,
                "mode": "voice",
                "pin_required": self._failure_count.get(user_id, 0) >= 3,
            }

        profile_embedding = await self.enrollment.get_profile_embedding(user_id)
        if profile_embedding is None:
            return {
                "verified": True,
                "confidence": 1.0,
                "user_id": user_id,
                "threshold_used": self.current_threshold,
                "mode": "disabled_no_profile",
                "pin_required": False,
            }

        live_embedding = self.embedding_engine.create_embedding(
            audio, sample_rate=sample_rate
        )
        confidence = self.embedding_engine.compare_embeddings(
            profile_embedding, live_embedding
        )

        threshold = self.current_threshold
        quality = self.embedding_engine.quality_score(audio, sample_rate=sample_rate)
        if quality < 0.4:
            threshold = max(0.65, threshold - 0.05)

        verified = confidence >= threshold
        self._failure_count[user_id] = (
            0 if verified else self._failure_count.get(user_id, 0) + 1
        )

        if verified:
            self._session_cache[user_id] = VerificationCache(
                verified=True,
                confidence=confidence,
                created_at=now,
                expires_at=now + timedelta(minutes=self._reverify_minutes),
            )
        else:
            self._session_cache.pop(user_id, None)

        await self._log_attempt(
            user_id=user_id,
            confidence=confidence,
            verified=verified,
            threshold=threshold,
        )

        return {
            "verified": verified,
            "confidence": round(confidence, 3),
            "user_id": user_id,
            "threshold_used": threshold,
            "mode": "voice",
            "pin_required": self._failure_count.get(user_id, 0) >= 3,
            "cached": False,
        }

    def set_threshold(self, level: str) -> None:
        candidate = (level or "medium").lower()
        if candidate not in self.THRESHOLDS:
            candidate = "medium"
        self._threshold_level = candidate

    @property
    def current_threshold(self) -> float:
        return self.THRESHOLDS[self._threshold_level]

    def reset_session(self, user_id: str = "default_user") -> None:
        self._session_cache.pop(user_id, None)

    def mark_pin_verified(
        self, user_id: str = "default_user", confidence: float = 0.99
    ) -> None:
        now = datetime.now(UTC)
        self._session_cache[user_id] = VerificationCache(
            verified=True,
            confidence=confidence,
            created_at=now,
            expires_at=now + timedelta(minutes=self._reverify_minutes),
        )
        self._failure_count[user_id] = 0

    async def _log_attempt(
        self, user_id: str, confidence: float, verified: bool, threshold: float
    ) -> None:
        database = await get_db()
        await database.execute(
            """
            INSERT INTO auth_attempts (user_id, confidence, verified, threshold, mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                float(confidence),
                1 if verified else 0,
                float(threshold),
                "voice",
                datetime.now(UTC).isoformat(),
            ),
        )
        await database.commit()
