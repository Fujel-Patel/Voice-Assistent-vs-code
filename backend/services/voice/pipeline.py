from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import numpy as np
from core.logger import get_logger

from services.voice.state_machine import VoiceState

if TYPE_CHECKING:
    from auth.access_control import AccessController
    from auth.liveness import LivenessDetector
    from auth.speaker_verify import SpeakerVerifier
    from brain.intent import IntentRouter
    from brain.memory.short_term import ShortTermMemory
    from core.config import JarvisConfig
    from core.event_bus import EventBus
    from infrastructure.audio.audio_player import AudioPlayer
    from infrastructure.audio.listener import WakeWordDetector
    from infrastructure.audio.recorder import AudioRecorder
    from numpy.typing import NDArray

    from services.brain.agent import ClaudeAgent
    from services.voice.state_machine import VoicePipeline as VoiceStateMachine
    from services.voice.stt_manager import STTManager
    from services.voice.tts import TTSManager

logger = get_logger(__name__)

from typing import TYPE_CHECKING, Protocol


class MessageBuilder(Protocol):
    def __call__(
        self, msg_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]: ...


BroadcastFn = Callable[[dict[str, Any]], Awaitable[None]]
GetAuthResult = Callable[[], dict[str, Any]]
SetAuthResult = Callable[[dict[str, Any]], None]
GetListener = Callable[[], "WakeWordDetector | None"]
GetAlwaysOn = Callable[[], bool]


