from __future__ import annotations

from collections import Counter
import json

from scripts import (
    build_governed_full_autonomy_v2_1_grounding_successor_011 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_grounding_successor_011 as runner,
)


def test_frozen_successor_is_fresh_balanced_and_network_free() -> None:
    result = runner.validate()

    assert result["status"] == "valid"
    assert result["case_count"] == 500
    assert result["control_case_count"] == 100
    assert result["control_complete_cluster_count"] == 20
    assert result["source_region_count"] == 300
    assert result["provider_calls"] == 0
    assert result["cost_usd"] == 0


def test_control_contains_five_complete_clusters_per_primary_course() -> None:
    cases, _gold, _chunks = builder.load_inputs()
    selected = set(builder.control_case_ids(cases))
    rows = [case for case in cases if case.case_id in selected]
    clusters = Counter(case.cluster_id for case in rows)
    assert set(clusters.values()) == {5}

    primary_courses = Counter()
    for cluster_id in sorted(clusters):
        course_counts = Counter(
            case.course_id for case in rows if case.cluster_id == cluster_id
        )
        primary = min(course_counts, key=lambda value: (-course_counts[value], value))
        primary_courses[primary] += 1
    assert primary_courses == {
        "computer-networking": 5,
        "data-structures": 5,
        "operating-systems": 5,
        "python-programming": 5,
    }


def test_instrument_forbids_provider_execution() -> None:
    instrument = json.loads(runner.INSTRUMENT.read_text(encoding="utf-8"))

    assert instrument["provider_execution_authorized"] is False
    assert instrument["maximum_provider_calls"] == 0
    assert instrument["maximum_cost_usd"] == 0
    assert instrument["quality_failure_rerun_allowed"] is False
