#!/usr/bin/env python3
"""Analyze local professor-fidelity judge calibration without overclaiming."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


LABELS = ("fail", "partial", "pass")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--swapped", type=Path, required=True)
    parser.add_argument("--sensitivity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _labels(judge: dict[str, Any], *, repeats: bool) -> dict[tuple[str, str, str], str]:
    labels = {}
    for record in judge["case_judgments"]:
        if bool(record["repeat"]) != repeats:
            continue
        for response in record["judgment"]["responses"]:
            condition = record["mapping"][response["label"]]
            for item in response["dimensions"]:
                labels[(record["case_id"], condition, item["dimension"])] = item["label"]
    return labels


def _agreement(left: dict[tuple[str, str, str], str], right: dict[tuple[str, str, str], str]) -> dict[str, Any]:
    common = sorted(set(left) & set(right))
    if not common:
        return {"n": 0, "exact_agreement": None, "linear_weighted_kappa": None}
    observed = sum(left[key] == right[key] for key in common) / len(common)
    left_counts = {label: sum(left[key] == label for key in common) for label in LABELS}
    right_counts = {label: sum(right[key] == label for key in common) for label in LABELS}
    disagreement = sum(
        abs(LABELS.index(left[key]) - LABELS.index(right[key])) / 2 for key in common
    ) / len(common)
    expected_disagreement = sum(
        (left_counts[left_label] / len(common))
        * (right_counts[right_label] / len(common))
        * abs(left_index - right_index)
        / 2
        for left_index, left_label in enumerate(LABELS)
        for right_index, right_label in enumerate(LABELS)
    )
    kappa = 1.0 if expected_disagreement == 0 and disagreement == 0 else (
        None if expected_disagreement == 0 else 1 - disagreement / expected_disagreement
    )
    return {"n": len(common), "exact_agreement": observed, "linear_weighted_kappa": kappa}


def _by_dimension(left: dict[tuple[str, str, str], str], right: dict[tuple[str, str, str], str]) -> dict[str, Any]:
    dimensions = sorted({key[2] for key in left} & {key[2] for key in right})
    return {
        dimension: _agreement(
            {key: value for key, value in left.items() if key[2] == dimension},
            {key: value for key, value in right.items() if key[2] == dimension},
        )
        for dimension in dimensions
    }


def analyze(run: dict[str, Any], primary: dict[str, Any], swapped: dict[str, Any], sensitivity: dict[str, Any]) -> dict[str, Any]:
    primary_labels = _labels(primary, repeats=False)
    repeat_labels = _labels(primary, repeats=True)
    swapped_labels = _labels(swapped, repeats=False)
    sensitivity_labels = _labels(sensitivity, repeats=False)
    run_rows = {(row["case_id"], row["condition"]): row for row in run["results"]}
    false_passes = []
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (case_id, condition, _), label in primary_labels.items():
        grouped[(case_id, condition)].append(label)
    for key, labels in grouped.items():
        if all(label == "pass" for label in labels) and not run_rows[key]["score"]["hard_gate_passed"]:
            false_passes.append({"case_id": key[0], "condition": key[1]})
    swapped_overall = _agreement(primary_labels, swapped_labels)
    repeat_overall = _agreement(primary_labels, repeat_labels)
    sensitivity_overall = _agreement(primary_labels, sensitivity_labels)
    gates = {
        "blinded_researcher_reference_present": False,
        "minimum_weighted_kappa_0_67": False,
        "minimum_exact_agreement_0_80": False,
        "minimum_swapped_order_consistency_0_90": (swapped_overall["exact_agreement"] or 0) >= 0.90,
        "minimum_repeat_consistency_0_90": (repeat_overall["exact_agreement"] or 0) >= 0.90,
        "zero_false_passes_on_hard_gate_failures": not false_passes,
    }
    return {
        "calibration_id": "professor-fidelity-v1-anchor-judge-calibration-001",
        "status": "ineligible-missing-blinded-researcher-reference",
        "automated_pedagogy_eligible": False,
        "source_run_id": run["run_id"],
        "models": {
            "primary": {"model": primary["model"], "digest": primary["model_digest"]},
            "sensitivity": {"model": sensitivity["model"], "digest": sensitivity["model_digest"]},
        },
        "overall": {
            "primary_vs_swapped": swapped_overall,
            "primary_repeat": repeat_overall,
            "primary_vs_sensitivity": sensitivity_overall,
        },
        "per_dimension": {
            "primary_vs_swapped": _by_dimension(primary_labels, swapped_labels),
            "primary_repeat": _by_dimension(primary_labels, repeat_labels),
            "primary_vs_sensitivity": _by_dimension(primary_labels, sensitivity_labels),
        },
        "gates": gates,
        "false_passes_on_hard_gate_failures": false_passes,
        "evaluator_failures": [
            "Gemma bundled attempt 001: malformed/truncated JSON before a result was written.",
            "Gemma bundled attempt 002: required-dimension drift after six checkpointed cases.",
            "Qwen single-response attempt 001: empty response because thinking was not explicitly disabled.",
        ],
        "limitations": [
            "The earlier Codex QA pass saw condition identities and is citation/policy QA only, not a blinded calibration reference.",
            "Model-to-model, repeat, and position agreement cannot substitute for the frozen blinded researcher reference.",
            "Automated pedagogy labels remain diagnostic until a blinded reviewer reference passes every frozen dimension gate.",
        ],
    }


def main() -> None:
    arguments = parse_args()
    result = analyze(
        load_json(arguments.run), load_json(arguments.primary),
        load_json(arguments.swapped), load_json(arguments.sensitivity),
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(f"{json.dumps(result, indent=2)}\n", encoding="utf-8")
    print(json.dumps({"calibration_id": result["calibration_id"], "status": result["status"], "overall": result["overall"], "gates": result["gates"]}, indent=2))


if __name__ == "__main__":
    main()
