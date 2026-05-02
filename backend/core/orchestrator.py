from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from api.settings_handler import SettingsHandler
from auth.access_control import AccessController
from auth.enrollment import VoiceEnrollment
from auth.liveness import LivenessDetector
from auth.speaker_verify import SpeakerVerifier
from brain.intent import IntentRouter
from brain.memory.context_builder import ContextBuilder
from brain.memory.long_term import LongTermMemory
from brain.memory.short_term import ShortTermMemory
from brain.memory.summarizer import Summarizer
from brain.prompt_templates import build_system_prompt
from infrastructure.audio.audio_player import AudioPlayer
from infrastructure.audio.listener import WakeWordDetector
from infrastructure.audio.recorder import AudioRecorder
from infrastructure.database.db import get_db
from infrastructure.websocket.manager import WSManager
from os_bridge.platform_detect import detect_platform
from plugins.plugin_manager import PluginManager
from services.brain.agent import ClaudeAgent
from services.voice.model_manager import ModelManager
from services.voice.pipeline import VoicePipeline
from services.voice.state_machine import VoicePipeline as VoiceStateMachine
from services.voice.state_machine import VoiceState
from services.voice.stt_manager import STTManager
from services.voice.tts import TTSManager

from core.config import JarvisConfig, load_config
from core.error_handler import setup_global_error_handler
from core.event_bus import EventBus
from core.health_check import HealthChecker
from core.logger import get_logger

logger = get_logger(__name__)


class MessageBuilder(Protocol):
    def __call__(
        self, msg_type: str, payload: dict[str, Any], request_id: str | None = None
    ) -> dict[str, Any]: ...


AsyncFn = Callable[[], Coroutine[Any, Any, None]]
ProbeFn = Callable[[], Awaitable[tuple[bool, str]]]


