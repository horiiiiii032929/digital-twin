from __future__ import annotations

from collections import Counter
import json

import pytest

from scripts.build_factual_qa_v3_10000_blueprints import (
    ANSWERABLE_SLICES,
    SLICE_COUNTS,
    STAGE_COUNTS,
    build_artifact,
    build_blueprints,
    build_sources,
    validate_design,
    validate_instrument,
)
from src.digital_twin.repository_freeze import RepositoryFreezeError


@pytest.fixture(scope="module")
def artifact() -> dict[str, object]:
    return build_artifact()


def test_builds_exact_unique_source_claim_and_case_grains(
    artifact: dict[str, object],
) -> None:
    sources = artifact["sources"]
    blueprints = artifact["blueprints"]
    assert isinstance(sources, list)
    assert isinstance(blueprints, list)

    source_ids = [source["source_unit_id"] for source in sources]
    claim_ids = [claim["claim_id"] for source in sources for claim in source["claims"]]
    blueprint_ids = [case["blueprint_id"] for case in blueprints]
    assert len(source_ids) == len(set(source_ids)) == 1_000
    assert len(claim_ids) == len(set(claim_ids)) == 8_000
    assert len(blueprint_ids) == len(set(blueprint_ids)) == 10_000


def test_instrument_keeps_truth_and_execution_boundaries_closed() -> None:
    instrument = validate_instrument()
    assert "LLM vote or agreement" in instrument["ground_truth_policy"]
    assert instrument["execution_safety"]["provider_execution_authorized"] is False
    assert instrument["execution_safety"]["dataset_write_authorized"] is False
    assert instrument["decision_rule"]["authorize_10000_by_this_instrument"] is False
    stage_call_limits = sum(stage["maximum_provider_calls"] for stage in instrument["stages"])
    assert stage_call_limits == instrument["execution_safety"]["full_scale_maximum_calls"]
    assert stage_call_limits == 21_206


def test_preserves_exact_slice_stage_course_and_modality_distributions(
    artifact: dict[str, object],
) -> None:
    sources = artifact["sources"]
    blueprints = artifact["blueprints"]
    assert Counter(case["slice"] for case in blueprints) == Counter(SLICE_COUNTS)
    assert Counter(case["checkpoint_stage"] for case in blueprints) == Counter(
        STAGE_COUNTS
    )
    assert set(Counter(case["course_id"] for case in blueprints).values()) == {500}
    for stage, expected_per_course in (
        ("pilot-100", 5),
        ("checkpoint-1000", 45),
        ("scale-10000", 450),
    ):
        stage_courses = Counter(
            case["course_id"]
            for case in blueprints
            if case["checkpoint_stage"] == stage
        )
        assert len(stage_courses) == 20
        assert set(stage_courses.values()) == {expected_per_course}
    modality_counts = Counter(source["modality"] for source in sources)
    assert modality_counts == {
        "text": 500,
        "code": 120,
        "table": 120,
        "diagram": 80,
        "equation": 60,
        "screenshot": 60,
        "scanned": 60,
    }


def test_multimodal_sources_have_inspectable_truth_representations(
    artifact: dict[str, object],
) -> None:
    sources = artifact["sources"]
    expected_kinds = {
        "text": "paragraph",
        "code": "code",
        "table": "table",
        "diagram": "diagram",
        "equation": "equation",
        "screenshot": "screenshot-layout",
        "scanned": "scanned-document",
    }
    for source in sources:
        assert source["representation"]["kind"] == expected_kinds[source["modality"]]
        rendered = json.dumps(source["representation"], sort_keys=True)
        assert all(claim["evidence_quote"] in rendered for claim in source["claims"])


def test_all_targets_and_evidence_have_exact_referential_integrity(
    artifact: dict[str, object],
) -> None:
    sources = artifact["sources"]
    blueprints = artifact["blueprints"]
    source_ids = {source["source_unit_id"] for source in sources}
    claim_sources = {
        claim["claim_id"]: source["source_unit_id"]
        for source in sources
        for claim in source["claims"]
    }
    for case in blueprints:
        assert set(case["evidence_unit_ids"]) == {
            claim_sources[claim_id] for claim_id in case["target_claim_ids"]
        }
        assert set(case["distractor_unit_ids"]).issubset(source_ids)
        if case["slice"] == "multi-source":
            assert len(set(case["evidence_unit_ids"])) == 2
        if case["slice"] in ANSWERABLE_SLICES:
            assert case["expected_action"] == "answer"


def test_boundary_actions_are_explicit(artifact: dict[str, object]) -> None:
    blueprints = artifact["blueprints"]
    expected = {
        "no-evidence": "abstain",
        "ambiguous": "clarify",
        "cross-course-confusion": "answer",
        "academic-integrity": "refuse",
    }
    for case in blueprints:
        if case["slice"] in expected:
            assert case["expected_action"] == expected[case["slice"]]
        if case["slice"] in {"no-evidence", "academic-integrity"}:
            assert case["target_claim_ids"] == []
            assert case["evidence_unit_ids"] == []


def test_build_is_byte_stable_and_uses_no_private_data(
    artifact: dict[str, object],
) -> None:
    second_sources = build_sources()
    second_blueprints = build_blueprints(second_sources)
    second_summary = validate_design(second_sources, second_blueprints)
    assert artifact["summary"]["content_sha256"] == second_summary["content_sha256"]
    assert artifact["summary"]["external_calls"] == 0
    assert artifact["summary"]["private_data_read"] is False
    serialized = str(artifact)
    assert "Academia Vault" not in serialized
    assert "/Users/" not in serialized


def test_write_path_remains_unauthorized(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import build_factual_qa_v3_10000_blueprints as module

    monkeypatch.setattr(module, "parse_args", lambda: type("Args", (), {"write": True, "output": module.DEFAULT_OUTPUT})())
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        module.main()
