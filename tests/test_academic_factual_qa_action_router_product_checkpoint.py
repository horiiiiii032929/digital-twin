from __future__ import annotations

import inspect

from scripts import academic_factual_qa_atomic_m2_t0_adapter as adapter
from scripts import build_academic_factual_qa_action_router_product_checkpoint as builder
from scripts import run_academic_factual_qa_action_router_product_checkpoint as runner


def test_action_router_checkpoint_is_finite_and_bounded_authorized() -> None:
    outputs = builder.build(metadata_verified_at=None)
    instrument = outputs[builder.INSTRUMENT]
    binding = outputs[builder.BINDING]

    assert outputs[builder.CASES]["case_count"] == 500
    assert outputs[builder.CONTROL_CASES]["case_count"] == 100
    assert instrument["execution"]["maximum_embedding_calls"] == 20
    assert instrument["execution"]["maximum_product_calls"] == 600
    assert instrument["execution"]["maximum_total_calls"] == 620
    assert instrument["execution"]["maximum_transport_retries"] == 0
    assert instrument["execution"]["maximum_cost_usd"] == 8.0
    assert instrument["boundaries"]["final_10000_opened"] is False
    assert binding["authorization"]["paid_execution_authorized"] is True
    assert binding["authorization"]["provider_execution_authorized"] is True
    assert binding["authorization"]["final_execution_authorized"] is False
    assert binding["metadata_status"] == "fresh"
    assert binding["data_controls"]["responses_store"] is False


def test_action_router_candidate_is_an_explicit_method_level_successor() -> None:
    outputs = builder.build(metadata_verified_at=None)
    candidate = outputs[builder.CANDIDATE_MANIFEST]
    control = outputs[builder.CONTROL_MANIFEST]

    assert candidate["retriever"] == control["retriever"]
    assert candidate["model_bindings"]["generator"] == control["model_bindings"][
        "generator"
    ]
    assert candidate["evidence_gate"] == "question-targeted-atomic-evidence-gate-v1"
    assert candidate["model_bindings"]["action-router"] == (
        "deterministic-tutor-action-router-v1"
    )
    assert control["evidence_gate"] == "atomic-structured-coverage-control-v1"
    assert control["model_bindings"]["action-router"] == "none-historical-control"


def test_action_router_adapter_has_no_hidden_gold_dependency() -> None:
    source = inspect.getsource(adapter)

    assert "candidate_gold_path" not in source
    assert "score_academic_factual_qa" not in source
    assert "QuestionTargetedAtomicEvidenceGate" in source
    assert "DeterministicActionRouterV1" in source


def test_action_router_checkpoint_has_terminal_network_free_simulations() -> None:
    assert runner.validate()["status"] == "passed-build-only"
    assert runner.simulate(scenario="pass")["status"] == "completed-keep"
    assert runner.simulate(scenario="quality-failure")["status"] == (
        "completed-refine"
    )
    assert runner.simulate(scenario="provider-failure")["status"] == (
        "invalid-execution"
    )
    assert runner.simulate(scenario="resume")["gold_opened_before_responses"] is False


def test_action_router_preflight_is_ready_after_bounded_authorization(
    monkeypatch,
) -> None:
    monkeypatch.setattr(runner, "_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-key")

    result = runner.preflight()

    assert result["status"] == "ready"
    assert result["blockers"] == []
    assert result["provider_calls"] == 0
    assert result["final_10000_opened"] is False
