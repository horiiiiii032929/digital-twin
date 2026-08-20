#!/usr/bin/env python3
"""Sanitize, compare, and record the one-time held-out retrieval result."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed

from scripts.draft_cross_course_benchmark import ROOT


METHODS = ("M0", "M1", "M2", "M3")
LABELS = {
    "M0": "BM25",
    "M1": "Qwen3 dense",
    "M2": "BM25 + dense RRF",
    "M3": "Hybrid + Qwen3 reranker",
}
IMPLEMENTATIONS = {
    "M0": "bm25-v1",
    "M1": "qwen3-dense-v1",
    "M2": "qwen3-hybrid-v1",
    "M3": "qwen3-reranked-hybrid-v1",
}
COMPARISONS = (("M2", "M0"), ("M3", "M0"), ("M3", "M2"))
INPUT_PATH = (
    ROOT / "experiments/runs/cross_course_retrieval_v1/heldout-001/"
    "local-qwen3-0-6b/heldout_result.json"
)
OUTPUT_JSON = ROOT / "reports/generated/cross-course-retrieval-v1-heldout.json"
OUTPUT_CSV = ROOT / "reports/generated/cross-course-retrieval-v1-heldout.csv"
OUTPUT_PNG = ROOT / "reports/generated/cross-course-retrieval-v1-heldout.png"
OUTPUT_SVG = ROOT / "reports/generated/cross-course-retrieval-v1-heldout.svg"
OUTPUT_REPORT = ROOT / "research/05_evaluation/cross-course-retrieval-v1-heldout-results.md"
OUTPUT_RECORD = ROOT / "research/05_evaluation/records/cross-course-retrieval-v1-heldout.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--output-png", type=Path, default=OUTPUT_PNG)
    parser.add_argument("--output-svg", type=Path, default=OUTPUT_SVG)
    parser.add_argument("--output-report", type=Path, default=OUTPUT_REPORT)
    parser.add_argument("--output-record", type=Path, default=OUTPUT_RECORD)
    parser.add_argument("--bootstrap-samples", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=5106)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def bootstrap_mean_interval(
    values: list[float],
    *,
    samples: int,
    rng: random.Random,
) -> list[float]:
    require(bool(values), "bootstrap values cannot be empty")
    estimates = [
        sum(rng.choice(values) for _ in values) / len(values)
        for _ in range(samples)
    ]
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def exact_two_sided_sign_p_value(wins: int, losses: int) -> float:
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    tail = min(wins, losses)
    probability = sum(math.comb(discordant, value) for value in range(tail + 1)) / (
        2**discordant
    )
    return min(1.0, 2 * probability)


def analyze(
    result: dict[str, Any],
    *,
    samples: int,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require(
        result["status"] == "heldout_retrieval_comparison_completed",
        "input is not the completed held-out comparison",
    )
    require(result["run_id"] == "cross-course-retrieval-v1-heldout-001", "wrong run ID")
    require(result["heldout_case_count"] == 60, "expected 60 held-out cases")
    require(result["heldout_file_reads"] == 1, "expected exactly one held-out read event")
    require(result["heldout_ledger_status"] == "completed", "held-out ledger is not complete")
    require(len(result["cases"]) == 240, "expected four methods across 60 cases")
    require(all(result["hard_gates"].values()), "a global held-out hard gate failed")

    positive_ids = sorted(
        {row["case_id"] for row in result["cases"] if row["is_positive"]}
    )
    boundary_ids = sorted(
        {row["case_id"] for row in result["cases"] if not row["is_positive"]}
    )
    lookup = {(row["case_id"], row["method"]): row for row in result["cases"]}
    require(len(lookup) == 240, "case-method rows are not unique")
    require(
        all(
            (case_id, method) in lookup
            for case_id in [*positive_ids, *boundary_ids]
            for method in METHODS
        ),
        "case-method matrix is incomplete",
    )

    rng = random.Random(seed)
    methods: dict[str, Any] = {}
    latency_ceiling = 10_000.0
    for method in METHODS:
        aggregate = result["aggregate"][method]
        values = [
            float(lookup[(case_id, method)]["ranking"]["complete_evidence_at_3"])
            for case_id in positive_ids
        ]
        p95 = float(aggregate["latency_p95_ms"])
        methods[method] = {
            "label": LABELS[method],
            "implementation_id": IMPLEMENTATIONS[method],
            "positive_cases": len(values),
            "boundary_cases": len(boundary_ids),
            "complete_evidence_success_at_3": aggregate["complete_evidence_success_at_3"],
            "complete_evidence_success_at_3_ci95": bootstrap_mean_interval(
                values, samples=samples, rng=rng
            ),
            "evidence_recall_at_5": aggregate["evidence_recall_at_5"],
            "ndcg_at_10": aggregate["ndcg_at_10"],
            "mrr": aggregate["mrr"],
            "no_evidence_accuracy": aggregate["no_evidence_accuracy_calibration"],
            "latency_p50_ms": aggregate["latency_p50_ms"],
            "latency_p95_ms": p95,
            "deployment_latency_passed": p95 <= latency_ceiling,
            "course_isolation_violations": aggregate["course_isolation_violations"],
        }

    primary_quality_metrics = (
        "complete_evidence_success_at_3",
        "evidence_recall_at_5",
        "ndcg_at_10",
        "mrr",
    )
    control = methods["M0"]
    for method in METHODS:
        methods[method]["quality_floor_passed"] = all(
            methods[method][metric] >= control[metric]
            for metric in primary_quality_metrics
        )

    comparisons: dict[str, Any] = {}
    for candidate, baseline in COMPARISONS:
        differences: list[float] = []
        wins = losses = 0
        for case_id in positive_ids:
            difference = (
                float(lookup[(case_id, candidate)]["ranking"]["complete_evidence_at_3"])
                - float(lookup[(case_id, baseline)]["ranking"]["complete_evidence_at_3"])
            )
            differences.append(difference)
            wins += difference > 0
            losses += difference < 0
        comparisons[f"{candidate}_vs_{baseline}"] = {
            "complete_evidence_at_3_difference": sum(differences) / len(differences),
            "paired_bootstrap_ci95": bootstrap_mean_interval(
                differences, samples=samples, rng=rng
            ),
            "wins": wins,
            "losses": losses,
            "ties": len(differences) - wins - losses,
            "exact_two_sided_sign_p_value": exact_two_sided_sign_p_value(wins, losses),
        }

    eligible = [
        method
        for method in METHODS
        if methods[method]["deployment_latency_passed"]
        and methods[method]["quality_floor_passed"]
    ]
    ranked = sorted(
        eligible,
        key=lambda method: (
            -methods[method]["complete_evidence_success_at_3"],
            -methods[method]["evidence_recall_at_5"],
            -methods[method]["ndcg_at_10"],
            -methods[method]["mrr"],
            METHODS.index(method),
        ),
    )
    selected_method = ranked[0] if ranked else None
    decision = {
        "outcome": "keep" if selected_method else "refine",
        "selected_method": selected_method,
        "selected_implementation_id": (
            methods[selected_method]["implementation_id"] if selected_method else None
        ),
        "eligible_methods": eligible,
        "rationale": (
            f"{LABELS[selected_method]} ranked highest among methods that passed the "
            "global gates, matched or exceeded BM25 on every primary quality metric, "
            "and passed the 10-second p95 deployment ceiling; retain BM25 as rollback."
            if selected_method
            else "No method passed the hard gates, quality floor, and latency rule; retain BM25 as rollback and refine."
        ),
        "limitations": [
            "This one-time result estimates held-out text-grounded retrieval only.",
            "Image-only and layout-dependent claims remain outside the text benchmark.",
            "Latency and memory describe one local workstation and do not establish concurrent capacity.",
            "The multimodal V3 candidate was dropped separately and no multimodal profile was selected.",
        ],
    }
    analysis = {
        "result_id": "cross-course-retrieval-v1-heldout-001",
        "status": "completed",
        "component": "retriever",
        "dataset": {
            "dataset_id": result["dataset_id"],
            "dataset_version": result["dataset_version"],
            "dataset_seal_id": result["dataset_seal_id"],
            "corpus_id": result["corpus_id"],
            "development_cases": 40,
            "heldout_cases": 60,
            "positive_cases": len(positive_ids),
            "boundary_cases": len(boundary_ids),
            "development_sha256": result["development_sha256"],
            "heldout_sha256": result["heldout_sha256"],
            "heldout_file_reads": 1,
            "heldout_ledger_status": "completed",
        },
        "configuration": result["configuration"],
        "methods": methods,
        "paired_comparisons": comparisons,
        "uncertainty": {
            "method": "case-level nonparametric bootstrap",
            "samples": samples,
            "seed": seed,
            "interval": "percentile 95% confidence interval",
        },
        "hard_gates": result["hard_gates"],
        "operational": result["operational"],
        "provenance": {
            "implementation_tree_sha256": result["implementation_tree_sha256"],
            "final_config_sha256": result["final_config_sha256"],
            "git_revision": result["git_revision"],
            "git_dirty": result["git_dirty"],
        },
        "decision": decision,
        "limitations": result["limitations"],
    }
    record = build_record(result, analysis)
    return analysis, record


def build_record(result: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    control_floor = {
        metric: analysis["methods"]["M0"][metric]
        for metric in (
            "complete_evidence_success_at_3",
            "evidence_recall_at_5",
            "ndcg_at_10",
            "mrr",
        )
    }
    candidates = []
    for method in METHODS:
        values = analysis["methods"][method]
        metrics = [
            {
                "name": "heldout-complete-evidence-at-3",
                "value": values["complete_evidence_success_at_3"],
                "unit": "ratio",
                "direction": "higher-is-better",
                "threshold": control_floor["complete_evidence_success_at_3"],
                "passed": values["complete_evidence_success_at_3"]
                >= control_floor["complete_evidence_success_at_3"],
            },
            {
                "name": "heldout-evidence-recall-at-5",
                "value": values["evidence_recall_at_5"],
                "unit": "ratio",
                "direction": "higher-is-better",
                "threshold": control_floor["evidence_recall_at_5"],
                "passed": values["evidence_recall_at_5"] >= control_floor["evidence_recall_at_5"],
            },
            {
                "name": "heldout-ndcg-at-10",
                "value": values["ndcg_at_10"],
                "unit": "ratio",
                "direction": "higher-is-better",
                "threshold": control_floor["ndcg_at_10"],
                "passed": values["ndcg_at_10"] >= control_floor["ndcg_at_10"],
            },
            {
                "name": "heldout-mrr",
                "value": values["mrr"],
                "unit": "ratio",
                "direction": "higher-is-better",
                "threshold": control_floor["mrr"],
                "passed": values["mrr"] >= control_floor["mrr"],
            },
            {
                "name": "warm-latency-p95",
                "value": values["latency_p95_ms"],
                "unit": "milliseconds",
                "direction": "lower-is-better",
                "threshold": 10_000.0,
                "passed": values["deployment_latency_passed"],
            },
            {
                "name": "course-isolation-violations",
                "value": values["course_isolation_violations"],
                "unit": "count",
                "direction": "lower-is-better",
                "threshold": 0.0,
                "passed": values["course_isolation_violations"] == 0,
            },
        ]
        gates = [
            {
                "name": name,
                "passed": bool(passed),
                "evidence": "The completed one-time runner recorded the frozen held-out result."
                if passed
                else "The candidate failed this gate in the held-out comparison.",
            }
            for name, passed in result["hard_gates"].items()
        ]
        gates.append(
            {
                "name": "deployment-latency",
                "passed": values["deployment_latency_passed"],
                "evidence": f"Warm p95 was {values['latency_p95_ms']:.2f} ms versus a 10,000 ms ceiling.",
            }
        )
        candidates.append(
            {
                "implementation": {
                    "implementation_id": values["implementation_id"],
                    "version": "cross-course-retrieval-v1",
                    "configuration": {
                        "method": method,
                        "device": result["configuration"]["runtime"]["device"],
                        "dtype": result["configuration"]["runtime"]["dtype"],
                        "rerank_candidate_limit": result["configuration"]["runtime"]["rerank_candidate_limit"],
                    },
                },
                "role": "control" if method == "M0" else "candidate",
                "metrics": metrics,
                "hard_gates": gates,
                "failures_by_category": (
                    {"operational": 1}
                    if not values["deployment_latency_passed"]
                    else {}
                ),
            }
        )
    return {
        "schema_version": 1,
        "run_id": analysis["result_id"],
        "component": "retriever",
        "dataset_id": f"{result['dataset_id']}-{result['dataset_version']}-heldout",
        "corpus_id": result["corpus_id"],
        "code_revision": result["git_revision"],
        "candidates": candidates,
        "decision": {
            "outcome": analysis["decision"]["outcome"],
            "selected_implementation_id": analysis["decision"]["selected_implementation_id"],
            "rationale": analysis["decision"]["rationale"],
            "limitations": analysis["decision"]["limitations"],
        },
    }


def write_csv(path: Path, analysis: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "method",
                "label",
                "positive_cases",
                "complete_evidence_success_at_3",
                "complete_evidence_ci95_low",
                "complete_evidence_ci95_high",
                "evidence_recall_at_5",
                "ndcg_at_10",
                "mrr",
                "no_evidence_accuracy",
                "latency_p50_ms",
                "latency_p95_ms",
                "deployment_latency_passed",
                "quality_floor_passed",
                "course_isolation_violations",
            ],
        )
        writer.writeheader()
        for method in METHODS:
            values = analysis["methods"][method]
            writer.writerow(
                {
                    "method": method,
                    "label": values["label"],
                    "positive_cases": values["positive_cases"],
                    "complete_evidence_success_at_3": values["complete_evidence_success_at_3"],
                    "complete_evidence_ci95_low": values["complete_evidence_success_at_3_ci95"][0],
                    "complete_evidence_ci95_high": values["complete_evidence_success_at_3_ci95"][1],
                    "evidence_recall_at_5": values["evidence_recall_at_5"],
                    "ndcg_at_10": values["ndcg_at_10"],
                    "mrr": values["mrr"],
                    "no_evidence_accuracy": values["no_evidence_accuracy"],
                    "latency_p50_ms": values["latency_p50_ms"],
                    "latency_p95_ms": values["latency_p95_ms"],
                    "deployment_latency_passed": values["deployment_latency_passed"],
                    "quality_floor_passed": values["quality_floor_passed"],
                    "course_isolation_violations": values["course_isolation_violations"],
                }
            )


def plot(path_png: Path, path_svg: Path, analysis: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    positions = np.arange(len(METHODS))
    complete = [
        analysis["methods"][method]["complete_evidence_success_at_3"] * 100
        for method in METHODS
    ]
    recall = [
        analysis["methods"][method]["evidence_recall_at_5"] * 100
        for method in METHODS
    ]
    fig, axis = plt.subplots(figsize=(10.5, 5.8), facecolor="white")
    axis.set_facecolor("white")
    height = 0.34
    first = axis.barh(
        positions - height / 2,
        complete,
        height,
        label="Complete evidence @3",
        color="#2563EB",
    )
    second = axis.barh(
        positions + height / 2,
        recall,
        height,
        label="Evidence recall @5",
        color="#D97706",
    )
    axis.set_yticks(positions, [LABELS[method] for method in METHODS])
    axis.invert_yaxis()
    axis.set_xlim(0, 100)
    axis.set_xlabel("Held-out retrieval quality (%)")
    axis.set_title(
        "Cross-course text retrieval: one-time held-out comparison",
        loc="left",
        fontweight="bold",
    )
    axis.grid(axis="x", color="#E2E8F0")
    axis.set_axisbelow(True)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    for bars in (first, second):
        for bar in bars:
            axis.text(
                bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                f"{bar.get_width():.1f}",
                va="center",
                fontsize=9,
            )
    fig.subplots_adjust(left=0.28, right=0.96, top=0.86, bottom=0.22)
    path_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_png, dpi=220, facecolor=fig.get_facecolor())
    fig.savefig(path_svg, facecolor=fig.get_facecolor())
    plt.close(fig)


def write_report(path: Path, analysis: dict[str, Any]) -> None:
    dataset = analysis["dataset"]
    decision = analysis["decision"]
    lines = [
        "# Cross-course retrieval v1 held-out results",
        "",
        "Result ID: cross-course-retrieval-v1-heldout-001",
        "",
        "Status: completed one-time held-out comparison.",
        "",
        f"The frozen text benchmark contained 60 held-out cases: {dataset['positive_cases']} answerable and {dataset['boundary_cases']} boundary cases. The 40-case development split, 20-case second-review quota, local Qwen3 binding, thresholds, and runtime configuration were fixed before this run. The held-out file was read once through the guarded runner and the ledger completed.",
        "",
        "## Aggregate results",
        "",
        "| Method | Complete evidence @3 | 95% bootstrap CI | Evidence recall @5 | nDCG@10 | MRR | No-evidence accuracy | Warm p95 | No regression | Deployment eligible |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for method in METHODS:
        values = analysis["methods"][method]
        ci = values["complete_evidence_success_at_3_ci95"]
        lines.append(
            f"| {values['label']} | {values['complete_evidence_success_at_3']:.1%} | {ci[0]:.1%}–{ci[1]:.1%} | {values['evidence_recall_at_5']:.1%} | {values['ndcg_at_10']:.3f} | {values['mrr']:.3f} | {values['no_evidence_accuracy']:.1%} | {values['latency_p95_ms']:.0f} ms | {'yes' if values['quality_floor_passed'] else 'no'} | {'yes' if values['deployment_latency_passed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"{decision['outcome'].title()} — {decision['rationale']}",
            "",
            "BM25 remains the rollback. The selected method, if any, is a text-only retrieval selection and does not support image-dependent coverage claims.",
            "",
            "## Paired comparisons",
            "",
        ]
    )
    for name, comparison in analysis["paired_comparisons"].items():
        ci = comparison["paired_bootstrap_ci95"]
        lines.append(
            f"- {name}: {comparison['complete_evidence_at_3_difference']:+.1%}; 95% paired bootstrap CI {ci[0]:+.1%} to {ci[1]:+.1%}; wins/losses/ties {comparison['wins']}/{comparison['losses']}/{comparison['ties']}; sign-test p={comparison['exact_two_sided_sign_p_value']:.3f}."
        )
    lines.extend(
        [
            "",
            "## Gates and limitations",
            "",
            "- All 240 method-case rows completed with zero course-isolation violations, provider failures, retries, and external calls.",
            "- Selection eligibility requires no regression against BM25 on any primary quality metric as well as passing the latency ceiling.",
            "- Thresholds were frozen from the development run and were not recalibrated on held-out cases.",
            "- Latency is single-process workstation evidence, not concurrent capacity evidence.",
            "- The text benchmark excludes image-only claims; multimodal V3 was dropped separately.",
            "",
            f"Code revision: {analysis['provenance']['git_revision']}; git dirty: {'yes' if analysis['provenance']['git_dirty'] else 'no'}; implementation hash: {analysis['provenance']['implementation_tree_sha256']}.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    require_pre_evaluation_operation_allowed("heldout_execution")
    require(args.bootstrap_samples >= 1_000, "use at least 1,000 bootstrap samples")
    source_bytes = args.input.read_bytes()
    result = json.loads(source_bytes)
    analysis, record = analyze(result, samples=args.bootstrap_samples, seed=args.seed)
    analysis["provenance"]["source_result_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        f"{json.dumps(analysis, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    args.output_record.parent.mkdir(parents=True, exist_ok=True)
    args.output_record.write_text(
        f"{json.dumps(record, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, analysis)
    plot(args.output_png, args.output_svg, analysis)
    write_report(args.output_report, analysis)
    print(
        json.dumps(
            {
                "status": "sanitized",
                "result_id": analysis["result_id"],
                "decision": analysis["decision"],
                "outputs": [
                    str(args.output_json.relative_to(ROOT)),
                    str(args.output_csv.relative_to(ROOT)),
                    str(args.output_report.relative_to(ROOT)),
                    str(args.output_record.relative_to(ROOT)),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
