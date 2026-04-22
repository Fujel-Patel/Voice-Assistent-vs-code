from __future__ import annotations

from pathlib import Path
from typing import Callable

from config.config_loader import JarvisConfig
from core.logger import get_logger

logger = get_logger(__name__)

MODELS_DIR = Path(__file__).parent.parent.parent / "models" / "whisper"
AVAILABLE_MODELS = {"tiny", "base", "small", "medium", "large-v3"}


class ModelManager:
    """Handles local faster-whisper model loading and switching."""

    def __init__(self, config: JarvisConfig):
        self._config = config
        self._loaded_model_name: str | None = None
        self._model = None

    @property
    def model(self):
        return self._model

    @property
    def loaded_model_name(self) -> str | None:
        return self._loaded_model_name

    def is_downloaded(self, model_name: str) -> bool:
        path = MODELS_DIR / model_name
        return path.exists() and any(path.iterdir())

    async def ensure_loaded(
        self,
        model_name: str | None = None,
        progress_cb: Callable[[str], None] | None = None,
    ):
        target = model_name or self._config.stt.model
        if target not in AVAILABLE_MODELS:
            raise ValueError(f"Unsupported model '{target}'. Allowed: {sorted(AVAILABLE_MODELS)}")

        if self._loaded_model_name == target and self._model is not None:
            return self._model

        progress_cb = progress_cb or (lambda _msg: None)
        progress_cb(f"Loading whisper model: {target}")

        MODELS_DIR.mkdir(parents=True, exist_ok=True)

        try:
            from faster_whisper import WhisperModel
        except Exception as exc:  # pragma: no cover - dependency runtime
            raise RuntimeError(f"faster-whisper import failed: {exc}") from exc

        compute_type = self._config.stt.compute_type
        model_path = MODELS_DIR / target

        try:
            self._model = WhisperModel(
                target,
                download_root=str(MODELS_DIR),
                compute_type=compute_type,
            )
            self._loaded_model_name = target
            progress_cb(f"Whisper model ready: {target}")
            logger.info(f"Whisper model loaded: {target}")
        except Exception as exc:
            logger.warning(f"Model load on preferred compute type failed: {exc}. Retrying on CPU/float32")
            self._model = WhisperModel(
                target,
                download_root=str(MODELS_DIR),
                compute_type="float32",
                device="cpu",
            )
            self._loaded_model_name = target
            progress_cb(f"Whisper model ready (CPU fallback): {target}")

        # Marker directory helps local status checks.
        model_path.mkdir(parents=True, exist_ok=True)
        return self._model

    async def switch_model(self, model_name: str):
        return await self.ensure_loaded(model_name=model_name)
