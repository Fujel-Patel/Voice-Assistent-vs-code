from __future__ import annotations

import asyncio
from enum import Enum
from typing import Awaitable, Callable

from core.event_bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)


class VoiceState(str, Enum):
    IDLE = "idle"
    WAKE_DETECTED = "wake_detected"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    VERIFYING = "verifying"
    THINKING = "thinking"
    SPEAKING = "speaking"


VALID_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
    VoiceState.IDLE: {VoiceState.WAKE_DETECTED, VoiceState.THINKING},
    VoiceState.WAKE_DETECTED: {VoiceState.LISTENING, VoiceState.IDLE},
    VoiceState.LISTENING: {VoiceState.TRANSCRIBING, VoiceState.IDLE},
    VoiceState.TRANSCRIBING: {VoiceState.VERIFYING, VoiceState.THINKING, VoiceState.IDLE},
    VoiceState.VERIFYING: {VoiceState.THINKING, VoiceState.IDLE},
    VoiceState.THINKING: {VoiceState.VERIFYING, VoiceState.SPEAKING, VoiceState.IDLE},
    VoiceState.SPEAKING: {VoiceState.IDLE, VoiceState.LISTENING},
}


StateBroadcast = Callable[[dict], Awaitable[None]]


class VoicePipeline:
    def __init__(self, event_bus: EventBus, state_broadcaster: StateBroadcast | None = None) -> None:
        self._event_bus = event_bus
        self._state_broadcaster = state_broadcaster
        self.state = VoiceState.IDLE
        self._lock = asyncio.Lock()

    async def transition(self, new_state: VoiceState) -> None:
        async with self._lock:
            await self._transition_locked(new_state)

    async def transition_if_state(
        self,
        expected_state: VoiceState | set[VoiceState],
        new_state: VoiceState,
    ) -> bool:
        expected_states = expected_state if isinstance(expected_state, set) else {expected_state}

        async with self._lock:
            if self.state not in expected_states:
                return False

            await self._transition_locked(new_state)
            return True

    async def _transition_locked(self, new_state: VoiceState) -> None:
        if new_state == self.state:
            return

        allowed = VALID_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise ValueError(
                f"Invalid transition: {self.state.value} -> {new_state.value}. "
                f"Allowed: {[s.value for s in sorted(allowed, key=lambda x: x.value)]}"
            )

        previous_state = self.state
        self.state = new_state
        payload = {
            "state": new_state.value,
            "previous_state": previous_state.value,
        }

        await self._event_bus.publish("voice_state_change", payload)
        if self._state_broadcaster is not None:
            await self._state_broadcaster(payload)

        logger.debug(f"Voice state transition: {previous_state.value} -> {new_state.value}")

    async def handle_interrupt(self) -> None:
        if self.state == VoiceState.SPEAKING:
            await self._event_bus.publish("tts_stop_requested", {})
            await self.transition(VoiceState.LISTENING)
            return

        if self.state == VoiceState.TRANSCRIBING:
            logger.info("Interrupt ignored while transcribing")
            return

        if self.state == VoiceState.IDLE:
            await self.transition(VoiceState.WAKE_DETECTED)
            await self.transition(VoiceState.LISTENING)

    async def reset(self) -> None:
        async with self._lock:
            previous = self.state
            self.state = VoiceState.IDLE
            payload = {
                "state": VoiceState.IDLE.value,
                "previous_state": previous.value,
            }
            await self._event_bus.publish("voice_state_change", payload)
            if self._state_broadcaster is not None:
                await self._state_broadcaster(payload)
