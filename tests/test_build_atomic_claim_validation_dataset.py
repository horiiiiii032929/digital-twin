from __future__ import annotations

import json

from scripts.build_atomic_claim_validation_dataset import (
    DEFAULT_OUTPUT,
    build_dataset,
)


def test_atomic_claim_confirmation_dataset_is_stable_and_stratified() -> None:
    first = build_dataset()
    second = build_dataset()

    assert first == second
    assert first["case_count"] == 120
    assert first["releasable_case_count"] == 40
    assert first["reject_case_count"] == 80
    assert set(first["slices"].values()) == {10}
    assert len(first["slices"]) == 12
    assert len({case["case_id"] for case in first["cases"]}) == 120


def test_frozen_atomic_claim_dataset_matches_the_builder() -> None:
    frozen = json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))

    assert frozen == build_dataset()
    assert frozen["status"] == "frozen-unopened"
    assert frozen["data_boundary"] == "synthetic-public-only"


def test_every_releasable_case_has_only_eligible_declared_lineage() -> None:
    dataset = build_dataset()

    for case in dataset["cases"]:
        if not case["expected_releasable"]:
            continue
        eligible = {
            hit["hit_id"]
            for hit in case["hits"]
            if hit["retrieval_allowed"]
        }
        assert case["claims"]
        for claim in case["claims"]:
            assert claim["evidence_hit_ids"]
            assert set(claim["evidence_hit_ids"]).issubset(eligible)


def test_every_reject_case_has_a_named_failure_slice() -> None:
    dataset = build_dataset()

    for case in dataset["cases"]:
        if case["expected_releasable"]:
            assert case["mutation_class"] is None
        else:
            assert case["mutation_class"]
