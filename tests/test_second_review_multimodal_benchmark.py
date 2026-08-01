import pytest

from scripts.second_review_multimodal_benchmark import (
    CHECK_FIELDS,
    build_case_payload,
    derive_decision,
    group_by_asset,
    make_batches,
    response_schema,
    validate_decisions,
)


def _checks(**overrides: bool) -> dict[str, bool]:
    checks = {field: True for field in CHECK_FIELDS}
    checks.update(overrides)
    return checks


def test_derive_decision_accepts_revises_and_rejects() -> None:
    assert derive_decision(_checks()) == "accept"
    assert derive_decision(_checks(modality_correct=False)) == "revise"
    assert derive_decision(_checks(claims_supported=False)) == "reject"


def test_make_batches_preserves_asset_groups() -> None:
    groups = [({"asset_id": str(index)}, []) for index in range(5)]

    batches = make_batches(groups, 2)

    assert [len(batch) for batch in batches] == [2, 2, 1]
    assert [group[0]["asset_id"] for batch in batches for group in batch] == [
        "0",
        "1",
        "2",
        "3",
        "4",
    ]
    with pytest.raises(ValueError, match="positive"):
        make_batches(groups, 0)


def test_response_schema_requires_exact_case_count() -> None:
    decisions = response_schema(3)["properties"]["decisions"]

    assert decisions["minItems"] == 3
    assert decisions["maxItems"] == 3
    assert set(CHECK_FIELDS).issubset(decisions["items"]["required"])


def test_validate_decisions_rejects_duplicate_and_missing_case_ids() -> None:
    decision = {
        "case_id": "case-1",
        **_checks(),
        "reason": "The evidence is visible.",
        "suggested_revision": "",
    }

    with pytest.raises(ValueError, match="duplicate"):
        validate_decisions({"decisions": [decision, decision]}, {"case-1"})
    with pytest.raises(ValueError, match="do not match"):
        validate_decisions({"decisions": [decision]}, {"case-2"})


def test_build_case_payload_omits_identity_and_prior_review_fields() -> None:
    case = {
        "case_id": "case-1",
        "slice": "positive",
        "modality": "diagram",
        "visual_dependency": "required",
        "query": "What connects A and B?",
        "expected_action": "retrieve",
        "required_claims": ["A connects to B"],
        "gold_region_ids": ["region-1"],
        "asset_id": "private-course-name",
        "review": {"assistant": "accept"},
    }
    asset = {
        "asset_id": "private-course-name",
        "path": "private/source.png",
        "course_id": "course-secret",
        "permission": "approved",
        "surrounding_text": "A and B",
        "regions": [
            {"region_id": "region-1", "bbox": [0.1, 0.2, 0.3, 0.4], "kind": "figure"}
        ],
    }

    payload = build_case_payload(case, asset)

    assert payload["case_id"] == "case-1"
    assert payload["gold_regions"] == [
        {"bbox_normalized_xywh": [0.1, 0.2, 0.3, 0.4], "kind": "figure"}
    ]
    assert "asset_id" not in payload
    assert "course_id" not in payload
    assert "path" not in payload
    assert "review" not in payload


def test_group_by_asset_is_deterministic() -> None:
    dataset = {
        "source_assets": [{"asset_id": "b"}, {"asset_id": "a"}],
        "cases": [
            {"case_id": "2", "asset_id": "a"},
            {"case_id": "3", "asset_id": "b"},
            {"case_id": "1", "asset_id": "a"},
        ],
    }

    groups = group_by_asset(dataset)

    assert [group[0]["asset_id"] for group in groups] == ["a", "b"]
    assert [case["case_id"] for case in groups[0][1]] == ["1", "2"]
