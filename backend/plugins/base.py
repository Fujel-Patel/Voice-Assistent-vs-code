from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PluginResult:
    """Standardized return from plugin.execute()."""

    success: bool
    output: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.output,
            "data": self.data,
            "error": self.error,
        }


class JarvisPlugin(abc.ABC):
    """Base class for all Jarvis plugins."""

    name: str = ""
    description: str = ""
    intents: list[str] = []
    version: str = "1.0"
    enabled: bool = True

    @abc.abstractmethod
    async def execute(self, intent: dict, context: dict) -> PluginResult | dict[str, Any]:
        raise NotImplementedError

    async def can_execute(self, intent: dict) -> bool:
        intent_type = intent.get("type") or intent.get("intent")
        return intent_type in self.intents

    def get_capabilities(self) -> list[dict[str, Any]]:
        if not self.intents:
            return []
        return [
            {
                "plugin": self.name,
                "intent": intent,
                "description": self.description or f"Handles '{intent}' requests",
            }
            for intent in self.intents
        ]

    def __repr__(self) -> str:
        return f"<Plugin name={self.name} intents={self.intents} enabled={self.enabled}>"
