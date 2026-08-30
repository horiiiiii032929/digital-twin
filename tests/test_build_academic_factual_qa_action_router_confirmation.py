from __future__ import annotations

from collections import Counter, defaultdict

import pytest

from scripts import build_academic_factual_qa_action_router_confirmation as builder
from src.digital_twin.evaluation.factual_qa_contract import EvaluationGoldV1
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk


@pytest.fixture(scope="module")
def result():
    return builder.build_byte_stable_packages()


def test_action_router_confirmation_is_fresh_finite_and_balanced(result) -> None:
    source = result["packages"]["source"]
    cases = result["packages"]["cases"]["cases"]
    gold = result["packages"]["gold"]["gold"]

    assert len(source["clusters"]) == 100
    assert len(source["chunks"]) == 300
    assert len(cases) == len(gold) == 500
    assert source["source_range_disjoint_from_all_prior_development"] is True
    assert source["source_family_disjoint_from_prior_development"] is False
    assert source["private_data_used"] is False
    assert source["final_split_opened"] is False
    assert Counter(row["slice"] for row in cases) == {
        "direct-factual": 100,
        "paraphrased": 100,
        "definition-explanation": 100,
        "structured-code": 27,
        "structured-equation": 11,
        "structured-table": 10,
        "multi-evidence": 52,
        "no-evidence": 25,
        "cross-course": 25,
        "ambiguity": 25,
        "academic-integrity": 25,
    }


def test_action_router_confirmation_ranges_do_not_overlap_prior_packages(result) -> None:
    prior = builder._prior_ranges()  # noqa: SLF001
    for chunk in result["packages"]["source"]["chunks"]:
        metadata = chunk["metadata"]
        start = int(metadata["char_start"])
        end = int(metadata["char_end"])
        assert not any(
            max(start, left) < min(end, right)
            for left, right in prior[
                (str(metadata["course_id"]), str(metadata["source_path"]))
            ]
        )


def test_action_router_confirmation_has_unique_atoms_questions_and_gold(result) -> None:
    source = result["packages"]["source"]
    cases = result["packages"]["cases"]["cases"]
    chunks = [DocumentChunk.model_validate(row) for row in source["chunks"]]
    gold = [
        EvaluationGoldV1.model_validate(row)
        for row in result["packages"]["gold"]["gold"]
    ]
    by_cluster = Counter(row.metadata["parent_cluster_id"] for row in chunks)
    by_source: dict[tuple[str, int, str], list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        by_source[
            (
                str(chunk.source_artifact_id),
                chunk.source_version,
                chunk.source_checksum,
            )
        ].append(chunk)
    for rows in by_source.values():
        ordered = sorted(rows, key=lambda row: int(row.metadata["char_start"]))
        for left, right in zip(ordered, ordered[1:]):
            assert int(left.metadata["char_end"]) <= int(
                right.metadata["char_start"]
            )
    normalized = [normalize_question(row["question"]) for row in cases]
    matchability = validate_exact_reference_matchability(gold=gold, chunks=chunks)

    assert set(by_cluster.values()) == {3}
    assert len(normalized) == len(set(normalized)) == 500
    assert matchability["missing_reference_count"] == 0
    assert result["byte_stable"] is True
    assert result["provider_calls"] == 0
