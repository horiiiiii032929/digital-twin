from __future__ import annotations

from scripts import run_academic_factual_qa_source_semantic_atom_comparison as runner


def test_source_semantic_atom_comparison_validates_frozen_contract() -> None:
    result = runner.validate(runner.DEFAULT_INSTRUMENT)

    assert result == {
        "instrument_id": "academic-factual-qa-source-semantic-atom-comparison-001",
        "status": "passed-build-only",
        "case_count": 500,
        "source_chunk_count": 300,
        "candidate_count": 2,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
    }


def test_source_semantic_atom_simulation_is_network_free_and_gold_closed() -> None:
    result = runner.simulate(runner.DEFAULT_INSTRUMENT)

    assert result["status"] == "passed-network-free-simulation"
    assert result["case_count"] == 20
    assert result["candidate_count"] == 2
    assert result["provider_calls"] == 0
    assert result["paid_cost_usd"] == 0
    assert result["hidden_gold_loaded"] is False


def test_source_semantic_atom_candidate_is_bound_without_provider_authority() -> None:
    instrument = runner._instrument(runner.DEFAULT_INSTRUMENT)  # noqa: SLF001
    identities = {row.architecture_id: row for row in instrument.candidates}

    assert set(identities) == {
        "typed-target-evidence-v1",
        "source-semantic-evidence-atoms-v1",
    }
    candidate = identities["source-semantic-evidence-atoms-v1"]
    assert candidate.rollback_architecture_id == "typed-target-evidence-v1"
    assert candidate.provider_execution_authorized is False


def test_source_semantic_atom_operational_failure_is_invalid() -> None:
    assert runner._terminal_decision(  # noqa: SLF001
        execution_valid=False,
        candidate_passed=False,
        candidate_selected=False,
    ) == ("invalid-execution", "correct-harness-only")
