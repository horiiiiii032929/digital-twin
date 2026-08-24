from __future__ import annotations

import copy

import pytest

from scripts.build_evidence_sufficiency_v2_decision_draft import DecisionDraftError
from scripts.build_evidence_sufficiency_v2_decision_draft_002 import (
    BASE_CONTENT_SHA256,
    DATASET_ID,
    HUMAN_CONFIRMATION_CASE_IDS,
    PRIORITY_REVIEW_CASE_IDS,
    _validate_corrected,
    build_corrected_draft,
)


@pytest.fixture(scope="module")
def draft() -> dict:
    return build_corrected_draft()


def test_corrected_draft_is_stable_and_preserves_distribution(draft: dict) -> None:
    repeated = build_corrected_draft()

    assert draft == repeated
    assert draft["dataset_id"] == DATASET_ID
    assert draft["predecessor"]["content_sha256"] == BASE_CONTENT_SHA256
    assert len(draft["cases"]) == 120
    assert sum(case["expected_action"] == "answer" for case in draft["cases"]) == 80
    assert sum(case["expected_action"] == "abstain" for case in draft["cases"]) == 40
    assert draft["provider_or_model_calls"] == 0
    assert draft["private_data_read"] is False
    assert draft["opened_for_candidate_evaluation"] is False
    assert draft["review"]["freeze_eligible"] is False


def test_every_multi_evidence_case_uses_two_distinct_active_sources(
    draft: dict,
) -> None:
    source_map = {source["source_unit_id"]: source for source in draft["sources"]}
    cases = [case for case in draft["cases"] if case["slice"] == "multi-evidence"]

    assert len(cases) == 15
    for case in cases:
        source_ids = [item["source_unit_id"] for item in case["evidence"]]
        assert len(source_ids) == len(set(source_ids)) == 2
        assert all(source_map[item]["active"] for item in source_ids)
        assert all(
            source_map[item]["course_id"] == case["course_id"] for item in source_ids
        )


def test_permission_cases_expose_the_exact_stale_source(draft: dict) -> None:
    source_map = {source["source_unit_id"]: source for source in draft["sources"]}
    cases = [case for case in draft["cases"] if case["slice"] == "permission-version"]

    assert len(cases) == 10
    for case in cases:
        active = source_map[case["evidence"][0]["source_unit_id"]]
        assert len(case["tempting_source_ids"]) == 1
        stale = source_map[case["tempting_source_ids"][0]]
        assert stale["active"] is False
        assert stale["logical_source_id"] == active["logical_source_id"]


def test_multimodal_slice_is_explicitly_a_derived_text_proxy(draft: dict) -> None:
    scope = draft["evidence_representation_scope"]
    assert scope["candidate_input"] == "retrieved-text-representation"
    assert scope["raw_visual_assets_present"] is False
    assert scope["raw_visual_quality_evaluated"] is False
    cases = [case for case in draft["cases"] if case["slice"] == "multimodal"]
    assert len(cases) == 10
    assert all(
        case["evidence_representation_scope"]
        == "derived-text-from-modality-tagged-source"
        for case in cases
    )


def test_priority_and_human_packets_cover_decision_boundaries(draft: dict) -> None:
    case_map = {case["case_id"]: case for case in draft["cases"]}
    assert tuple(draft["priority_review_case_ids"]) == PRIORITY_REVIEW_CASE_IDS
    assert tuple(draft["human_confirmation_case_ids"]) == HUMAN_CONFIRMATION_CASE_IDS
    assert {case_map[item]["slice"] for item in draft["priority_review_case_ids"]} == {
        "ambiguous",
        "cross-course",
        "multi-evidence",
        "multimodal",
        "near-domain",
        "no-evidence",
        "permission-version",
    }


@pytest.mark.parametrize("mutation", ["multi", "permission", "visual"])
def test_corrected_validator_rejects_regressions(draft: dict, mutation: str) -> None:
    changed = copy.deepcopy(draft)
    if mutation == "multi":
        case = next(
            item for item in changed["cases"] if item["slice"] == "multi-evidence"
        )
        case["evidence"][1]["source_unit_id"] = case["evidence"][0]["source_unit_id"]
        pattern = "evidence source binding|distinct sources"
    elif mutation == "permission":
        case = next(
            item for item in changed["cases"] if item["slice"] == "permission-version"
        )
        case["tempting_source_ids"] = []
        pattern = "stale distractor"
    else:
        changed["evidence_representation_scope"]["raw_visual_quality_evaluated"] = True
        pattern = "raw-visual quality"
    with pytest.raises(DecisionDraftError, match=pattern):
        _validate_corrected(changed)
