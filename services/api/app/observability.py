"""Bounded operational metrics without request or course content."""

from __future__ import annotations

from collections import Counter, deque
from threading import RLock


class OperationalMetrics:
    def __init__(self, *, latency_window: int = 10_000) -> None:
        self._lock = RLock()
        self._requests: Counter[str] = Counter()
        self._statuses: Counter[str] = Counter()
        self._latencies_ms: deque[float] = deque(maxlen=latency_window)

    def observe_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        route_key = f"{method} {route}"
        with self._lock:
            self._requests[route_key] += 1
            self._statuses[str(status_code)] += 1
            self._latencies_ms.append(duration_ms)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            latencies = sorted(self._latencies_ms)
            total = sum(self._requests.values())
            errors = sum(
                count
                for code, count in self._statuses.items()
                if int(code) >= 500
            )
            p50 = _percentile(latencies, 0.50)
            p95 = _percentile(latencies, 0.95)
            error_rate = errors / total if total else 0.0
            alerts: list[dict[str, object]] = []
            if total >= 20 and error_rate > 0.01:
                alerts.append(
                    {
                        "code": "server-error-rate-high",
                        "severity": "critical",
                        "value": error_rate,
                        "threshold": 0.01,
                    }
                )
            if len(latencies) >= 20 and p95 > 750:
                alerts.append(
                    {
                        "code": "api-latency-p95-high",
                        "severity": "warning",
                        "value": p95,
                        "threshold": 750.0,
                    }
                )
            return {
                "request_count": total,
                "server_error_count": errors,
                "server_error_rate": error_rate,
                "latency_sample_count": len(latencies),
                "latency_p50_ms": p50,
                "latency_p95_ms": p95,
                "requests_by_route": dict(sorted(self._requests.items())),
                "responses_by_status": dict(sorted(self._statuses.items())),
                "alerts": alerts,
            }


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    index = max(0, min(len(values) - 1, int(round((len(values) - 1) * quantile))))
    return values[index]
