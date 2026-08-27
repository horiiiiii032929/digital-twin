from __future__ import annotations

from collections import Counter

from scripts.build_academic_factual_qa_open_10000 import (
    MAX_CLUSTERS_PER_SECTION,
    build_recommended_source_plan,
    feasibility_report,
    preflight,
    validate_design,
)
from src.digital_twin.evaluation import (
    SourceClusterV1,
    build_deterministic_cluster_truth,
)


def test_requested_allocation_is_rejected_and_correction_is_feasible() -> None:
    report = feasibility_report()

    assert report["requested_feasible"] is False
    assert set(report["requested_failures"]) == {
        "computer-networking",
        "data-structures",
    }
    assert report["recommended_inventory_feasible"] is True


def test_recommended_plan_is_stable_stratified_and_non_overlapping() -> None:
    first = build_recommended_source_plan()
    second = build_recommended_source_plan()

    assert first["content_sha256"] == second["content_sha256"]
    assert first["cluster_count"] == 2100
    assert first["case_count_after_accepted_generation"] == 10500
    clusters = first["clusters"]
    assert Counter(row["split"] for row in clusters) == {
        "development": 100,
        "final": 2000,
    }
    assert Counter(row["course_id"] for row in clusters) == {
        "operating-systems": 396,
        "computer-networking": 450,
        "data-structures": 350,
        "python-programming": 904,
    }
    assert min(len(row["text"]) for row in clusters) >= 100
    assert min(len(row["text"].split()) for row in clusters) >= 4
    assert Counter(row["answerable_slices"][-1] for row in clusters if row["split"] == "final") == {
        "multi-evidence": 1000,
        "structured-code": 700,
        "structured-equation": 250,
        "structured-table": 50,
    }
    assert all(
        not row["answerable_slices"][-1].startswith("structured-")
        or row["answerable_slices"][-1] == row["source_modality"]
        for row in clusters
    )
    assert max(Counter(row["source_family_id"] for row in clusters).values()) <= MAX_CLUSTERS_PER_SECTION
    ranges: dict[tuple[str, str], list[tuple[int, int]]] = {}
    for row in clusters:
        key = (row["course_id"], row["source_path"])
        candidate = (row["char_start"], row["char_end"])
        assert all(
            max(candidate[0], left) >= min(candidate[1], right)
            for left, right in ranges.setdefault(key, [])
        )
        ranges[key].append(candidate)


def test_frozen_allocation_passes_but_attempt_003_revokes_preflight() -> None:
    validation = validate_design()
    live = preflight()

    assert validation["status"] == "passed-build-only-allocation-frozen"
    assert live["status"] == "blocked-not-authorized"
    assert "source-allocation-not-approved" not in live["blockers"]
    assert "dataset-construction-authorized-false" in live["blockers"]
    assert live["provider_calls"] == 0


def test_all_2100_source_windows_yield_deterministic_truth_without_provider_calls() -> None:
    plan = build_recommended_source_plan()
    cases = 0
    for payload in plan["clusters"]:
        cluster = SourceClusterV1.model_validate(payload)
        truth = build_deterministic_cluster_truth(
            cluster,
            course_ids=(
                "operating-systems",
                "computer-networking",
                "data-structures",
                "python-programming",
            ),
        )
        assert len(truth.questions) == 5
        cases += len(truth.questions)

    assert cases == 10_500
