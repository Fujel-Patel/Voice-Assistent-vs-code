from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

import numpy as np
from core.logger import get_logger
from numpy.typing import NDArray

logger = get_logger(__name__)


class SpeakerEmbeddingEngine:
    """Create and compare speaker embeddings.

    Uses resemblyzer when available. Falls back to a deterministic numpy-based
    spectral embedding so the auth flow and tests work without heavy runtime deps.
    """

    EMBEDDING_SIZE = 256

    def __init__(self, model_dir: Path | None = None) -> None:
        self.model_dir = (
            model_dir or (Path.home() / ".jarvis" / "models" / "auth")
        ).expanduser()
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._encoder = None

    def create_embedding(
        self, audio: NDArray[np.float32], sample_rate: int = 16000
    ) -> NDArray[np.float32]:
        cleaned = self._preprocess_audio(audio, sample_rate)
        if cleaned.size < sample_rate:
            raise ValueError(
                "Audio too short for speaker embedding. Minimum length is 1 second."
            )

        encoder = self._get_resemblyzer_encoder()
        if encoder is not None:
            embedding = encoder.embed_utterance(cleaned)
            return self._normalize_embedding(np.asarray(embedding, dtype=np.float32))

        return self._fallback_embedding(cleaned, sample_rate)

    def compare_embeddings(
        self, emb1: NDArray[np.float32], emb2: NDArray[np.float32]
    ) -> float:
        a = self._normalize_embedding(np.asarray(emb1, dtype=np.float32))
        b = self._normalize_embedding(np.asarray(emb2, dtype=np.float32))

        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0

        similarity = float(np.dot(a, b) / denom)
        return float(np.clip(similarity, 0.0, 1.0))

    def average_embeddings(
        self, embeddings: Iterable[NDArray[np.float32]]
    ) -> NDArray[np.float32]:
        vectors = [
            self._normalize_embedding(np.asarray(vector, dtype=np.float32))
            for vector in embeddings
        ]
        if len(vectors) < 1:
            raise ValueError("No embeddings provided")

        stacked = np.stack(vectors)
        mean = np.mean(stacked, axis=0)
        return self._normalize_embedding(mean)

    def quality_score(
        self, audio: NDArray[np.float32], sample_rate: int = 16000
    ) -> float:
        cleaned = self._preprocess_audio(audio, sample_rate)
        if cleaned.size == 0:
            return 0.0

        rms = float(np.sqrt(np.mean(np.square(cleaned))))
        peak = float(np.max(np.abs(cleaned)) + 1e-8)
        crest = peak / max(rms, 1e-8)
        snr_like = float(np.clip((rms * 18.0), 0.0, 1.0))
        clipping_penalty = 0.2 if peak >= 0.98 else 0.0
        noise_penalty = 0.2 if crest < 2.0 else 0.0
        return float(np.clip(snr_like - clipping_penalty - noise_penalty, 0.0, 1.0))

    def _preprocess_audio(
        self, audio: NDArray[np.float32], sample_rate: int
    ) -> NDArray[np.float32]:
        waveform = np.asarray(audio, dtype=np.float32)
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)

        max_abs = float(np.max(np.abs(waveform)) + 1e-8)
        if max_abs > 1.5:
            waveform = waveform / 32768.0
        waveform = np.clip(waveform, -1.0, 1.0)

        # Simple silence trimming based on energy threshold.
        threshold = max(0.01, float(np.percentile(np.abs(waveform), 60) * 0.25))
        mask = np.abs(waveform) > threshold
        if np.any(mask):
            first = int(np.argmax(mask))
            last = int(len(mask) - np.argmax(mask[::-1]))
            waveform = waveform[first:last]

        if sample_rate != 16000 and waveform.size > 0:
            waveform = self._resample_linear(waveform, sample_rate, 16000)

        if waveform.size > 0:
            waveform = waveform / (float(np.max(np.abs(waveform))) + 1e-8)

        return waveform.astype(np.float32)

    def _resample_linear(
        self, audio: NDArray[np.float32], in_rate: int, out_rate: int
    ) -> NDArray[np.float32]:
        if in_rate == out_rate:
            return audio
        ratio = out_rate / in_rate
        out_len = max(1, int(len(audio) * ratio))
        positions = np.linspace(0, len(audio) - 1, out_len)
        left = np.floor(positions).astype(int)
        right = np.clip(left + 1, 0, len(audio) - 1)
        alpha = positions - left
        return cast(
            NDArray[np.float32],
            (audio[left] * (1.0 - alpha) + audio[right] * alpha).astype(np.float32),
        )

    def _fallback_embedding(
        self, audio: NDArray[np.float32], sample_rate: int
    ) -> NDArray[np.float32]:
        windowed = audio * np.hanning(len(audio))
        spectrum = np.abs(np.fft.rfft(windowed))
        if spectrum.size < 8:
            raise ValueError("Audio quality too low to create speaker embedding")

        # Bucket FFT magnitudes into 256 bands.
        chunks = np.array_split(spectrum, self.EMBEDDING_SIZE)
        vector = np.array(
            [float(np.mean(chunk)) if chunk.size else 0.0 for chunk in chunks],
            dtype=np.float32,
        )

        # Add temporal features for better discrimination.
        frame = int(sample_rate * 0.03)
        if frame > 0 and len(audio) >= frame:
            energy = [
                float(np.mean(np.square(audio[idx : idx + frame])))
                for idx in range(0, len(audio) - frame, frame)
            ]
            if energy:
                trend = np.interp(
                    np.linspace(0, len(energy) - 1, self.EMBEDDING_SIZE),
                    np.arange(len(energy)),
                    np.asarray(energy, dtype=np.float32),
                )
                vector = 0.7 * vector + 0.3 * trend.astype(np.float32)

        return self._normalize_embedding(vector)

    def _normalize_embedding(
        self, embedding: NDArray[np.float32]
    ) -> NDArray[np.float32]:
        if embedding.shape[0] != self.EMBEDDING_SIZE:
            embedding = np.resize(embedding, self.EMBEDDING_SIZE)

        norm = float(np.linalg.norm(embedding))
        if norm == 0:
            return np.zeros(self.EMBEDDING_SIZE, dtype=np.float32)
        return (embedding / norm).astype(np.float32)

    def _get_resemblyzer_encoder(self) -> Any:
        if self._encoder is not None:
            return self._encoder

        try:
            from resemblyzer import VoiceEncoder

            logger.info("Loading resemblyzer VoiceEncoder for speaker authentication")
            self._encoder = VoiceEncoder()
        except Exception as exc:
            logger.warning(
                f"Resemblyzer unavailable, using fallback embedding engine: {exc}"
            )
            self._encoder = None

        return self._encoder
