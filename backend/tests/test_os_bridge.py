from __future__ import annotations

from os_bridge.platform_detect import detect_platform
from plugins.system_control import SystemControlPlugin


def test_platform_detection() -> None:
    info = detect_platform()
    payload = info.to_dict()

    assert payload["os"] in {"linux", "windows", "macos"}
    assert isinstance(payload["os_version"], str)
    assert isinstance(payload["available_tools"], list)


def test_available_tools_type() -> None:
    info = detect_platform()
    assert all(isinstance(tool, str) for tool in info.available_tools)


from typing import Any


def test_linux_commands(mocker: Any) -> None:
    plugin = SystemControlPlugin()
    run = mocker.patch.object(plugin, "_run")
    mocker.patch("plugins.system_control.shutil.which", return_value="/usr/bin/pactl")

    plugin._volume_command("linux", "volume_up", None)

    run.assert_called_once_with(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+10%"])
