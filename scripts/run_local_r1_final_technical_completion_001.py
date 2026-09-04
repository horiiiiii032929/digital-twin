#!/usr/bin/env python3
"""Orchestrate the two bounded paid stages before local R1.1 qualification."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from dotenv import load_dotenv

from scripts import run_professor_fidelity_proxy_c0_c3_002 as profile_proxy
from scripts import run_true_visual_product_checkpoint as visual_checkpoint
from src.digital_twin.evaluation.finite_program_io import atomic_write_json
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "local-r1-final-technical-completion-001"
PROGRAM_PATH = ROOT / (
    "research/05_evaluation/instruments/local_r1_final_technical_completion_001.json"
)
OUTPUT_ROOT = ROOT / "reports/generated/local-r1-final-technical-completion-001"
RESULT_PATH = OUTPUT_ROOT / "program-result.json"


class LocalR1CompletionError(RuntimeError):
    """Raised when the finite technical-completion program drifts."""


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LocalR1CompletionError(f"JSON root is invalid: {path.name}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repo_clean() -> bool:
    return not subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate() -> dict[str, Any]:
    program = _load(PROGRAM_PATH)
    if (
        program.get("program_id") != PROGRAM_ID
        or program.get("known_benchmark_10000_touched") is not False
        or program.get("private_data_authorized") is not False
        or program.get("automatic_child_progression") is not True
    ):
        raise LocalR1CompletionError("program authority boundary drifted")
    expected_order = [
        "true-visual-product-checkpoint-001",
        "professor-fidelity-proxy-c0-c3-002",
    ]
    if program.get("execution_order") != expected_order:
        raise LocalR1CompletionError("program execution order drifted")
    for child in program.get("children", []):
        path = ROOT / child["instrument_path"]
        if _file_sha256(path) != child["instrument_file_sha256"]:
            raise LocalR1CompletionError(
                f"child instrument binding drifted: {child['run_id']}"
            )
    visual = visual_checkpoint.validate()
    proxy = profile_proxy.validate()
    return {
        "status": "passed-build-only",
        "program_id": PROGRAM_ID,
        "provider_execution_authorized": program["provider_execution_authorized"],
        "paid_execution_authorized": program["paid_execution_authorized"],
        "children": {
            visual["instrument_id"]: visual["status"],
            proxy["instrument_id"]: proxy["status"],
        },
        "known_benchmark_10000_touched": False,
        "provider_calls": 0,
    }


def simulate() -> dict[str, Any]:
    validation = validate()
    visual = visual_checkpoint.simulate()
    proxy = profile_proxy.simulate()
    return {
        **validation,
        "status": "passed-network-free-simulation",
        "children": {
            visual["instrument_id"]: visual["status"],
            proxy["instrument_id"]: proxy["status"],
        },
        "provider_calls": 0,
    }


def _program_authorized(program: dict[str, Any]) -> bool:
    return bool(
        program.get("provider_execution_authorized")
        and program.get("paid_execution_authorized")
    )


def preflight(*, resume: bool = False) -> dict[str, Any]:
    validation = validate()
    program = _load(PROGRAM_PATH)
    blockers: list[str] = []
    if not _program_authorized(program):
        blockers.append("program-not-authorized")
    try:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "method_evaluation_execution"
        )
    except RepositoryFreezeError:
        blockers.append("program-freeze-authorization-missing")
    if not _repo_clean():
        blockers.append("repository-dirty")
    if not os.getenv("JINA_API_KEY", "").strip():
        blockers.append("jina-api-key-missing")
    if not os.getenv("OPENAI_API_KEY", "").strip():
        blockers.append("openai-api-key-missing")
    visual = visual_checkpoint.preflight(
        resume=resume and visual_checkpoint.RESPONSE_LEDGER.exists()
    )
    proxy = profile_proxy.preflight(
        resume=resume and profile_proxy.LEDGER_PATH.exists()
    )
    if visual["status"] != "ready" and not (
        resume and visual_checkpoint.RESULT_PATH.exists()
    ):
        blockers.append(f"visual-child-{visual['status']}")
    if proxy["status"] != "ready" and not (
        resume and profile_proxy.RESULT_PATH.exists()
    ):
        blockers.append(f"profile-child-{proxy['status']}")
    if RESULT_PATH.exists():
        blockers.append("program-result-exists")
    return {
        **validation,
        "status": "ready" if not blockers else "blocked",
        "blockers": blockers,
        "git_revision": _git_revision(),
        "git_clean": _repo_clean(),
        "visual_preflight": visual,
        "profile_preflight": proxy,
        "resume": resume,
    }


def _load_result(path: Path, *, run_id: str) -> dict[str, Any]:
    value = _load(path)
    if value.get("result_id") != run_id or "status" not in value:
        raise LocalR1CompletionError(f"child result is malformed: {path.name}")
    if run_id == visual_checkpoint.INSTRUMENT_ID:
        instrument = visual_checkpoint._load_hashed(visual_checkpoint.INSTRUMENT_PATH)
        if (
            value.get("instrument_sha256") != instrument["content_sha256"]
            or value.get("code_revision") != _git_revision()
        ):
            raise LocalR1CompletionError("visual child result binding drifted")
    elif run_id == profile_proxy.RUN_ID:
        instrument = _load(profile_proxy.INSTRUMENT_PATH)
        run_binding = value.get("run_binding")
        if (
            not isinstance(run_binding, dict)
            or run_binding.get("instrument_sha256")
            != profile_proxy.canonical_sha256(instrument)
            or run_binding.get("code_revision") != _git_revision()
        ):
            raise LocalR1CompletionError("profile child result binding drifted")
    return value


def _write_program_result(children: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = [row["status"] for row in children]
    status = (
        "invalid-execution"
        if any(value == "invalid-execution" for value in statuses)
        else "completed"
    )
    result = {
        "schema_version": "1.0.0",
        "result_id": PROGRAM_ID,
        "status": status,
        "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "code_revision": _git_revision(),
        "children": [
            {
                "result_id": row["result_id"],
                "status": row["status"],
                "decision": row["decision"],
            }
            for row in children
        ],
        "known_benchmark_10000_touched": False,
        "next_stage": "local-r1.1-qualification-007",
    }
    if RESULT_PATH.exists():
        raise LocalR1CompletionError("program result already exists")
    atomic_write_json(RESULT_PATH, result)
    return result


async def execute(*, resume: bool) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise LocalR1CompletionError(
            f"program preflight is blocked: {readiness['blockers']}"
        )
    children: list[dict[str, Any]] = []
    if visual_checkpoint.RESULT_PATH.exists():
        visual = _load_result(
            visual_checkpoint.RESULT_PATH,
            run_id=visual_checkpoint.INSTRUMENT_ID,
        )
    else:
        visual = await visual_checkpoint.execute(
            resume=resume and visual_checkpoint.RESPONSE_LEDGER.exists()
        )
    children.append(visual)
    if visual["status"] == "invalid-execution":
        return _write_program_result(children)

    if profile_proxy.RESULT_PATH.exists():
        proxy = _load_result(
            profile_proxy.RESULT_PATH,
            run_id=profile_proxy.RUN_ID,
        )
    else:
        proxy = await profile_proxy.execute(
            resume=resume and profile_proxy.LEDGER_PATH.exists()
        )
    children.append(proxy)
    return _write_program_result(children)


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    action.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.execute or args.resume:
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID,
            "external_model_evaluation",
        )
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID,
            "method_evaluation_execution",
        )
    if args.validate:
        result = validate()
    elif args.simulate:
        result = simulate()
    elif args.preflight:
        result = preflight()
    else:
        result = asyncio.run(execute(resume=args.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
