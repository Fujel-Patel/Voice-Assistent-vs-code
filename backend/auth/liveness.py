from __future__ import annotations

import random
from typing import Any

import numpy as np


class LivenessDetector:
    WORDS = ["blue", "delta", "echo", "gamma", "nova", "signal", "vector", "atlas"]

    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def generate_challenge(self) -> dict[str, Any]:
        style = random.choice(["phrase", "number", "repeat"])
        if style == "number":
            phrase = " ".join(str(random.randint(0, 9)) for _ in range(4))
        else:
            phrase = " ".join(random.choice(self.WORDS) for _ in range(4))
        return {
            "type": style,
            "phrase": phrase,
            "timeout_seconds": self.timeout_seconds,
        }

    def verify_challenge(
        self,
        audio: np.ndarray,
        expected_phrase: str,
        transcript_text: str | None = None,
        response_latency_seconds: float | None = None,
    ) -> dict[str, Any]:
        matched = self._phrase_match(expected_phrase, transcript_text or "")

        if response_latency_seconds is None:
            # Fallback heuristic from audio duration only.
            response_latency_seconds = float(len(audio) / 16000.0)

        audio_duration_seconds = float(len(audio) / 16000.0)
        timing_natural = 0.5 < response_latency_seconds <= 5.0
        replay_risk = self._replay_risk(audio)
        human_like_duration = audio_duration_seconds >= 1.5
        passed = matched and timing_natural and (replay_risk < 0.95 or human_like_duration)

        return {
            "passed": passed,
            "phrase_matched": matched,
            "timing_natural": timing_natural,
            "replay_risk": replay_risk,
        }

    def should_trigger(self, mode: str, is_sensitive: bool, session_new: bool) -> bool:
        mode = (mode or "sensitive_only").lower()
        if mode == "never":
            return False
        if mode == "always":
            return True
        if mode == "sensitive_only":
            return is_sensitive or session_new
        return False

    def _phrase_match(self, expected: str, actual: str) -> bool:
        expected_tokens = [token for token in expected.lower().split() if token]
        actual_tokens = [token for token in actual.lower().split() if token]
        if not expected_tokens:
            return False

        overlap = len(set(expected_tokens) & set(actual_tokens))
        score = overlap / max(1, len(set(expected_tokens)))
        return score >= 0.75

    def _replay_risk(self, audio: np.ndarray) -> float:
        waveform = np.asarray(audio, dtype=np.float32)
        if waveform.ndim > 1:
            waveform = np.mean(waveform, axis=1)
        if waveform.size == 0:
            return 1.0

        max_abs = float(np.max(np.abs(waveform)) + 1e-8)
        if max_abs > 1.5:
            waveform = waveform / 32768.0

        # Low dynamic range and very flat envelopes are suspicious.
        frame = max(1, int(len(waveform) / 50))
        envelope = [float(np.mean(np.abs(waveform[i : i + frame]))) for i in range(0, len(waveform), frame)]
        variation = float(np.std(envelope))
        return float(np.clip(1.0 - (variation * 15.0), 0.0, 1.0))
