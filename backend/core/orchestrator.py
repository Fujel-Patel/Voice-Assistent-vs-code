from __future__ import annotations

import asyncio
import base64
import json
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import numpy as np

if TYPE_CHECKING:
    import asyncio
from uuid import uuid4

# Ensure local imports work when running `python backend/main.py`
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
import sys

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.settings_handler import SettingsHandler
from auth.access_control import AccessController
from auth.enrollment import VoiceEnrollment
from auth.liveness import LivenessDetector
from auth.speaker_verify import SpeakerVerifier
from brain.claude_agent import ClaudeAgent
from brain.intent import IntentRouter
from brain.memory.context_builder import ContextBuilder
from brain.memory.long_term import LongTermMemory
from brain.memory.short_term import ShortTermMemory
from brain.memory.summarizer import Summarizer
from brain.prompt_templates import build_system_prompt
from config.config_loader import JarvisConfig, load_config
from os_bridge.platform_detect import detect_platform
from plugins.plugin_manager import PluginManager
from storage.db import get_db
from voice.audio_player import AudioPlayer
from voice.listener import WakeWordDetector
from voice.model_manager import ModelManager
from voice.recorder import AudioRecorder
from voice.state_machine import VoicePipeline, VoiceState
from voice.stt_manager import STTManager
from voice.tts import TTSManager

from core.error_handler import setup_global_error_handler
from core.event_bus import EventBus
from core.health_check import HealthChecker
from core.logger import get_logger

logger = get_logger(__name__)


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


