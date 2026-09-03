from __future__ import annotations

from types import SimpleNamespace
import json

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


def test_019_is_terminally_refine_and_authority_is_revoked() -> None:
    result = runner.validate_attempt()

    assert result["case_count"] == 820
    assert result["reuses_unopened_confirmation_018_hidden_gold"] is True
    assert result["prior_public_canary_count"] == 2
    assert result["product_route_canary_accepts_safe_fallback"] is True
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False


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


def test_019_preflight_is_blocked_after_revocation() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False


def test_terminal_result_atomically_updates_checkpoint(tmp_path) -> None:
    result_path = tmp_path / "result.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    result = {
        "status": "completed-keep",
        "summary": {"case_count": 820},
    }
    result_path.write_text(json.dumps(result), encoding="utf-8")
    checkpoint_path.write_text(
        json.dumps({"status": "canaries-passed", "completed_case_count": 2}),
        encoding="utf-8",
    )
    context = SimpleNamespace(
        result_path=result_path,
        checkpoint_path=checkpoint_path,
    )

    runner.shared._write_terminal_checkpoint(result, context=context)

    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint["status"] == "completed-keep"
    assert checkpoint["terminal"] is True
    assert checkpoint["completed_case_count"] == 820
    assert len(checkpoint["result_sha256"]) == 64
