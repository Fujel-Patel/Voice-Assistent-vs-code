from __future__ import annotations

import asyncio


class AudioQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def enqueue(self, audio_chunk: bytes) -> None:
        await self._queue.put(audio_chunk)

    async def dequeue(self, timeout: float | None = None) -> bytes | None:
        try:
            if timeout is None:
                return await self._queue.get()
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    async def clear(self) -> None:
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    def empty(self) -> bool:
        return self._queue.empty()
