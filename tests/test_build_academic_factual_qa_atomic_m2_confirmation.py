from __future__ import annotations

from collections import Counter, defaultdict

import pytest

from scripts.build_academic_factual_qa_atomic_m2_confirmation import (
    INSTRUMENT_ID,
    PROGRAM_ID,
    TARGET_ALLOCATION,
    _json_bytes,
    build_byte_stable_packages,
    build_packages,
    excluded_source_families,
)
from src.digital_twin.evaluation.factual_qa_contract import EvaluationGoldV1
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk


@pytest.fixture(scope="module")
def result():
    return build_byte_stable_packages()


def test_atomic_m2_allocation_and_package_bounds(result) -> None:
    source = result["packages"]["source"]
    cases = result["packages"]["cases"]
    gold = result["packages"]["gold"]
    observed = Counter(
        (row["course_id"], row["source_modality"]) for row in source["clusters"]
    )
    expected = {
        (course_id, modality): count
        for course_id, allocation in TARGET_ALLOCATION.items()
        for modality, count in allocation.items()
    }

    assert result["program_id"] == PROGRAM_ID
    assert result["instrument_id"] == INSTRUMENT_ID
    assert result["cluster_count"] == source["cluster_count"] == 100
    assert result["case_count"] == cases["case_count"] == gold["case_count"] == 500
    assert dict(observed) == expected
    assert source["target_allocation"] == TARGET_ALLOCATION
    assert source["registered_region_count"] == 300
    assert source["public_sources_only"] is True
    assert source["private_data_read"] is False
    assert source["final_split_opened"] is False
    assert result["provider_calls"] == 0


def test_atomic_m2_families_are_disjoint_from_both_prior_sets(result) -> None:
    source = result["packages"]["source"]
    selected = {row["source_family_id"] for row in source["clusters"]}
    excluded = excluded_source_families()

    assert selected.isdisjoint(excluded["historical_build_source_plan"])
    assert selected.isdisjoint(excluded["afqc_103_source_package"])
    assert source["source_family_disjoint_from_historical_build_source_plan"] is True
    assert source["source_family_disjoint_from_afqc_103"] is True


def test_atomic_regions_and_normalized_questions_are_non_overlapping_and_unique(
    result,
) -> None:
    source = result["packages"]["source"]
    cases = result["packages"]["cases"]
    by_source: dict[tuple[str, int, str], list[dict]] = defaultdict(list)
    for chunk in source["chunks"]:
        assert chunk["metadata"]["search_description"]
        by_source[
            (
                chunk["source_artifact_id"],
                chunk["source_version"],
                chunk["source_checksum"],
            )
        ].append(chunk)
    for chunks in by_source.values():
        ordered = sorted(chunks, key=lambda row: int(row["metadata"]["char_start"]))
        for left, right in zip(ordered, ordered[1:]):
            assert int(left["metadata"]["char_end"]) <= int(
                right["metadata"]["char_start"]
            )

    normalized = [normalize_question(row["question"]) for row in cases["cases"]]
    assert len(normalized) == len(set(normalized)) == 500
    assert source["authoritative_evidence_unit"] == "minimal-non-overlapping-atom"
    assert source["authoritative_regions_non_overlapping"] is True
    assert source["parent_cluster_context_usage"] == "search-metadata-only"
    assert result["answer_atom_mapping"]["uniquely_mapped_answer_span_count"] > 0


def test_atomic_gold_is_exactly_matchable(result) -> None:
    chunks = [
        DocumentChunk.model_validate(row) for row in result["packages"]["source"]["chunks"]
    ]
    gold = [
        EvaluationGoldV1.model_validate(row)
        for row in result["packages"]["gold"]["gold"]
    ]
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)

    assert matchability["missing_reference_count"] == 0
    assert matchability["required_reference_count"] == result["answer_atom_mapping"][
        "uniquely_mapped_answer_span_count"
    ]


def test_atomic_packages_are_byte_stable(result) -> None:
    rebuilt = build_packages()

    assert result["byte_stable"] is True
    for key in ("source", "cases", "gold"):
        assert _json_bytes(result["packages"][key]) == _json_bytes(
            rebuilt["packages"][key]
        )
