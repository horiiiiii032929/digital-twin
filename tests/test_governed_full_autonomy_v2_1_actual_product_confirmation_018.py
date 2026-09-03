from __future__ import annotations

import asyncio
import json

from scripts import (
    governed_full_autonomy_v2_1_actual_product_runtime as product_runtime,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_confirmation_018 as runner,
)
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmMessage, LlmResponse
from src.digital_twin.student.autonomy_models import ReactiveIntentProposalV3


class _CanaryClient:
    def __init__(self, returned_model: str) -> None:
        self.returned_model = returned_model

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        assert messages
        assert task == "reactive_tutoring_intent"
        content = ReactiveIntentProposalV3(
            proposed_intent="give_hint",
            reason_code="transport-canary",
        )
        return LlmResponse(
            content=content.model_dump_json(),
            provider_model=self.returned_model,
            provider_revision=self.returned_model,
            usage=GenerationUsage(
                input_tokens=40,
                output_tokens=20,
                total_tokens=60,
                approximate_cost_usd=0.000032,
            ),
        )


def test_018_is_terminally_invalid_and_provider_revoked() -> None:
    result = runner.validate_attempt()
    instrument = json.loads(runner.INSTRUMENT.read_text(encoding="utf-8"))

    assert result["case_count"] == 820
    assert result["source_family_count"] == 50
    assert result["source_disjoint_from_confirmations_012_through_017"] is True
    assert result["instructional_wording_family_disjoint_from_confirmation_016"] is True
    assert result["provider_execution_authorized"] is False
    assert result["paid_execution_authorized"] is False
    assert instrument["dataset"]["source_family_range"] == [351, 400]
    assert instrument["dataset"]["quality_results_previously_opened"] == 0
    assert instrument["terminal_result"]["hidden_gold_opened"] is False
    assert instrument["terminal_result"]["bulk_case_count"] == 0


def test_018_separates_transport_reactive_and_autonomous_canaries() -> None:
    result = runner.validate_attempt()
    rows = {case.case_id: case for _condition, case, _gold in runner.package.build_contract()}

    assert result["direct_transport_identity_canary_required"] is True
    assert result["product_route_canary_case_ids"] == [
        "release-fresh-h-e1-trajectory-001-t1-v2-reactive-seed-1",
        "release-fresh-h-e1-long-horizon-001",
    ]
    assert all(case_id in rows for case_id in runner.CONTEXT.canary_case_ids)
    assert any(
        event.kind == "practice-outcome"
        for event in rows["release-fresh-h-e1-long-horizon-001"].events
    )
    assert runner.CONTEXT.expected_canary_models == {
        "t1-v2-reactive": {"gpt-5.6-luna"},
        "t1-v2-autonomous": {"gpt-5.6-luna"},
    }


def test_direct_transport_canary_records_exact_identity_and_cost(monkeypatch) -> None:
    engine = product_runtime.selected_h_e1_engine_binding()
    monkeypatch.setattr(
        product_runtime,
        "_engine_client",
        lambda _engine, *, role: _CanaryClient(engine.planner_model),
    )

    result = asyncio.run(
        product_runtime.run_engine_transport_identity_canary(
            engine,
            maximum_cost_usd=0.01,
        )
    )

    assert result["status"] == "passed"
    assert result["provider_calls"] == 1
    assert result["completed_calls"] == 1
    assert result["returned_models"] == ["gpt-5.6-luna"]
    assert result["input_tokens"] == 40
    assert result["output_tokens"] == 20
    assert result["cost_usd"] == 0.000032
    assert len(str(result["content_sha256"])) == 64


def test_direct_transport_canary_rejects_identity_drift(monkeypatch) -> None:
    engine = product_runtime.selected_h_e1_engine_binding()
    monkeypatch.setattr(
        product_runtime,
        "_engine_client",
        lambda _engine, *, role: _CanaryClient("unexpected-model"),
    )

    result = asyncio.run(
        product_runtime.run_engine_transport_identity_canary(
            engine,
            maximum_cost_usd=0.01,
        )
    )

    assert result["status"] == "failed"
    assert result["returned_models"] == ["unexpected-model"]
    assert result["provider_calls"] == 1


def test_018_preflight_is_blocked_after_revocation() -> None:
    result = runner.shared.preflight(context=runner.CONTEXT)

    assert "provider-execution-not-authorized" in result["blockers"]
    assert "paid-execution-not-authorized" in result["blockers"]
    assert "repository-freeze-authorization-missing" in result["blockers"]
    assert result["provider_calls"] == 0
    assert result["hidden_gold_loaded"] is False
