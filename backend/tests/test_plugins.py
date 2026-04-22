from __future__ import annotations

import pytest

from plugins.app_launcher import AppLauncherPlugin
from plugins.plugin_manager import PluginManager
from plugins.system_control import SystemControlPlugin


def test_plugin_registration() -> None:
    manager = PluginManager()
    discovered = manager.discover_plugins()
    assert "app_launcher" in discovered
    assert "web_search" in discovered
    assert "system_control" in discovered
    assert "screen_reader" in discovered
    assert manager.plugins.get("open-app") is not None
    assert manager.plugins.get("web-search") is not None
    assert manager.plugins.get("system-control") is not None
    assert manager.plugins.get("screen-read") is not None


@pytest.mark.asyncio
async def test_app_launcher_open(mocker) -> None:
    plugin = AppLauncherPlugin()

    launch_mock = mocker.patch.object(plugin, "_launch_command")
    finder = mocker.patch.object(plugin, "_find_processes", side_effect=[[], [mocker.Mock(pid=1234)]])

    result = await plugin.execute(
        {
            "type": "open-app",
            "params": {"app_name": "vs code"},
        },
        context={},
    )

    assert result.success is True
    assert "Opening" in result.output
    launch_mock.assert_called_once()
    assert finder.call_count == 2


@pytest.mark.asyncio
async def test_app_launcher_close(mocker) -> None:
    plugin = AppLauncherPlugin()

    proc = mocker.Mock()
    proc.pid = 999
    proc.is_running.return_value = False

    mocker.patch.object(plugin, "_find_processes", return_value=[proc])

    result = await plugin.execute(
        {
            "type": "close-app",
            "params": {"app_name": "chrome"},
        },
        context={},
    )

    assert result.success is True
    proc.terminate.assert_called_once()


def test_app_alias_resolution() -> None:
    plugin = AppLauncherPlugin()
    assert plugin.resolve_alias("vs code") == "code"


@pytest.mark.asyncio
async def test_volume_control(mocker) -> None:
    plugin = SystemControlPlugin()
    volume_cmd = mocker.patch.object(plugin, "_volume_command")

    result = await plugin.execute(
        {
            "type": "system-control",
            "params": {"action": "volume_set", "value": 50},
        },
        context={},
    )

    assert result.success is True
    volume_cmd.assert_called_once()


@pytest.mark.asyncio
async def test_brightness_control(mocker) -> None:
    plugin = SystemControlPlugin()
    brightness_cmd = mocker.patch.object(plugin, "_brightness_command")

    result = await plugin.execute(
        {
            "type": "system-control",
            "params": {"action": "brightness_set", "value": 60},
        },
        context={},
    )

    assert result.success is True
    brightness_cmd.assert_called_once()
