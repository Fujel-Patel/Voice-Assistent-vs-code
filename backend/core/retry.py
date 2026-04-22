from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions_to_retry: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry async call with exponential backoff."""

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(fn)
        async def wrapper(*args, **kwargs) -> T:
            attempt = 0
            while True:
                try:
                    return await fn(*args, **kwargs)
                except exceptions_to_retry as exc:
                    attempt += 1
                    if attempt > max_retries:
                        raise
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    logger.warning(
                        f"Retrying {fn.__name__} after error: {exc}. "
                        f"attempt={attempt}/{max_retries}, delay={delay:.2f}s"
                    )
                    await asyncio.sleep(delay)

        return wrapper

    return decorator
