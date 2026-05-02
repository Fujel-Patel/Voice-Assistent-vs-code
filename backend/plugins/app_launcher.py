from __future__ import annotations

import asyncio
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import psutil as _psutil_type
else:
    try:
        import psutil as _psutil_type
    except Exception:  # pragma: no cover - handled gracefully at runtime
        _psutil_type = None  # type: ignore[assignment]

psutil = _psutil_type

from core.logger import get_logger
from os_bridge.platform_detect import detect_platform

from plugins.base import JarvisPlugin, PluginResult

logger = get_logger(__name__)


class AppLauncherPlugin(JarvisPlugin):
    name = "app_launcher"
    description = "Open and close desktop applications"
    intents = ["open-app", "close-app", "list-apps"]

    ALIASES: dict[str, list[str]] = {
        "code": ["vscode", "visual studio code", "vs code", "code"],
        "google-chrome": ["chrome", "google chrome", "chrome browser"],
        "firefox": ["firefox", "mozilla firefox", "firefox browser"],
        "gnome-terminal": ["terminal", "console", "command line", "shell"],
        "nautilus": ["files", "file manager", "explorer", "nautilus"],
        "spotify": ["spotify", "music player"],
    }

    def _extract_intent_type(self, intent: dict[str, Any]) -> str:
        return str(intent.get("type") or intent.get("intent") or "")

    def _extract_app_name(self, intent: dict[str, Any]) -> str:
        params = (
            intent.get("params", {}) if isinstance(intent.get("params"), dict) else {}
        )
        return str(
            params.get("app_name")
            or params.get("app")
            or intent.get("app_name")
            or intent.get("app")
            or ""
        ).strip()

    def _normalize(self, value: str) -> str:
        return " ".join(value.lower().replace("_", " ").replace("-", " ").split())

    def resolve_alias(self, app_name: str) -> str:
        if not app_name:
            return ""

        normalized = self._normalize(app_name)
        for canonical, aliases in self.ALIASES.items():
            if normalized == self._normalize(canonical):
                return canonical
            if any(normalized == self._normalize(alias) for alias in aliases):
                return canonical
        return app_name

    def _candidate_names(self, command: str) -> list[str]:
        base = Path(command).name.lower()
        result = {base, base.replace(".exe", "")}
        for alias in self.ALIASES.get(command, []):
            result.add(alias.lower())
        return list(result)

    async def execute(
        self, intent: dict[str, Any], context: dict[str, Any]
    ) -> PluginResult:
        intent_type = self._extract_intent_type(intent)
        app_name = self._extract_app_name(intent)

        if intent_type == "open-app":
            return await self._open_app(app_name)
        if intent_type == "close-app":
            return await self._close_app(app_name)
        if intent_type == "list-apps":
            return await self._list_running_apps()

        return PluginResult(
            success=False,
            output=f"Unsupported app action: {intent_type}",
            error="unsupported_action",
        )

    async def _open_app(self, app_name: str) -> PluginResult:
        if not app_name:
            return PluginResult(
                success=False,
                output="Please provide an app name.",
                error="missing_app_name",
            )

        command = self.resolve_alias(app_name)
        running = await asyncio.to_thread(
            self._find_processes, self._candidate_names(command)
        )
        if running:
            return PluginResult(
                success=True,
                output=f"{app_name} is already running.",
                data={
                    "app_name": app_name,
                    "resolved_command": command,
                    "already_running": True,
                },
            )

        platform_info = detect_platform()
        try:
            await asyncio.to_thread(self._launch_command, command, platform_info.os)
            await asyncio.sleep(0.4)
            started = await asyncio.to_thread(
                self._find_processes, self._candidate_names(command)
            )
            return PluginResult(
                success=True,
                output=f"Opening {app_name}.",
                data={
                    "app_name": app_name,
                    "resolved_command": command,
                    "pids": [proc.pid for proc in started],
                },
            )
        except FileNotFoundError:
            return PluginResult(
                success=False,
                output=f"I could not find {app_name} on this system.",
                error="app_not_found",
                data={"app_name": app_name, "resolved_command": command},
            )
        except Exception as exc:
            logger.exception(f"Failed to open app '{app_name}': {exc}")
            return PluginResult(
                success=False,
                output=f"Failed to open {app_name}.",
                error="open_failed",
                data={"app_name": app_name, "reason": str(exc)},
            )

    def _launch_command(self, command: str, os_name: str) -> None:
        if os_name == "windows":
            subprocess.Popen(
                ["cmd", "/c", "start", "", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
        if os_name == "macos":
            subprocess.Popen(
                ["open", "-a", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return

        try:
            subprocess.Popen(
                [command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            subprocess.Popen(
                ["xdg-open", command],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    async def _close_app(self, app_name: str) -> PluginResult:
        if not app_name:
            return PluginResult(
                success=False,
                output="Please provide an app name.",
                error="missing_app_name",
            )

        command = self.resolve_alias(app_name)
        processes = await asyncio.to_thread(
            self._find_processes, self._candidate_names(command)
        )
        if not processes:
            return PluginResult(
                success=False,
                output=f"{app_name} is not running.",
                error="process_not_found",
                data={"app_name": app_name},
            )

        closed_pids: list[int] = []
        forced_pids: list[int] = []

        for proc in processes:
            try:
                proc.terminate()
            except Exception:
                continue

        await asyncio.sleep(1.0)

        for proc in processes:
            if proc.is_running():
                try:
                    proc.kill()
                    forced_pids.append(proc.pid)
                except Exception:
                    continue
            closed_pids.append(proc.pid)

        return PluginResult(
            success=True,
            output=f"Closed {app_name}.",
            data={
                "app_name": app_name,
                "closed_pids": closed_pids,
                "forced_pids": forced_pids,
            },
        )

    async def _list_running_apps(self) -> PluginResult:
        processes = await asyncio.to_thread(self._iter_gui_processes)
        return PluginResult(
            success=True,
            output=f"Found {len(processes)} running apps.",
            data={"apps": processes[:80]},
        )

    def _find_processes(self, candidates: Iterable[str]) -> list[Any]:
        if psutil is None:
            return []

        names = {c.lower() for c in candidates if c}
        matched: list[Any] = []

        for proc in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                pexe = Path(proc.info.get("exe") or "").name.lower()
                cmdline = " ".join(proc.info.get("cmdline") or []).lower()
                if any(
                    token and (token in pname or token in pexe or token in cmdline)
                    for token in names
                ):
                    matched.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return matched

    def _iter_gui_processes(self) -> list[dict[str, Any]]:
        if psutil is None:
            return []

        entries: list[dict[str, Any]] = []
        for proc in psutil.process_iter(["pid", "name", "username", "terminal"]):
            try:
                terminal = proc.info.get("terminal")
                if terminal:
                    continue
                entries.append(
                    {
                        "pid": proc.info.get("pid"),
                        "name": proc.info.get("name") or "unknown",
                        "username": proc.info.get("username") or "unknown",
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return entries

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [
            {
                "intent": "open-app",
                "description": "Launch desktop applications by friendly name",
            },
            {
                "intent": "close-app",
                "description": "Close running applications gracefully",
            },
            {"intent": "list-apps", "description": "List running GUI applications"},
        ]
