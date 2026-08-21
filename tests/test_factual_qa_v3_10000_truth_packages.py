from __future__ import annotations

from collections import Counter

import pytest

from scripts.build_factual_qa_v3_10000_truth_packages import (
    INSTRUMENT_ID,
    build_artifact,
    normalize_question,
    validate_instrument,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


@pytest.fixture(scope="module")
def artifact() -> dict:
    return build_artifact()


def test_truth_package_instrument_is_provider_and_write_unauthorized() -> None:
    instrument = validate_instrument()

    assert instrument["instrument_id"] == INSTRUMENT_ID
    assert instrument["execution_safety"]["provider_execution_authorized"] is False
    assert instrument["execution_safety"]["dataset_write_authorized"] is False
    assert instrument["truth_package_contract"]["model_generated_ground_truth_allowed"] is False

    with pytest.raises(RepositoryFreezeError):
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)


def test_all_truth_packages_are_exactly_distributed_and_byte_stable(
    artifact: dict,
) -> None:
    summary = artifact["summary"]
    repeated = build_artifact()["summary"]

    assert summary["truth_package_count"] == 10_000
    assert summary["source_count"] == 1_000
    assert summary["claim_count"] == 8_000
    assert summary["action_counts"] == {
        "abstain": 1_000,
        "answer": 8_000,
        "clarify": 500,
        "refuse": 500,
    }
    assert summary["content_sha256"] == repeated["content_sha256"]
    assert summary["configuration_sha256"] == repeated["configuration_sha256"]
    assert summary["private_data_read"] is False
    assert summary["provider_calls"] == 0


def test_canonical_questions_are_normalized_unique(artifact: dict) -> None:
    packages = artifact["truth_packages"]
    normalized = [normalize_question(package["canonical_question"]) for package in packages]

    assert len(normalized) == len(set(normalized)) == 10_000
    assert all(
        package["normalized_canonical_question"]
        == normalize_question(package["canonical_question"])
        for package in packages
    )
    assert artifact["summary"]["exact_normalized_duplicate_count"] == 0


def test_answer_truth_is_exactly_source_linked(artifact: dict) -> None:
    source_map = {
        source["source_unit_id"]: source for source in artifact["sources"]
    }
    answerable = [
        package
        for package in artifact["truth_packages"]
        if package["expected_action"] == "answer"
    ]

    assert len(answerable) == 8_000
    for package in answerable:
        assert package["selected_claim_ids"] == [
            claim["claim_id"] for claim in package["structured_target_claims"]
        ]
        assert len(package["citations"]) == len(package["structured_target_claims"])
        for claim, citation in zip(
            package["structured_target_claims"], package["citations"], strict=True
        ):
            assert citation == {
                "source_unit_id": claim["source_unit_id"],
                "quote": claim["evidence_quote"],
            }
            assert citation["quote"] in source_map[citation["source_unit_id"]]["source_truth"]


def test_boundary_actions_have_no_authoritative_lineage(artifact: dict) -> None:
    boundaries = [
        package
        for package in artifact["truth_packages"]
        if package["expected_action"] in {"abstain", "clarify", "refuse"}
    ]

    assert len(boundaries) == 2_000
    assert Counter(package["expected_action"] for package in boundaries) == Counter(
        {"abstain": 1_000, "clarify": 500, "refuse": 500}
    )
    assert all(package["selected_claim_ids"] == [] for package in boundaries)
    assert all(package["citations"] == [] for package in boundaries)
    assert all(package["structured_target_claims"] == [] for package in boundaries)
    assert all(package["candidate_claims"] == [] for package in boundaries)
    assert all(package["context_source_ids"] == [] for package in boundaries)
    assert all(package["boundary_reason"] for package in boundaries)


def test_cross_course_cases_never_select_distractor_lineage(artifact: dict) -> None:
    blueprints = {
        blueprint["blueprint_id"]: blueprint for blueprint in artifact["blueprints"]
    }
    cases = [
        package
        for package in artifact["truth_packages"]
        if package["slice"] == "cross-course-confusion"
    ]

    assert len(cases) == 500
    for package in cases:
        assert package["expected_action"] == "abstain"
        distractors = set(blueprints[package["blueprint_id"]]["distractor_unit_ids"])
        assert not distractors.intersection(
            citation["source_unit_id"] for citation in package["citations"]
        )
