from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from core.logger import get_logger
from os_bridge.platform_detect import detect_platform

from plugins.base import JarvisPlugin, PluginResult

logger = get_logger(__name__)


class SystemControlPlugin(JarvisPlugin):
    name = "system_control"
    description = "Control system settings like volume, brightness, and power"
    intents = ["system-control"]

    ACTIONS: dict[str, str] = {
        "volume_up": "Increase volume by 10%",
        "volume_down": "Decrease volume by 10%",
        "volume_set": "Set volume to specific level",
        "volume_mute": "Toggle mute",
        "brightness_up": "Increase brightness",
        "brightness_down": "Decrease brightness",
        "brightness_set": "Set brightness to specific level",
        "lock_screen": "Lock the computer",
        "sleep": "Put computer to sleep",
        "screenshot": "Take a screenshot",
    }

    async def execute(
        self, intent: dict[str, Any], context: dict[str, Any]
    ) -> PluginResult:
        params = (
            intent.get("params", {}) if isinstance(intent.get("params"), dict) else {}
        )
        action = str(params.get("action") or "").strip()
        value = params.get("value")

        if not action:
            return PluginResult(
                success=False,
                output="Missing system control action.",
                error="missing_action",
            )

        if action.startswith("volume"):
            return await self._control_volume(action, value)
        if action.startswith("brightness"):
            return await self._control_brightness(action, value)
        if action == "lock_screen":
            return await self._lock_screen()
        if action == "sleep":
            return await self._sleep_system()
        if action == "screenshot":
            return await self._take_screenshot()

        return PluginResult(
            success=False,
            output=f"Unsupported system action: {action}",
            error="unsupported_action",
        )

    async def _control_volume(self, action: str, value: Any) -> PluginResult:
        platform_info = detect_platform()
        try:
            await asyncio.to_thread(
                self._volume_command, platform_info.os, action, value
            )
            message = f"Volume action completed: {action}."
            if action == "volume_set":
                message = f"Set volume to {int(value)}%."
            return PluginResult(
                success=True, output=message, data={"action": action, "value": value}
            )
        except Exception as exc:
            return PluginResult(
                success=False,
                output="Volume control failed.",
                error=str(exc),
                data={"action": action},
            )

    def _volume_command(self, os_name: str, action: str, value: Any) -> None:
        if os_name == "linux":
            self._run_first_available(
                [
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"]
                    if action == "volume_up"
                    else None,
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-10%"]
                    if action == "volume_down"
                    else None,
                    ["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{int(value)}%"]
                    if action == "volume_set"
                    else None,
                    ["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"]
                    if action == "volume_mute"
                    else None,
                    ["amixer", "-D", "pulse", "sset", "Master", "5%+"]
                    if action == "volume_up"
                    else None,
                    ["amixer", "-D", "pulse", "sset", "Master", "5%-"]
                    if action == "volume_down"
                    else None,
                    ["amixer", "-D", "pulse", "sset", "Master", f"{int(value)}%"]
                    if action == "volume_set"
                    else None,
                    ["amixer", "-D", "pulse", "sset", "Master", "toggle"]
                    if action == "volume_mute"
                    else None,
                ]
            )
            return

        if os_name == "windows":
            raise RuntimeError("Windows volume control integration pending")
        if os_name == "macos":
            if action == "volume_set":
                self._run(["osascript", "-e", f"set volume output volume {int(value)}"])
                return
            if action == "volume_up":
                self._run(
                    [
                        "osascript",
                        "-e",
                        "set volume output volume ((output volume of (get volume settings)) + 10)",
                    ]
                )
                return
            if action == "volume_down":
                self._run(
                    [
                        "osascript",
                        "-e",
                        "set volume output volume ((output volume of (get volume settings)) - 10)",
                    ]
                )
                return
            if action == "volume_mute":
                self._run(["osascript", "-e", "set volume with output muted"])
                return

        raise RuntimeError("Unsupported OS for volume control")

    async def _control_brightness(self, action: str, value: Any) -> PluginResult:
        platform_info = detect_platform()
        try:
            await asyncio.to_thread(
                self._brightness_command, platform_info.os, action, value
            )
            return PluginResult(
                success=True,
                output=f"Brightness action completed: {action}.",
                data={"action": action, "value": value},
            )
        except Exception as exc:
            return PluginResult(
                success=False,
                output="Brightness control failed.",
                error=str(exc),
                data={"action": action},
            )

    def _brightness_command(self, os_name: str, action: str, value: Any) -> None:
        if os_name == "linux":
            self._run_first_available(
                [
                    ["brightnessctl", "set", "+10%"]
                    if action == "brightness_up"
                    else None,
                    ["brightnessctl", "set", "10%-"]
                    if action == "brightness_down"
                    else None,
                    ["brightnessctl", "set", f"{int(value)}%"]
                    if action == "brightness_set"
                    else None,
                    [
                        "xrandr",
                        "--output",
                        "eDP-1",
                        "--brightness",
                        str(max(0.1, min(1.0, int(value) / 100.0))),
                    ]
                    if action == "brightness_set"
                    else None,
                ]
            )
            return

        if os_name == "windows":
            try:
                import screen_brightness_control as sbc
            except Exception as exc:
                raise RuntimeError(
                    f"screen-brightness-control unavailable: {exc}"
                ) from exc

            current = sbc.get_brightness(display=0)
            level = (
                current[0] if isinstance(current, list) and current else int(current)
            )
            if action == "brightness_up":
                sbc.set_brightness(min(100, level + 10))
            elif action == "brightness_down":
                sbc.set_brightness(max(1, level - 10))
            elif action == "brightness_set":
                sbc.set_brightness(int(value))
            return

        if os_name == "macos":
            if action != "brightness_set":
                raise RuntimeError(
                    "macOS brightness only supports brightness_set in current phase"
                )
            raise RuntimeError("macOS brightness CLI not configured")

        raise RuntimeError("Unsupported OS for brightness control")

    async def _lock_screen(self) -> PluginResult:
        platform_info = detect_platform()
        try:
            await asyncio.to_thread(self._lock_command, platform_info.os)
            return PluginResult(success=True, output="Locking the screen now.")
        except Exception as exc:
            return PluginResult(
                success=False, output="Failed to lock the screen.", error=str(exc)
            )

    def _lock_command(self, os_name: str) -> None:
        if os_name == "linux":
            self._run_first_available(
                [
                    ["loginctl", "lock-session"],
                    ["xdg-screensaver", "lock"],
                    ["gnome-screensaver-command", "--lock"],
                ]
            )
            return
        if os_name == "windows":
            self._run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return
        if os_name == "macos":
            self._run(["pmset", "displaysleepnow"])
            return
        raise RuntimeError("Unsupported OS for lock screen")

    async def _sleep_system(self) -> PluginResult:
        platform_info = detect_platform()
        try:
            await asyncio.to_thread(self._sleep_command, platform_info.os)
            return PluginResult(success=True, output="Putting system to sleep.")
        except Exception as exc:
            return PluginResult(
                success=False, output="Failed to put system to sleep.", error=str(exc)
            )

    def _sleep_command(self, os_name: str) -> None:
        if os_name == "linux":
            self._run_first_available(
                [["systemctl", "suspend"], ["loginctl", "suspend"]]
            )
            return
        if os_name == "windows":
            self._run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return
        if os_name == "macos":
            self._run(["pmset", "sleepnow"])
            return
        raise RuntimeError("Unsupported OS for sleep")

    async def _take_screenshot(self) -> PluginResult:
        platform_info = detect_platform()
        out_dir = Path.home() / "Pictures" / "jarvis_screenshots"
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"jarvis_{int(asyncio.get_running_loop().time() * 1000)}.png"

        try:
            await asyncio.to_thread(self._screenshot_command, platform_info.os, target)
            return PluginResult(
                success=True, output="Screenshot captured.", data={"path": str(target)}
            )
        except Exception as exc:
            return PluginResult(
                success=False, output="Failed to take screenshot.", error=str(exc)
            )

    def _screenshot_command(self, os_name: str, target: Path) -> None:
        if os_name == "linux":
            self._run_first_available(
                [
                    ["gnome-screenshot", "-f", str(target)],
                    ["scrot", str(target)],
                    ["import", "-window", "root", str(target)],
                ]
            )
            return
        if os_name == "windows":
            ps_cmd = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "Add-Type -AssemblyName System.Drawing; "
                "$bmp = New-Object Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width,"
                "[System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height); "
                "$g=[Drawing.Graphics]::FromImage($bmp); "
                "$g.CopyFromScreen(0,0,0,0,$bmp.Size); "
                f"$bmp.Save('{str(target)}');"
            )
            self._run(["powershell", "-NoProfile", "-Command", ps_cmd])
            return
        if os_name == "macos":
            self._run(["screencapture", str(target)])
            return
        raise RuntimeError("Unsupported OS for screenshot")

    def _run_first_available(self, commands: list[list[str] | None]) -> None:
        errors: list[str] = []
        for cmd in commands:
            if not cmd:
                continue
            if shutil.which(cmd[0]) is None:
                continue
            try:
                self._run(cmd)
                return
            except Exception as exc:
                errors.append(str(exc))
        raise RuntimeError(
            "No suitable command available" if not errors else "; ".join(errors)
        )

    def _run(self, command: list[str]) -> None:
        subprocess.run(
            command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def get_capabilities(self) -> list[dict[str, Any]]:
        return [
            {"intent": "system-control", "description": f"{k}: {v}"}
            for k, v in self.ACTIONS.items()
        ]
