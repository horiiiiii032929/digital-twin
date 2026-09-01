from __future__ import annotations

from collections import Counter

from scripts import build_cross_engine_sealed_confirmation_010 as builder


def test_sealed_confirmation_is_byte_stable_source_disjoint_and_balanced() -> None:
    result = builder.build_byte_stable_packages()
    source = result["packages"]["source"]
    cases = result["packages"]["cases"]["cases"]
    gold = result["packages"]["gold"]["gold"]

    assert result["byte_stable"] is True
    assert result["cluster_count"] == 200
    assert result["case_count"] == 1_000
    assert result["matchability"]["missing_reference_count"] == 0
    assert source["source_range_disjoint_from_all_prior_development"] is True
    assert source["selection_diagnostics"]["maximum_clusters_per_source_family"] <= 5
    assert len({row["case_id"] for row in cases}) == 1_000
    assert {row["case_id"] for row in cases} == {row["case_id"] for row in gold}
    assert Counter(row["expected_action"] for row in gold) == {
        "answer": 800,
        "abstain": 100,
        "clarify": 50,
        "refuse": 50,
    }


def test_sealed_confirmation_contains_structured_source_modalities() -> None:
    source = builder.build_packages()["packages"]["source"]
    observed = Counter(
        (row["course_id"], row["source_modality"])
        for row in source["clusters"]
    )

    assert observed == Counter(
        {
            (course_id, modality): count
            for course_id, allocation in builder.TARGET_ALLOCATION.items()
            for modality, count in allocation.items()
        }
    )
