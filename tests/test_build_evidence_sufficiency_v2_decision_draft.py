from __future__ import annotations

import copy
from collections import Counter

import pytest

from scripts.build_evidence_sufficiency_v2_decision_draft import (
    DecisionDraftError,
    EXPECTED_SLICE_COUNTS,
    build_draft,
    main,
    validate_draft,
)
from src.digital_twin.repository_freeze import RepositoryFreezeError


@pytest.fixture(scope="module")
def draft() -> dict:
    return build_draft()


def payload_without_hash(draft: dict) -> dict:
    return {key: copy.deepcopy(value) for key, value in draft.items() if key != "content_sha256"}


def test_draft_is_exactly_distributed_and_byte_stable(draft: dict) -> None:
    repeated = build_draft()

    assert len(draft["cases"]) == 120
    assert Counter(case["expected_action"] for case in draft["cases"]) == Counter(
        {"answer": 80, "abstain": 40}
    )
    assert Counter(case["slice"] for case in draft["cases"]) == Counter(
        EXPECTED_SLICE_COUNTS
    )
    assert len(draft["sources"]) == 40
    assert draft["content_sha256"] == repeated["content_sha256"]
    assert draft["provider_or_model_calls"] == 0
    assert draft["private_data_read"] is False
    assert draft["opened_for_candidate_evaluation"] is False


def test_answer_cases_bind_exact_active_source_truth(draft: dict) -> None:
    source_map = {source["source_unit_id"]: source for source in draft["sources"]}
    claim_map = {
        claim["claim_id"]: (source, claim)
        for source in draft["sources"]
        for claim in source["claims"]
    }

    for case in draft["cases"]:
        if case["expected_action"] != "answer":
            continue
        assert case["required_claims"]
        assert len(case["required_claims"]) == len(case["evidence"])
        for required, evidence in zip(
            case["required_claims"], case["evidence"], strict=True
        ):
            source, claim = claim_map[required["claim_id"]]
            assert source_map[evidence["source_unit_id"]] == source
            assert source["active"] is True
            assert source["tutoring_allowed"] is True
            assert source["course_id"] == case["course_id"]
            assert evidence["claim_id"] == required["claim_id"]
            assert required["statement"] == claim["statement"]
            assert evidence["quote"] == claim["evidence_quote"]


def test_abstain_cases_have_no_authoritative_lineage(draft: dict) -> None:
    cases = [case for case in draft["cases"] if case["expected_action"] == "abstain"]

    assert len(cases) == 40
    assert all(case["required_claims"] == [] for case in cases)
    assert all(case["evidence"] == [] for case in cases)
    assert all(case["boundary_reason"] for case in cases)


def test_cross_course_and_near_domain_distractors_match_the_intended_boundary(
    draft: dict,
) -> None:
    source_map = {source["source_unit_id"]: source for source in draft["sources"]}
    active_topics = {
        course_id: {
            source["topic"]
            for source in draft["sources"]
            if source["active"] and source["course_id"] == course_id
        }
        for course_id in {source["course_id"] for source in draft["sources"]}
    }

    for case in draft["cases"]:
        if case["slice"] == "cross-course":
            tempting = source_map[case["tempting_source_ids"][0]]
            assert tempting["course_id"] != case["course_id"]
            assert tempting["topic"] not in active_topics[case["course_id"]]
        if case["case_id"].startswith("esv2-near-abstain-"):
            tempting = source_map[case["tempting_source_ids"][0]]
            assert tempting["course_id"] == case["course_id"]
            topic_token = tempting["topic"].replace("-", " ").removesuffix("s")
            assert topic_token in case["question"].casefold()


def test_permission_slice_spans_distinct_superseded_source_pairs(draft: dict) -> None:
    source_map = {source["source_unit_id"]: source for source in draft["sources"]}
    cases = [case for case in draft["cases"] if case["slice"] == "permission-version"]
    logical_ids = {
        source_map[case["evidence"][0]["source_unit_id"]]["logical_source_id"]
        for case in cases
    }

    assert len(cases) == len(logical_ids) == 10
    for logical_id in logical_ids:
        versions = [
            source for source in draft["sources"] if source["logical_source_id"] == logical_id
        ]
        assert Counter(source["active"] for source in versions) == Counter(
            {True: 1, False: 1}
        )


def test_answer_slices_are_stratified_across_all_courses(draft: dict) -> None:
    for slice_name in (
        "direct",
        "multi-evidence",
        "multimodal",
        "near-domain",
        "paraphrase",
        "permission-version",
    ):
        course_ids = {
            case["course_id"]
            for case in draft["cases"]
            if case["slice"] == slice_name and case["expected_action"] == "answer"
        }
        assert len(course_ids) == 6


def test_review_packet_is_bounded_and_every_case_remains_pending(draft: dict) -> None:
    assert len(draft["priority_review_case_ids"]) == 12
    assert len(set(draft["priority_review_case_ids"])) == 12
    assert all(
        case["review_status"] == "pending-independent-review"
        for case in draft["cases"]
    )
    assert draft["review"] == {
        "structural_review": "pending",
        "independent_advisory_review": "pending",
        "human_priority_review": "pending",
        "freeze_eligible": False,
    }


def test_write_mode_is_blocked_by_repository_execution_freeze(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    output = tmp_path / "must-not-exist.json"
    monkeypatch.setattr(
        "sys.argv",
        ["build_evidence_sufficiency_v2_decision_draft", "--write", "--output", str(output)],
    )

    with pytest.raises(RepositoryFreezeError, match="dataset_generation"):
        main()
    assert not output.exists()


@pytest.mark.parametrize("mutation", ["quote", "source", "duplicate"])
def test_validator_rejects_corrupted_truth_or_duplicate_question(
    draft: dict,
    mutation: str,
) -> None:
    changed = payload_without_hash(draft)
    answer = next(case for case in changed["cases"] if case["expected_action"] == "answer")
    if mutation == "quote":
        answer["evidence"][0]["quote"] = "fabricated evidence"
        pattern = "quote"
    elif mutation == "source":
        answer["evidence"][0]["source_unit_id"] = "unknown-source"
        pattern = "source"
    else:
        changed["cases"][1]["question"] = changed["cases"][0]["question"]
        pattern = "questions"

    with pytest.raises(DecisionDraftError, match=pattern):
        validate_draft(changed)
