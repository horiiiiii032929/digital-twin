#!/usr/bin/env python3
"""Compare baseline and candidate M2 dependency compatibility artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


QUALITY_METRICS = (
    "complete_evidence_success_at_3",
    "evidence_recall_at_3",
    "ndcg_at_10",
    "mrr",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"compatibility artifact must be an object: {path}")
    return value


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    same_binding = baseline.get("binding") == candidate.get("binding")
    same_case_ids = set(baseline.get("top3_by_case", {})) == set(
        candidate.get("top3_by_case", {})
    )
    exact_top3 = (
        same_case_ids
        and baseline.get("top3_by_case") == candidate.get("top3_by_case")
    )
    quality = {
        name: {
            "baseline": baseline.get("aggregate", {}).get(name),
            "candidate": candidate.get("aggregate", {}).get(name),
            "passed": (
                candidate.get("aggregate", {}).get(name) is not None
                and baseline.get("aggregate", {}).get(name) is not None
                and candidate["aggregate"][name] >= baseline["aggregate"][name]
            ),
        }
        for name in QUALITY_METRICS
    }
    baseline_latency = baseline.get("aggregate", {}).get(
        "latency_p95_ms_median"
    )
    candidate_latency = candidate.get("aggregate", {}).get(
        "latency_p95_ms_median"
    )
    latency_ratio = (
        candidate_latency / baseline_latency
        if baseline_latency and candidate_latency is not None
        else None
    )
    gates = {
        "complete_control_and_candidate": (
            baseline.get("status") == "complete"
            and candidate.get("status") == "complete"
            and baseline.get("label") == "baseline"
            and candidate.get("label") == "candidate"
        ),
        "clean_revisions": (
            baseline.get("working_tree_dirty") is False
            and candidate.get("working_tree_dirty") is False
        ),
        "same_frozen_binding": same_binding,
        "all_40_case_ids_match": same_case_ids and len(baseline.get("top3_by_case", {})) == 40,
        "all_top3_rankings_identical": exact_top3,
        "quality_metrics_do_not_regress": all(
            metric["passed"] for metric in quality.values()
        ),
        "zero_course_isolation_violations": (
            baseline.get("aggregate", {}).get("course_isolation_violations") == 0
            and candidate.get("aggregate", {}).get("course_isolation_violations")
            == 0
        ),
        "no_heldout_or_external_calls": all(
            artifact.get("binding", {}).get("heldout_file_reads") == 0
            and artifact.get("binding", {}).get("external_provider_calls") == 0
            for artifact in (baseline, candidate)
        ),
        "candidate_p95_latency_within_20_percent": (
            latency_ratio is not None and latency_ratio <= 1.20
        ),
    }
    return {
        "comparison_id": "dependency-compatibility-python-ml-001",
        "status": "complete",
        "decision": "keep" if all(gates.values()) else "drop",
        "baseline": {
            "evaluation_id": baseline.get("evaluation_id"),
            "code_revision": baseline.get("code_revision"),
            "dependencies": baseline.get("runtime", {}).get("dependencies"),
        },
        "candidate": {
            "evaluation_id": candidate.get("evaluation_id"),
            "code_revision": candidate.get("code_revision"),
            "dependencies": candidate.get("runtime", {}).get("dependencies"),
        },
        "quality": quality,
        "latency": {
            "baseline_p95_ms_median": baseline_latency,
            "candidate_p95_ms_median": candidate_latency,
            "candidate_to_baseline_ratio": latency_ratio,
            "maximum_ratio": 1.20,
        },
        "gates": gates,
    }


def main() -> None:
    arguments = parse_args()
    result = compare(load_json(arguments.baseline), load_json(arguments.candidate))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(f"{json.dumps(result, indent=2)}\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if result["decision"] != "keep":
        raise SystemExit("ML dependency compatibility gates failed")


if __name__ == "__main__":
    main()
