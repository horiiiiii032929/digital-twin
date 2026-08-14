#!/usr/bin/env python3
"""Validate the prepared professor-fidelity path without opening private data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.judge_professor_fidelity import (
    DEEPSEEK_DOCUMENTED_REVISION,
    DEEPSEEK_EXPECTED_FINGERPRINT,
    DEEPSEEK_MODEL,
    JUDGE_CONTRACT_REVISION,
    JUDGE_MODELS,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "package.json"
PLAN_PATH = (
    ROOT / "research/04_experiments/2026-08-14-professor-fidelity-post-audit-v3-plan.md"
)
PURGE_RECORD_PATH = (
    ROOT / "research/00_admin/2026-08-14-github-public-history-purge-closure.md"
)
PRIVATE_REVIEW_ROOT = (
    ROOT / "reports/generated/course-tutor-v1.2.3-hybrid-authoring-review"
)
SEALED_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v2"
ANCHOR_CANDIDATE_PATH = (
    ROOT / "research/05_evaluation/profiles/"
    "professor-fidelity-anchor-v4-p3-candidate.json"
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate() -> dict[str, Any]:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    scripts = package["scripts"]
    judge_commands = {
        name: command
        for name, command in scripts.items()
        if name.startswith("judge:professor-fidelity")
    }
    required_commands = {
        "seal:course-tutor-splits",
        "qualify:professor-fidelity-judge-v4",
        "benchmark:professor-fidelity-anchor",
        "benchmark:professor-fidelity-development",
        "benchmark:professor-fidelity-heldout",
        "judge:professor-fidelity-development",
        "judge:professor-fidelity-development-swapped",
        "judge:professor-fidelity-development-qwen-sensitivity",
        "judge:professor-fidelity-heldout",
        "judge:professor-fidelity-heldout-swapped",
        "judge:professor-fidelity-heldout-qwen-sensitivity",
        "analyze:professor-fidelity-development",
        "judge:professor-fidelity-anchor",
        "judge:professor-fidelity-anchor-swapped",
        "judge:professor-fidelity-anchor-qwen-sensitivity",
        "prepare:professor-fidelity-anchor-review",
        "finalize:professor-fidelity-anchor-review",
        "calibrate:professor-fidelity-anchor-prehuman",
        "calibrate:professor-fidelity-anchor",
        "summarize:professor-fidelity-anchor-machine",
    }
    _require(required_commands.issubset(scripts), "post-audit commands are incomplete")
    _require(judge_commands, "professor-fidelity judge commands are absent")
    _require(
        all("gemma" not in command.casefold() for command in judge_commands.values()),
        "an active professor-fidelity judge command still references Gemma",
    )
    _require(
        "--model deepseek-v4-pro" in scripts["judge:professor-fidelity-development"],
        "development primary judge is not DeepSeek V4 Pro",
    )
    _require(
        "--model deepseek-v4-pro" in scripts["judge:professor-fidelity-heldout"],
        "held-out primary judge is not DeepSeek V4 Pro",
    )
    _require(
        "--confirm-heldout-once" in scripts["benchmark:professor-fidelity-heldout"],
        "held-out execution lacks one-time confirmation",
    )
    _require(
        "--model qwen3:4b"
        in scripts["judge:professor-fidelity-development-qwen-sensitivity"],
        "development sensitivity judge is not local Qwen",
    )
    anchor_command_names = {
        name for name in required_commands if "professor-fidelity-anchor" in name
    }
    anchor_commands = {name: scripts[name] for name in anchor_command_names}
    _require(
        all("anchor-002" in command for command in anchor_commands.values()),
        "an active anchor command does not use anchor-002",
    )
    _require(
        all("anchor-001" not in command for command in anchor_commands.values()),
        "an active anchor command still references invalid anchor-001",
    )
    primary_anchor_command = scripts["judge:professor-fidelity-anchor"]
    _require(
        "--attempt-id 002" in primary_anchor_command
        and "judgments-deepseek-v4-pro-attempt-002.json" in primary_anchor_command,
        "active primary anchor judge is not isolated as attempt 002",
    )
    _require(JUDGE_MODELS == (DEEPSEEK_MODEL, "qwen3:4b"), "judge model set drifted")
    _require(PLAN_PATH.is_file(), "post-audit v3 plan is missing")
    _require(PURGE_RECORD_PATH.is_file(), "GitHub purge closure record is missing")
    _require(ANCHOR_CANDIDATE_PATH.is_file(), "anchor V4 Pro/P3 candidate is missing")

    private_artifacts = {
        name: (PRIVATE_REVIEW_ROOT / filename).is_file()
        for name, filename in (
            ("ensemble", "ensemble_review.json"),
            ("human_packet", "human_audit_packet.md"),
            ("human_template", "human_audit_template.json"),
        )
    }
    sealed_artifacts = {
        name: (SEALED_ROOT / filename).is_file()
        for name, filename in (
            ("seal", "seal.json"),
            ("development", "development.json"),
            ("heldout", "heldout.json"),
            ("heldout_ledger", "heldout_once_ledger.json"),
        )
    }
    return {
        "status": "passed",
        "execution_status": "machine-review-ineligible-human-work-deferred",
        "active_anchor": {
            "run_id": "professor-fidelity-v2-anchor-002",
            "candidate_profile": "professor-fidelity-anchor-v4-p3-candidate",
            "selection_status": "not-selected",
            "generation_status": "complete-48-of-48",
        },
        "active_primary_judge": {
            "model": DEEPSEEK_MODEL,
            "documented_revision": DEEPSEEK_DOCUMENTED_REVISION,
            "expected_fingerprint": DEEPSEEK_EXPECTED_FINGERPRINT,
            "thinking": True,
            "reasoning_effort": "high",
            "contract_revision": JUDGE_CONTRACT_REVISION,
            "attempt_id": "002",
            "result_status": "complete-calibration-ineligible",
            "repeat_exact_agreement": 0.6875,
        },
        "active_sensitivity_judge": {
            "model": "qwen3:4b",
            "status": "invalid-attempt-001-rerun-prohibited",
        },
        "active_gemma_calls": 0,
        "private_artifact_content_read": False,
        "heldout_content_read": False,
        "model_called": False,
        "private_artifact_presence": private_artifacts,
        "sealed_artifact_presence": sealed_artifacts,
        "ordered_gates": [
            "decide whether to redesign the automated pedagogy evaluator",
            "complete bounded human packets only when the work resumes",
            "validate audit and create immutable seal plus unopened ledger",
            "execute development C0-C3",
            "run DeepSeek/Qwen blinded judging and calibration",
            "analyze and register development decision",
            "open held-out once only if every development gate passes",
        ],
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
