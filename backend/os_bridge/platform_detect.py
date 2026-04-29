from __future__ import annotations

import os
import platform
import shutil
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PlatformInfo:
    os: str
    os_version: str
    desktop: str
    display_server: str
    available_tools: list[str]
    package_managers: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _detect_desktop() -> str:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION")
    if desktop:
        return desktop
    if platform.system().lower() == "windows":
        return "Windows Shell"
    if platform.system().lower() == "darwin":
        return "Aqua"
    return "unknown"


def _detect_display_server() -> str:
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _available_tools_for(current_os: str) -> list[str]:
    tools_map = {
        "linux": [
            "xdotool",
            "wmctrl",
            "pactl",
            "xrandr",
            "loginctl",
            "gnome-screenshot",
            "scrot",
        ],
        "windows": ["powershell", "taskkill", "nircmd"],
        "macos": ["osascript", "pmset", "screencapture"],
    }
    tools = tools_map.get(current_os, [])
    return [name for name in tools if shutil.which(name)]


def _detect_package_managers() -> list[str]:
    managers = [
        "apt",
        "dnf",
        "pacman",
        "zypper",
        "snap",
        "flatpak",
        "brew",
        "winget",
        "choco",
    ]
    return [name for name in managers if shutil.which(name)]


def detect_platform() -> PlatformInfo:
    system = platform.system().lower()
    if system == "darwin":
        os_name = "macos"
    elif system == "windows":
        os_name = "windows"
    else:
        os_name = "linux"

    version = platform.platform()
    desktop = _detect_desktop()
    display_server = _detect_display_server() if os_name == "linux" else "native"

    return PlatformInfo(
        os=os_name,
        os_version=version,
        desktop=desktop,
        display_server=display_server,
        available_tools=_available_tools_for(os_name),
        package_managers=_detect_package_managers(),
    )