class JarvisBackend:
    config: JarvisConfig
    event_bus: EventBus
    clients: set[Any]
    stop_event: asyncio.Event
    always_on_enabled: bool
    websocket_ready: bool
    wake_queue: asyncio.Queue[dict[str, Any]]
    model_manager: ModelManager
    stt: STTManager
    recorder: AudioRecorder
    tts_manager: TTSManager
    audio_player: AudioPlayer
    state_machine: VoicePipeline
    long_term_memory: LongTermMemory
    short_term_memory: ShortTermMemory
    plugin_manager: PluginManager
    system_prompt: str
    context_builder: ContextBuilder
    brain_agent: ClaudeAgent
    intent_router: IntentRouter
    settings_handler: SettingsHandler
    enrollment: VoiceEnrollment
    speaker_verifier: SpeakerVerifier
    liveness_detector: LivenessDetector
    access_controller: AccessController
    latest_auth_result: dict[str, Any]
    latest_health_status: dict[str, Any]
    summarizer: Summarizer
    session_id: str
    listener: WakeWordDetector | None
    health_checker: HealthChecker

    def __init__(self) -> None:
        self.config = load_config()
        self.event_bus = EventBus()

        self.clients: set[Any] = set()
        self.stop_event = asyncio.Event()
        self.always_on_enabled = False
        self.websocket_ready = False

        self.wake_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        self.model_manager = ModelManager(self.config)
        self.stt = STTManager(config=self.config, event_bus=self.event_bus)
        self.recorder = AudioRecorder(config=self.config, event_bus=self.event_bus)
        self.tts_manager = TTSManager(config=self.config, event_bus=self.event_bus)
        self.audio_player = AudioPlayer(
            event_bus=self.event_bus,
            volume=self.config.tts.volume,
            sample_rate=self.config.tts.sample_rate,
        )
        self.state_machine = VoicePipeline(
            event_bus=self.event_bus, state_broadcaster=self._broadcast_state
        )
        self.long_term_memory = LongTermMemory()
        self.short_term_memory = ShortTermMemory(
            max_turns=self.config.brain.short_term_turns,
            on_rollover=self._on_memory_rollover,
        )
        self.plugin_manager = PluginManager()
        self.plugin_manager.discover_plugins()
        self.system_prompt = build_system_prompt(
            self.plugin_manager.get_all_capabilities()
        )
        self.context_builder = ContextBuilder(
            short_term_memory=self.short_term_memory,
            long_term_memory=self.long_term_memory,
            token_budget=self.config.brain.token_budget,
            system_prompt=self.system_prompt,
        )
        self.brain_agent = ClaudeAgent(
            config=self.config,
            context_builder=self.context_builder,
            system_prompt=self.system_prompt,
        )
        self.intent_router = IntentRouter(
            plugin_manager=self.plugin_manager, context_provider=self._intent_context
        )
        self.settings_handler = SettingsHandler()
        self.enrollment = VoiceEnrollment()
        self.speaker_verifier = SpeakerVerifier(
            enrollment=self.enrollment,
            threshold=self.config.auth.threshold,
            reverify_minutes=self.config.auth.reverify_minutes,
            session_timeout_minutes=self.config.auth.session_timeout_minutes,
        )
        self.liveness_detector = LivenessDetector()
        self.access_controller = AccessController(pin_code=self.config.auth.pin_code)
        self.latest_auth_result: dict[str, Any] = {
            "verified": not self.config.auth.enabled,
            "confidence": 1.0 if not self.config.auth.enabled else 0.0,
            "mode": "disabled" if not self.config.auth.enabled else "voice",
        }
        self.latest_health_status: dict[str, Any] = {
            "microphone": False,
            "model_loaded": False,
            "websocket": False,
            "apis": {
                "claude": bool(self.config.provider_keys.anthropic_api_key),
                "gemini": bool(self.config.provider_keys.gemini_api_key),
                "groq": bool(self.config.provider_keys.groq_api_key),
                "openrouter": bool(self.config.provider_keys.openrouter_api_key),
                "ollama": bool(self.config.provider_keys.ollama_base_url),
                "elevenlabs": bool(self.config.elevenlabs_api_key),
            },
        }
        self.summarizer = Summarizer(
            brain_agent=self.brain_agent, long_term_memory=self.long_term_memory
        )
        self.session_id = str(uuid4())
        self.listener: WakeWordDetector | None = None
        self.health_checker = HealthChecker(
            event_bus=self.event_bus,
            microphone_probe=self._probe_microphone,
            model_probe=self._probe_model,
            websocket_probe=self._probe_websocket,
            interval_seconds=30.0,
        )

    def _is_provider_ready(self, provider_name: str) -> bool:
        provider = (provider_name or "").lower().strip()
        if provider == "claude":
            return bool(self.config.provider_keys.anthropic_api_key)
        if provider == "gemini":
            return bool(self.config.provider_keys.gemini_api_key)
        if provider == "groq":
            return bool(self.config.provider_keys.groq_api_key)
        if provider == "openrouter":
            return bool(self.config.provider_keys.openrouter_api_key)
        if provider == "ollama":
            return bool(self.config.provider_keys.ollama_base_url)
        return False

    async def start(self) -> None:
        setup_global_error_handler()

        await self.event_bus.publish("backend_started", {"status": "starting"})
        await self._register_event_handlers()
        await get_db()

        loop = asyncio.get_running_loop()

        def _on_wake() -> None:
            loop.call_soon_threadsafe(
                self.wake_queue.put_nowait,
                {"ts": datetime.now(UTC).isoformat()},
            )

        self.listener = WakeWordDetector(
            config=self.config,
            event_bus=self.event_bus,
            on_wake_word=_on_wake,
            event_loop=loop,
        )
        self.listener.start()

        await self.health_checker.start_periodic()
        asyncio.create_task(self._ws_keepalive_loop(), name="ws-keepalive")
        asyncio.create_task(self._warm_startup_models(), name="startup-model-warmup")
        asyncio.create_task(self._voice_loop(), name="voice-pipeline-loop")
        self.websocket_ready = True

        await self.event_bus.publish("backend_started", {"status": "ready"})

    async def stop(self) -> None:
        self.stop_event.set()

        if self.listener:
            self.listener.stop()

        self.tts_manager.cancel()
        await self.audio_player.stop()

        await self.health_checker.stop()
        self.websocket_ready = False

        for client in list(self.clients):
            try:
                await client.close(code=1001, reason="Server shutdown")
            except Exception:
                pass

    async def _register_event_handlers(self) -> None:
        async def on_health(payload: dict[str, Any]) -> None:
            enriched = self._enrich_health_payload(payload)
            self.latest_health_status = enriched
            await self.broadcast(
                self._message(
                    msg_type="health_status",
                    payload=enriched,
                )
            )

        async def on_listener_error(payload: dict[str, Any]) -> None:
            await self.broadcast(
                self._message(
                    msg_type="error",
                    payload={
                        "code": "LISTENER_ERROR",
                        "message": payload.get("message", "Listener error"),
                        "recoverable": True,
                    },
                )
            )

        async def on_tts_started(payload: dict[str, Any]) -> None:
            await self.broadcast(
                self._message(
                    msg_type="tts_started", payload={"text": payload.get("text", "")}
                )
            )
            await self.broadcast(
                self._message(
                    msg_type="tts_start", payload={"text": payload.get("text", "")}
                )
            )

        async def on_tts_completed(payload: dict[str, Any]) -> None:
            await self.broadcast(
                self._message(
                    msg_type="tts_completed",
                    payload={"duration_ms": int(payload.get("duration_ms", 0))},
                )
            )
            await self.broadcast(self._message(msg_type="tts_end", payload={}))

        async def on_audio_level(payload: dict[str, Any]) -> None:
            await self.broadcast(
                self._message(
                    msg_type="audio_level",
                    payload={"levels": payload.get("levels", [])},
                )
            )

        async def on_tts_stop_requested(_payload: dict[str, Any]) -> None:
            self.tts_manager.cancel()
            await self.audio_player.stop()

        async def on_wake_word_detected(_payload: dict[str, Any]) -> None:
            if self.state_machine.state == VoiceState.SPEAKING:
                await self.state_machine.handle_interrupt()

        self.event_bus.subscribe("health_check", on_health)
        self.event_bus.subscribe("listener_error", on_listener_error)
        self.event_bus.subscribe("tts_started", on_tts_started)
        self.event_bus.subscribe("tts_completed", on_tts_completed)
        self.event_bus.subscribe("audio_level", on_audio_level)
        self.event_bus.subscribe("tts_stop_requested", on_tts_stop_requested)
        self.event_bus.subscribe("wake_word_detected", on_wake_word_detected)

    async def broadcast(self, payload: dict[str, Any]) -> None:
        if not self.clients:
            return

        body = json.dumps(payload)
        tasks = [client.send_text(body) for client in list(self.clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Broadcast failure: {result}")

    async def _broadcast_state(self, payload: dict[str, Any]) -> None:
        await self.broadcast(
            self._message(msg_type="voice_state_change", payload=payload)
        )

    async def _voice_loop(self) -> None:
        while not self.stop_event.is_set():
            trigger = await self.wake_queue.get()
            request_id = str(uuid4())
            logger.info(f"Wake trigger received: {trigger}")

            try:
                # Release mic from wake word detector before recording starts
                if self.listener:
                    self.listener.pause()

                await self.state_machine.transition(VoiceState.WAKE_DETECTED)
                await self.state_machine.transition(VoiceState.LISTENING)

                # Initialize streaming STT
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

                # Start recording with real-time audio feeding to STT stream
                recording = await self.recorder.start_recording(
                    on_audio_chunk=stt_stream.process_audio
                )

                # Resume wake word detector as soon as recording is done (success or fail)
                if self.listener:
                    self.listener.resume()

                if recording is None:
                    logger.warning(
                        "Recording returned None - audio too short or VAD timeout"
                    )
                    await self.state_machine.reset()
                    continue

                # If an interrupt/reset happened while recording, abandon this trigger cleanly.
                if self.state_machine.state != VoiceState.LISTENING:
                    logger.info(
                        f"Recording completed after state changed to {self.state_machine.state.value}; dropping stale trigger"
                    )
                    continue

                await self.state_machine.transition(VoiceState.TRANSCRIBING)

                # Get final transcript from stream
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
                        self.latest_auth_result = auth_result
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

                    async def _tts_text_iter() -> AsyncIterator[str]:
                        while True:
                            item = await tts_text_queue.get()
                            if item is None:
                                break
                            yield item

                    tts_playback_task: asyncio.Task[None] | None = None
                    if self.config.brain.stream_chunks:
                        streaming_was_attempted = True
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

                    if not streaming_was_attempted or final_chunk_payload is None:
                        if streaming_was_attempted:
                            logger.warning(
                                "Streaming produced no final payload, falling back to non-streaming"
                            )
                            tts_playback_task = None
                        brain_result = await self.brain_agent.process_input(
                            user_text, {"request_id": request_id}
                        )
                        response_text = brain_result.get("response_text", "")
                        intent = brain_result.get("intent", "unknown")
                        action = brain_result.get("action")
                    else:
                        response_text = final_chunk_payload.get("response", "")
                        intent = final_chunk_payload.get("intent", "unknown")
                        action = final_chunk_payload.get("action")
                        if not response_text:
                            response_text = _stitch_text_chunks(collected_chunks)

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
                                self.latest_auth_result = auth_result
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

                    # Push clean text to UI immediately so users see response without extra action latency.
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
                    await self.state_machine.transition(VoiceState.SPEAKING)

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

                # Always-on: auto-queue next listen after completing a voice cycle
                if (
                    self.always_on_enabled
                    and cast(Any, self.state_machine.state) == VoiceState.IDLE
                ):
                    await asyncio.sleep(0.5)
                    if (
                        self.always_on_enabled
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

    def _message(
        self, msg_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]:
        return {
            "type": msg_type,
            "payload": payload,
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id or str(uuid4()),
        }

    def _intent_context(self) -> dict[str, Any]:
        return {
            "user_os": detect_platform().to_dict(),
            "user_prefs": {},
            "session_id": self.session_id,
            "brain_agent": self.brain_agent,
            "auth_result": self.latest_auth_result,
        }

    def _decode_audio_payload(self, audio_base64: str) -> np.ndarray[Any, Any]:
        import numpy as np

        raw = base64.b64decode(audio_base64)
        return np.frombuffer(raw, dtype=np.int16)

    def _normalize_response_text(self, text: str) -> str:
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

    async def _probe_microphone(self) -> tuple[bool, str]:
        try:
            import sounddevice as sd

            dev = sd.query_devices(kind="input")
            name = dev.get("name", "default") if isinstance(dev, dict) else "default"
            return True, f"input device available: {name}"
        except Exception as exc:
            return False, f"microphone unavailable: {exc}"

    async def _probe_model(self) -> tuple[bool, str]:
        if isinstance(self.stt, STTManager):
            return True, f"stt manager ready (primary: {self.stt.primary_engine_name})"

        loaded = self.model_manager.loaded_model_name
        if loaded:
            return True, f"stt model loaded: {loaded}"

        default_provider = self.config.brain.providers.default_provider
        if self._is_provider_ready(default_provider):
            return True, f"brain provider ready: {default_provider}"

        return False, "no ready brain/stt model yet"

    async def _probe_websocket(self) -> tuple[bool, str]:
        is_running = self.websocket_ready
        return is_running, "server running" if is_running else "server not running"

    async def _ws_keepalive_loop(self) -> None:
        """Send periodic pings to keep WebSocket connections alive through proxies."""
        while not self.stop_event.is_set():
            await asyncio.sleep(30)
            if self.clients:
                await self.broadcast(
                    self._message(
                        msg_type="ping",
                        payload={"ts": datetime.now(UTC).isoformat()},
                    )
                )

    async def _on_memory_rollover(self, turns: list[dict[str, Any]]) -> None:
        if not turns:
            return
        await self.summarizer.summarize_turns(self.session_id, turns)

    def _enrich_health_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload = payload or {}
        payload_apis = payload.get("apis") or {}

        return {
            **payload,
            "microphone": bool(payload.get("microphone", False)),
            "model_loaded": bool(
                payload.get("model_loaded", payload.get("modelLoaded", False))
            ),
            "websocket": bool(payload.get("websocket", self.websocket_ready)),
            "apis": {
                "claude": bool(payload_apis.get("claude"))
                or bool(self.config.provider_keys.anthropic_api_key),
                "gemini": bool(payload_apis.get("gemini"))
                or bool(self.config.provider_keys.gemini_api_key),
                "groq": bool(payload_apis.get("groq"))
                or bool(self.config.provider_keys.groq_api_key),
                "openrouter": bool(payload_apis.get("openrouter"))
                or bool(self.config.provider_keys.openrouter_api_key),
                "ollama": bool(payload_apis.get("ollama"))
                or bool(self.config.provider_keys.ollama_base_url),
                "elevenlabs": bool(payload_apis.get("elevenlabs"))
                or bool(self.config.elevenlabs_api_key),
            },
        }

    async def _warm_startup_models(self) -> None:
        try:
            self.latest_health_status = self._enrich_health_payload(
                {
                    **self.latest_health_status,
                    "model_loaded": True,
                }
            )
            await self.broadcast(
                self._message(
                    msg_type="health_status",
                    payload=self.latest_health_status,
                )
            )
        except Exception as exc:
            logger.warning(f"STT startup warmup skipped: {exc}")

    async def _process_text_command(self, user_text: str, request_id: str) -> None:
        cmd_start = time.perf_counter()
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

        auth_result = self.latest_auth_result or {
            "verified": True,
            "confidence": 1.0,
            "mode": "keyboard",
            "threshold_used": 0.0,
            "pin_required": False,
        }

        # Try streaming path first for lower latency
        streaming_was_attempted = False
        if self.config.brain.stream_chunks:
            streaming_was_attempted = True
            collected_chunks: list[str] = []
            final_chunk_payload: dict[str, Any] | None = None
            tts_text_queue: asyncio.Queue[str | None] = asyncio.Queue()
            first_chunk_time: float | None = None
            tts_playback_task: asyncio.Task[None] | None = None

            async def _tts_text_iter() -> AsyncIterator[str]:
                while True:
                    item = await tts_text_queue.get()
                    if item is None:
                        break
                    yield item

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
                            first_chunk_time = time.perf_counter()
                        await tts_text_queue.put(text_chunk)
                        await self.broadcast(
                            self._message(
                                msg_type="assistant_response_chunk",
                                payload={"text_chunk": text_chunk, "is_final": False},
                                request_id=request_id,
                            )
                        )

            await tts_text_queue.put(None)

            if not streaming_was_attempted or final_chunk_payload is None:
                if streaming_was_attempted:
                    logger.warning(
                        "Streaming produced no final payload, falling back to non-streaming"
                    )
                    tts_playback_task = None
                brain_result = await self.brain_agent.process_input(
                    user_text, {"request_id": request_id}
                )
                response_text = brain_result.get("response_text", "")
                intent = brain_result.get("intent", "unknown")
                action = brain_result.get("action")
            else:
                response_text = final_chunk_payload.get("response", "")
                intent = final_chunk_payload.get("intent", "unknown")
                action = final_chunk_payload.get("action")
                if not response_text:
                    response_text = _stitch_text_chunks(collected_chunks)

            response_text = self._normalize_response_text(response_text)
            latency_ms = (
                int((first_chunk_time - cmd_start) * 1000)
                if first_chunk_time
                else int((time.perf_counter() - cmd_start) * 1000)
            )

            await self.short_term_memory.add_turn(
                "assistant",
                response_text,
                metadata={"intent": intent, "tokens": max(1, len(response_text) // 4)},
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

        # Fallback: non-streaming path
        brain_result = await self.brain_agent.process_input(
            user_text, {"request_id": request_id}
        )
        response_text = self._normalize_response_text(
            brain_result.get("response_text", "")
        )
        intent = brain_result.get("intent", "unknown")
        action = brain_result.get("action")
        latency_ms = int((time.perf_counter() - cmd_start) * 1000)

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


_orchestrator_instance: JarvisBackend | None = None


def get_orchestrator() -> JarvisBackend:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = JarvisBackend()
    return _orchestrator_instance
