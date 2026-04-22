"""Lightweight in-memory metrics counters for local observability."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from time import perf_counter
from typing import Dict


@dataclass
class MetricsStore:
    """Tracks counts and rolling latency totals by metric name."""

    counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_total_ms: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    latency_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _lock: Lock = field(default_factory=Lock)

    def incr(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self.counters[name] += amount

    def observe_latency_ms(self, name: str, value_ms: float) -> None:
        with self._lock:
            self.latency_total_ms[name] += value_ms
            self.latency_count[name] += 1

    def snapshot(self) -> dict:
        with self._lock:
            latency_avg = {
                name: (self.latency_total_ms[name] / self.latency_count[name])
                for name in self.latency_count
                if self.latency_count[name] > 0
            }
            return {
                "counters": dict(self.counters),
                "latency_avg_ms": latency_avg,
            }


metrics = MetricsStore()


class time_metric:
    """Context manager to record elapsed time in milliseconds."""

    def __init__(self, metric_name: str) -> None:
        self.metric_name = metric_name
        self._start = 0.0

    def __enter__(self) -> "time_metric":
        self._start = perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        elapsed_ms = (perf_counter() - self._start) * 1000
        metrics.observe_latency_ms(self.metric_name, elapsed_ms)
