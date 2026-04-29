from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import numpy as np
from storage.db import get_db

if TYPE_CHECKING:
    from numpy.typing import NDArray
    from sentence_transformers import SentenceTransformer


class LongTermMemory:
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2") -> None:
        self.embedding_model_name = embedding_model
        self._embedder: SentenceTransformer | Literal[False] | None = None

    def _ensure_embedder(self) -> SentenceTransformer | Literal[False]:
        if self._embedder is not None:
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer(self.embedding_model_name)
        except Exception:
            self._embedder = False
        return self._embedder

    def _embed(self, text: str) -> NDArray[np.float32]:
        embedder = self._ensure_embedder()
        if embedder is False:
            # Fallback embedding: deterministic hash projection.
            arr = np.zeros(64, dtype=np.float32)
            for i, ch in enumerate(text.encode("utf-8", "ignore")):
                arr[i % 64] += float(ch) / 255.0
            norm = np.linalg.norm(arr)
            return arr if norm == 0 else arr / norm

        # Mypy knows embedder is SentenceTransformer here
        vec = embedder.encode(text)
        out = np.array(vec, dtype=np.float32)
        norm = np.linalg.norm(out)
        return out if norm == 0 else out / norm

    async def store_summary(
        self,
        session_id: str,
        summary: str,
        topics: list[str],
        turn_count: int = 0,
    ) -> None:
        db = await get_db()
        embedding = self._embed(summary).tobytes()
        await db.execute(
            """
            INSERT INTO conversations(session_id, summary, key_topics, embedding, created_at, turn_count)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                summary,
                json.dumps(topics),
                sqlite3.Binary(embedding),
                datetime.now(UTC).isoformat(),
                turn_count,
            ),
        )
        await db.commit()

    async def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        db = await get_db()
        rows = await db.fetch_all(
            """
            SELECT id, session_id, summary, key_topics, embedding, created_at, turn_count
            FROM conversations
            ORDER BY id DESC
            LIMIT 200
            """
        )
        if not rows:
            return []

        q = self._embed(query)
        scored = []
        for row in rows:
            emb_blob = row.get("embedding")
            if not emb_blob:
                continue
            v = np.frombuffer(emb_blob, dtype=np.float32)
            if v.size == 0:
                continue
            sim = float(np.dot(q[: min(len(q), len(v))], v[: min(len(q), len(v))]))
            scored.append((sim, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[dict[str, Any]] = []
        for sim, row in scored[:top_k]:
            out.append(
                {
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "summary": row["summary"],
                    "key_topics": json.loads(row.get("key_topics") or "[]"),
                    "similarity": sim,
                    "created_at": row["created_at"],
                    "turn_count": row["turn_count"],
                }
            )
        return out

    async def get_user_preferences(self) -> dict[str, str]:
        db = await get_db()
        rows = await db.fetch_all("SELECT key, value FROM user_preferences")
        return {row["key"]: row["value"] for row in rows}

    async def learn_preference(
        self, key: str, value: str, source: str = "inferred"
    ) -> None:
        db = await get_db()
        await db.execute(
            """
            INSERT INTO user_preferences(key, value, learned_at, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
              value=excluded.value,
              learned_at=excluded.learned_at,
              source=excluded.source
            """,
            (key, value, datetime.now(UTC).isoformat(), source),
        )
        await db.commit()
