from __future__ import annotations

from copy import deepcopy
import json

import pytest

from scripts import run_professor_fidelity_proxy_harness as runner
from src.digital_twin.evaluation.professor_fidelity_proxy import (
    ProfessorFidelityProxyError,
    build_blinded_packet,
    score_reviews,
    validate_dataset,
)


def test_proxy_harness_is_runnable_and_does_not_claim_real_fidelity() -> None:
    validation = runner.validate()
    simulation = runner.simulate()

    assert validation["case_count"] == 12
    assert validation["answerable_count"] == 8
    assert validation["boundary_count"] == 4
    assert validation["provider_calls"] == 0
    assert validation["real_professor_fidelity_claim"] is False
    assert simulation["status"] == "completed-go-deeper"
    assert simulation["reviewer_count"] == 2
    assert simulation["review_count"] == 24
    assert simulation["preferred_condition_counts"] == {"C2": 24}
    assert simulation["claim_boundary"]["real_professor_fidelity"] is False


def test_blinding_is_seeded_and_hides_condition_labels_from_items() -> None:
    dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
    responses = runner._simulated_responses(dataset)

    first = build_blinded_packet(dataset, responses, seed=42024)
    second = build_blinded_packet(dataset, responses, seed=42024)

    assert first == second
    assert all(
        set(response) == {"alias", "action", "text", "citations"}
        for item in first["items"]
        for response in item["responses"]
    )
    assert all(
        response["alias"] in {"A", "B", "C", "D"}
        for item in first["items"]
        for response in item["responses"]
    )


def test_response_portfolio_rejects_missing_or_duplicate_conditions() -> None:
    dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
    responses = runner._simulated_responses(dataset)

    with pytest.raises(ProfessorFidelityProxyError, match="cover C0-C3"):
        build_blinded_packet(dataset, responses[:-1], seed=1)


def test_synthetic_dataset_cannot_become_professor_reference() -> None:
    dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
    drifted = deepcopy(dataset)
    drifted["real_professor_reference"] = True

    with pytest.raises(ProfessorFidelityProxyError, match="cannot be a professor reference"):
        validate_dataset(drifted)


def test_review_scoring_requires_two_complete_reviewer_configurations() -> None:
    dataset = json.loads(runner.DATASET_PATH.read_text(encoding="utf-8"))
    packet = build_blinded_packet(dataset, runner._simulated_responses(dataset), seed=2)

    with pytest.raises(ProfessorFidelityProxyError, match="at least two"):
        score_reviews(packet, [])
