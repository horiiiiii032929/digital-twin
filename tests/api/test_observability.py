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
