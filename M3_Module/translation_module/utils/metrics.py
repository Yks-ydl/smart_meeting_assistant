from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LatencyLogger:
    """延迟监控（占位）。"""

    values: list[int] = field(default_factory=list)

    def log(self, latency_ms: int) -> None:
        self.values.append(latency_ms)

    def report(self) -> dict[str, float]:
        if not self.values:
            return {"count": 0, "avg_ms": 0.0, "p95_ms": 0.0}
        values = sorted(self.values)
        p95_index = int(len(values) * 0.95) - 1
        p95_index = max(0, min(p95_index, len(values) - 1))
        return {
            "count": float(len(values)),
            "avg_ms": sum(values) / len(values),
            "p95_ms": float(values[p95_index]),
        }
