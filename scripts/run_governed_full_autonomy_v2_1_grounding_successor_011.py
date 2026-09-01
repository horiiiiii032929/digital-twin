#!/usr/bin/env python3
"""Run the finite fresh 500+100 grounding-successor decision."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import (
    build_governed_full_autonomy_v2_1_grounding_successor_011 as builder,
)
from scripts import (
    run_governed_full_autonomy_v2_1_cross_engine_evaluation_010 as shared,
)
from scripts.cross_engine_factual import execute_factual_package, factual_hard_gates
from src.digital_twin.evaluation.cross_engine_program import ProductEngineBindingV1
from src.digital_twin.evaluation.factual_qa_contract import EvaluationCaseV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


INSTRUMENT_ID = builder.INSTRUMENT_ID
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_grounding_successor_011.json"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
RESULT_PATH = OUTPUT_ROOT / "result.json"


class GroundingSuccessorExecutionError(RuntimeError):
    """Raised when the frozen grounding decision cannot be executed safely."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _relevant_worktree_changes() -> list[str]:
    output = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [
        row
        for row in output.splitlines()
        if row and not row[3:].startswith(".claude/")
    ]


def _load_instrument() -> dict[str, Any]:
    payload = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    if payload.get("instrument_id") != INSTRUMENT_ID:
        raise GroundingSuccessorExecutionError("instrument identity drifted")
    return payload


def _engine() -> ProductEngineBindingV1:
    return ProductEngineBindingV1(
        engine_id="e0-source-compiler",
        provider="deterministic",
        planner_model="deterministic-policy",
        generator_model="deterministic-evidence-set-grounded-generator-v2",
        planner_reasoning_effort="none",
        generator_reasoning_effort="none",
        maximum_output_tokens=600,
        input_price_usd_per_million=0,
        output_price_usd_per_million=0,
        credential_environment_variable=None,
        returned_identity_must_equal=None,
        dated_snapshot=True,
    )


def validate() -> dict[str, Any]:
    instrument = _load_instrument()
    cases, gold, chunks = builder.load_inputs()
    controls = set(builder.control_case_ids(cases))
    if len(cases) != 500 or len(gold) != 500 or len(controls) != 100:
        raise GroundingSuccessorExecutionError("frozen package cardinality drifted")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise GroundingSuccessorExecutionError("public/gold identity drifted")
    if any(
        sum(case.cluster_id == other.cluster_id for other in cases) != 5
        for case in cases
    ):
        raise GroundingSuccessorExecutionError("cluster cardinality drifted")
    expected_hashes = instrument["package_sha256"]
    observed_hashes = {
        "cases": _sha256(builder.CASES_PATH),
        "gold": _sha256(builder.GOLD_PATH),
        "sources": _sha256(builder.SOURCE_PATH),
    }
    if observed_hashes != expected_hashes:
        raise GroundingSuccessorExecutionError("frozen package hash drifted")
    candidate_ranking = builder.rankings(control=False)
    control_ranking = builder.rankings(control=True)
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "valid",
        "case_count": len(cases),
        "control_case_count": len(controls),
        "control_complete_cluster_count": len(
            {case.cluster_id for case in cases if case.case_id in controls}
        ),
        "source_region_count": len(chunks),
        "candidate_ranking_sha256": candidate_ranking["content_sha256"],
        "control_ranking_sha256": control_ranking["content_sha256"],
        "provider_calls": 0,
        "cost_usd": 0,
    }


def preflight(*, resume: bool) -> dict[str, Any]:
    validation = validate()
    instrument = _load_instrument()
    blockers: list[str] = []
    if instrument.get("status") != "frozen-pending-execution":
        blockers.append("instrument-not-frozen")
    if not instrument.get("method_evaluation_execution_authorized"):
        blockers.append("method-execution-not-authorized")
    if instrument.get("provider_execution_authorized"):
        blockers.append("provider-execution-must-remain-disabled")
    if instrument.get("code_revision") != _git_revision():
        blockers.append("code-revision-drifted")
    if _relevant_worktree_changes():
        blockers.append("worktree-dirty")
    if RESULT_PATH.exists() and not resume:
        blockers.append("exclusive-result-already-exists")
    return {
        **validation,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "hidden_gold_opened": False,
    }


