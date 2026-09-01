from __future__ import annotations

from scripts import run_academic_factual_qa_semantic_target_comparison as runner


def test_semantic_target_comparison_validates_frozen_two_candidate_contract() -> None:
    result = runner.validate(runner.DEFAULT_INSTRUMENT)

    assert result == {
        "instrument_id": "academic-factual-qa-semantic-target-comparison-001",
        "status": "passed-build-only",
        "case_count": 500,
        "source_chunk_count": 300,
        "candidate_count": 2,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
    }


def test_semantic_target_comparison_simulation_is_network_free_and_gold_closed() -> None:
    result = runner.simulate(runner.DEFAULT_INSTRUMENT)

    assert result["status"] == "passed-network-free-simulation"
    assert result["case_count"] == 20
    assert result["candidate_count"] == 2
    assert result["provider_calls"] == 0
    assert result["paid_cost_usd"] == 0
    assert result["hidden_gold_loaded"] is False


def test_semantic_target_comparison_binds_best_valid_baseline_and_successor() -> None:
    instrument = runner._instrument(runner.DEFAULT_INSTRUMENT)  # noqa: SLF001
    identities = {row.architecture_id: row for row in instrument.candidates}

    assert set(identities) == {
        "typed-target-evidence-v1",
        "semantic-target-resolution-v3",
    }
    assert identities["typed-target-evidence-v1"].role == "baseline"
    assert identities["semantic-target-resolution-v3"].rollback_architecture_id == (
        "typed-target-evidence-v1"
    )
    assert all(not row.provider_execution_authorized for row in instrument.candidates)
