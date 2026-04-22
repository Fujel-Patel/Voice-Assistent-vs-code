"""IPC message validation helpers for backend services."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID


REQUIRED_KEYS = {"type", "payload"}
OPTIONAL_KEYS = {"timestamp", "request_id"}


def _is_iso8601(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def validate_message_envelope(message: Any) -> tuple[bool, str | None]:
    """Validate common IPC envelope fields.

    Returns:
        (True, None) on success, (False, reason) on validation failure.
    """
    if not isinstance(message, dict):
        return False, "Message must be an object"

    missing = REQUIRED_KEYS - set(message.keys())
    if missing:
        return False, f"Missing required keys: {', '.join(sorted(missing))}"

    unknown = set(message.keys()) - REQUIRED_KEYS - OPTIONAL_KEYS
    if unknown:
        return False, f"Unknown envelope keys: {', '.join(sorted(unknown))}"

    if not isinstance(message["type"], str) or not message["type"].strip():
        return False, "Field 'type' must be a non-empty string"

    if not isinstance(message["payload"], dict):
        return False, "Field 'payload' must be an object"

    if "timestamp" in message and not _is_iso8601(str(message["timestamp"])):
        return False, "Field 'timestamp' must be ISO-8601"

    if "request_id" in message and not _is_uuid(str(message["request_id"])):
        return False, "Field 'request_id' must be a UUID"

    return True, None
