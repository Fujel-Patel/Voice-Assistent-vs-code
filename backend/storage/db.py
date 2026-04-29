from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import aiosqlite
from core.logger import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(
        self, db_path: str | Path = Path(__file__).parent.parent / "data" / "jarvis.db"
    ) -> None:
        self.db_path = Path(db_path)
        self._conn: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:
            if self._conn is not None:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = await aiosqlite.connect(str(self.db_path))
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA journal_mode=WAL")
            await self._conn.execute("PRAGMA synchronous=NORMAL")
            await self._conn.execute("PRAGMA temp_store=MEMORY")
            await self._conn.execute("PRAGMA foreign_keys=ON")
            await self._run_migrations()
            logger.info(f"Database initialized at {self.db_path}")

    async def _run_migrations(self) -> None:
        if self._conn is None:
            return
        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            return

        files = sorted(p for p in migrations_dir.glob("*.sql"))
        for file_path in files:
            sql = file_path.read_text(encoding="utf-8")
            await self._conn.executescript(sql)
        await self._conn.commit()

    async def execute(
        self, query: str, params: tuple[Any, ...] | list[Any] | None = None
    ) -> aiosqlite.Cursor:
        if self._conn is None:
            await self.initialize()
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        return await self._conn.execute(query, tuple(params or ()))

    async def fetch_all(
        self, query: str, params: tuple[Any, ...] | list[Any] | None = None
    ) -> list[dict[str, Any]]:
        if self._conn is None:
            await self.initialize()
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        async with self._conn.execute(query, tuple(params or ())) as cur:
            rows = await cur.fetchall()
            return [dict(row) for row in rows]

    async def commit(self) -> None:
        if self._conn is None:
            await self.initialize()
        if self._conn is None:
            raise RuntimeError("Database connection not initialized")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


db = Database()


async def get_db() -> Database:
    await db.initialize()
    return db
