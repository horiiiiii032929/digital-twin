"""Tests for provider-qualification analysis validation and statistics."""

import copy
import random

import pytest

from scripts.analyze_cross_course_provider_result import (
    analyze,
    bootstrap_mean_interval,
    exact_two_sided_sign_p_value,
)


def qualification_result() -> dict:
    rows = []
    for index in range(40):
        is_positive = index < 35
        for method in ("M0", "M1", "M2", "M3"):
            row = {
                "case_id": f"case-{index:02d}",
                "method": method,
                "is_positive": is_positive,
            }
            if is_positive:
                row["ranking"] = {
                    "complete_evidence_at_3": float(method != "M0"),
                }
            rows.append(row)
    aggregate = {
        method: {
            "complete_evidence_success_at_3": float(method != "M0"),
            "evidence_recall_at_1": 0.5,
            "evidence_recall_at_3": 0.75,
            "evidence_recall_at_5": 0.9,
            "ndcg_at_10": 0.8,
            "mrr": 0.8,
            "course_isolation_violations": 0,
            "latency_p50_ms": 10.0,
            "latency_p95_ms": 20.0,
        }
        for method in ("M0", "M1", "M2", "M3")
    }
    return {
        "status": "development_provider_qualification",
        "qualification_id": "cross-course-provider-qualification-v1",
        "provider_pair": {
            "pair_id": "local-qwen3-0-6b",
            "embedding": {},
            "reranking": {},
        },
        "development_case_count": 40,
        "heldout_file_reads": 0,
        "heldout_ledger_status": "unopened",
        "cases": rows,
        "aggregate": aggregate,
        "hard_gates": {
            "complete_40_case_run": True,
            "heldout_file_reads": 0,
            "course_isolation_violations": 0,
            "provider_failures": 0,
            "cost_cap_passed": True,
        },
        "dataset_id": "dataset",
        "dataset_version": "v1",
        "dataset_seal_id": "seal",
        "development_sha256": "a" * 64,
        "configuration": {
            "ladder": {},
            "device": "mps",
            "dtype": "float16",
            "batch_size": 8,
        },
        "operational": {
            "corpus_load_seconds": 1.0,
            "embedding_index_build_seconds": 2.0,
            "peak_rss_bytes": 3,
            "local_model_cache_bytes": 4,
            "total_provider_usage": {
                "request_count": 1,
                "input_tokens": 2,
                "retry_count": 0,
                "failure_count": 0,
                "approximate_cost_usd": 0.0,
            },
        },
        "implementation_tree_sha256": "b" * 64,
        "git_revision": "c" * 40,
        "git_dirty": False,
        "limitations": [],
    }


def test_analyze_accepts_complete_development_control() -> None:
    result = analyze(qualification_result(), samples=1000, seed=5106)

    assert result["dataset"]["heldout_file_reads"] == 0
    assert result["methods"]["M3"]["complete_evidence_success_at_3"] == 1.0
    assert result["decision"]["provider_selected"] is False


def test_analyze_rejects_heldout_access() -> None:
    source = qualification_result()
    source["heldout_file_reads"] = 1

    with pytest.raises(ValueError, match="heldout file was read"):
        analyze(source, samples=1000, seed=5106)


def test_statistics_are_seeded_and_handle_ties() -> None:
    assert bootstrap_mean_interval(
        [0.0, 1.0, 1.0, 1.0],
        samples=1000,
        rng=random.Random(5106),
    ) == [0.25, 1.0]
    assert exact_two_sided_sign_p_value(0, 0) == 1.0
    assert exact_two_sided_sign_p_value(6, 0) == 0.03125


def test_analyze_rejects_duplicate_case_method_rows() -> None:
    source = qualification_result()
    source["cases"][-1] = copy.deepcopy(source["cases"][0])

    with pytest.raises(ValueError, match="not unique"):
        analyze(source, samples=1000, seed=5106)
