"""Graceful fallback execution helpers for backend services."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

FallbackStep = Callable[[], Awaitable[Any]]


class FallbackChainError(RuntimeError):
    """Raised when every fallback step fails."""


async def run_fallback_chain(*steps: FallbackStep) -> Any:
    """Run async steps in order and return the first successful result."""
    if not steps:
        raise ValueError("At least one fallback step is required")

    errors: list[Exception] = []
    for step in steps:
        try:
            return await step()
        except Exception as exc:  # pragma: no cover - broad by design
            errors.append(exc)

    details = "; ".join(str(err) for err in errors)
    raise FallbackChainError(f"All fallback steps failed: {details}")
