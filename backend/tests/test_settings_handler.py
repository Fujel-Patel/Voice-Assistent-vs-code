from __future__ import annotations

from typing import Any

import api.settings_handler as settings_module
import pytest
from api.settings_handler import SettingsHandler


@pytest.mark.asyncio
async def test_get_settings_returns_payload(mocker: Any) -> None:
    mocker.patch.object(settings_module, "get_config_dict", return_value={})
    handler = SettingsHandler()

    result = await handler.handle("get_settings", {})

    assert result["type"] == "settings_response"
    assert result["payload"]["ok"] is True
    assert "settings" in result["payload"]
    assert "system_info" in result["payload"]


@pytest.mark.asyncio
async def test_update_setting_calls_save_setting(mocker: Any) -> None:
    mocker.patch.object(settings_module, "get_config_dict", return_value={})
    save_setting = mocker.patch.object(settings_module, "save_setting")
    handler = SettingsHandler()

    result = await handler.handle("update_setting", {"key": "tts.volume", "value": 0.7})

    save_setting.assert_called_once_with("tts.volume", 0.7)
    assert result["type"] == "settings_updated"
    assert result["payload"]["ok"] is True


@pytest.mark.asyncio
async def test_update_setting_rejects_invalid_value(mocker: Any) -> None:
    mocker.patch.object(settings_module, "get_config_dict", return_value={})
    save_setting = mocker.patch.object(settings_module, "save_setting")
    handler = SettingsHandler()

    result = await handler.handle("update_setting", {"key": "tts.volume", "value": 2.0})

    save_setting.assert_not_called()
    assert result["type"] == "settings_response"
    assert result["payload"]["ok"] is False