class VoicePipeline:
    def __init__(
        self,
        *,
        config: JarvisConfig,
        event_bus: EventBus,
        stt: STTManager,
        recorder: AudioRecorder,
        tts_manager: TTSManager,
        audio_player: AudioPlayer,
        state_machine: VoiceStateMachine,
        brain_agent: ClaudeAgent,
        intent_router: IntentRouter,
        access_controller: AccessController,
        liveness_detector: LivenessDetector,
        speaker_verifier: SpeakerVerifier,
        short_term_memory: ShortTermMemory,
        wake_queue: asyncio.Queue[dict[str, Any]],
        stop_event: asyncio.Event,
        broadcast: BroadcastFn,
        message_builder: MessageBuilder,
        get_listener: GetListener,
        get_always_on: GetAlwaysOn,
        get_auth_result: GetAuthResult,
        set_auth_result: SetAuthResult,
    ) -> None:
        self.config = config
        self.event_bus = event_bus
        self.stt = stt
        self.recorder = recorder
        self.tts_manager = tts_manager
        self.audio_player = audio_player
        self.state_machine = state_machine
        self.brain_agent = brain_agent
        self.intent_router = intent_router
        self.access_controller = access_controller
        self.liveness_detector = liveness_detector
        self.speaker_verifier = speaker_verifier
        self.short_term_memory = short_term_memory
        self.wake_queue = wake_queue
        self.stop_event = stop_event
        self.broadcast = broadcast
        self._message = message_builder
        self._get_listener = get_listener
        self._get_always_on = get_always_on
        self._get_auth_result = get_auth_result
        self._set_auth_result = set_auth_result

    async def _voice_loop(self) -> None:
        while not self.stop_event.is_set():
            trigger = await self.wake_queue.get()
            request_id = str(uuid4())
            logger.info(f"Wake trigger received: {trigger}")

            try:
                listener = self._get_listener()
                if listener:
                    listener.pause()

                await self.state_machine.transition(VoiceState.WAKE_DETECTED)
                await self.state_machine.transition(VoiceState.LISTENING)

                async def _on_transcript_chunk(chunk_payload: dict[str, Any]) -> None:
                    await self.broadcast(
                        self._message(
                            msg_type="transcript_chunk",
                            payload={
                                "text": chunk_payload.get("text", ""),
                                "chunk": chunk_payload.get("chunk", ""),
                                "is_final": bool(chunk_payload.get("is_final", False)),
                            },
                            request_id=request_id,
                        )
                    )

                stt_stream = self.stt.open_stream(on_chunk=_on_transcript_chunk)
                recording = await self.recorder.start_recording(
                    on_audio_chunk=stt_stream.process_audio
                )

                listener = self._get_listener()
                if listener:
                    listener.resume()

                if recording is None:
                    logger.warning(
                        "Recording returned None - audio too short or VAD timeout"
                    )
                    await self.state_machine.reset()
                    continue

                if self.state_machine.state != VoiceState.LISTENING:
                    logger.info(
                        "Recording completed after state changed to "
                        f"{self.state_machine.state.value}; dropping stale trigger"
                    )
                    continue

                await self.state_machine.transition(VoiceState.TRANSCRIBING)

                transcript = await stt_stream.finalize()
                logger.info(f"Final transcript: {transcript}")

                await self.broadcast(
                    self._message(
                        msg_type="transcription_result",
                        payload={
                            "text": transcript.get("text", ""),
                            "confidence": transcript.get("confidence", 0.0),
                            "language": transcript.get("language", "unknown"),
                        },
                        request_id=request_id,
                    )
                )

                await self.event_bus.publish("transcription_result", transcript)

                user_text = transcript.get("text", "").strip()
                if user_text:
                    auth_result: dict[str, Any] = {
                        "verified": True,
                        "confidence": 1.0,
                        "mode": "disabled",
                        "threshold_used": 0.0,
                        "pin_required": False,
                    }

                    if self.config.auth.enabled and self.config.auth.mode != "off":
                        await self.state_machine.transition(VoiceState.VERIFYING)
                        audio_float = recording.audio.astype(np.float32) / 32768.0
                        auth_result = await self.speaker_verifier.verify(
                            audio_float,
                            user_id=self.config.auth.default_user_id,
                            sample_rate=recording.sample_rate,
                        )
                        self._set_auth_result(auth_result)
                        await self.broadcast(
                            self._message(
                                msg_type="auth_result",
                                payload=auth_result,
                                request_id=request_id,
                            )
                        )

                    await self.state_machine.transition(VoiceState.THINKING)
                    await self.short_term_memory.add_turn(
                        "user",
                        user_text,
                        metadata={"tokens": max(1, len(user_text) // 4)},
                    )

                    final_chunk_payload: dict[str, Any] | None = None
                    collected_chunks: list[str] = []
                    tts_text_queue: asyncio.Queue[str | None] = asyncio.Queue()
                    streaming_was_attempted = False
                    streaming_succeeded = False

                    async def _tts_text_iter() -> AsyncIterator[str]:
                        while True:
                            item = await tts_text_queue.get()
                            if item is None:
                                break
                            yield item

                    tts_playback_task: asyncio.Task[None] | None = None
                    if self.config.brain.stream_chunks:
                        streaming_was_attempted = True
                        async for event in self.brain_agent.stream_response(
                            user_text, {"request_id": request_id}
                        ):
                            if event.get("type") == "assistant_response_chunk":
                                payload = event.get("payload", {})
                                if payload.get("is_final"):
                                    final_chunk_payload = payload
                                else:
                                    text_chunk = payload.get("text_chunk", "")
                                    collected_chunks.append(text_chunk)
                                    await tts_text_queue.put(text_chunk)
                                    await self.broadcast(
                                        self._message(
                                            msg_type="assistant_response_chunk",
                                            payload={
                                                "text_chunk": text_chunk,
                                                "is_final": False,
                                            },
                                            request_id=request_id,
                                        )
                                    )
                                    await self.broadcast(
                                        self._message(
                                            msg_type="tts_chunk",
                                            payload={"text": text_chunk},
                                            request_id=request_id,
                                        )
                                    )
                        await tts_text_queue.put(None)

                        if collected_chunks:
                            streaming_succeeded = True

                        if streaming_succeeded:
                            await self.state_machine.transition(VoiceState.SPEAKING)
                            await self.broadcast(
                                self._message(
                                    msg_type="tts_start",
                                    payload={"text": ""},
                                    request_id=request_id,
                                )
                            )
                            tts_playback_task = asyncio.create_task(
                                self.audio_player.play_stream(
                                    self.tts_manager.stream_synthesize(
                                        _tts_text_iter()
                                    ),
                                    sample_rate=self.config.tts.sample_rate,
                                )
                            )

                    if not streaming_was_attempted:
                        brain_result = await self.brain_agent.process_input(
                            user_text, {"request_id": request_id}
                        )
                        response_text = brain_result.get("response_text", "")
                        intent = brain_result.get("intent", "unknown")
                        action = brain_result.get("action")
                    elif streaming_succeeded:
                        if final_chunk_payload:
                            response_text = final_chunk_payload.get("response", "")
                            intent = final_chunk_payload.get("intent", "unknown")
                            action = final_chunk_payload.get("action")
                        else:
                            response_text = ""
                            intent = "unknown"
                            action = None
                        if not response_text:
                            response_text = self._stitch_text_chunks(collected_chunks)
                        # Add explicit return to prevent double brain call
                        return
                    else:
                        logger.warning(
                            "Streaming produced no chunks, falling back to non-streaming"
                        )
                        brain_result = await self.brain_agent.process_input(
                            user_text, {"request_id": request_id}
                        )
                        response_text = brain_result.get("response_text", "")
                        intent = brain_result.get("intent", "unknown")
                        action = brain_result.get("action")

                    response_text = self._normalize_response_text(response_text)

                    if (
                        self.config.auth.enabled
                        and self.config.auth.mode == "challenge"
                    ):
                        session_new = not bool(auth_result.get("cached"))
                        needs_liveness = self.liveness_detector.should_trigger(
                            mode=self.config.auth.liveness,
                            is_sensitive=self.access_controller.is_sensitive_intent(
                                intent
                            ),
                            session_new=session_new,
                        )
                        if needs_liveness:
                            await self.state_machine.transition(VoiceState.VERIFYING)
                            challenge = self.liveness_detector.generate_challenge()
                            await self.broadcast(
                                self._message(
                                    msg_type="auth_challenge",
                                    payload=challenge,
                                    request_id=request_id,
                                )
                            )

                            challenge_prompt = (
                                f"For verification, please say: {challenge['phrase']}"
                            )
                            challenge_audio = await self.tts_manager.synthesize(
                                challenge_prompt
                            )
                            await self.audio_player.play(
                                challenge_audio, sample_rate=self.config.tts.sample_rate
                            )

                            challenge_start = asyncio.get_running_loop().time()
                            challenge_recording = await self.recorder.start_recording()
                            challenge_passed = False
                            if challenge_recording is not None:
                                challenge_stt = await self.stt.transcribe(
                                    challenge_recording.audio
                                )
                                challenge_result = self.liveness_detector.verify_challenge(
                                    challenge_recording.audio,
                                    expected_phrase=challenge["phrase"],
                                    transcript_text=challenge_stt.get("text", ""),
                                    response_latency_seconds=asyncio.get_running_loop().time()
                                    - challenge_start,
                                )
                                challenge_passed = bool(challenge_result.get("passed"))
                                await self.broadcast(
                                    self._message(
                                        msg_type="auth_challenge_result",
                                        payload=challenge_result,
                                        request_id=request_id,
                                    )
                                )

                            if not challenge_passed:
                                auth_result = {
                                    **auth_result,
                                    "verified": False,
                                    "mode": "voice_liveness_failed",
                                }
                                self._set_auth_result(auth_result)
                                await self.broadcast(
                                    self._message(
                                        msg_type="auth_result",
                                        payload=auth_result,
                                        request_id=request_id,
                                    )
                                )

                            await self.state_machine.transition(VoiceState.THINKING)

                    await self.short_term_memory.add_turn(
                        "assistant",
                        response_text,
                        metadata={
                            "intent": intent,
                            "tokens": max(1, len(response_text) // 4),
                        },
                    )

                    intent_data = {
                        "intent": intent,
                        "response": response_text,
                        "action": action,
                    }

                    await self.broadcast(
                        self._message(
                            msg_type="assistant_response",
                            payload={
                                "text": response_text,
                                "intent": intent,
                                "action_taken": None,
                                "auth": auth_result,
                            },
                            request_id=request_id,
                        )
                    )

                    allowed = await self.access_controller.check_access(
                        intent_data, auth_result
                    )
                    if not allowed:
                        route_result = {
                            "status": "denied",
                            "message": self.access_controller.denial_message(),
                            "response": self.access_controller.denial_message(),
                            "intent": intent,
                            "action": None,
                            "action_result": {
                                "success": False,
                                "message": "Restricted in limited-access mode",
                            },
                        }
                    else:
                        route_result = await self.intent_router.route(intent_data)

                    action_taken = route_result.get("action_result")

                    if action_taken is not None:
                        await self.broadcast(
                            self._message(
                                msg_type="assistant_response",
                                payload={
                                    "text": response_text,
                                    "intent": intent,
                                    "action_taken": action_taken,
                                    "auth": auth_result,
                                },
                                request_id=request_id,
                            )
                        )
                    if tts_playback_task is not None:
                        await tts_playback_task
                        await self.broadcast(
                            self._message(
                                msg_type="tts_end",
                                payload={},
                                request_id=request_id,
                            )
                        )
                    else:
                        await self.state_machine.transition(VoiceState.SPEAKING)
                        await self.broadcast(
                            self._message(
                                msg_type="tts_start",
                                payload={"text": ""},
                                request_id=request_id,
                            )
                        )
                        await self.broadcast(
                            self._message(
                                msg_type="tts_chunk",
                                payload={"text": response_text},
                                request_id=request_id,
                            )
                        )
                        audio_data = await self.tts_manager.synthesize(response_text)
                        await self.audio_player.play(
                            audio_data, sample_rate=self.config.tts.sample_rate
                        )
                        await self.broadcast(
                            self._message(
                                msg_type="tts_end",
                                payload={},
                                request_id=request_id,
                            )
                        )

                    await self.state_machine.transition(VoiceState.IDLE)
                else:
                    await self.state_machine.transition(VoiceState.IDLE)

                if (
                    self._get_always_on()
                    and cast(Any, self.state_machine.state) == VoiceState.IDLE
                ):
                    await asyncio.sleep(0.5)
                    if (
                        self._get_always_on()
                        and cast(Any, self.state_machine.state) == VoiceState.IDLE
                    ):
                        self.wake_queue.put_nowait(
                            {
                                "ts": datetime.now(UTC).isoformat(),
                                "source": "always_on",
                            }
                        )
            except Exception as exc:
                logger.exception(f"Voice loop error: {exc}")
                await self.broadcast(
                    self._message(
                        msg_type="error",
                        payload={
                            "code": "VOICE_PIPELINE_ERROR",
                            "message": str(exc),
                            "recoverable": True,
                        },
                        request_id=request_id,
                    )
                )
            finally:
                if self.state_machine.state != VoiceState.IDLE:
                    await self.state_machine.reset()

    async def _process_text_command(self, user_text: str, request_id: str) -> None:
        auth_result = self._get_auth_result() or {
            "verified": True,
            "confidence": 1.0,
            "mode": "keyboard",
            "threshold_used": 0.0,
            "pin_required": False,
        }
        await self._run_turn(user_text, request_id, auth_result)

    async def _run_turn(
        self, user_text: str, request_id: str, auth_result: dict[str, Any]
    ) -> None:
        cmd_start = asyncio.get_running_loop().time()
        await self.state_machine.transition(VoiceState.THINKING)
        await self.short_term_memory.add_turn(
            "user", user_text, metadata={"tokens": max(1, len(user_text) // 4)}
        )

        await self.broadcast(
            self._message(
                msg_type="response_start",
                payload={
                    "request_id": request_id,
                    "provider": self.config.brain.providers.default_provider,
                },
                request_id=request_id,
            )
        )

        if self.config.brain.stream_chunks:
            collected_chunks: list[str] = []
            final_chunk_payload: dict[str, Any] | None = None
            tts_text_queue: asyncio.Queue[str | None] = asyncio.Queue()
            first_chunk_time: float | None = None
            tts_playback_task: asyncio.Task[None] | None = None
            streaming_succeeded = False

            async def _tts_text_iter() -> AsyncIterator[str]:
                while True:
                    item = await tts_text_queue.get()
                    if item is None:
                        break
                    yield item

            async for event in self.brain_agent.stream_response(
                user_text, {"request_id": request_id}
            ):
                if event.get("type") == "assistant_response_chunk":
                    payload = event.get("payload", {})
                    if payload.get("is_final"):
                        final_chunk_payload = payload
                    else:
                        text_chunk = payload.get("text_chunk", "")
                        collected_chunks.append(text_chunk)
                        if first_chunk_time is None:
                            first_chunk_time = asyncio.get_running_loop().time()
                        await tts_text_queue.put(text_chunk)
                        await self.broadcast(
                            self._message(
                                msg_type="assistant_response_chunk",
                                payload={
                                    "text_chunk": text_chunk,
                                    "is_final": False,
                                },
                                request_id=request_id,
                            )
                        )

            await tts_text_queue.put(None)

            if collected_chunks:
                streaming_succeeded = True
                await self.state_machine.transition(VoiceState.SPEAKING)
                await self.broadcast(
                    self._message(
                        msg_type="tts_start",
                        payload={"text": ""},
                        request_id=request_id,
                    )
                )
                tts_playback_task = asyncio.create_task(
                    self.audio_player.play_stream(
                        self.tts_manager.stream_synthesize(_tts_text_iter()),
                        sample_rate=self.config.tts.sample_rate,
                    )
                )

            if streaming_succeeded:
                if final_chunk_payload:
                    response_text = final_chunk_payload.get("response", "")
                    intent = final_chunk_payload.get("intent", "unknown")
                    action = final_chunk_payload.get("action")
                else:
                    response_text = ""
                    intent = "unknown"
                    action = None
                if not response_text:
                    response_text = self._stitch_text_chunks(collected_chunks)
            else:
                logger.warning(
                    "Streaming produced no chunks, falling back to non-streaming"
                )
                brain_result = await self.brain_agent.process_input(
                    user_text, {"request_id": request_id}
                )
                response_text = brain_result.get("response_text", "")
                intent = brain_result.get("intent", "unknown")
                action = brain_result.get("action")

            response_text = self._normalize_response_text(response_text)
            latency_ms = (
                int((first_chunk_time - cmd_start) * 1000)
                if first_chunk_time
                else int((asyncio.get_running_loop().time() - cmd_start) * 1000)
            )

            await self.short_term_memory.add_turn(
                "assistant",
                response_text,
                metadata={
                    "intent": intent,
                    "tokens": max(1, len(response_text) // 4),
                },
            )

            await self.broadcast(
                self._message(
                    msg_type="assistant_response",
                    payload={
                        "text": response_text,
                        "intent": intent,
                        "action_taken": None,
                        "auth": auth_result,
                        "latency_ms": latency_ms,
                    },
                    request_id=request_id,
                )
            )

            intent_data = {
                "intent": intent,
                "response": response_text,
                "action": action,
            }
            allowed = await self.access_controller.check_access(
                intent_data, auth_result
            )
            if allowed:
                route_result = await self.intent_router.route(intent_data)
                action_taken = route_result.get("action_result")
                if action_taken is not None:
                    await self.broadcast(
                        self._message(
                            msg_type="assistant_response",
                            payload={
                                "text": response_text,
                                "intent": intent,
                                "action_taken": action_taken,
                                "auth": auth_result,
                                "latency_ms": latency_ms,
                            },
                            request_id=request_id,
                        )
                    )

            if tts_playback_task is not None:
                await tts_playback_task
            else:
                await self.state_machine.transition(VoiceState.SPEAKING)
                await self.broadcast(
                    self._message(
                        msg_type="tts_chunk",
                        payload={"text": response_text},
                        request_id=request_id,
                    )
                )
                audio_data = await self.tts_manager.synthesize(response_text)
                await self.audio_player.play(
                    audio_data, sample_rate=self.config.tts.sample_rate
                )
            await self.broadcast(
                self._message(msg_type="tts_end", payload={}, request_id=request_id)
            )
            await self.state_machine.transition(VoiceState.IDLE)
            return

        brain_result = await self.brain_agent.process_input(
            user_text, {"request_id": request_id}
        )
        response_text = self._normalize_response_text(
            brain_result.get("response_text", "")
        )
        intent = brain_result.get("intent", "unknown")
        action = brain_result.get("action")
        latency_ms = int((asyncio.get_running_loop().time() - cmd_start) * 1000)

        await self.short_term_memory.add_turn(
            "assistant",
            response_text,
            metadata={"intent": intent, "tokens": max(1, len(response_text) // 4)},
        )

        intent_data = {"intent": intent, "response": response_text, "action": action}

        await self.broadcast(
            self._message(
                msg_type="assistant_response",
                payload={
                    "text": response_text,
                    "intent": intent,
                    "action_taken": None,
                    "auth": auth_result,
                    "latency_ms": latency_ms,
                },
                request_id=request_id,
            )
        )

        allowed = await self.access_controller.check_access(intent_data, auth_result)
        if not allowed:
            route_result = {
                "status": "denied",
                "message": self.access_controller.denial_message(),
                "response": self.access_controller.denial_message(),
                "intent": intent,
                "action": None,
                "action_result": {
                    "success": False,
                    "message": "Restricted in limited-access mode",
                },
            }
        else:
            route_result = await self.intent_router.route(intent_data)

        action_taken = route_result.get("action_result")
        if action_taken is not None:
            await self.broadcast(
                self._message(
                    msg_type="assistant_response",
                    payload={
                        "text": response_text,
                        "intent": intent,
                        "action_taken": action_taken,
                        "auth": auth_result,
                        "latency_ms": latency_ms,
                    },
                    request_id=request_id,
                )
            )

        await self.state_machine.transition(VoiceState.SPEAKING)
        await self.broadcast(
            self._message(
                msg_type="tts_start", payload={"text": ""}, request_id=request_id
            )
        )
        audio_data = await self.tts_manager.synthesize(response_text)
        await self.audio_player.play(
            audio_data, sample_rate=self.config.tts.sample_rate
        )
        await self.broadcast(
            self._message(msg_type="tts_end", payload={}, request_id=request_id)
        )
        await self.state_machine.transition(VoiceState.IDLE)

    @staticmethod
    def _stitch_text_chunks(chunks: list[str]) -> str:
        if not chunks:
            return ""

        out = ""
        for chunk in chunks:
            part = str(chunk or "")
            if not part:
                continue

            if not out:
                out = part
                continue

            prev = out[-1]
            first = part[0]
            needs_space = prev.isalnum() and first.isalnum()
            out += (" " if needs_space else "") + part

        return out.strip()

    @staticmethod
    def _normalize_response_text(text: str) -> str:
        candidate = str(text or "").strip()
        if not candidate:
            return ""

        if candidate.startswith("```") and candidate.endswith("```"):
            candidate = candidate.removeprefix("```").removesuffix("```").strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()

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

        return candidate.strip()

    @staticmethod
    def _decode_audio_payload(audio_base64: str) -> NDArray[np.int16]:
        raw = base64.b64decode(audio_base64)
        return cast("NDArray[np.int16]", np.frombuffer(raw, dtype=np.int16))
