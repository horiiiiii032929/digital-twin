from __future__ import annotations

import json

import pytest

from scripts import run_professor_fidelity_proxy_c0_c3_002 as predecessor
from scripts import run_professor_fidelity_proxy_c0_c3_003 as successor


def test_successor_moves_unsupported_constraints_to_local_validation() -> None:
    historical = predecessor._generator_schema("case-001", "C2")  # noqa: SLF001
    corrected = successor._generator_schema("case-001", "C2")  # noqa: SLF001
    corrected_review = successor._review_schema("item-001")  # noqa: SLF001

    assert "uniqueItems" in json.dumps(historical)
    for forbidden in successor._PROVIDER_UNSUPPORTED_CONSTRAINTS:  # noqa: SLF001
        assert forbidden not in json.dumps(corrected)
        assert forbidden not in json.dumps(corrected_review)
    assert corrected["required"] == historical["required"]
    assert corrected["properties"].keys() == historical["properties"].keys()


def test_deterministic_validation_still_rejects_duplicate_semantic_lists() -> None:
    output = {
        "supported_source_facts": ["fact", "fact"],
        "citations": [],
        "applied_profile_features": [],
    }

    with pytest.raises(predecessor.ProfessorProxyCheckpointError, match="duplicate"):
        successor._validate_output_lists(output)  # noqa: SLF001


def test_deterministic_validation_enforces_removed_length_limits() -> None:
    output = {
        "response": "x" * 1401,
        "supported_source_facts": [],
        "citations": [],
        "applied_profile_features": [],
    }

    with pytest.raises(predecessor.ProfessorProxyCheckpointError, match="length"):
        successor._validate_output_lists(output)  # noqa: SLF001

    review = {
        "scores": [
            {"alias": alias, **{name: 3 for name in predecessor.FIDELITY_DIMENSIONS}}
            for alias in predecessor.ALIASES
        ],
        "rationale": "",
    }
    with pytest.raises(predecessor.ProfessorProxyCheckpointError, match="rationale"):
        successor._validate_review(review)  # noqa: SLF001


def test_successor_validation_and_simulation_are_network_free(monkeypatch) -> None:
    successor.configure_successor()
    monkeypatch.setattr(
        predecessor.DirectProviderJsonTransport,
        "call_with_ledger",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network call")),
    )

    validation = predecessor.validate()
    simulation = predecessor.simulate()

    assert validation["instrument_id"] == successor.RUN_ID
    assert validation["provider_calls"] == 0
    assert simulation["status"] == "passed-network-free-simulation"
    assert simulation["hard_gate_simulation_passed"] is True
    assert simulation["subjective_gate_simulation_passed"] is True
    assert simulation["provider_calls"] == 0
