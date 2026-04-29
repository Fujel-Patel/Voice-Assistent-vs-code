from __future__ import annotations

from enum import StrEnum
from typing import Any


class AccessLevel(StrEnum):
    FULL = "full"
    LIMITED = "limited"
    BLOCKED = "blocked"


class AccessController:
    PERMISSION_MATRIX: dict[str, dict[AccessLevel, bool]] = {
        "conversation": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: True,
            AccessLevel.BLOCKED: False,
        },
        "web-search": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: True,
            AccessLevel.BLOCKED: False,
        },
        "screen-read": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: True,
            AccessLevel.BLOCKED: False,
        },
        "open-app": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: False,
            AccessLevel.BLOCKED: False,
        },
        "close-app": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: False,
            AccessLevel.BLOCKED: False,
        },
        "system-control": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: False,
            AccessLevel.BLOCKED: False,
        },
        "file-operation": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: False,
            AccessLevel.BLOCKED: False,
        },
        "clipboard": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: False,
            AccessLevel.BLOCKED: False,
        },
        "reminder": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: False,
            AccessLevel.BLOCKED: False,
        },
        "unknown": {
            AccessLevel.FULL: True,
            AccessLevel.LIMITED: True,
            AccessLevel.BLOCKED: False,
        },
    }

    SENSITIVE_INTENTS = {
        "open-app",
        "close-app",
        "system-control",
        "file-operation",
        "clipboard",
        "reminder",
    }

    def __init__(self, pin_code: str = "1234") -> None:
        self._pin_code = str(pin_code)

    async def check_access(
        self, intent_data: dict[str, Any], auth_result: dict[str, Any] | None
    ) -> bool:
        intent = self._canonical_intent(str(intent_data.get("intent", "unknown")))
        level = self.resolve_level(auth_result)
        rules = self.PERMISSION_MATRIX.get(intent, self.PERMISSION_MATRIX["unknown"])
        return bool(rules.get(level, False))

    def resolve_level(self, auth_result: dict[str, Any] | None) -> AccessLevel:
        if auth_result is None:
            return AccessLevel.LIMITED
        if auth_result.get("blocked"):
            return AccessLevel.BLOCKED
        return AccessLevel.FULL if auth_result.get("verified") else AccessLevel.LIMITED

    def denial_message(self) -> str:
        return (
            "I'm sorry, I can't perform that action without voice verification. "
            "Would you like to verify your identity?"
        )

    def is_sensitive_intent(self, intent: str) -> bool:
        return self._canonical_intent(intent) in self.SENSITIVE_INTENTS

    def verify_pin(self, pin: str) -> bool:
        return str(pin) == self._pin_code

    def _canonical_intent(self, intent: str) -> str:
        normalized = (intent or "unknown").strip().lower().replace("_", "-")

        aliases = {
            "general": "conversation",
            "chat": "conversation",
            "web_search": "web-search",
            "web search": "web-search",
            "search": "web-search",
            "screen_read": "screen-read",
            "screen-read": "screen-read",
            "openapp": "open-app",
            "closeapp": "close-app",
            "system": "system-control",
            "system-control": "system-control",
            "file": "file-operation",
            "file-manager": "file-operation",
            "clipboard-read": "clipboard",
            "clipboard-write": "clipboard",
            "schedule": "reminder",
        }

        return aliases.get(normalized, normalized)
