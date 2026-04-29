"""
Jarvis Core — Internal Event Bus (Pub/Sub)
==========================================
A lightweight async pub/sub system for internal communication
between backend modules (voice → brain → TTS → WebSocket).

Architecture review recommendation: Modules should communicate
via events, not direct function calls, to avoid tight coupling.

Usage:
    from core.event_bus import event_bus

    # Subscribe
    async def on_transcription(payload: dict):
        print(payload["text"])

    event_bus.subscribe("transcription.ready", on_transcription)

    # Publish
    await event_bus.publish("transcription.ready", {"text": "Open Chrome"})
"""

import asyncio
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

Handler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    """
    Async publish/subscribe event bus.
    All handlers are called concurrently via asyncio.gather.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._wildcard_subscribers: list[Handler] = []

    def subscribe(self, event: str, handler: Handler) -> None:
        """
        Subscribe to a specific event type.

        Args:
            event: Event name, e.g. "voice.transcription_ready"
            handler: Async callable that receives the event payload dict.
        """
        self._subscribers[event].append(handler)
        logger.debug(f"Subscribed to '{event}': {handler.__name__}")

    def subscribe_all(self, handler: Handler) -> None:
        """Subscribe to ALL events (useful for logging, debugging)."""
        self._wildcard_subscribers.append(handler)

    def unsubscribe(self, event: str, handler: Handler) -> None:
        """Remove a handler from an event."""
        if handler in self._subscribers[event]:
            self._subscribers[event].remove(handler)

    async def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """
        Publish an event to all subscribers.
        All handlers are called concurrently.

        Args:
            event: Event name.
            payload: Data to pass to handlers.
        """
        payload = payload or {}
        handlers = self._subscribers.get(event, []) + self._wildcard_subscribers

        if not handlers:
            logger.debug(f"No subscribers for event '{event}'")
            return

        logger.debug(f"Publishing '{event}' to {len(handlers)} handler(s)")

        results = await asyncio.gather(
            *[handler(payload) for handler in handlers],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Event handler error for '{event}' "
                    f"[handler={handlers[i].__name__}]: {result}"
                )

    def clear(self) -> None:
        """Remove all subscribers (useful for testing)."""
        self._subscribers.clear()
        self._wildcard_subscribers.clear()


# ── Jarvis standard event names ──────────────────────────
# These mirror the IPC protocol events in shared/ipc_protocol.json


class JarvisEvents:
    """Centralized event name constants to avoid typos."""

    # Voice pipeline
    WAKE_WORD_DETECTED = "voice.wake_word_detected"
    LISTENING_STARTED = "voice.listening_started"
    LISTENING_STOPPED = "voice.listening_stopped"
    TRANSCRIPTION_READY = "voice.transcription_ready"
    TRANSCRIPTION_FAILED = "voice.transcription_failed"

    # AI brain
    INTENT_CLASSIFIED = "brain.intent_classified"
    CLAUDE_RESPONSE_STARTED = "brain.claude_response_started"
    CLAUDE_RESPONSE_CHUNK = "brain.claude_response_chunk"
    CLAUDE_RESPONSE_DONE = "brain.claude_response_done"

    # TTS
    TTS_STARTED = "tts.started"
    TTS_CHUNK_READY = "tts.chunk_ready"
    TTS_DONE = "tts.done"
    TTS_INTERRUPTED = "tts.interrupted"

    # OS control
    OS_COMMAND_EXECUTED = "os.command_executed"
    OS_COMMAND_FAILED = "os.command_failed"

    # System
    HEALTH_STATUS_CHANGED = "system.health_changed"
    CONFIG_UPDATED = "system.config_updated"
    ERROR_OCCURRED = "system.error"


# Module-level singleton (imported everywhere)
event_bus = EventBus()
