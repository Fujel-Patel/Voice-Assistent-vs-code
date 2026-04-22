from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from core.logger import get_logger
from plugins.plugin_manager import PluginManager

logger = get_logger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)
_CODE_FENCE_ANY_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

KNOWN_INTENTS = {
    "open-app",
    "close-app",
    "web-search",
    "system-control",
    "file-operation",
    "screen-read",
    "conversation",
    "reminder",
    "clipboard",
    "unknown",
}


class IntentValidationError(ValueError):
    pass


def validate_intent_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise IntentValidationError("Intent payload must be a dict")

    intent = payload.get("intent")
    response = payload.get("response")
    action = payload.get("action")

    if not isinstance(intent, str) or not intent:
        raise IntentValidationError("Missing or invalid 'intent'")
    if intent not in KNOWN_INTENTS:
        intent = "unknown"
    if not isinstance(response, str):
        raise IntentValidationError("Missing or invalid 'response'")

    if action is not None:
        if not isinstance(action, dict):
            raise IntentValidationError("Field 'action' must be object or null")
        if "type" not in action or "params" not in action:
            raise IntentValidationError("Action must contain 'type' and 'params'")

    return {
        "intent": intent,
        "response": response,
        "action": action,
    }


class IntentClassifier:
    """Backwards-compatible parser for JSON responses from LLM providers."""

    def _normalize_response_text(self, text: str) -> str:
        candidate = (text or "").strip()
        if not candidate:
            return ""

        fenced = _CODE_FENCE_RE.match(candidate)
        if fenced:
            candidate = fenced.group(1).strip()

        # Some providers return nested JSON as string content. Unwrap once or twice.
        for _ in range(2):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                break

            if isinstance(parsed, str):
                candidate = parsed.strip()
                continue

            if isinstance(parsed, dict):
                nested = parsed.get("response") or parsed.get("text") or ""
                nested_text = str(nested).strip()
                if nested_text:
                    candidate = nested_text
                    continue
            break

        return self._improve_readability(candidate)

    def _improve_readability(self, text: str) -> str:
        candidate = str(text or "")
        if not candidate:
            return ""

        # Add a space after punctuation when words are glued (e.g., "Hello,sir" -> "Hello, sir").
        candidate = re.sub(r"([,.;!?])(?=[^\s])", r"\1 ", candidate)

        # Split merged lower->upper boundaries (e.g., "desktopAssistant" -> "desktop Assistant").
        candidate = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", candidate)

        # Fix a few frequent merged phrases from model output.
        candidate = re.sub(r"\bIam\b", "I am", candidate)
        candidate = re.sub(r"\bIam(?=[a-z])", "I am ", candidate)
        candidate = re.sub(r"\bHowmay\b", "How may", candidate)
        candidate = re.sub(r"\bHowcan\b", "How can", candidate)
        candidate = re.sub(r"\bIassist\b", "I assist", candidate)
        candidate = re.sub(r"\bIassistyou\b", "I assist you", candidate)
        candidate = re.sub(r"\bassistyou\b", "assist you", candidate)

        # Collapse accidental repeated whitespace.
        candidate = re.sub(r"\s+", " ", candidate)
        return candidate.strip()

    def _extract_embedded_payload(self, text: str) -> dict[str, Any] | None:
        if not text:
            return None

        fenced_candidates = [m.group(1).strip() for m in _CODE_FENCE_ANY_RE.finditer(text) if m.group(1).strip()]
        for candidate in fenced_candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed

        return None

    def _looks_like_conversation_text(self, text: str) -> bool:
        candidate = (text or "").strip()
        if not candidate:
            return False

        words = re.findall(r"[A-Za-z]{2,}", candidate)
        if len(words) < 3:
            return False

        # Require at least one whitespace separator to avoid treating tokens like
        # "not-json-gibberish" as normal conversation.
        return bool(re.search(r"\s", candidate))

    def parse(self, raw: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw, dict):
            return validate_intent_payload(raw)

        text = (raw or "").strip()
        if not text:
            return {"intent": "unknown", "response": "Could you clarify that?", "action": None}

        fenced = _CODE_FENCE_RE.match(text)
        candidate = fenced.group(1).strip() if fenced else text

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            embedded_payload = self._extract_embedded_payload(text)
            if isinstance(embedded_payload, dict):
                try:
                    validated = validate_intent_payload(embedded_payload)
                    validated["response"] = self._normalize_response_text(validated.get("response", ""))
                    return validated
                except IntentValidationError:
                    response_text = str(embedded_payload.get("response") or embedded_payload.get("text") or "").strip()
                    if response_text:
                        return {
                            "intent": "conversation",
                            "response": self._normalize_response_text(response_text),
                            "action": None,
                        }

            # If provider returned plain text, treat it as a normal conversation reply.
            normalized = self._normalize_response_text(candidate)
            if not self._looks_like_conversation_text(normalized):
                return {"intent": "unknown", "response": "Could you clarify that?", "action": None}

            return {
                "intent": "conversation",
                "response": normalized,
                "action": None,
            }

        try:
            validated = validate_intent_payload(payload)
            validated["response"] = self._normalize_response_text(validated.get("response", ""))
            return validated
        except IntentValidationError:
            if isinstance(payload, dict):
                response_text = str(payload.get("response") or payload.get("text") or "").strip()
                if response_text:
                    return {
                        "intent": "conversation",
                        "response": self._normalize_response_text(response_text),
                        "action": None,
                    }

            return {"intent": "unknown", "response": "Could you clarify that?", "action": None}


class IntentRouter:
    def __init__(self, plugin_manager: PluginManager | None = None, context_provider: Callable[[], dict[str, Any]] | None = None) -> None:
        self.handlers: dict[str, Callable[[dict[str, Any] | None], Awaitable[dict[str, Any]]]] = {}
        self.plugin_manager = plugin_manager
        self.context_provider = context_provider or (lambda: {})
        self.register("conversation", self._conversation_handler)
        self.register("unknown", self._unknown_handler)

    def register(
        self,
        intent: str,
        handler: Callable[[dict[str, Any] | None], Awaitable[dict[str, Any]]],
    ) -> None:
        self.handlers[intent] = handler

    async def route(self, intent_data: dict[str, Any]) -> dict[str, Any]:
        validated = validate_intent_payload(intent_data)
        intent = validated["intent"]
        logger.info(f"Intent classified: {intent}")

        action = validated.get("action")
        if action and self.plugin_manager is not None:
            plugin_result = await self.plugin_manager.execute(action, self.context_provider())
            return {
                "status": "ok" if plugin_result.get("success") else "error",
                "message": plugin_result.get("message") or validated["response"],
                "response": validated["response"],
                "intent": intent,
                "action": action,
                "action_result": plugin_result,
            }

        handler = self.handlers.get(intent)
        if handler is None:
            return {
                "status": "no_handler",
                "message": f"No handler for intent '{intent}' yet.",
                "response": validated["response"],
                "intent": intent,
                "action": action,
            }
        result = await handler(action)
        result.setdefault("response", validated["response"])
        result.setdefault("intent", intent)
        result.setdefault("action", action)
        return result

    async def _conversation_handler(self, action: dict[str, Any] | None) -> dict[str, Any]:
        return {"status": "ok", "message": "conversation", "action": action}

    async def _unknown_handler(self, action: dict[str, Any] | None) -> dict[str, Any]:
        return {
            "status": "clarify",
            "message": "I could not determine intent. Please clarify your request.",
            "action": action,
        }
