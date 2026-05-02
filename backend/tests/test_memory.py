from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import pytest
from brain.memory.context_builder import ContextBuilder
from brain.memory.long_term import LongTermMemory
from brain.memory.short_term import ShortTermMemory
from infrastructure.database.db import Database

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.asyncio
async def test_short_term_add_turn() -> None:
    memory = ShortTermMemory(max_turns=20)
    await memory.add_turn("user", "hello", {"tokens": 2})
    history = await memory.get_history(10)
    assert len(history) == 1
    assert history[0]["content"] == "hello"


@pytest.mark.asyncio
async def test_short_term_max_turns() -> None:
    memory = ShortTermMemory(max_turns=2)
    await memory.add_turn("user", "one", {"tokens": 1})
    await memory.add_turn("assistant", "two", {"tokens": 1})
    await memory.add_turn("user", "three", {"tokens": 1})
    history = await memory.get_history(10)
    assert len(history) == 2
    assert history[0]["content"] == "two"


@pytest.mark.asyncio
async def test_short_term_token_budget() -> None:
    memory = ShortTermMemory(max_turns=10)
    await memory.add_turn("user", "a", {"tokens": 5})
    await memory.add_turn("assistant", "b", {"tokens": 5})
    await memory.trim_to_budget(5)
    token_count = await memory.get_token_count()
    assert token_count <= 5


@pytest.mark.asyncio
async def test_long_term_store_and_search(tmp_path: Path) -> None:
    from typing import Any

    from infrastructure.database import db as db_module

    cast(Any, db_module).db = Database(db_path=tmp_path / "memory.db")
    await cast(Any, db_module).db.initialize()

    long_term = LongTermMemory()
    await long_term.store_summary(
        "s1", "User asked about python and vscode", ["python", "vscode"], turn_count=4
    )

    results = await long_term.search("vscode", top_k=1)
    assert results
    assert "summary" in results[0]


@pytest.mark.asyncio
async def test_context_builder() -> None:
    short_term = ShortTermMemory(max_turns=20)
    await short_term.add_turn("user", "Open VS Code", {"tokens": 4})
    await short_term.add_turn("assistant", "Opening VS Code", {"tokens": 4})

    class DummyLongTerm:
        async def get_user_preferences(self) -> dict[str, Any]:
            return {"preferred_editor": "vscode"}

        async def search(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
            return [{"summary": "User prefers VS Code for coding."}]

    builder = ContextBuilder(
        short_term_memory=short_term,
        long_term_memory=DummyLongTerm(),
        token_budget=4000,
    )
    messages = await builder.build_context("Open terminal")
    assert messages[0]["role"] == "system"
    assert any(
        m["role"] == "user" and "Open terminal" in m["content"] for m in messages
    )
