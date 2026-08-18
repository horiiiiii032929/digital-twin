import copy

from scripts.compare_ml_dependency_compatibility import compare


def _artifact(label: str) -> dict:
    return {
        "evaluation_id": f"dependency-compatibility-{label}",
        "status": "complete",
        "label": label,
        "code_revision": f"{label}-revision",
        "working_tree_dirty": False,
        "runtime": {
            "dependencies": {
                "torch": "2.9.1" if label == "baseline" else "2.13.0",
                "transformers": "4.57.6" if label == "baseline" else "5.15.0",
            }
        },
        "binding": {
            "profile": "student-tutor-v1",
            "heldout_file_reads": 0,
            "external_provider_calls": 0,
        },
        "aggregate": {
            "complete_evidence_success_at_3": 0.8,
            "evidence_recall_at_3": 0.8,
            "ndcg_at_10": 0.8,
            "mrr": 0.8,
            "course_isolation_violations": 0,
            "latency_p95_ms_median": 100 if label == "baseline" else 119,
        },
        "top3_by_case": {
            f"case-{index:02d}": ["a", "b", "c"] for index in range(40)
        },
    }


def test_dependency_compatibility_accepts_exact_rankings_and_bounded_latency():
    result = compare(_artifact("baseline"), _artifact("candidate"))

    assert result["decision"] == "keep"
    assert all(result["gates"].values())


def test_dependency_compatibility_rejects_ranking_or_quality_regression():
    baseline = _artifact("baseline")
    candidate = copy.deepcopy(_artifact("candidate"))
    candidate["top3_by_case"]["case-00"] = ["b", "a", "c"]
    candidate["aggregate"]["mrr"] = 0.79

    result = compare(baseline, candidate)

    assert result["decision"] == "drop"
    assert result["gates"]["all_top3_rankings_identical"] is False
    assert result["gates"]["quality_metrics_do_not_regress"] is False
