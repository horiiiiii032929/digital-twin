"""Plot the short professor-facing IT5002 retrieval component result."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "experiments"
    / "runs"
    / "it5002_retrieval_rapid_v1"
    / "development_result.json"
)
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "figures"
CONDITIONS = ("R0", "R1", "R2", "R3", "R4", "R5")
METHODS = {
    "R0": "R0  Fixed-window BM25",
    "R1": "R1  Heading-aware BM25",
    "R2": "R2  Qwen3 dense",
    "R3": "R3  BM25 + dense RRF",
    "R4": "R4  Contextual hybrid",
    "R5": "R5  Qwen3 reranker",
}
COLORS = {
    "R0": "#8AB6D6",
    "R1": "#2364AA",
    "R2": "#8E6BBE",
    "R3": "#D4A72C",
    "R4": "#E07A2D",
    "R5": "#5B3C88",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, Any]]:
    result = json.loads(path.read_text(encoding="utf-8"))
    if result["run_id"] != "it5002-retrieval-rapid-v1-development":
        raise ValueError("unexpected development result")
    if result["case_count"] != 26:
        raise ValueError("expected 26 development cases")

    rows = []
    for condition in CONDITIONS:
        values = result["aggregate"][condition]
        if values["answerable_denominator"] != 13:
            raise ValueError(f"{condition} answerable denominator changed")
        if values["no_evidence_denominator"] != 13:
            raise ValueError(f"{condition} no-evidence denominator changed")
        rows.append(
            {
                "condition": condition,
                "method": METHODS[condition],
                "complete_successes": values["complete_evidence_numerator"],
                "answerable_cases": values["answerable_denominator"],
                "complete_evidence_rate": values[
                    "complete_evidence_success_at_3"
                ],
                "correct_abstentions": values["no_evidence_numerator"],
                "no_evidence_cases": values["no_evidence_denominator"],
                "no_evidence_accuracy": values["no_evidence_accuracy"],
                "p95_latency_seconds": values["latency_p95_ms"] / 1000,
                "latency_gate_seconds": 5.0,
                "scope": "development-only",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def plot(path: Path, rows: list[dict[str, Any]]) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.grid.axis": "x",
            "grid.alpha": 0.2,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    methods = [row["method"] for row in rows]
    successes = [row["complete_successes"] for row in rows]
    latencies = [row["p95_latency_seconds"] for row in rows]
    colors = [COLORS[row["condition"]] for row in rows]
    y = np.arange(len(rows))

    figure, (quality_axis, latency_axis) = plt.subplots(
        1,
        2,
        figsize=(13.5, 6.5),
        gridspec_kw={"wspace": 0.42},
    )
    figure.suptitle(
        "IT5002 retrieval component screening",
        fontsize=17,
        fontweight="bold",
        x=0.06,
        ha="left",
    )
    figure.text(
        0.06,
        0.91,
        "Development only: 13 answerable + 13 no-evidence cases per method; "
        "invalid held-out run excluded",
        fontsize=10,
        color="#555555",
    )

    quality_bars = quality_axis.barh(
        y,
        successes,
        color=colors,
        edgecolor="#FFFFFF",
        linewidth=0.8,
    )
    quality_axis.set_title("Complete-evidence success@3")
    quality_axis.set_xlabel("Complete cases out of 13")
    quality_axis.set_yticks(y, methods)
    quality_axis.set_xlim(0, 13)
    quality_axis.invert_yaxis()
    quality_axis.bar_label(
        quality_bars,
        labels=[f"{value}/13" for value in successes],
        padding=4,
        fontsize=9,
    )

    latency_bars = latency_axis.barh(
        y,
        latencies,
        color=colors,
        edgecolor="#FFFFFF",
        linewidth=0.8,
    )
    latency_axis.set_title("Warm p95 retrieval latency")
    latency_axis.set_xlabel("Seconds per query (log scale)")
    latency_axis.set_yticks(y, [row["condition"] for row in rows])
    latency_axis.set_xscale("log")
    latency_axis.set_xlim(0.04, 120)
    latency_axis.invert_yaxis()
    latency_axis.axvline(
        5,
        color="#333333",
        linestyle="--",
        linewidth=1.3,
        label="5 s product gate",
    )
    latency_axis.bar_label(
        latency_bars,
        labels=[format_latency(value) for value in latencies],
        padding=4,
        fontsize=9,
    )
    latency_axis.legend(frameon=False, loc="lower right")

    figure.text(
        0.06,
        0.035,
        "All six methods correctly abstained on 13/13 development "
        "no-evidence cases. R5-local-MPS was dropped; hosted semantic "
        "retrieval remains a separate candidate.",
        fontsize=9,
        color="#444444",
    )
    figure.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def format_latency(seconds: float) -> str:
    return f"{seconds * 1000:.0f} ms" if seconds < 1 else f"{seconds:.1f} s"


def main() -> None:
    args = parse_args()
    rows = load_rows(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        args.output_dir / "it5002-professor-retrieval-component.csv",
        rows,
    )
    plot(
        args.output_dir / "it5002-professor-retrieval-component.png",
        rows,
    )
    print(
        json.dumps(
            {
                "chart": str(
                    args.output_dir
                    / "it5002-professor-retrieval-component.png"
                ),
                "csv": str(
                    args.output_dir
                    / "it5002-professor-retrieval-component.csv"
                ),
                "rows": len(rows),
                "status": "passed",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
