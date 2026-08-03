"""Create compact tables and a figure from current registered RAG results."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "research" / "05_evaluation" / "records"

DISPLAY_NAMES = {
    "bm25-calibrated": "BM25",
    "bge-small-dense": "Dense BGE",
    "bm25-bge-rrf": "Hybrid RRF",
    "any-hit-evidence-gate": "Any hit",
    "semantic-agreement-evidence-gate": "Semantic",
    "minimum-raw-score-evidence-gate": "Score threshold",
    "lexical-coverage-evidence-gate": "Lexical coverage",
    "deterministic-grounded-generator": "Deterministic",
    "ollama-gemma3-4b": "Gemma 3 4B",
}

NUMBER_WORDS = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize the current registered RAG evaluation numbers."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports" / "generated",
        help="Directory for CSV, Markdown, and PNG outputs.",
    )
    return parser.parse_args()


def load_record(name: str) -> dict[str, Any]:
    return json.loads((RECORDS / name).read_text(encoding="utf-8"))


def metrics(candidate: dict[str, Any]) -> dict[str, float]:
    return {item["name"]: float(item["value"]) for item in candidate["metrics"]}


def gate_evidence(candidate: dict[str, Any], name: str) -> str:
    return next(
        gate["evidence"] for gate in candidate["hard_gates"] if gate["name"] == name
    )


def parse_accuracy(evidence: str) -> float:
    fraction = re.search(r"(\d+)\s*/\s*(\d+)", evidence)
    if fraction:
        return int(fraction.group(1)) / int(fraction.group(2))

    all_cases = re.search(
        r"\ball\s+(one|two|three|four|five|six)\b",
        evidence,
        flags=re.IGNORECASE,
    )
    if all_cases:
        return 1.0

    words = re.search(
        r"\b(zero|one|two|three|four|five|six)\s+of\s+"
        r"(one|two|three|four|five|six)\b",
        evidence,
        flags=re.IGNORECASE,
    )
    if not words:
        raise ValueError(f"Could not parse accuracy from: {evidence}")
    denominator = NUMBER_WORDS[words.group(2).lower()]
    numerator = NUMBER_WORDS[words.group(1).lower()]
    return numerator / denominator


def retrieval_frame(record: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for candidate in record["candidates"]:
        values = metrics(candidate)
        rows.append(
            {
                "candidate": DISPLAY_NAMES[candidate["implementation"]["implementation_id"]],
                "recall_at_3": values["recall-at-3"],
                "recall_at_5": values["recall-at-5"],
                "ndcg_at_3_binary": values["ndcg-at-3"],
                "no_evidence_accuracy": parse_accuracy(
                    gate_evidence(candidate, "no-evidence-accuracy")
                ),
                "mean_latency_ms": values["mean-latency"],
                "p95_latency_ms": values["p95-latency"],
                "held_out_cases": 40,
                "answerable_cases": 34,
                "no_evidence_cases": 6,
                "decision": record["decision"]["outcome"],
            }
        )
    return pd.DataFrame(rows)


def sufficiency_frame(record: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for candidate in record["candidates"]:
        values = metrics(candidate)
        failures = candidate.get("failures_by_category", {})
        false_answers = int(failures.get("false-answer", 0))
        false_abstentions = int(failures.get("false-abstention", 0))
        rows.append(
            {
                "candidate": DISPLAY_NAMES[candidate["implementation"]["implementation_id"]],
                "answerable_recall": values["answerable-recall"],
                "no_evidence_accuracy": parse_accuracy(
                    gate_evidence(candidate, "no-evidence-accuracy")
                ),
                "balanced_accuracy": values["balanced-accuracy"],
                "false_answers": false_answers,
                "false_answer_rate": false_answers / 18,
                "false_abstentions": false_abstentions,
                "false_abstention_rate": false_abstentions / 32,
                "mean_gate_latency_ms": values["mean-gate-latency"],
                "held_out_cases": 50,
                "answerable_cases": 32,
                "no_evidence_cases": 18,
                "decision": record["decision"]["outcome"],
            }
        )
    return pd.DataFrame(rows)


def generation_frame(record: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for candidate in record["candidates"]:
        values = metrics(candidate)
        failures = int(candidate.get("failures_by_category", {}).get("grounded-support", 0))
        rows.append(
            {
                "candidate": DISPLAY_NAMES[candidate["implementation"]["implementation_id"]],
                "policy_accuracy": values["policy-action-accuracy"],
                "citation_reference_validity": values[
                    "citation-relationship-validity"
                ],
                "diagnostic_grounded_support": values[
                    "diagnostic-grounded-support"
                ],
                "grounded_support_failures": failures,
                "answer_cases": 18,
                "total_cases": 25,
                "reported_cost_usd": values["reported-cost"],
                "decision": record["decision"]["outcome"],
            }
        )
    return pd.DataFrame(rows)


def percent(value: float) -> str:
    return f"{value:.1%}"


def markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.astype(str).itertuples(index=False, name=None):
        lines.append(
            "| "
            + " | ".join(value.replace("|", "\\|") for value in row)
            + " |"
        )
    return "\n".join(lines)


def write_markdown(
    output: Path,
    retrieval: pd.DataFrame,
    sufficiency: pd.DataFrame,
    generation: pd.DataFrame,
) -> None:
    retrieval_view = retrieval[
        [
            "candidate",
            "recall_at_3",
            "recall_at_5",
            "ndcg_at_3_binary",
            "no_evidence_accuracy",
            "mean_latency_ms",
            "p95_latency_ms",
        ]
    ].copy()
    for column in [
        "recall_at_3",
        "recall_at_5",
        "ndcg_at_3_binary",
        "no_evidence_accuracy",
    ]:
        retrieval_view[column] = retrieval_view[column].map(percent)
    retrieval_view["mean_latency_ms"] = retrieval_view["mean_latency_ms"].map(
        lambda value: f"{value:.3f}"
    )
    retrieval_view["p95_latency_ms"] = retrieval_view["p95_latency_ms"].map(
        lambda value: f"{value:.3f}"
    )

    sufficiency_view = sufficiency[
        [
            "candidate",
            "answerable_recall",
            "no_evidence_accuracy",
            "balanced_accuracy",
            "false_answers",
            "false_abstentions",
            "mean_gate_latency_ms",
        ]
    ].copy()
    for column in [
        "answerable_recall",
        "no_evidence_accuracy",
        "balanced_accuracy",
    ]:
        sufficiency_view[column] = sufficiency_view[column].map(percent)
    sufficiency_view["false_answers"] = sufficiency_view["false_answers"].map(
        lambda value: f"{value}/18"
    )
    sufficiency_view["false_abstentions"] = sufficiency_view[
        "false_abstentions"
    ].map(lambda value: f"{value}/32")
    sufficiency_view["mean_gate_latency_ms"] = sufficiency_view[
        "mean_gate_latency_ms"
    ].map(lambda value: f"{value:.3f}")

    generation_view = generation[
        [
            "candidate",
            "policy_accuracy",
            "citation_reference_validity",
            "diagnostic_grounded_support",
            "grounded_support_failures",
            "reported_cost_usd",
        ]
    ].copy()
    for column in [
        "policy_accuracy",
        "citation_reference_validity",
        "diagnostic_grounded_support",
    ]:
        generation_view[column] = generation_view[column].map(percent)
    generation_view["grounded_support_failures"] = generation_view[
        "grounded_support_failures"
    ].map(lambda value: f"{value}/18")
    generation_view["reported_cost_usd"] = generation_view[
        "reported_cost_usd"
    ].map(lambda value: f"${value:.2f}")

    text = "\n\n".join(
        [
            "# Current RAG numbers — 16 July 2026",
            "DeepSeek has not been run yet. These are the current synthetic baseline and candidate results.",
            "## Retrieval — 40 held-out questions (34 answerable, 6 no-evidence)\n\n"
            + markdown_table(retrieval_view),
            "## Evidence sufficiency — 50 held-out questions (32 answerable, 18 no-evidence)\n\n"
            + markdown_table(sufficiency_view),
            "## Generation — 25 cases (18 generated answer cases)\n\n"
            + markdown_table(generation_view)
            + "\n\nReported cost is API spend; local compute cost was not monetized.",
            "## Short reading\n\n"
            "- Hybrid RRF has the best Recall@3 and Recall@5, but its binary nDCG@3 is slightly below BM25 and it falsely accepts 1/6 no-evidence questions.\n"
            "- The semantic evidence gate is the best current gate by balanced accuracy, but still has 5/18 false answers and 8/32 false abstentions.\n"
            "- Gemma passes structural policy and citation-reference checks, but only 15/18 generated answers passed the diagnostic grounded-support review.\n"
            "- Therefore, no retrieval replacement, evidence gate, model, or prompt was selected from these harder comparisons.",
        ]
    )
    output.write_text(text + "\n", encoding="utf-8")


def add_percent_labels(axis: plt.Axes, containers: list[Any]) -> None:
    for container in containers:
        axis.bar_label(container, labels=[f"{bar.get_height():.0%}" for bar in container], fontsize=8, padding=2)


def plot_summary(
    output: Path,
    retrieval: pd.DataFrame,
    sufficiency: pd.DataFrame,
    generation: pd.DataFrame,
) -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )
    colors = ["#2563EB", "#D97706", "#64748B"]
    figure, axes = plt.subplots(3, 1, figsize=(11, 13), constrained_layout=True)
    figure.suptitle(
        "Current RAG evaluation numbers — 16 July 2026\n"
        "Synthetic data; DeepSeek has not been run",
        fontsize=15,
        fontweight="bold",
    )

    retrieval_metrics = ["recall_at_3", "recall_at_5", "ndcg_at_3_binary"]
    retrieval_labels = ["Recall@3", "Recall@5", "nDCG@3 (binary)"]
    x = np.arange(len(retrieval))
    width = 0.24
    retrieval_bars = []
    for index, (metric, label) in enumerate(zip(retrieval_metrics, retrieval_labels, strict=True)):
        retrieval_bars.append(
            axes[0].bar(
                x + (index - 1) * width,
                retrieval[metric],
                width,
                label=label,
                color=colors[index],
            )
        )
    axes[0].set_title("Retrieval quality — 34 answerable held-out questions")
    axes[0].set_xticks(x, retrieval["candidate"])
    axes[0].set_ylim(0, 1.08)
    axes[0].yaxis.set_major_formatter(PercentFormatter(1.0))
    axes[0].legend(frameon=False, ncols=3, loc="upper center")
    axes[0].grid(axis="y", color="#E2E8F0", linewidth=0.8)
    add_percent_labels(axes[0], retrieval_bars)

    error_metrics = ["false_answer_rate", "false_abstention_rate"]
    error_labels = ["False answers (n=18)", "False abstentions (n=32)"]
    x = np.arange(len(sufficiency))
    width = 0.34
    error_bars = []
    for index, (metric, label) in enumerate(zip(error_metrics, error_labels, strict=True)):
        error_bars.append(
            axes[1].bar(
                x + (index - 0.5) * width,
                sufficiency[metric],
                width,
                label=label,
                color=colors[index],
            )
        )
    axes[1].set_title("Evidence-sufficiency errors — 50 held-out questions")
    axes[1].set_xticks(x, sufficiency["candidate"])
    axes[1].set_ylim(0, 1.12)
    axes[1].yaxis.set_major_formatter(PercentFormatter(1.0))
    axes[1].legend(frameon=False, ncols=2, loc="upper center")
    axes[1].grid(axis="y", color="#E2E8F0", linewidth=0.8)
    add_percent_labels(axes[1], error_bars)

    generation_metrics = [
        "policy_accuracy",
        "citation_reference_validity",
        "diagnostic_grounded_support",
    ]
    generation_labels = ["Policy", "Citation reference", "Grounded support"]
    x = np.arange(len(generation))
    width = 0.24
    generation_bars = []
    for index, (metric, label) in enumerate(zip(generation_metrics, generation_labels, strict=True)):
        generation_bars.append(
            axes[2].bar(
                x + (index - 1) * width,
                generation[metric],
                width,
                label=label,
                color=colors[index],
            )
        )
    axes[2].set_title("Generation checks — 25 cases; grounded support uses 18 generated answers")
    axes[2].set_xticks(x, generation["candidate"])
    axes[2].set_ylim(0, 1.12)
    axes[2].yaxis.set_major_formatter(PercentFormatter(1.0))
    axes[2].legend(frameon=False, ncols=3, loc="upper center")
    axes[2].grid(axis="y", color="#E2E8F0", linewidth=0.8)
    add_percent_labels(axes[2], generation_bars)

    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.set_ylabel("Rate")

    figure.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    retrieval = retrieval_frame(load_record("retrieval-v2.json"))
    sufficiency = sufficiency_frame(load_record("evidence-sufficiency-v1.json"))
    generation = generation_frame(load_record("generation-v1-gemma3-4b.json"))

    retrieval.to_csv(args.output_dir / "retrieval-comparison.csv", index=False)
    sufficiency.to_csv(args.output_dir / "evidence-gate-comparison.csv", index=False)
    generation.to_csv(args.output_dir / "generation-comparison.csv", index=False)
    write_markdown(
        args.output_dir / "current-rag-numbers.md",
        retrieval,
        sufficiency,
        generation,
    )
    plot_summary(
        args.output_dir / "current-rag-numbers.png",
        retrieval,
        sufficiency,
        generation,
    )

    print(f"Wrote current RAG number tables and chart to {args.output_dir}")


if __name__ == "__main__":
    main()
