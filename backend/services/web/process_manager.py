from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ProcessManager:
    """Manage backend child processes for service/startup orchestration."""

    command: list[str]
    cwd: str | Path
    max_restarts: int = 3
    restart_delay_seconds: float = 2.0

    _process: asyncio.subprocess.Process | None = field(default=None, init=False)
    _restart_count: int = field(default=0, init=False)

    async def start(self) -> int:
        if self._process and self._process.returncode is None:
            return self._process.pid or -1

        self._process = await asyncio.create_subprocess_exec(
            *self.command,
            cwd=str(self.cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._restart_count = 0
        logger.info(
            f"Started process pid={self._process.pid} cmd={' '.join(self.command)}"
        )
        return self._process.pid or -1

    async def restart(self) -> int:
        await self.stop()
        return await self.start()

    async def monitor(self) -> None:
        """Restart the process on crash up to max_restarts."""
        while self._process is not None:
            code = await self._process.wait()
            if code == 0:
                logger.info("Managed process exited cleanly")
                return

            self._restart_count += 1
            if self._restart_count > self.max_restarts:
                logger.error("Managed process restart limit reached")
                return

            logger.warning(
                f"Managed process crashed with code={code}. "
                f"Restarting {self._restart_count}/{self.max_restarts}"
            )
            await asyncio.sleep(self.restart_delay_seconds)
            self._process = await asyncio.create_subprocess_exec(
                *self.command,
                cwd=str(self.cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    async def stop(self) -> None:
        if self._process is None:
            return
        if self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=8.0)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
        logger.info("Managed process stopped")
        self._process = None

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None