class JarvisBackend:
    config: JarvisConfig
    event_bus: EventBus
    ws_manager: WSManager
    voice_pipeline: VoicePipeline
    stop_event: asyncio.Event
    always_on_enabled: bool
    websocket_ready: bool
    wake_queue: asyncio.Queue[dict[str, Any]]
    model_manager: ModelManager
    stt: STTManager
    recorder: AudioRecorder
    tts_manager: TTSManager
    audio_player: AudioPlayer
    state_machine: VoiceStateMachine
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
    _message: MessageBuilder
    _warm_startup_models: AsyncFn
    _enrich_health_payload: Callable[[dict[str, Any]], dict[str, Any]]

    def __init__(self) -> None:
        self.config = load_config()
        self.event_bus = EventBus()

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

        def _message(
            msg_type: str, payload: dict[str, Any], request_id: str | None = None
        ) -> dict[str, Any]:
            return {
                "type": msg_type,
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
                "request_id": request_id or str(uuid4()),
            }

        self._message = _message
        self.ws_manager = WSManager(
            message_builder=self._message,
            stop_event=self.stop_event,
        )

        self.state_machine = VoiceStateMachine(
            event_bus=self.event_bus, state_broadcaster=self.ws_manager._broadcast_state
        )
        self.long_term_memory = LongTermMemory()

        async def _on_memory_rollover(turns: list[dict[str, Any]]) -> None:
            if not turns:
                return
            await self.summarizer.summarize_turns(self.session_id, turns)

        self.short_term_memory = ShortTermMemory(
            max_turns=self.config.brain.short_term_turns,
            on_rollover=_on_memory_rollover,
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

        def _intent_context() -> dict[str, Any]:
            return {
                "user_os": detect_platform().to_dict(),
                "user_prefs": {},
                "session_id": self.session_id,
                "brain_agent": self.brain_agent,
                "auth_result": self.latest_auth_result,
            }

        self.intent_router = IntentRouter(
            plugin_manager=self.plugin_manager, context_provider=_intent_context
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
        self.latest_auth_result = {
            "verified": not self.config.auth.enabled,
            "confidence": 1.0 if not self.config.auth.enabled else 0.0,
            "mode": "disabled" if not self.config.auth.enabled else "voice",
        }
        self.latest_health_status = {
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
        self.listener = None

        def _set_auth_result(result: dict[str, Any]) -> None:
            self.latest_auth_result = result

        def _get_auth_result() -> dict[str, Any]:
            return self.latest_auth_result

        def _is_provider_ready(provider_name: str) -> bool:
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

        async def _probe_microphone() -> tuple[bool, str]:
            try:
                import sounddevice as sd

                dev = sd.query_devices(kind="input")
                name = (
                    dev.get("name", "default") if isinstance(dev, dict) else "default"
                )
                return True, f"input device available: {name}"
            except Exception as exc:
                return False, f"microphone unavailable: {exc}"

        async def _probe_model() -> tuple[bool, str]:
            if isinstance(self.stt, STTManager):
                return (
                    True,
                    f"stt manager ready (primary: {self.stt.primary_engine_name})",
                )

            loaded = self.model_manager.loaded_model_name
            if loaded:
                return True, f"stt model loaded: {loaded}"

            default_provider = self.config.brain.providers.default_provider
            if _is_provider_ready(default_provider):
                return True, f"brain provider ready: {default_provider}"

            return False, "no ready brain/stt model yet"

        async def _probe_websocket() -> tuple[bool, str]:
            is_running = self.websocket_ready
            return is_running, "server running" if is_running else "server not running"

        def _enrich_health_payload(payload: dict[str, Any]) -> dict[str, Any]:
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

        self._enrich_health_payload = _enrich_health_payload

        async def _warm_startup_models() -> None:
            try:
                self.latest_health_status = self._enrich_health_payload(
                    {
                        **self.latest_health_status,
                        "model_loaded": True,
                    }
                )
                await self.ws_manager.broadcast(
                    self._message(
                        msg_type="health_status",
                        payload=self.latest_health_status,
                    )
                )
            except Exception as exc:
                logger.warning(f"STT startup warmup skipped: {exc}")

        self._warm_startup_models = _warm_startup_models

        self.health_checker = HealthChecker(
            event_bus=self.event_bus,
            microphone_probe=_probe_microphone,
            model_probe=_probe_model,
            websocket_probe=_probe_websocket,
            interval_seconds=30.0,
        )

        self.voice_pipeline = VoicePipeline(
            config=self.config,
            event_bus=self.event_bus,
            stt=self.stt,
            recorder=self.recorder,
            tts_manager=self.tts_manager,
            audio_player=self.audio_player,
            state_machine=self.state_machine,
            brain_agent=self.brain_agent,
            intent_router=self.intent_router,
            access_controller=self.access_controller,
            liveness_detector=self.liveness_detector,
            speaker_verifier=self.speaker_verifier,
            short_term_memory=self.short_term_memory,
            wake_queue=self.wake_queue,
            stop_event=self.stop_event,
            broadcast=self.ws_manager.broadcast,
            message_builder=self._message,
            get_listener=lambda: self.listener,
            get_always_on=lambda: self.always_on_enabled,
            get_auth_result=_get_auth_result,
            set_auth_result=_set_auth_result,
        )

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
        asyncio.create_task(self.ws_manager._ws_keepalive_loop(), name="ws-keepalive")
        asyncio.create_task(self._warm_startup_models(), name="startup-model-warmup")
        asyncio.create_task(
            self.voice_pipeline._voice_loop(), name="voice-pipeline-loop"
        )
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

        for client in list(self.ws_manager.clients):
            try:
                await client.close(code=1001, reason="Server shutdown")
            except Exception:
                pass

    async def _register_event_handlers(self) -> None:
        async def on_health(payload: dict[str, Any]) -> None:
            enriched = self._enrich_health_payload(payload)
            self.latest_health_status = enriched
            await self.ws_manager.broadcast(
                self._message(
                    msg_type="health_status",
                    payload=enriched,
                )
            )

        async def on_listener_error(payload: dict[str, Any]) -> None:
            await self.ws_manager.broadcast(
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
            await self.ws_manager.broadcast(
                self._message(
                    msg_type="tts_started",
                    payload={"text": payload.get("text", "")},
                )
            )
            await self.ws_manager.broadcast(
                self._message(
                    msg_type="tts_start",
                    payload={"text": payload.get("text", "")},
                )
            )

        async def on_tts_completed(payload: dict[str, Any]) -> None:
            await self.ws_manager.broadcast(
                self._message(
                    msg_type="tts_completed",
                    payload={"duration_ms": int(payload.get("duration_ms", 0))},
                )
            )
            await self.ws_manager.broadcast(
                self._message(msg_type="tts_end", payload={})
            )

        async def on_audio_level(payload: dict[str, Any]) -> None:
            await self.ws_manager.broadcast(
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


_orchestrator_instance: JarvisBackend | None = None


def get_orchestrator() -> JarvisBackend:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = JarvisBackend()
    return _orchestrator_instance
