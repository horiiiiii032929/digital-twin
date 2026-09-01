from __future__ import annotations

from collections import Counter, defaultdict
import json

import pytest

from scripts import build_academic_factual_qa_source_semantic_atoms as builder
from src.digital_twin.evaluation.factual_qa_contract import EvaluationGoldV1
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.semantic_evidence_atoms import ATOM_VERSION
from src.digital_twin.grounding.source_range_evidence import canonicalize_source_claim


@pytest.fixture(scope="module")
def result():
    return builder.build_byte_stable_packages()


def test_source_semantic_atom_successor_is_fresh_balanced_and_finite(result) -> None:
    source = result["packages"]["source"]
    cases = result["packages"]["cases"]["cases"]
    gold = result["packages"]["gold"]["gold"]

    assert len(source["clusters"]) == 100
    assert len(source["chunks"]) == 300
    assert len(cases) == len(gold) == 500
    assert Counter(row["course_id"] for row in source["clusters"]) == {
        "operating-systems": 25,
        "computer-networking": 25,
        "data-structures": 25,
        "python-programming": 25,
    }
    assert source["source_range_disjoint_from_all_prior_development"] is True
    assert source["semantic_atom_version"] == ATOM_VERSION
    assert source["provider_calls"] == 0
    assert source["private_data_used"] is False
    assert source["final_split_opened"] is False


def test_source_semantic_atoms_are_exact_matchable_and_related(result) -> None:
    source = result["packages"]["source"]
    chunks = [DocumentChunk.model_validate(row) for row in source["chunks"]]
    gold = [
        EvaluationGoldV1.model_validate(row)
        for row in result["packages"]["gold"]["gold"]
    ]
    by_cluster: dict[str, list[DocumentChunk]] = defaultdict(list)
    for chunk in chunks:
        by_cluster[str(chunk.metadata["parent_cluster_id"])].append(chunk)

    assert set(len(rows) for rows in by_cluster.values()) == {3}
    for rows in by_cluster.values():
        identifiers = {row.id for row in rows}
        for row in rows:
            assert set(json.loads(row.metadata["semantic_related_atom_ids"])) == (
                identifiers - {row.id}
            )
            assert canonicalize_source_claim(
                row.text, modality=row.metadata["modality"]
            ) in row.metadata["semantic_search_text"]
    assert validate_exact_reference_matchability(gold=gold, chunks=chunks) == {
        "required_reference_count": 474,
        "matched_reference_count": 474,
        "missing_reference_count": 0,
    }


def test_source_semantic_atom_questions_are_unique_and_byte_stable(result) -> None:
    questions = [
        normalize_question(row["question"])
        for row in result["packages"]["cases"]["cases"]
    ]

    assert len(questions) == len(set(questions)) == 500
    assert result["byte_stable"] is True
