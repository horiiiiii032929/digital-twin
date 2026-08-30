from __future__ import annotations

from collections import Counter
import inspect

from scripts import academic_factual_qa_atomic_m2_t0_adapter as adapter
from scripts import build_academic_factual_qa_atomic_m2_product_checkpoint as builder
from scripts import run_academic_factual_qa_atomic_m2_product_checkpoint as runner


def test_product_checkpoint_is_finite_and_keeps_gold_out_of_public_inputs() -> None:
    outputs = builder.build(verified_at="2026-08-30T00:00:00+00:00")
    candidate = outputs[builder.CASES]
    control = outputs[builder.CONTROL_CASES]
    instrument = outputs[builder.INSTRUMENT]

    assert candidate["case_count"] == 500
    assert control["case_count"] == 100
    assert len({row["cluster_id"] for row in control["cases"]}) == 20
    assert Counter(row["slice"] for row in control["cases"])["academic-integrity"] > 0
    assert all(
        not ({"canonical_answer", "claims", "evidence", "expected_action"} & set(row))
        for row in candidate["cases"] + control["cases"]
    )
    assert instrument["execution"]["maximum_product_calls"] == 600
    assert instrument["execution"]["maximum_transport_retries"] == 0
    assert instrument["execution"]["maximum_cost_usd"] == 7.0
    assert instrument["execution"]["final_execution_authorized"] is False


def test_candidate_and_control_change_only_the_evidence_gate() -> None:
    outputs = builder.build(verified_at="2026-08-30T00:00:00+00:00")
    candidate = outputs[builder.CANDIDATE_MANIFEST]
    control = outputs[builder.CONTROL_MANIFEST]

    assert candidate["retriever"] == control["retriever"]
    assert candidate["generator"] == control["generator"]
    assert candidate["policy"] == control["policy"]
    assert candidate["model_bindings"] == control["model_bindings"]
    assert candidate["evidence_gate"] != control["evidence_gate"]


def test_response_adapter_has_no_hidden_gold_or_scorer_dependency() -> None:
    source = inspect.getsource(adapter)

    assert "UPSTREAM_GOLD" not in source
    assert "CONTROL_GOLD" not in source
    assert "candidate_gold_path" not in source
    assert "score_academic_factual_qa" not in source


def test_product_runner_has_finite_terminal_simulations() -> None:
    assert runner.simulate(scenario="pass")["status"] == "completed-keep"
    assert (
        runner.simulate(scenario="product-failure")["status"]
        == "completed-refine"
    )
    assert (
        runner.simulate(scenario="provider-failure")["status"]
        == "invalid-execution"
    )
    assert runner.simulate(scenario="resume")["gold_opened_before_responses"] is False
