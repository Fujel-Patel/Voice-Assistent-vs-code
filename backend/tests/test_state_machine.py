from __future__ import annotations

import pytest

from core.event_bus import EventBus
from voice.state_machine import VoicePipeline, VoiceState


@pytest.mark.asyncio
async def test_valid_transitions(event_bus: EventBus):
    pipeline = VoicePipeline(event_bus=event_bus)

    await pipeline.transition(VoiceState.WAKE_DETECTED)
    await pipeline.transition(VoiceState.LISTENING)

    assert pipeline.state == VoiceState.LISTENING


@pytest.mark.asyncio
async def test_invalid_transition(event_bus: EventBus):
    pipeline = VoicePipeline(event_bus=event_bus)

    with pytest.raises(ValueError):
        await pipeline.transition(VoiceState.TRANSCRIBING)


@pytest.mark.asyncio
async def test_transition_if_state_success(event_bus: EventBus):
    pipeline = VoicePipeline(event_bus=event_bus)

    transitioned = await pipeline.transition_if_state(VoiceState.IDLE, VoiceState.THINKING)

    assert transitioned is True
    assert pipeline.state == VoiceState.THINKING


@pytest.mark.asyncio
async def test_transition_if_state_mismatch(event_bus: EventBus):
    pipeline = VoicePipeline(event_bus=event_bus)
    await pipeline.transition(VoiceState.WAKE_DETECTED)

    transitioned = await pipeline.transition_if_state(VoiceState.IDLE, VoiceState.THINKING)

    assert transitioned is False
    assert pipeline.state == VoiceState.WAKE_DETECTED


@pytest.mark.asyncio
async def test_interrupt_while_speaking(event_bus: EventBus):
    pipeline = VoicePipeline(event_bus=event_bus)

    await pipeline.transition(VoiceState.WAKE_DETECTED)
    await pipeline.transition(VoiceState.LISTENING)
    await pipeline.transition(VoiceState.TRANSCRIBING)
    await pipeline.transition(VoiceState.THINKING)
    await pipeline.transition(VoiceState.SPEAKING)

    await pipeline.handle_interrupt()

    assert pipeline.state == VoiceState.LISTENING


@pytest.mark.asyncio
async def test_state_change_event(event_bus: EventBus):
    seen = []

    async def _handler(payload: dict):
        seen.append(payload)

    event_bus.subscribe("voice_state_change", _handler)

    pipeline = VoicePipeline(event_bus=event_bus)
    await pipeline.transition(VoiceState.WAKE_DETECTED)

    assert seen
    assert seen[-1]["state"] == "wake_detected"
    assert seen[-1]["previous_state"] == "idle"
