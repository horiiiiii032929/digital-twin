#!/usr/bin/env python3
"""Sanitize, analyze, and plot the private cross-course development pilot."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import ROOT, sha256_file


INPUT_PATH = (
    ROOT
    / "experiments/runs/cross_course_retrieval_pilot_v1/"
    "development_result.json"
)
OUTPUT_JSON = (
    ROOT / "reports/generated/cross-course-retrieval-pilot-v1.json"
)
OUTPUT_CSV = (
    ROOT / "reports/generated/cross-course-retrieval-pilot-v1.csv"
)
OUTPUT_PNG = (
    ROOT / "reports/generated/cross-course-retrieval-pilot-v1.png"
)
OUTPUT_SVG = (
    ROOT / "reports/generated/cross-course-retrieval-pilot-v1.svg"
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
        result["status"] == "development_pilot_not_method_selection",
        "input is not a development pilot",
    )
    require(result["development_case_count"] == 40, "expected 40 development cases")
    require(result["heldout_cases_loaded"] == 0, "heldout cases were loaded")
    require(len(result["cases"]) == 160, "expected four methods across 40 cases")
    positive_ids = sorted(
        {
            row["case_id"]
            for row in result["cases"]
            if row["is_positive"]
        }
    )
    require(len(positive_ids) == 35, "expected 35 positive cases")
    lookup = {
        (row["case_id"], row["method"]): row
        for row in result["cases"]
    }
    rng = random.Random(seed)
    methods: dict[str, Any] = {}
    for method, label in METHOD_LABELS.items():
        values = [
            float(
                lookup[(case_id, method)]["ranking"][
                    "complete_evidence_at_3"
                ]
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
            "evidence_recall_at_5": aggregate["evidence_recall_at_5"],
            "ndcg_at_10": aggregate["ndcg_at_10"],
            "mrr": aggregate["mrr"],
            "course_isolation_violations": aggregate[
                "course_isolation_violations"
            ],
            "latency_p50_ms_fixed_order_contaminated": aggregate[
                "latency_p50_ms"
            ],
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
    return {
        "run_id": result["run_id"],
        "status": result["status"],
        "source_result_sha256": None,
        "development_cases": 40,
        "positive_cases": 35,
        "boundary_cases": 5,
        "heldout_cases_loaded": 0,
        "researcher_verified_at_run": result["researcher_verified_at_run"],
        "independently_reviewed_at_run": result[
            "independently_reviewed_at_run"
        ],
        "methods": methods,
        "paired_comparisons": comparisons,
        "operational": {
            "external_provider_called": False,
            "approximate_cost_usd": result["operational"][
                "approximate_cost_usd"
            ],
            "latency_interpretation": (
                "Fixed method order warmed shared dense-query execution; "
                "latency values are descriptive and not cross-method estimates."
            ),
        },
        "limitations": result["limitations"],
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
    fig, ax = plt.subplots(figsize=(11.2, 6.6), facecolor="#FAFBFC")
    ax.set_facecolor("#FAFBFC")
    complete_bars = ax.barh(
        positions - height / 2,
        complete,
        height,
        color="#3267A8",
        edgecolor="#1E3557",
        linewidth=0.8,
        label="Complete evidence @3",
    )
    recall_bars = ax.barh(
        positions + height / 2,
        recall,
        height,
        color="#E2B44F",
        edgecolor="#6F5318",
        linewidth=0.8,
        hatch="//",
        label="Evidence Recall @5",
    )
    ax.set_xlim(0, 100)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Development quality (%)", color="#263238")
    ax.set_title(
        "Cross-course retrieval method comparison",
        loc="left",
        fontsize=18,
        fontweight="bold",
        color="#17212B",
        pad=38,
    )
    ax.text(
        0,
        1.035,
        (
            "35 positive development cases • assistant-QC benchmark • "
            "held-out cases not accessed"
        ),
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
        bbox_to_anchor=(0.5, -0.22),
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
    comparison = analysis["paired_comparisons"]
    ax.text(
        0,
        -0.31,
        (
            "Paired completeness: M2 vs M0 +14.3 pp (5 wins, 0 losses); "
            "M3 vs M2 +2.9 pp (1 win, 0 losses)."
        ),
        transform=ax.transAxes,
        fontsize=9.5,
        color="#45515D",
    )
    ax.text(
        0,
        -0.37,
        (
            "Preliminary development evidence only; "
            f"M2 vs M0 sign-test p={comparison['M2_vs_M0']['exact_two_sided_sign_p_value']:.4f}. "
            "No production method selected."
        ),
        transform=ax.transAxes,
        fontsize=9,
        color="#6A747E",
    )
    fig.subplots_adjust(left=0.27, right=0.95, top=0.80, bottom=0.28)
    path_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path_png, dpi=220, facecolor=fig.get_facecolor())
    fig.savefig(path_svg, facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> int:
    args = parse_args()
    require(args.bootstrap_samples >= 1000, "use at least 1000 bootstrap samples")
    result = json.loads(args.input.read_text(encoding="utf-8"))
    analysis = analyze(
        result,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    analysis["source_result_sha256"] = sha256_file(args.input)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        f"{json.dumps(analysis, indent=2)}\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, analysis)
    plot(args.output_png, args.output_svg, analysis)
    print(
        json.dumps(
            {
                "status": "complete",
                "output_json": str(args.output_json),
                "output_csv": str(args.output_csv),
                "output_png": str(args.output_png),
                "output_svg": str(args.output_svg),
                "paired_comparisons": analysis["paired_comparisons"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
