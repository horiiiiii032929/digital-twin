from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.build_academic_factual_qa_source_aligned_confirmation import (
    TARGET_ALLOCATION,
    build_packages,
)
from src.digital_twin.evaluation.factual_qa_contract import EvaluationGoldV1
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    FiniteRetrievalEvaluationError,
    validate_exact_reference_matchability,
)
from src.digital_twin.grounding.models import DocumentChunk


@pytest.fixture(scope="module")
def packages():
    return build_packages()


def test_source_aligned_confirmation_is_fresh_balanced_and_matchable(packages) -> None:
    source = packages["packages"]["source"]
    cases = packages["packages"]["cases"]
    gold = packages["packages"]["gold"]

    assert packages["cluster_count"] == 100
    assert packages["case_count"] == 500
    assert packages["matchability"]["missing_reference_count"] == 0
    assert source["source_family_disjoint_from_afqc_100"] is True
    assert source["target_allocation"] == TARGET_ALLOCATION
    assert cases["source_plan_sha256"] == source["content_sha256"]
    assert gold["source_plan_sha256"] == source["content_sha256"]
    assert packages["provider_calls"] == 0


def test_region_ids_are_source_derived_and_shared_by_gold_and_runtime(packages) -> None:
    source = packages["packages"]["source"]
    gold = packages["packages"]["gold"]
    runtime_ids = {row["region_id"] for row in source["chunks"]}
    gold_ids = {
        evidence["region_id"]
        for row in gold["gold"]
        for claim in row["claims"]
        for evidence in claim["evidence_refs"]
    }

    assert None not in runtime_ids
    assert gold_ids <= runtime_ids
    assert all(value.startswith("source-region-") for value in gold_ids)


def test_missing_region_fails_before_ranking(packages) -> None:
    chunks = [DocumentChunk.model_validate(row) for row in packages["packages"]["source"]["chunks"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in packages["packages"]["gold"]["gold"]]
    mutated = deepcopy(chunks)
    mutated.pop()

    with pytest.raises(FiniteRetrievalEvaluationError, match="cannot exactly match"):
        validate_exact_reference_matchability(gold=gold, chunks=mutated)
