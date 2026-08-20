from collections import defaultdict, deque

import pytest

from services.api.app.config import AppSettings
from services.api.app.middleware import RateLimitMiddleware
from services.api.app.observability import OperationalMetrics


def test_operational_metrics_raise_bounded_threshold_alerts():
    metrics = OperationalMetrics()
    for index in range(20):
        metrics.observe_request(
            method="GET",
            route="/api/synthetic",
            status_code=500 if index == 0 else 200,
            duration_ms=800,
        )

    snapshot = metrics.snapshot()

    assert {alert["code"] for alert in snapshot["alerts"]} == {
        "server-error-rate-high",
        "api-latency-p95-high",
    }


@pytest.mark.parametrize("latency_window", (0, -1, True, 1.5))
def test_operational_metrics_reject_invalid_window(latency_window):
    with pytest.raises(ValueError, match="positive integer"):
        OperationalMetrics(latency_window=latency_window)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"method": " ", "route": "/api/test", "status_code": 200, "duration_ms": 1}, "required"),
        ({"method": "GET", "route": " ", "status_code": 200, "duration_ms": 1}, "required"),
        ({"method": "GET", "route": "/api/test", "status_code": True, "duration_ms": 1}, "HTTP status"),
        ({"method": "GET", "route": "/api/test", "status_code": 99, "duration_ms": 1}, "HTTP status"),
        ({"method": "GET", "route": "/api/test", "status_code": 200, "duration_ms": float("nan")}, "finite"),
        ({"method": "GET", "route": "/api/test", "status_code": 200, "duration_ms": -1}, "finite"),
    ),
)
def test_operational_metrics_reject_malformed_observations(kwargs, message):
    with pytest.raises(ValueError, match=message):
        OperationalMetrics().observe_request(**kwargs)


def test_rate_limit_key_storage_is_bounded_and_expired_keys_are_pruned(monkeypatch):
    now = [100.0]
    monkeypatch.setattr(
        "services.api.app.middleware.time.monotonic", lambda: now[0]
    )
    limiter = RateLimitMiddleware(lambda *_: None, settings=AppSettings())
    limiter._events = defaultdict(
        deque,
        {f"session:{index}": deque([now[0]]) for index in range(10_000)},
    )

    assert limiter._allow("session:overflow", 1) is False
    assert len(limiter._events) == 10_000

    now[0] = 161.0
    assert limiter._allow("session:new", 1) is True
    assert dict(limiter._events) == {"session:new": deque([161.0])}
