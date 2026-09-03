from __future__ import annotations

from types import SimpleNamespace

from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_019 as runner,
)


def _response(*, model: str | None, status: str) -> SimpleNamespace:
    return SimpleNamespace(
        operational_status="completed",
        provider_calls=1,
        operational_metrics=SimpleNamespace(
            call_records=[SimpleNamespace(provider_model=model, status=status)]
        ),
    )


def test_019_reuses_only_the_unopened_018_package_and_is_authorized() -> None:
    result = runner.validate_attempt()

    assert result["case_count"] == 820
    assert result["reuses_unopened_confirmation_018_hidden_gold"] is True
    assert result["prior_public_canary_count"] == 2
    assert result["product_route_canary_accepts_safe_fallback"] is True
    assert result["provider_execution_authorized"] is True
    assert result["paid_execution_authorized"] is True


def test_019_route_canary_accepts_exact_identity_safe_fallback() -> None:
    responses = [
        ("t1-v2-reactive", _response(model="gpt-5.6-luna", status="completed")),
        ("t1-v2-autonomous", _response(model="gpt-5.6-luna", status="failed")),
    ]

    assert runner.shared._canaries_valid(responses, context=runner.CONTEXT) is True


def test_019_route_canary_rejects_missing_or_drifted_identity() -> None:
    missing = [
        ("t1-v2-reactive", _response(model="gpt-5.6-luna", status="completed")),
        ("t1-v2-autonomous", _response(model=None, status="failed")),
    ]
    drifted = [
        ("t1-v2-reactive", _response(model="gpt-5.6-luna", status="completed")),
        ("t1-v2-autonomous", _response(model="unexpected-model", status="failed")),
    ]

    assert runner.shared._canaries_valid(missing, context=runner.CONTEXT) is False
    assert runner.shared._canaries_valid(drifted, context=runner.CONTEXT) is False


def test_019_preflight_has_no_authorization_blocker() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" not in result["blockers"]
    assert "paid-execution-not-authorized" not in result["blockers"]
    assert "repository-freeze-authorization-missing" not in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
