#!/usr/bin/env python3
"""Validate the paused professor-fidelity path without opening private data."""

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
POLICY_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "professor_fidelity_execution_policy_v1.json"
)
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
CORRECTION_RECORD_PATH = (
    ROOT
    / "research/05_evaluation/records/"
    "professor-fidelity-v2-anchor-002-machine-review-summary-001-"
    "analysis-correction-001.json"
)
CORRECTION_RUN_ID = (
    "professor-fidelity-v2-anchor-002-machine-review-summary-001-"
    "analysis-correction-001"
)
CORRECTION_CODE_REVISION = "dbd7a71c4fd7da48773f68bd3358faab099ef4cc"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _validate_commands(scripts: dict[str, str]) -> dict[str, Any]:
    preflights = {
        "development": "preflight:professor-fidelity-development",
        "heldout": "preflight:professor-fidelity-heldout",
    }
    for split, name in preflights.items():
        _require(name in scripts, f"{split} preflight command is missing")
        command = scripts[name]
        _require(f"--split {split}" in command, f"{split} preflight split drifted")
        _require("--execute" not in command, f"{split} preflight can execute")
        _require("--allow-external-provider" not in command, f"{split} preflight authorizes a provider")

    historical_names = {
        "historical:benchmark:generation-gemma3",
        "historical:benchmark:professor-fidelity-anchor",
        "historical:judge:professor-fidelity-anchor",
        "historical:judge:professor-fidelity-anchor-swapped",
        "historical:judge:professor-fidelity-anchor-qwen-sensitivity",
        "historical:prepare:professor-fidelity-anchor-review",
        "historical:finalize:professor-fidelity-anchor-review",
        "historical:calibrate:professor-fidelity-anchor-prehuman",
        "historical:calibrate:professor-fidelity-anchor",
        "historical:summarize:professor-fidelity-anchor-machine",
    }
    _require(historical_names.issubset(scripts), "historical commands are incomplete")
    _require(
        all("--confirm-historical-reproduction" not in scripts[name] for name in historical_names),
        "historical confirmation must be supplied interactively, not baked into a command",
    )
    _require(
        all("anchor-001" not in scripts[name] for name in historical_names),
        "a historical command references invalid anchor-001",
    )

    deferred = {
        name: command
        for name, command in scripts.items()
        if name.startswith("deferred:") and "professor-fidelity" in name
    }
    _require(len(deferred) == 7, "deferred professor-fidelity commands drifted")
    _require(
        any("--model deepseek-v4-pro" in command for command in deferred.values()),
        "deferred primary judge is not DeepSeek V4 Pro",
    )
    _require(
        any("--model qwen3:4b" in command for command in deferred.values()),
        "deferred sensitivity judge is not local Qwen",
    )

    retired_active_names = {
        "benchmark:generation-local",
        "benchmark:professor-fidelity-anchor",
        "benchmark:professor-fidelity-development",
        "benchmark:professor-fidelity-heldout",
        "judge:professor-fidelity-development",
        "judge:professor-fidelity-heldout",
        "judge:professor-fidelity-anchor",
        "analyze:professor-fidelity-development",
    }
    _require(
        retired_active_names.isdisjoint(scripts),
        "a retired executable command remains in the active namespace",
    )
    active = {
        name: command
        for name, command in scripts.items()
        if not name.startswith(("historical:", "deferred:"))
    }
    _require(
        all("gemma3:4b" not in command.casefold() for command in active.values()),
        "an active command still invokes Gemma",
    )
    _require(
        "--attempt-id 002" in scripts["historical:judge:professor-fidelity-anchor"],
        "historical primary anchor judge is not isolated as attempt 002",
    )
    return {
        "active_preflights": sorted(preflights.values()),
        "historical_command_count": len(historical_names),
        "deferred_command_count": len(deferred),
    }


def validate() -> dict[str, Any]:
    package = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))
    command_status = _validate_commands(package["scripts"])
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    _require(
        policy.get("schema_version") == "1.0.0"
        and policy.get("policy_id") == "professor-fidelity-execution-policy-v1"
        and policy.get("status") == "paused",
        "professor-fidelity execution policy is absent or not paused",
    )
    splits = policy.get("splits", {})
    _require(splits.get("development", {}).get("authorized") is False, "development is authorized while paused")
    _require(splits.get("heldout", {}).get("authorized") is False, "held-out is authorized while paused")
    _require(
        splits.get("anchor", {}).get("scope") == "historical-reproduction-only"
        and splits.get("anchor", {}).get("requires_historical_confirmation") is True,
        "anchor historical-reproduction policy drifted",
    )
    heldout_requirement = splits["heldout"]["requires_development_result"]
    _require(
        heldout_requirement.get("decision") == "keep"
        and heldout_requirement.get("heldout_eligible") is True
        and heldout_requirement.get("all_decision_gates") is True
        and heldout_requirement.get("result_id") is None,
        "held-out development-result gate drifted",
    )
    _require(JUDGE_MODELS == (DEEPSEEK_MODEL, "qwen3:4b"), "judge model set drifted")
    _require(PLAN_PATH.is_file(), "post-audit v3 plan is missing")
    _require(PURGE_RECORD_PATH.is_file(), "GitHub purge closure record is missing")
    _require(ANCHOR_CANDIDATE_PATH.is_file(), "anchor V4 Pro/P3 candidate is missing")
    _require(CORRECTION_RECORD_PATH.is_file(), "analysis correction record is missing")

    correction = json.loads(CORRECTION_RECORD_PATH.read_text(encoding="utf-8"))
    _require(correction.get("run_id") == CORRECTION_RUN_ID, "analysis correction run ID drifted")
    _require(correction.get("code_revision") == CORRECTION_CODE_REVISION, "analysis correction code revision drifted")
    _require(correction.get("decision", {}).get("outcome") == "refine", "analysis correction decision drifted")
    candidates = correction.get("candidates", [])
    _require(
        len(candidates) == 2
        and candidates[1].get("implementation", {}).get("implementation_id")
        == "anchor-machine-review-corrected-interpretation",
        "analysis correction candidate is missing",
    )
    corrected_gates = {
        gate.get("name"): gate.get("passed")
        for gate in candidates[1].get("hard_gates", [])
    }
    _require(
        corrected_gates.get("separate-pedagogy-from-hidden-hard-gates") is True,
        "analysis correction still grades pedagogy on hidden hard gates",
    )

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
        "execution_status": "machine-review-ineligible-paused-human-work-deferred",
        "execution_policy": {
            "policy_id": policy["policy_id"],
            "status": policy["status"],
            "development_authorized": False,
            "heldout_authorized": False,
            **command_status,
        },
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
        "analysis_correction": {
            "run_id": CORRECTION_RUN_ID,
            "code_revision": CORRECTION_CODE_REVISION,
            "decision": correction["decision"]["outcome"],
            "interpretation_status": "corrected",
            "cross_layer_disagreement": "diagnostic-not-calibration-gate",
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
            "preserve and report the ineligible machine-review result",
            "resume evaluator redesign only with separate authorization",
            "complete bounded human packets only after authorized resumption",
            "authorize development in the tracked execution policy",
            "execute and register a complete development analysis",
            "require Keep plus every development gate before held-out authorization",
            "open held-out once only with explicit confirmation",
        ],
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
