#!/usr/bin/env python3
"""Recompute the V4 Pro development action metric without model calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.run_generator_qualification import _actual_action


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/generated/generator-qualification-v2-v4-pro-development-001.json"
DATASET = ROOT / "research/05_evaluation/generator_qualification_v1_development.json"
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/generator-qualification-v2-v4-pro-development-001-"
    "action-analysis-correction-001.json"
)
RUN_SHA256 = "7e5e703373cd52c106d21a0336d93ebd67f2406e179145d2e4f0ba0eac15a27b"
DATASET_SHA256 = "a57ffeb7618e300a1647d733d605461c948b6b84ba9a1f48af904a0f814156c4"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def corrected_record(result: dict[str, Any]) -> dict[str, Any]:
    expected_action = result["expected_action"]
    policy_action = {
        "redirect": "redirect-graded-work",
        "abstain": "no-evidence",
    }.get(expected_action, "answer")
    corrected_action = _actual_action(
        policy_action,
        result["answer"].casefold(),
        scenario_type=result["scenario_type"],
    )
    corrected_pass = all(
        (
            result["completed"],
            corrected_action == expected_action,
            result["required_terms_passed"],
            result["forbidden_terms_absent"],
            result["citation_source_identity_passed"],
            result["provider_identity_passed"],
        )
    )
    return {
        "case_id": result["case_id"],
        "scenario_type": result["scenario_type"],
        "expected_action": expected_action,
        "original_action": result["actual_action"],
        "corrected_action": corrected_action,
        "original_pass": result["deterministic_checks_passed"],
        "corrected_pass": corrected_pass,
    }


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def main() -> int:
    args = parse_args()
    if sha256_file(RUN) != RUN_SHA256 or sha256_file(DATASET) != DATASET_SHA256:
        raise ValueError("source run or dataset differs from the frozen correction")
    run = json.loads(RUN.read_text(encoding="utf-8"))
    records = [corrected_record(item) for item in run["results"]]
    changed = [
        item for item in records if item["original_action"] != item["corrected_action"]
    ]
    remaining = [item for item in records if not item["corrected_pass"]]
    corrected_by_scenario = Counter(
        item["scenario_type"] for item in records if item["corrected_pass"]
    )
    output = {
        "result_id": "generator-qualification-v2-v4-pro-development-001-action-analysis-correction-001",
        "status": "complete-no-model-analysis-correction",
        "source_run_sha256": RUN_SHA256,
        "dataset_sha256": DATASET_SHA256,
        "source_execution_revision": run["code_revision"],
        "analysis_revision": _code_revision(),
        "analysis_worktree_dirty": _working_tree_dirty(),
        "model_called": False,
        "private_text_read": False,
        "heldout_read": False,
        "original_passes": sum(item["original_pass"] for item in records),
        "corrected_passes": sum(item["corrected_pass"] for item in records),
        "changed_action_cases": changed,
        "remaining_failures": remaining,
        "corrected_passes_by_scenario": dict(sorted(corrected_by_scenario.items())),
    }
    if (
        [item["case_id"] for item in changed] != ["gqv1-dev-005"]
        or [item["case_id"] for item in remaining] != ["gqv1-dev-045"]
        or output["corrected_passes"] != 47
    ):
        raise ValueError("corrected action result differs from the frozen prediction")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
