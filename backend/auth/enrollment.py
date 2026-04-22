from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from core.logger import get_logger
from storage.db import get_db
from .embeddings import SpeakerEmbeddingEngine

logger = get_logger(__name__)

ENROLLMENT_PHRASES = [
    "Jarvis, activate all systems",
    "Good morning, Jarvis",
    "Run a full diagnostic",
]


@dataclass
class EnrollmentSession:
    user_id: str
    embeddings: list[np.ndarray] = field(default_factory=list)
    quality_scores: list[float] = field(default_factory=list)


class VoiceEnrollment:
    def __init__(self, embedding_engine: SpeakerEmbeddingEngine | None = None) -> None:
        self.embedding_engine = embedding_engine or SpeakerEmbeddingEngine()
        self._sessions: dict[str, EnrollmentSession] = {}

    async def start_enrollment(self, user_id: str) -> dict[str, Any]:
        db_status = await self._check_db_connection()
        if not db_status["db_connected"]:
            return {
                "success": False,
                "step": 1,
                "total_steps": len(ENROLLMENT_PHRASES),
                "phrase": ENROLLMENT_PHRASES[0],
                "instructions": "Please say the phrase clearly",
                "error": "Database connection failed. Please retry after backend is ready.",
                **db_status,
            }

        self._sessions[user_id] = EnrollmentSession(user_id=user_id)
        return {
            "success": True,
            "step": 1,
            "total_steps": len(ENROLLMENT_PHRASES),
            "phrase": ENROLLMENT_PHRASES[0],
            "instructions": "Please say the phrase clearly",
            **db_status,
        }

    async def process_sample(
        self,
        user_id: str,
        audio: np.ndarray,
        step: int,
        transcript_text: str | None = None,
        capture_duration_ms: int | None = None,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        session = self._sessions.setdefault(user_id, EnrollmentSession(user_id=user_id))
        expected_step = len(session.embeddings) + 1
        if step != expected_step:
            raise ValueError(f"Unexpected step. Expected {expected_step}, got {step}")

        expected_phrase = ENROLLMENT_PHRASES[step - 1]
        phrase_ok = self._phrase_matches(expected_phrase, transcript_text)
        if transcript_text is not None and not phrase_ok:
            return self._with_latency(
                {
                "step": step,
                "success": False,
                "complete": False,
                "error": f"That does not match. Please say: {expected_phrase}",
                },
                started_at=started_at,
                capture_duration_ms=capture_duration_ms,
            )

        quality_score = self.embedding_engine.quality_score(audio)
        duration_seconds = len(audio) / 16000.0
        if duration_seconds < 3.0:
            return self._with_latency(
                {
                "step": step,
                "success": False,
                "complete": False,
                "error": "Please speak for at least 3 seconds",
                },
                started_at=started_at,
                capture_duration_ms=capture_duration_ms,
            )
        if quality_score < 0.35:
            return self._with_latency(
                {
                "step": step,
                "success": False,
                "complete": False,
                "error": "Please try in a quieter environment",
                },
                started_at=started_at,
                capture_duration_ms=capture_duration_ms,
            )

        clipping = float(np.max(np.abs(audio)))
        if clipping > 32500:
            return self._with_latency(
                {
                "step": step,
                "success": False,
                "complete": False,
                "error": "You are too close to the microphone",
                },
                started_at=started_at,
                capture_duration_ms=capture_duration_ms,
            )

        embedding = self.embedding_engine.create_embedding(audio)
        session.embeddings.append(embedding)
        session.quality_scores.append(quality_score)

        profile_strength = int(round(sum(session.quality_scores) / len(session.quality_scores) * 100))
        complete = len(session.embeddings) >= len(ENROLLMENT_PHRASES)

        next_phrase = None
        if not complete:
            next_phrase = ENROLLMENT_PHRASES[len(session.embeddings)]

        return self._with_latency(
            {
                "step": step,
                "success": True,
                "quality_score": round(quality_score, 3),
                "profile_strength": profile_strength,
                "next_phrase": next_phrase,
                "complete": complete,
            },
            started_at=started_at,
            capture_duration_ms=capture_duration_ms,
        )

    async def complete_enrollment(self, user_id: str) -> dict[str, Any]:
        started_at = perf_counter()
        session = self._sessions.get(user_id)
        if session is None or len(session.embeddings) < 3:
            return self._with_latency(
                {
                "success": False,
                "message": "Enrollment requires 3 samples",
                },
                started_at=started_at,
            )

        profile_embedding = self.embedding_engine.average_embeddings(session.embeddings)
        strength = float(sum(session.quality_scores) / len(session.quality_scores) * 100.0)

        encrypted = self._encrypt_embedding(profile_embedding)
        now = datetime.now(timezone.utc).isoformat()

        database = await get_db()
        await database.execute(
            """
            INSERT INTO voice_profiles (
                user_id, embedding, sample_count, profile_strength, created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                embedding=excluded.embedding,
                sample_count=excluded.sample_count,
                profile_strength=excluded.profile_strength,
                updated_at=excluded.updated_at,
                is_active=1
            """,
            (
                user_id,
                encrypted,
                len(session.embeddings),
                strength,
                now,
                now,
            ),
        )
        await database.commit()

        del self._sessions[user_id]
        return self._with_latency(
            {
                "success": True,
                "profile_strength": int(round(strength)),
                "message": "Voice profile created successfully",
                "db_connected": True,
            },
            started_at=started_at,
        )

    async def get_profile_embedding(self, user_id: str) -> np.ndarray | None:
        database = await get_db()
        rows = await database.fetch_all(
            "SELECT embedding FROM voice_profiles WHERE user_id = ? AND is_active = 1",
            (user_id,),
        )
        if not rows:
            return None

        encrypted = rows[0]["embedding"]
        return self._decrypt_embedding(encrypted)

    def _phrase_matches(self, expected: str, transcript_text: str | None) -> bool:
        if transcript_text is None:
            return True
        expected_tokens = set(expected.lower().replace(",", "").split())
        spoken_tokens = set((transcript_text or "").lower().replace(",", "").split())
        overlap = len(expected_tokens & spoken_tokens)
        return overlap / max(1, len(expected_tokens)) >= 0.7

    def _encrypt_embedding(self, embedding: np.ndarray) -> bytes:
        payload = embedding.astype(np.float32).tobytes()
        fernet = self._fernet()
        return fernet.encrypt(payload)

    def _decrypt_embedding(self, encrypted_blob: bytes) -> np.ndarray:
        fernet = self._fernet()
        plain = fernet.decrypt(encrypted_blob)
        return np.frombuffer(plain, dtype=np.float32)

    def _fernet(self):
        try:
            from cryptography.fernet import Fernet
        except Exception as exc:  # pragma: no cover - dependency/runtime specific
            raise RuntimeError(f"cryptography is required for voice profile encryption: {exc}")

        key = os.getenv("JARVIS_AUTH_EMBEDDING_KEY")
        if key:
            return Fernet(key.encode("utf-8"))

        key_path = Path.home() / ".jarvis" / "auth.key"
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            return Fernet(key_path.read_text(encoding="utf-8").strip().encode("utf-8"))

        generated = Fernet.generate_key()
        key_path.write_text(generated.decode("utf-8"), encoding="utf-8")
        os.chmod(key_path, 0o600)
        return Fernet(generated)

    async def _check_db_connection(self) -> dict[str, Any]:
        try:
            database = await get_db()
            await database.fetch_all("SELECT 1 AS ok")
            return {"db_connected": True}
        except Exception as exc:
            logger.exception(f"Enrollment DB check failed: {exc}")
            return {
                "db_connected": False,
                "db_error": str(exc),
            }

    def _with_latency(
        self,
        payload: dict[str, Any],
        *,
        started_at: float,
        capture_duration_ms: int | None = None,
    ) -> dict[str, Any]:
        processing_latency_ms = int((perf_counter() - started_at) * 1000)
        capture_latency_ms = int(max(0, capture_duration_ms or 0))
        total_pipeline_latency_ms = processing_latency_ms + capture_latency_ms

        return {
            **payload,
            "processing_latency_ms": processing_latency_ms,
            "capture_latency_ms": capture_latency_ms,
            "total_pipeline_latency_ms": total_pipeline_latency_ms,
        }
