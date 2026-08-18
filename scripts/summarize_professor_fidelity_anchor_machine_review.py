#!/usr/bin/env python3
"""Summarize anchor-002 machine review without emitting private response text."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.analyze_judge_calibration import (
    _agreement,
    _exact_agreement,
    _labels,
    _pairwise_labels,
)
from scripts.judge_professor_fidelity import write_json_exclusive


ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "experiments/runs/professor_fidelity_v2/anchor-002"
PACKET_ROOT = ROOT / "reports/generated/professor-fidelity-anchor-blinded-review-v4"
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/"
    "professor-fidelity-v2-anchor-002-machine-review-summary.json"
)
ARTIFACTS = {
    "source_run": (
        RUN_ROOT / "result.json",
        "6290755a44848a6c8a2239a4cee5d09e02c8f7007f2620a0f1c1a05df28a8cf1",
    ),
    "primary": (
        RUN_ROOT / "judgments-deepseek-v4-pro-attempt-002.json",
        "d86d554aa42bf372ecb793c0bca432910fe9bbd89a99526b8b5c57b17a6ae41d",
    ),
    "swapped_invalid_checkpoint": (
        RUN_ROOT / "judgments-deepseek-v4-pro-swapped-attempt-001-checkpoint.json",
        "e51f7b5bf1295927ecfb326045aa63cac63109a24ccf613458d7752490c788ef",
    ),
    "qwen_invalid_checkpoint": (
        RUN_ROOT / "judgments-qwen3-sensitivity-attempt-001-checkpoint.json",
        "35dcaf21f4e3ed4b82732b21586e7c066be7ed8aaf2999ac3d34cbbb9aa6f8c1",
    ),
    "review_packet": (
        PACKET_ROOT / "packet.md",
        "a3033655a79b6eba8f3adde5e4122ad36a930803aa76b08a1468c467b19e37c8",
    ),
    "review_template": (
        PACKET_ROOT / "review_template.json",
        "eac281d0cd17bc5d7582aef20dde4dfe10c4bd47fcc6efecc4a798ab0d44fac9",
    ),
    "review_mapping": (
        PACKET_ROOT / "mapping.json",
        "cd54dc7c4a2e37de48099d349b41ce3bf3c2aaa1ef507f343b876116c3e23a8e",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm-historical-reproduction", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def _load(name: str) -> dict[str, Any]:
    path, expected = ARTIFACTS[name]
    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    if observed != expected:
        raise ValueError(f"{name} hash drifted")
    return json.loads(path.read_text(encoding="utf-8"))


def _condition_metrics(run: dict[str, Any]) -> list[dict[str, Any]]:
    records = []
    for condition in ("C0", "C1", "C2", "C3"):
        rows = [row for row in run["results"] if row["condition"] == condition]
        citation_applicable_rows = [
            row
            for row in rows
            if row["score"].get("citation_applicable_claims", 0) > 0
        ]
        records.append(
            {
                "condition": condition,
                "n": len(rows),
                "hard_gate_passes": sum(
                    row["score"]["deterministic_hard_gates_passed"] for row in rows
                ),
                "structural_passes": sum(
                    row["score"]["deterministic_structural_success"] for row in rows
                ),
                "action_passes": sum(row["score"]["action_passed"] for row in rows),
                "citation_identity_valid": sum(
                    row["score"]["citation_identity_validity"] is True for row in rows
                ),
                "citation_source_correct": sum(
                    row["score"]["citation_source_correctness"] is True for row in rows
                ),
                "citation_source_applicable_n": len(citation_applicable_rows),
                "citation_source_correct_applicable": sum(
                    row["score"]["citation_source_correctness"] is True
                    for row in citation_applicable_rows
                ),
            }
        )
    return records


def _pairwise_repeat_agreement(judge: dict[str, Any]) -> dict[str, Any]:
    return _exact_agreement(
        _pairwise_labels(judge, repeats=False),
        _pairwise_labels(judge, repeats=True),
    )


def summarize() -> dict[str, Any]:
    run = _load("source_run")
    primary = _load("primary")
    swapped = _load("swapped_invalid_checkpoint")
    qwen = _load("qwen_invalid_checkpoint")
    template = _load("review_template")
    for name in ("review_packet", "review_mapping"):
        path, expected = ARTIFACTS[name]
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"{name} hash drifted")
    if (
        run.get("status") != "completed-pending-judge"
        or primary.get("status") != "complete"
        or primary.get("attempt_id") != "002"
        or swapped.get("completed_cases") != 5
        or qwen.get("completed_cases") != 2
        or template.get("status") != "draft"
        or any(
            dimension.get("label")
            for judgment in template.get("judgments", [])
            for dimension in judgment.get("pedagogy_dimensions", [])
        )
    ):
        raise ValueError("anchor machine-review artifact status drifted")

    primary_labels = _labels(primary, repeats=False)
    repeat_labels = _labels(primary, repeats=True)
    swapped_labels = _labels(swapped, repeats=False)
    qwen_labels = _labels(qwen, repeats=False)
    primary_pairwise = _pairwise_labels(primary, repeats=False)
    swapped_pairwise = _pairwise_labels(swapped, repeats=False)
    run_rows = {(row["case_id"], row["condition"]): row for row in run["results"]}
    grouped: dict[tuple[str, str], list[str]] = {}
    for (case_id, condition, _), label in primary_labels.items():
        grouped.setdefault((case_id, condition), []).append(label)
    cross_layer_disagreements = [
        {"case_id": key[0], "condition": key[1]}
        for key, labels in sorted(grouped.items())
        if all(label == "pass" for label in labels)
        and not run_rows[key]["score"]["deterministic_hard_gates_passed"]
    ]
    repeat_agreement = _agreement(primary_labels, repeat_labels)
    pairwise_repeat_agreement = _pairwise_repeat_agreement(primary)
    return {
        "summary_id": "professor-fidelity-v2-anchor-002-machine-review-summary-001",
        "status": "ineligible",
        "decision": "refine",
        "source_run_id": run["run_id"],
        "data_boundary": "private-anchor-aggregate-only",
        "private_response_text_emitted": False,
        "heldout_opened": False,
        "artifacts": {
            name: {"path": str(path.relative_to(ROOT)), "sha256": expected}
            for name, (path, expected) in ARTIFACTS.items()
        },
        "generation": {
            "completed_attempts": run["completed_attempts"],
            "requested_attempts": run["requested_attempts"],
            "provider_model": run["provider_model"],
            "provider_revision": run["provider_revision"],
            "cost_usd": run["cost_usd"],
            "condition_metrics": _condition_metrics(run),
        },
        "primary": {
            "status": "complete",
            "calls": primary["transport"]["calls"],
            "base_cases": sum(not row["repeat"] for row in primary["case_judgments"]),
            "repeat_cases": sum(row["repeat"] for row in primary["case_judgments"]),
            "repeat_responses": sum(
                len(row["judgment"]["responses"])
                for row in primary["case_judgments"]
                if row["repeat"]
            ),
            "repeat_labels": repeat_agreement["n"],
            "cost_usd": primary["transport"]["cost_usd"],
            "repeat_agreement": repeat_agreement,
            "pairwise_repeat_agreement": pairwise_repeat_agreement,
            "quote_alignment_count": sum(
                len(row["judgment"].get("quote_alignments", []))
                for row in primary["case_judgments"]
            ),
        },
        "invalid_diagnostics": {
            "swapped": {
                "completed_cases": swapped["completed_cases"],
                "calls": swapped["transport"]["calls"],
                "failure": "DeepSeek judge returned empty content during case 6",
                "primary_partial_agreement": _agreement(primary_labels, swapped_labels),
                "pairwise_position_partial_agreement": _exact_agreement(
                    primary_pairwise, swapped_pairwise
                ),
                "rerun_permitted": False,
            },
            "qwen": {
                "completed_cases": qwen["completed_cases"],
                "calls": qwen["transport"]["calls"],
                "failure": "evidence quote was not uniquely source-aligned during case 3",
                "primary_partial_agreement": _agreement(primary_labels, qwen_labels),
                "rerun_permitted": False,
            },
        },
        "gates": {
            "primary_complete": True,
            "minimum_repeat_consistency_0_90": (
                repeat_agreement["exact_agreement"] or 0
            )
            >= 0.90,
            "swapped_complete": False,
            "sensitivity_complete": False,
            "minimum_pairwise_position_consistency_0_90": False,
            "blinded_human_reference_present": False,
        },
        "cross_layer_diagnostics": {
            "pedagogy_all_pass_with_deterministic_failure": (
                cross_layer_disagreements
            ),
            "interpretation": (
                "Diagnostic only: the pedagogy judge was blinded to citations and "
                "deterministic hard-gate results, so this is not an evaluator "
                "calibration failure."
            ),
        },
        "human_packet": {
            "status": template["status"],
            "judgment_count": len(template["judgments"]),
            "completed_labels": 0,
            "filled_by_model": False,
        },
        "code_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(
                ["git", "status", "--porcelain"], cwd=ROOT, text=True
            ).strip()
        ),
    }


def main() -> None:
    arguments = parse_args()
    if not arguments.confirm_historical_reproduction:
        raise ValueError(
            "anchor summarization is historical reproduction and requires "
            "--confirm-historical-reproduction"
        )
    result = summarize()
    write_json_exclusive(arguments.output, result)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "artifacts"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