def _atomic_result(payload: dict[str, Any], *, resume: bool) -> None:
    if RESULT_PATH.is_file():
        existing = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if resume and existing == payload:
            return
        raise GroundingSuccessorExecutionError("exclusive result already exists")
    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = RESULT_PATH.with_name(f"{RESULT_PATH.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, RESULT_PATH)


def _inputs(*, control: bool) -> tuple[list[EvaluationCaseV1], dict[str, Any]]:
    cases, gold, _chunks = builder.load_inputs()
    if control:
        selected = set(builder.control_case_ids(cases))
        cases = [case for case in cases if case.case_id in selected]
        gold = [row for row in gold if row.case_id in selected]
    return cases, {row.case_id: row for row in gold}


async def _run(*, output_root: Path, resume: bool) -> dict[str, Any]:
    instrument = _load_instrument()
    engine = _engine()
    code_revision = _git_revision()
    candidate_cases, candidate_gold = _inputs(control=False)
    candidate = await execute_factual_package(
        output_root=output_root,
        engine=engine,
        package_id="fresh-development-500",
        cases=candidate_cases,
        gold=candidate_gold,
        source_package_path=builder.SOURCE_PATH,
        ranking=builder.rankings(control=False),
        control=False,
        code_revision=code_revision,
        maximum_cost_usd=0,
        resume=resume,
        known_benchmark=False,
        retriever=builder.CANDIDATE_ARCHITECTURE_ID,
        maximum_concurrency=8,
        program_id=INSTRUMENT_ID,
        profile_sha256=instrument["profile_sha256"],
        deterministic_generator="deterministic-evidence-set-grounded-generator-v2",
    )
    control_cases, control_gold = _inputs(control=True)
    control = await execute_factual_package(
        output_root=output_root,
        engine=engine,
        package_id="fresh-development-100-control",
        cases=control_cases,
        gold=control_gold,
        source_package_path=builder.SOURCE_PATH,
        ranking=builder.rankings(control=True),
        control=True,
        code_revision=code_revision,
        maximum_cost_usd=0,
        resume=resume,
        known_benchmark=False,
        retriever=builder.CONTROL_ARCHITECTURE_ID,
        maximum_concurrency=8,
        program_id=INSTRUMENT_ID,
        profile_sha256=instrument["profile_sha256"],
        deterministic_generator="deterministic-evidence-set-grounded-generator-v2",
    )
    gates = factual_hard_gates(candidate)
    interval_passed = (
        candidate["summary"]["fully_grounded_source_family_interval"]["lower_95"]
        >= 0.93
    )
    retrieval_gates = {
        "canonical_all_evidence_at_3": candidate["summary"]["metrics"][
            "canonical_all_evidence_at_3"
        ]
        >= 0.90,
        "evidence_recall_at_5": candidate["summary"]["metrics"][
            "evidence_recall_at_5"
        ]
        >= 0.95,
        "source_family_lower_95": interval_passed,
    }
    paired = shared._paired_control_pass(candidate, control)  # noqa: SLF001
    passed = all(gates.values()) and all(retrieval_gates.values()) and paired["passed"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-keep" if passed else "completed-refine",
        "decision": "Keep" if passed else "Refine",
        "code_revision": code_revision,
        "package_sha256": instrument["package_sha256"],
        "candidate": {
            "summary": candidate["summary"],
            "gates": {**gates, **retrieval_gates},
        },
        "control": {"summary": control["summary"]},
        "paired": paired,
        "provider_calls": candidate["provider_calls"] + control["provider_calls"],
        "cost_usd": candidate["cost_usd"] + control["cost_usd"],
        "hidden_gold_opened_after_durable_response_ledgers": True,
        "known_benchmark": False,
        "quality_claim": True,
    }


def simulate() -> dict[str, Any]:
    validate()
    with tempfile.TemporaryDirectory(prefix="grounding-successor-011-") as directory:
        result = asyncio.run(_run(output_root=Path(directory), resume=False))
    return {**result, "quality_claim": False, "status": f"simulated-{result['status']}"}


def execute(*, resume: bool) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["blockers"]:
        raise GroundingSuccessorExecutionError(
            "preflight blocked: " + ", ".join(readiness["blockers"])
        )
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    result = asyncio.run(_run(output_root=OUTPUT_ROOT, resume=resume))
    if result["provider_calls"] != 0 or result["cost_usd"] != 0:
        raise GroundingSuccessorExecutionError("network-free execution used a provider")
    _atomic_result(result, resume=resume)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        result = execute(resume=arguments.resume)
    elif arguments.preflight:
        result = preflight(resume=arguments.resume)
    elif arguments.simulate:
        result = simulate()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
