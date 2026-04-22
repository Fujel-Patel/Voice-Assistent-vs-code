from __future__ import annotations

import threading
import time
from collections.abc import Callable
import asyncio
from pathlib import Path

import numpy as np

from config.config_loader import JarvisConfig
from core.error_handler import MicrophoneError
from core.event_bus import EventBus
from core.logger import get_logger

logger = get_logger(__name__)


class WakeWordDetector:
    """openWakeWord-based wake word detector running in a background thread."""

    def __init__(
        self,
        config: JarvisConfig,
        event_bus: EventBus,
        on_wake_word: Callable[[], None],
        event_loop: asyncio.AbstractEventLoop,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._on_wake_word = on_wake_word
        self._loop = event_loop
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="wake-word-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _emit_async(self, event_name: str, payload: dict) -> None:
        asyncio.run_coroutine_threadsafe(self._event_bus.publish(event_name, payload), self._loop)

    def _run(self) -> None:
        try:
            import openwakeword
            from openwakeword.model import Model as OpenWakeWordModel
        except Exception as exc:  # pragma: no cover - import-time dependency
            logger.error(f"openWakeWord import failed: {exc}")
            self._emit_async("listener_error", {"message": str(exc)})
            return

        try:
            import pyaudio
        except Exception as exc:  # pragma: no cover - import-time dependency
            logger.error(f"PyAudio import failed: {exc}")
            self._emit_async("listener_error", {"message": str(exc)})
            return

        sensitivity = max(0.0, min(1.0, self._config.wake_word.sensitivity))
        vad_threshold = max(0.0, min(1.0, self._config.wake_word.openwakeword_vad_threshold))
        keyword = (self._config.wake_word.keyword or "jarvis").lower()
        keyword_aliases = self._keyword_aliases(keyword)
        model_path = (self._config.wake_word.openwakeword_model_path or "").strip()

        model_kwargs: dict[str, object] = {
            "vad_threshold": vad_threshold,
            "enable_speex_noise_suppression": self._config.wake_word.openwakeword_enable_speex,
        }

        if model_path:
            resolved = Path(model_path).expanduser().resolve()
            if not resolved.exists():
                message = f"openWakeWord model file not found: {resolved}"
                logger.error(message)
                self._emit_async("listener_error", {"message": message})
                return
            model_kwargs["wakeword_models"] = [str(resolved)]

        # Download bundled models once when using built-in model names.
        if "wakeword_models" not in model_kwargs:
            try:
                openwakeword.utils.download_models()
            except Exception as exc:
                logger.warning(f"openWakeWord model download skipped: {exc}")

        retries = 0
        while not self._stop_event.is_set():
            detector = None
            audio = None
            stream = None
            try:
                detector = OpenWakeWordModel(**model_kwargs)

                audio = pyaudio.PyAudio()
                stream = audio.open(
                    rate=16000,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=1280,
                )
                self._emit_async("listener_started", {"keyword": keyword})
                logger.info(f"Wake word detector started (keyword={keyword}, sensitivity={sensitivity})")
                last_detection_at = 0.0

                while not self._stop_event.is_set():
                    pcm = stream.read(1280, exception_on_overflow=False)
                    frame = np.frombuffer(pcm, dtype=np.int16)
                    scores = detector.predict(frame)
                    top_model, top_score = self._best_score(scores, keyword_aliases)
                    now = time.monotonic()
                    if top_score >= sensitivity and (now - last_detection_at) >= 1.0:
                        last_detection_at = now
                        self._emit_async("wake_word_detected", {"keyword": keyword})
                        logger.info(f"Wake word detected (model={top_model}, score={top_score:.3f})")
                        self._on_wake_word()

                return
            except Exception as exc:
                retries += 1
                err_msg = f"Wake listener error (attempt {retries}): {exc}"
                logger.error(err_msg)
                self._emit_async("listener_error", {"message": err_msg})
                if "No Default Input Device Available" in str(exc):
                    self._emit_async(
                        "health_check",
                        {
                            "microphone": False,
                            "message": "No microphone found",
                        },
                    )
                    MicrophoneError(str(exc))
                if self._stop_event.is_set():
                    return
                time.sleep(min(5.0, 0.5 * retries))
            finally:
                try:
                    if stream is not None:
                        stream.stop_stream()
                        stream.close()
                except Exception:
                    pass
                try:
                    if audio is not None:
                        audio.terminate()
                except Exception:
                    pass
                try:
                    if detector is not None:
                        del detector
                except Exception:
                    pass

    def _keyword_aliases(self, keyword: str) -> set[str]:
        normalized = keyword.strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {normalized, normalized.replace("_", "")}
        if normalized and not normalized.startswith("hey_"):
            aliases.add(f"hey_{normalized}")
            aliases.add(f"hey{normalized}")
        return {alias for alias in aliases if alias}

    def _best_score(self, scores: object, keyword_aliases: set[str]) -> tuple[str, float]:
        if not isinstance(scores, dict):
            return "unknown", 0.0

        best_model = "unknown"
        best_score = 0.0
        for model_name, raw_score in scores.items():
            try:
                score = float(raw_score)
            except Exception:
                continue

            canonical = str(model_name).lower().replace(" ", "_").replace("-", "_")
            if keyword_aliases and not any(alias in canonical for alias in keyword_aliases):
                continue

            if score > best_score:
                best_score = score
                best_model = str(model_name)

        # If no keyword-specific match was found, use the top score across all models.
        if best_model == "unknown":
            for model_name, raw_score in scores.items():
                try:
                    score = float(raw_score)
                except Exception:
                    continue
                if score > best_score:
                    best_score = score
                    best_model = str(model_name)

        return best_model, best_score
