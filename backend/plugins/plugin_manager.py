from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import Any

from core.logger import get_logger

from plugins.base import JarvisPlugin, PluginResult

logger = get_logger(__name__)


class PluginManager:
    """Discovers, loads, and manages plugins."""

    def __init__(self) -> None:
        self.plugins_by_name: dict[str, JarvisPlugin] = {}
        self.plugins: dict[str, JarvisPlugin] = {}

    def register(self, plugin: JarvisPlugin) -> None:
        if not plugin.name:
            raise ValueError("Plugin name cannot be empty")
        if plugin.name in self.plugins_by_name:
            raise ValueError(f"Plugin '{plugin.name}' already registered")

        self.plugins_by_name[plugin.name] = plugin
        for intent in plugin.intents:
            self.plugins[intent] = plugin

        logger.info(f"Plugin registered: {plugin.name} ({len(plugin.intents)} intents)")
        logger.debug(f"Plugin intents for {plugin.name}: {plugin.intents}")

    def discover_plugins(self) -> list[str]:
        discovered: list[str] = []
        package = importlib.import_module("plugins")

        for module_info in pkgutil.iter_modules(package.__path__):
            name = module_info.name
            if name.startswith("_") or name in {"base", "plugin_manager"}:
                continue

            module_name = f"plugins.{name}"
            try:
                module = importlib.import_module(module_name)
            except Exception as exc:
                logger.warning(f"Skipping plugin module {module_name}: {exc}")
                continue

            for _, cls in inspect.getmembers(module, inspect.isclass):
                if cls is JarvisPlugin or not issubclass(cls, JarvisPlugin):
                    continue
                if cls.__module__ != module.__name__:
                    continue

                try:
                    plugin = cls()
                    self.register(plugin)
                    discovered.append(plugin.name)
                except Exception as exc:
                    logger.warning(
                        f"Failed to initialize plugin class {cls.__name__}: {exc}"
                    )

        return discovered

    async def execute(
        self, intent_data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        intent_type = intent_data.get("type") or intent_data.get("intent")
        if not intent_type:
            return {"success": False, "message": "Missing intent type"}

        plugin = self.plugins.get(intent_type)
        if not plugin or not plugin.enabled:
            return {"success": False, "message": f"No handler for {intent_type}"}

        if not await plugin.can_execute(intent_data):
            return {"success": False, "message": f"Plugin cannot execute {intent_type}"}

        result = await plugin.execute(intent_data, context)
        if isinstance(result, PluginResult):
            payload = result.to_dict()
        elif isinstance(result, dict):
            payload = result
        else:
            payload = {
                "success": False,
                "message": "Plugin returned unsupported result",
                "error": "invalid_plugin_result",
            }

        payload.setdefault("success", False)
        payload.setdefault("message", "")
        payload.setdefault("data", {})
        return payload

    def get_all_capabilities(self) -> str:
        lines: list[str] = []
        for plugin in self.plugins_by_name.values():
            if not plugin.enabled:
                continue
            lines.append(f"- {plugin.name}: {plugin.description or 'No description'}")
            for capability in plugin.get_capabilities():
                intent = capability.get("intent", "")
                desc = capability.get("description", "")
                lines.append(f"  - {intent}: {desc}")
        return "\n".join(lines).strip()
