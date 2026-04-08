from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.core.logging import correlation_context, get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class MetricPoint:
    name: str
    value: float
    labels: dict[str, object]


class InMemoryMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = (
            defaultdict(float)
        )
        self._observations: list[MetricPoint] = []

    def increment(
        self,
        name: str,
        value: float = 1.0,
        **labels: object,
    ) -> None:
        normalized = _normalize_labels(labels)
        key = (name, tuple(sorted((k, str(v)) for k, v in normalized.items())))
        with self._lock:
            self._counters[key] += value

        logger.info(
            "Metric counter incremented.",
            extra={
                "context": correlation_context(
                    metric=name,
                    value=value,
                    labels=normalized,
                )
            },
        )

    def observe(
        self,
        name: str,
        value: float,
        **labels: object,
    ) -> None:
        normalized = _normalize_labels(labels)
        point = MetricPoint(name=name, value=float(value), labels=normalized)
        with self._lock:
            self._observations.append(point)

        logger.info(
            "Metric observation recorded.",
            extra={
                "context": correlation_context(
                    metric=name,
                    value=float(value),
                    labels=normalized,
                )
            },
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            counters = {
                f"{name}|{dict(labels)}": value
                for (name, labels), value in self._counters.items()
            }
            observations = [
                {
                    "name": point.name,
                    "value": point.value,
                    "labels": point.labels,
                }
                for point in self._observations
            ]
        return {
            "counters": counters,
            "observations": observations,
        }


def _normalize_labels(labels: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in labels.items() if value is not None}


_METRICS = InMemoryMetrics()


def get_metrics() -> InMemoryMetrics:
    return _METRICS
