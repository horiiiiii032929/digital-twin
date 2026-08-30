#!/usr/bin/env python3
"""Validate, simulate, preflight, and execute the finite evaluation program."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.finite_program import (  # noqa: E402
    PROGRAM_ID,
    ProgramError,
    ProgramLedgerV1,
    ProgramStageName,
    ProgramStageStatus,
    load_program_manifest,
)
from src.digital_twin.evaluation.finite_program_runner import (  # noqa: E402
    FiniteProgramRunner,
    build_stage_result,
)
from src.digital_twin.model_policy import (  # noqa: E402
    OPENAI_MODEL_PRICING_USD_PER_MILLION,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_evaluation_program_001.json"
)
DEFAULT_OUTPUT_ROOT = ROOT / "reports/generated/course-digital-twin-evaluation-program-001"
PROGRAM_LEDGER_NAME = "program-ledger.sqlite3"
EXPECTED_MODELS = {
    "gpt-5.4-nano-2026-03-17": (0.20, 1.25),
    "gpt-5.4-mini-2026-03-17": (0.75, 4.50),
    "gpt-5.6-luna": (0.20, 1.20),
    "gpt-5.4-2026-03-05": (2.50, 15.00),
}


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProgramError(f"required JSON is unavailable: {path.name}") from error
    if not isinstance(value, dict):
        raise ProgramError(f"required JSON root is not an object: {path.name}")
    return value


def _validate_package(path: Path, *, key: str, count: int) -> dict[str, Any]:
    payload = _load_object(path)
    rows = payload.get(key)
    if not isinstance(rows, list) or len(rows) != count:
        raise ProgramError(f"{path.name} does not contain {count} {key}")
    expected = canonical_json_sha256(
        {name: value for name, value in payload.items() if name != "content_sha256"}
    )
    if payload.get("content_sha256") != expected:
        raise ProgramError(f"package hash drifted: {path.name}")
    return payload


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def validate() -> dict[str, Any]:
    manifest = load_program_manifest(INSTRUMENT_PATH)
    observed = {
        row.model: (
            row.input_price_usd_per_million,
            row.output_price_usd_per_million,
        )
        for row in manifest.models
    }
    if observed != EXPECTED_MODELS:
        raise ProgramError("finite program model or price bindings drifted")
    for model, prices in EXPECTED_MODELS.items():
        if OPENAI_MODEL_PRICING_USD_PER_MILLION.get(model) != prices:
            raise ProgramError(f"repository model policy drifted for {model}")
    development = _validate_package(
        ROOT / manifest.development_cases_path, key="cases", count=500
    )
    gold = _validate_package(
        ROOT / manifest.development_gold_path, key="gold", count=500
    )
    public_ids = {str(row["case_id"]) for row in development["cases"]}
    gold_ids = {str(row["case_id"]) for row in gold["gold"]}
    if public_ids != gold_ids or len(public_ids) != 500:
        raise ProgramError("development public/gold identities drifted")
    visual = _load_object(ROOT / manifest.visual_dataset_path)
    visual_expected_hash = canonical_json_sha256(
        {name: value for name, value in visual.items() if name != "content_sha256"}
    )
    if (
        visual.get("cluster_count") != 30
        or len(visual.get("assets", [])) != 30
        or visual.get("case_count") != 60
        or visual.get("content_sha256") != visual_expected_hash
        or visual.get("private_data_used") is not False
    ):
        raise ProgramError("true-visual supplement distribution drifted")
    source_plan = _load_object(ROOT / manifest.source_plan_path)
    clusters = source_plan.get("clusters")
    if not isinstance(clusters, list):
        raise ProgramError("source plan clusters are unavailable")
    expected_source_hash = canonical_json_sha256(
        {
            name: value
            for name, value in source_plan.items()
            if name != "content_sha256"
        }
    )
    if (
        source_plan.get("content_sha256") != expected_source_hash
        or source_plan.get("cluster_count") != 2_100
        or source_plan.get("private_data_read") is not False
        or source_plan.get("raw_source_committed") is not False
        or source_plan.get("provider_calls") != 0
    ):
        raise ProgramError("source plan provenance or privacy boundary drifted")
    identifiers = [str(row.get("cluster_id", "")) for row in clusters]
    if len(identifiers) != len(set(identifiers)) or any(not row for row in identifiers):
        raise ProgramError("source plan cluster identities drifted")
    allowed_licenses = {"CC-BY-SA-3.0", "CC-BY-NC-SA-4.0", "CC-BY-2.5-CA"}
    ranges: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    for row in clusters:
        source_path = Path(str(row.get("source_path", "")))
        repository_url = str(row.get("repository_url", ""))
        if (
            source_path.is_absolute()
            or ".." in source_path.parts
            or repository_url.startswith("https://github.com/") is False
            or row.get("license_spdx") not in allowed_licenses
            or row.get("source_modality") not in {
                "text",
                "structured-code",
                "structured-equation",
                "structured-table",
            }
        ):
            raise ProgramError("source plan contains an ineligible public source")
        start = int(row.get("char_start", -1))
        end = int(row.get("char_end", -1))
        if start < 0 or end <= start or not str(row.get("text", "")).strip():
            raise ProgramError("source plan contains an invalid source range")
        key = (str(row.get("course_id", "")), str(source_path))
        candidate = (start, end)
        if any(
            max(start, left) < min(end, right)
            for left, right in ranges[key]
        ):
            raise ProgramError("source plan source ranges overlap")
        ranges[key].append(candidate)
    if max(Counter(row["source_family_id"] for row in clusters).values()) > 5:
        raise ProgramError("source plan exceeds the source-family reuse cap")
    split_counts = {
        split: sum(row.get("split") == split for row in clusters)
        for split in ("development", "final")
    }
    if split_counts != {"development": 100, "final": 2_000}:
        raise ProgramError("source plan split distribution drifted")
    return {
        "program_id": PROGRAM_ID,
        "status": "passed-build-only",
        "program_manifest_sha256": manifest.content_sha256,
        "total_budget_usd": manifest.total_budget_usd,
        "projected_p99_cost_usd": sum(
            row.projected_p99_cost_usd for row in manifest.stages
        ),
        "stage_count": len(manifest.stages),
        "development_case_count": 500,
        "final_cluster_count": 2_000,
        "final_case_target": 10_000,
        "visual_asset_count": 30,
        "visual_case_count": 60,
        "provider_calls": 0,
        "paid_execution_authorized": manifest.paid_execution_authorized,
        "private_data_used": False,
    }


def preflight(*, output_root: Path, require_authorized: bool) -> dict[str, Any]:
    manifest = load_program_manifest(INSTRUMENT_PATH)
    result = validate()
    technical: list[str] = []
    authority: list[str] = []
    projected_p99 = sum(row.projected_p99_cost_usd for row in manifest.stages)
    if projected_p99 > manifest.total_budget_usd:
        technical.append("projected-p99-cost-exceeds-global-budget")
    for stage in manifest.stages:
        if stage.projected_p99_cost_usd > stage.budget_usd:
            technical.append(f"projected-p99-cost-exceeds-stage-budget:{stage.name.value}")
    try:
        age = manifest.metadata_age_hours(now=datetime.now(UTC))
    except ProgramError as error:
        technical.append(str(error))
    else:
        if age > manifest.metadata_freshness_hours:
            technical.append("provider-metadata-older-than-24-hours")
    if _git_dirty():
        technical.append("working-tree-dirty")
    if not os.getenv(manifest.credential_environment_variable, "").strip():
        technical.append("openai-credential-missing")
    qwen_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                ROOT
                / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    if not qwen_root.is_dir():
        technical.append("pinned-local-qwen-index-model-missing")
    if shutil.which("rsvg-convert") is None:
        technical.append("verified-svg-renderer-missing")
    try:
        from scripts.course_digital_twin_evaluation_live_stages import (
            LIVE_EXECUTORS_COMPLETE,
            live_executors,
        )

        if not LIVE_EXECUTORS_COMPLETE or len(live_executors(manifest)) != 9:
            technical.append("live-stage-executor-bundle-incomplete")
    except (ImportError, RuntimeError, ValueError):
        technical.append("live-stage-executor-bundle-unavailable")
    ledger_path = output_root / PROGRAM_LEDGER_NAME
    if ledger_path.exists():
        technical.append("exclusive-program-output-used; use --resume")
    if not manifest.provider_execution_authorized:
        authority.append("provider-execution-authorized-false")
    if not manifest.paid_execution_authorized:
        authority.append("paid-execution-authorized-false")
    try:
        for operation in (
            "dataset_generation",
            "external_model_evaluation",
            "local_model_evaluation",
            "method_evaluation_execution",
        ):
            require_bounded_pilot_operation_allowed(PROGRAM_ID, operation)
    except RepositoryFreezeError:
        authority.append("repository-bounded-authorization-absent")
    status = "ready"
    if technical:
        status = "blocked-not-ready"
    elif authority:
        status = "blocked-not-authorized" if require_authorized else "ready-pending-authorization"
    return {
        **result,
        "status": status,
        "technical_blockers": sorted(set(technical)),
        "authorization_blockers": sorted(set(authority)),
        "credential_value_emitted": False,
        "projected_p99_cost_usd": projected_p99,
        "remaining_projection_headroom_usd": (
            manifest.total_budget_usd - projected_p99
        ),
        "provider_calls": 0,
    }


def _simulation_executors(manifest, scenario: str):
    calls: dict[ProgramStageName, int] = {}

    def execute(context):
        calls[context.stage] = calls.get(context.stage, 0) + 1
        if scenario == "second-invalid" and context.stage == ProgramStageName.RETRIEVAL_DECISION:
            status = ProgramStageStatus.INVALID_EXECUTION
        elif scenario == "retrieval-quality-failure" and context.stage == ProgramStageName.RETRIEVAL_DECISION:
            status = ProgramStageStatus.COMPLETED_REFINE
        elif scenario == "product-quality-failure" and context.stage == ProgramStageName.PRODUCT_DEVELOPMENT:
            status = ProgramStageStatus.COMPLETED_REFINE
        elif scenario == "interrupted-resume" and context.stage == ProgramStageName.PRODUCT_DEVELOPMENT and calls[context.stage] == 1:
            status = ProgramStageStatus.INVALID_EXECUTION
        elif context.stage in {ProgramStageName.TRUE_VISUAL, ProgramStageName.SYNTHETIC_PROFILE}:
            status = ProgramStageStatus.COMPLETED_GO_DEEPER
        else:
            status = ProgramStageStatus.COMPLETED_KEEP
        cost = 51.0 if scenario == "budget-stop" and context.stage == ProgramStageName.RETRIEVAL_DECISION else 0.0
        return build_stage_result(
            manifest=manifest,
            stage=context.stage,
            status=status,
            provider_calls=0,
            cost_usd=cost,
            metrics={"simulation": True},
        )

    return {row.name: execute for row in manifest.stages}


def simulate(scenario: str) -> dict[str, Any]:
    manifest = load_program_manifest(INSTRUMENT_PATH)
    with tempfile.TemporaryDirectory(prefix="finite-program-simulation-") as directory:
        root = Path(directory)
        ledger = ProgramLedgerV1(
            root / PROGRAM_LEDGER_NAME,
            manifest=manifest,
            code_revision="a" * 40,
            resume=False,
        )
        runner = FiniteProgramRunner(
            root=ROOT,
            output_root=root / "stages",
            manifest=manifest,
            ledger=ledger,
            executors=_simulation_executors(manifest, scenario),
        )
        try:
            snapshot = runner.run(resume=False)
        except ProgramError as error:
            snapshot = ledger.snapshot()
            snapshot["expected_failure"] = type(error).__name__
        finally:
            ledger.close()
    return {"scenario": scenario, "provider_calls": 0, **snapshot}


def execute(*, output_root: Path, resume: bool) -> dict[str, Any]:
    load_dotenv(ROOT / ".env", override=False)
    readiness = preflight(output_root=output_root, require_authorized=True)
    if resume:
        readiness["technical_blockers"] = [
            row
            for row in readiness["technical_blockers"]
            if not row.startswith("exclusive-program-output-used")
        ]
        if not readiness["technical_blockers"] and not readiness["authorization_blockers"]:
            readiness["status"] = "ready"
    if readiness["status"] != "ready":
        raise ProgramError(f"program preflight blocked: {readiness['status']}")
    manifest = load_program_manifest(INSTRUMENT_PATH)
    from scripts.course_digital_twin_evaluation_live_stages import live_executors

    ledger = ProgramLedgerV1(
        output_root / PROGRAM_LEDGER_NAME,
        manifest=manifest,
        code_revision=_git_revision(),
        resume=resume,
    )
    try:
        return FiniteProgramRunner(
            root=ROOT,
            output_root=output_root / "stages",
            manifest=manifest,
            ledger=ledger,
            executors=live_executors(manifest),
        ).run(resume=resume)
    except BaseException:
        ledger.mark_interrupted()
        raise
    finally:
        ledger.close()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument(
        "--simulate",
        choices=(
            "pass",
            "retrieval-quality-failure",
            "product-quality-failure",
            "second-invalid",
            "interrupted-resume",
            "budget-stop",
        ),
    )
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def main() -> int:
    args = _arguments()
    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID)
    load_dotenv(ROOT / ".env", override=False)
    if args.validate:
        result = validate()
    elif args.simulate:
        result = simulate(args.simulate)
    elif args.preflight:
        result = preflight(output_root=args.output_root, require_authorized=False)
    else:
        result = execute(output_root=args.output_root, resume=args.resume)
    print(json.dumps(result, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
