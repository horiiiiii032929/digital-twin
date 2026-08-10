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
    parser.add_argument("--reference", type=Path)
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


def _pairwise_labels(
    judge: dict[str, Any], *, repeats: bool
) -> dict[tuple[str, str], str]:
    labels = {}
    for record in judge["case_judgments"]:
        if bool(record["repeat"]) != repeats:
            continue
        for item in record["judgment"].get("c1_c2_pairwise", []):
            labels[(record["case_id"], item["dimension"])] = item["preference"]
    return labels


def _reference_labels(
    reference: dict[str, Any] | None,
) -> dict[tuple[str, str, str], str]:
    if reference is None:
        return {}
    reviewer = reference.get("reviewer", {})
    if not all(
        (
            reference.get("status") == "complete",
            reviewer.get("blinded_to_conditions") is True,
            reviewer.get("role") in {"researcher", "professor"},
        )
    ):
        return {}
    labels = {}
    for judgment in reference.get("judgments", []):
        for dimension in judgment.get("pedagogy_dimensions", []):
            labels[
                (
                    judgment["case_id"],
                    judgment["condition"],
                    dimension["dimension"],
                )
            ] = dimension["label"]
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


def _exact_agreement(left: dict[Any, str], right: dict[Any, str]) -> dict[str, Any]:
    common = sorted(set(left) & set(right))
    return {
        "n": len(common),
        "exact_agreement": (
            sum(left[key] == right[key] for key in common) / len(common)
            if common
            else None
        ),
    }


def _by_dimension(left: dict[tuple[str, str, str], str], right: dict[tuple[str, str, str], str]) -> dict[str, Any]:
    dimensions = sorted({key[2] for key in left} & {key[2] for key in right})
    return {
        dimension: _agreement(
            {key: value for key, value in left.items() if key[2] == dimension},
            {key: value for key, value in right.items() if key[2] == dimension},
        )
        for dimension in dimensions
    }


def analyze(
    run: dict[str, Any],
    primary: dict[str, Any],
    swapped: dict[str, Any],
    sensitivity: dict[str, Any],
    reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    primary_labels = _labels(primary, repeats=False)
    repeat_labels = _labels(primary, repeats=True)
    swapped_labels = _labels(swapped, repeats=False)
    sensitivity_labels = _labels(sensitivity, repeats=False)
    reference_labels = _reference_labels(reference)
    primary_pairwise = _pairwise_labels(primary, repeats=False)
    swapped_pairwise = _pairwise_labels(swapped, repeats=False)
    run_rows = {(row["case_id"], row["condition"]): row for row in run["results"]}
    false_passes = []
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    for (case_id, condition, _), label in primary_labels.items():
        grouped[(case_id, condition)].append(label)
    for key, labels in grouped.items():
        hard_gate_passed = run_rows[key]["score"].get(
            "deterministic_hard_gates_passed",
            run_rows[key]["score"].get("hard_gate_passed", False),
        )
        if all(label == "pass" for label in labels) and not hard_gate_passed:
            false_passes.append({"case_id": key[0], "condition": key[1]})
    swapped_overall = _agreement(primary_labels, swapped_labels)
    pairwise_position = _exact_agreement(primary_pairwise, swapped_pairwise)
    repeat_overall = _agreement(primary_labels, repeat_labels)
    sensitivity_overall = _agreement(primary_labels, sensitivity_labels)
    reference_overall = _agreement(primary_labels, reference_labels)
    reference_by_dimension = _by_dimension(primary_labels, reference_labels)
    dimension_reference_passed = bool(reference_by_dimension) and all(
        record["exact_agreement"] is not None
        and record["exact_agreement"] >= 0.80
        and record["linear_weighted_kappa"] is not None
        and record["linear_weighted_kappa"] >= 0.67
        for record in reference_by_dimension.values()
    )
    gates = {
        "blinded_researcher_reference_present": bool(reference_labels),
        "minimum_weighted_kappa_0_67": (
            reference_overall["linear_weighted_kappa"] is not None
            and reference_overall["linear_weighted_kappa"] >= 0.67
        ),
        "minimum_exact_agreement_0_80": (
            reference_overall["exact_agreement"] is not None
            and reference_overall["exact_agreement"] >= 0.80
        ),
        "every_dimension_passes_reference_gates": dimension_reference_passed,
        "minimum_pairwise_position_consistency_0_90": (
            pairwise_position["exact_agreement"] is not None
            and pairwise_position["exact_agreement"] >= 0.90
        ),
        "minimum_repeat_consistency_0_90": (repeat_overall["exact_agreement"] or 0) >= 0.90,
        "zero_false_passes_on_hard_gate_failures": not false_passes,
    }
    eligible = all(gates.values())
    return {
        "calibration_id": "professor-fidelity-v1-anchor-judge-calibration-001",
        "status": "eligible" if eligible else "ineligible",
        "automated_pedagogy_eligible": eligible,
        "source_run_id": run["run_id"],
        "models": {
            "primary": {"model": primary["model"], "digest": primary["model_digest"]},
            "sensitivity": {"model": sensitivity["model"], "digest": sensitivity["model_digest"]},
        },
        "overall": {
            "primary_vs_swapped": swapped_overall,
            "pairwise_position_consistency": pairwise_position,
            "primary_repeat": repeat_overall,
            "primary_vs_sensitivity": sensitivity_overall,
            "primary_vs_blinded_reference": reference_overall,
        },
        "per_dimension": {
            "primary_vs_swapped": _by_dimension(primary_labels, swapped_labels),
            "primary_repeat": _by_dimension(primary_labels, repeat_labels),
            "primary_vs_sensitivity": _by_dimension(primary_labels, sensitivity_labels),
            "primary_vs_blinded_reference": reference_by_dimension,
        },
        "gates": gates,
        "false_passes_on_hard_gate_failures": false_passes,
        "evaluator_failures": [
            "Gemma bundled attempt 001: malformed/truncated JSON before a result was written.",
            "Gemma bundled attempt 002: required-dimension drift after six checkpointed cases.",
            "Qwen single-response attempt 001: empty response because thinking was not explicitly disabled.",
        ],
        "limitations": [
            "Only a completed review whose reviewer was blinded to condition identities can serve as the calibration reference.",
            "Model-to-model, repeat, and position agreement cannot substitute for the frozen blinded researcher reference.",
            "Automated pedagogy labels remain diagnostic until a blinded reviewer reference passes every frozen dimension gate.",
        ],
    }


def main() -> None:
    arguments = parse_args()
    result = analyze(
        load_json(arguments.run), load_json(arguments.primary),
        load_json(arguments.swapped), load_json(arguments.sensitivity),
        load_json(arguments.reference) if arguments.reference else None,
    )
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(f"{json.dumps(result, indent=2)}\n", encoding="utf-8")
    print(json.dumps({"calibration_id": result["calibration_id"], "status": result["status"], "overall": result["overall"], "gates": result["gates"]}, indent=2))


if __name__ == "__main__":
    main()
