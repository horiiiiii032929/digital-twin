#!/usr/bin/env python3
"""Validate and sanitize one development provider-qualification result."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import ROOT


INPUT_PATH = (
    ROOT
    / "experiments/runs/cross_course_provider_qualification_v1/"
    "local-qwen3-0-6b/development_result.json"
)
OUTPUT_JSON = (
    ROOT
    / "reports/generated/"
    "cross-course-provider-qualification-local-qwen3-v1.json"
)
OUTPUT_CSV = (
    ROOT
    / "reports/generated/"
    "cross-course-provider-qualification-local-qwen3-v1.csv"
)
OUTPUT_PNG = (
    ROOT
    / "reports/generated/"
    "cross-course-provider-qualification-local-qwen3-v1.png"
)
OUTPUT_SVG = (
    ROOT
    / "reports/generated/"
    "cross-course-provider-qualification-local-qwen3-v1.svg"
)
METHOD_LABELS = {
    "M0": "BM25",
    "M1": "Qwen3 dense",
    "M2": "BM25 + dense RRF",
    "M3": "Hybrid + Qwen3 reranker",
}
COMPARISONS = (("M2", "M0"), ("M3", "M0"), ("M3", "M2"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=INPUT_PATH)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--output-csv", type=Path, default=OUTPUT_CSV)
    parser.add_argument("--output-png", type=Path, default=OUTPUT_PNG)
    parser.add_argument("--output-svg", type=Path, default=OUTPUT_SVG)
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
    probability = sum(
        math.comb(discordant, value)
        for value in range(tail + 1)
    ) / (2**discordant)
    return min(1.0, 2 * probability)


def analyze(
    result: dict[str, Any],
    *,
    samples: int,
    seed: int,
) -> dict[str, Any]:
    require(
        result["status"] == "development_provider_qualification",
        "input is not a development provider qualification",
    )
    require(
        result["provider_pair"]["pair_id"] == "local-qwen3-0-6b",
        "input is not the local Qwen3 control",
    )
    require(result["development_case_count"] == 40, "expected 40 development cases")
    require(result["heldout_file_reads"] == 0, "heldout file was read")
    require(
        result["heldout_ledger_status"] == "unopened",
        "heldout ledger was not unopened",
    )
    require(len(result["cases"]) == 160, "expected four methods across 40 cases")
    require(
        result["hard_gates"]["complete_40_case_run"] is True,
        "40-case hard gate failed",
    )
    require(
        result["hard_gates"]["course_isolation_violations"] == 0,
        "course-isolation hard gate failed",
    )
    require(
        result["hard_gates"]["provider_failures"] == 0,
        "provider-failure hard gate failed",
    )

    positive_ids = sorted(
        {
            row["case_id"]
            for row in result["cases"]
            if row["is_positive"]
        }
    )
    boundary_ids = sorted(
        {
            row["case_id"]
            for row in result["cases"]
            if not row["is_positive"]
        }
    )
    require(len(positive_ids) == 35, "expected 35 positive cases")
    require(len(boundary_ids) == 5, "expected five boundary cases")
    lookup = {
        (row["case_id"], row["method"]): row
        for row in result["cases"]
    }
    require(len(lookup) == 160, "case-method rows are not unique")
    require(
        all(
            (case_id, method) in lookup
            for case_id in [*positive_ids, *boundary_ids]
            for method in METHOD_LABELS
        ),
        "case-method matrix is incomplete",
    )

    rng = random.Random(seed)
    methods: dict[str, Any] = {}
    for method, label in METHOD_LABELS.items():
        values = [
            float(
                lookup[(case_id, method)]["ranking"]["complete_evidence_at_3"]
            )
            for case_id in positive_ids
        ]
        aggregate = result["aggregate"][method]
        methods[method] = {
            "label": label,
            "positive_cases": len(values),
            "complete_evidence_success_at_3": aggregate[
                "complete_evidence_success_at_3"
            ],
            "complete_evidence_success_at_3_ci95": bootstrap_mean_interval(
                values,
                samples=samples,
                rng=rng,
            ),
            "evidence_recall_at_1": aggregate["evidence_recall_at_1"],
            "evidence_recall_at_3": aggregate["evidence_recall_at_3"],
            "evidence_recall_at_5": aggregate["evidence_recall_at_5"],
            "ndcg_at_10": aggregate["ndcg_at_10"],
            "mrr": aggregate["mrr"],
            "course_isolation_violations": aggregate[
                "course_isolation_violations"
            ],
            "latency_p50_ms_descriptive": aggregate["latency_p50_ms"],
            "latency_p95_ms_descriptive": aggregate["latency_p95_ms"],
        }

    comparisons: dict[str, Any] = {}
    for candidate, baseline in COMPARISONS:
        differences: list[float] = []
        wins = 0
        losses = 0
        for case_id in positive_ids:
            candidate_value = float(
                lookup[(case_id, candidate)]["ranking"][
                    "complete_evidence_at_3"
                ]
            )
            baseline_value = float(
                lookup[(case_id, baseline)]["ranking"][
                    "complete_evidence_at_3"
                ]
            )
            difference = candidate_value - baseline_value
            differences.append(difference)
            wins += difference > 0
            losses += difference < 0
        comparisons[f"{candidate}_vs_{baseline}"] = {
            "complete_evidence_at_3_difference": sum(differences)
            / len(differences),
            "paired_bootstrap_ci95": bootstrap_mean_interval(
                differences,
                samples=samples,
                rng=rng,
            ),
            "wins": wins,
            "losses": losses,
            "ties": len(differences) - wins - losses,
            "exact_two_sided_sign_p_value": exact_two_sided_sign_p_value(
                wins,
                losses,
            ),
        }

    usage = result["operational"]["total_provider_usage"]
    return {
        "result_id": "cross-course-provider-qualification-v1-local-qwen3",
        "qualification_id": result["qualification_id"],
        "status": result["status"],
        "provider_pair": result["provider_pair"],
        "dataset": {
            "dataset_id": result["dataset_id"],
            "dataset_version": result["dataset_version"],
            "dataset_seal_id": result["dataset_seal_id"],
            "development_sha256": result["development_sha256"],
            "development_cases": 40,
            "positive_cases": 35,
            "boundary_cases": 5,
            "heldout_file_reads": 0,
            "heldout_ledger_status": "unopened",
        },
        "configuration": {
            "ladder": result["configuration"]["ladder"],
            "device": result["configuration"]["device"],
            "dtype": result["configuration"]["dtype"],
            "batch_size": result["configuration"]["batch_size"],
        },
        "methods": methods,
        "paired_comparisons": comparisons,
        "hard_gates": result["hard_gates"],
        "operational": {
            "corpus_load_seconds": result["operational"]["corpus_load_seconds"],
            "embedding_index_build_seconds": result["operational"][
                "embedding_index_build_seconds"
            ],
            "peak_rss_bytes": result["operational"]["peak_rss_bytes"],
            "local_model_cache_bytes": result["operational"][
                "local_model_cache_bytes"
            ],
            "request_count": usage["request_count"],
            "input_tokens_estimated": usage["input_tokens"],
            "retry_count": usage["retry_count"],
            "failure_count": usage["failure_count"],
            "approximate_cost_usd": usage["approximate_cost_usd"],
            "latency_interpretation": (
                "Fixed method order and shared execution make latency descriptive "
                "for this workstation, not a provider-quality selection gate."
            ),
        },
        "provenance": {
            "implementation_tree_sha256": result["implementation_tree_sha256"],
            "git_revision": result["git_revision"],
            "git_dirty": result["git_dirty"],
            "source_result_sha256": None,
        },
        "decision": {
            "outcome": "refine",
            "provider_selected": False,
            "rationale": (
                "The local control completed and passed every hard gate. Keep it "
                "as the provider control, run the prospectively frozen hosted "
                "candidate, and make no provider selection from one side of the "
                "comparison."
            ),
        },
        "limitations": [
            *result["limitations"],
            "Only the local control has run; the hosted candidate is pending.",
            "Development metrics do not support a held-out generalization claim.",
        ],
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
                "course_isolation_violations",
            ],
        )
        writer.writeheader()
        for method, values in analysis["methods"].items():
            writer.writerow(
                {
                    "method": method,
                    "label": values["label"],
                    "positive_cases": values["positive_cases"],
                    "complete_evidence_success_at_3": values[
                        "complete_evidence_success_at_3"
                    ],
                    "complete_evidence_ci95_low": values[
                        "complete_evidence_success_at_3_ci95"
                    ][0],
                    "complete_evidence_ci95_high": values[
                        "complete_evidence_success_at_3_ci95"
                    ][1],
                    "evidence_recall_at_5": values["evidence_recall_at_5"],
                    "ndcg_at_10": values["ndcg_at_10"],
                    "mrr": values["mrr"],
                    "course_isolation_violations": values[
                        "course_isolation_violations"
                    ],
                }
            )


def plot(path_png: Path, path_svg: Path, analysis: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt
    import numpy as np

    methods = list(METHOD_LABELS)
    labels = [analysis["methods"][method]["label"] for method in methods]
    complete = [
        analysis["methods"][method]["complete_evidence_success_at_3"] * 100
        for method in methods
    ]
    recall = [
        analysis["methods"][method]["evidence_recall_at_5"] * 100
        for method in methods
    ]
    positions = np.arange(len(methods))
    height = 0.32
    fig, ax = plt.subplots(figsize=(10.8, 5.8), facecolor="#FAFBFC")
    ax.set_facecolor("#FAFBFC")
    complete_bars = ax.barh(
        positions - height / 2,
        complete,
        height,
        color="#3267A8",
        edgecolor="#1E3557",
        linewidth=0.8,
        label="All required evidence in top 3",
    )
    recall_bars = ax.barh(
        positions + height / 2,
        recall,
        height,
        color="#E2B44F",
        edgecolor="#6F5318",
        linewidth=0.8,
        hatch="//",
        label="Required evidence found in top 5",
    )
    ax.set_xlim(0, 100)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Development retrieval quality (%)", color="#263238")
    ax.set_title(
        "Local Qwen3 retrieval qualification",
        loc="left",
        fontsize=18,
        fontweight="bold",
        color="#17212B",
        pad=38,
    )
    ax.text(
        0,
        1.035,
        "35 answerable cases · 40 total development cases",
        transform=ax.transAxes,
        fontsize=10.5,
        color="#59636E",
        va="bottom",
    )
    ax.xaxis.grid(True, color="#DDE2E7", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#98A2AD")
    ax.tick_params(axis="y", length=0, labelcolor="#263238")
    ax.tick_params(axis="x", colors="#59636E")
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.24),
        ncol=2,
        frameon=False,
    )
    for bars in (complete_bars, recall_bars):
        for bar in bars:
            value = bar.get_width()
            ax.text(
                value + 1.0,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}",
                va="center",
                fontsize=9.5,
                color="#263238",
                fontfamily="monospace",
            )
    fig.subplots_adjust(left=0.28, right=0.95, top=0.78, bottom=0.24)
    path_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_png, dpi=220, facecolor=fig.get_facecolor())
    fig.savefig(path_svg, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    args = parse_args()
    require(args.bootstrap_samples >= 1000, "use at least 1000 bootstrap samples")
    source_bytes = args.input.read_bytes()
    result = json.loads(source_bytes)
    analysis = analyze(
        result,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    analysis["provenance"]["source_result_sha256"] = hashlib.sha256(
        source_bytes
    ).hexdigest()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        f"{json.dumps(analysis, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, analysis)
    plot(args.output_png, args.output_svg, analysis)
    print(
        json.dumps(
            {
                "status": "sanitized",
                "result_id": analysis["result_id"],
                "source_result_sha256": analysis["provenance"][
                    "source_result_sha256"
                ],
                "outputs": [
                    str(args.output_json.relative_to(ROOT)),
                    str(args.output_csv.relative_to(ROOT)),
                    str(args.output_png.relative_to(ROOT)),
                    str(args.output_svg.relative_to(ROOT)),
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
