#!/usr/bin/env python3
"""Network-free verification and preflight for cross-engine evaluation 010."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from typing import Any

from dotenv import load_dotenv

from scripts import (
    build_governed_full_autonomy_v2_1_cross_engine_evaluation_010 as builder,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as autonomy,
)
from scripts import (
    run_governed_full_autonomy_v2_1_actual_product_evaluation_002 as shared,
)
from src.digital_twin.evaluation import (
    AutonomyEvaluationResponseV1,
    AutonomyRawEvidenceV2,
    CrossEngineProgramLedgerV1,
    ProductEngineBindingV1,
    score_autonomy_case_independently,
    summarize_independent_autonomy_scores,
)
from scripts.cross_engine_factual import (
    execute_factual_arm,
    execute_factual_package,
    factual_hard_gates,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = builder.PROGRAM_ID
GROUNDING_RESULT = ROOT / (
    "research/05_evaluation/records/"
    "academic-factual-qa-ambiguity-safe-comparison-002.json"
)
OUTPUT_ROOT = ROOT / "reports/generated" / PROGRAM_ID
PROGRAM_LEDGER = OUTPUT_ROOT / "program.sqlite3"
PROGRAM_RESULT = OUTPUT_ROOT / "result.json"


class CrossEngineExecutionError(RuntimeError):
    pass


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
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise CrossEngineExecutionError(f"exclusive output exists: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _e0() -> ProductEngineBindingV1:
    return next(
        item for item in builder.load_program().engines if item.engine_id == "e0"
    )


def _context() -> shared.ActualProductEvaluationContext:
    return shared.ActualProductEvaluationContext(
        builder=autonomy,
        instrument_id=PROGRAM_ID,
        grounding_result_path=GROUNDING_RESULT,
        grounding_result_id="academic-factual-qa-ambiguity-safe-comparison-002",
        selected_grounding_architecture_id=(
            "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ),
        runtime_grounding_architecture_id=(
            "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ),
        source_resolver=autonomy.source_fixture_for_case,
        engine_binding=_e0(),
        independent_scoring=True,
    )


def validate() -> dict[str, Any]:
    result = builder.validate()
    return {
        **result,
        "runner_status": "valid-network-free-only",
        "paid_execute_command_available": True,
    }


async def _simulate(*, limit: int | None = None) -> dict[str, Any]:
    validate()
    context = _context()
    contract = autonomy.build_contract()
    selected = contract if limit is None else contract[:limit]
    scores = []
    with tempfile.TemporaryDirectory(prefix="cross-engine-010-independent-") as directory:
        for condition, case, gold in selected:
            response = await shared._run_case(
                Path(directory),
                condition,
                case,
                provider_backed=False,
                remaining_cost_usd=1.0,
                context=context,
            )
            raw = response.diagnostic_trace.get("independent_evidence_v2")
            evidence = AutonomyRawEvidenceV2.model_validate(raw)
            scores.append(
                score_autonomy_case_independently(case, gold, response, evidence)
            )
    summary = summarize_independent_autonomy_scores(scores)
    return {
        "program_id": PROGRAM_ID,
        "status": (
            "passed-independent-network-free-simulation"
            if summary["all_case_hard_gates_passed"]
            else "failed-independent-network-free-simulation"
        ),
        "case_count": len(scores),
        "summary": summary,
        "provider_calls": 0,
        "cost_usd": 0,
        "quality_claim": False,
    }


def simulate(*, limit: int | None = None) -> dict[str, Any]:
    return asyncio.run(_simulate(limit=limit))


def _autonomy_context(engine: ProductEngineBindingV1) -> shared.ActualProductEvaluationContext:
    return shared.ActualProductEvaluationContext(
        builder=autonomy,
        instrument_id=f"{PROGRAM_ID}-{engine.engine_id}-autonomy",
        grounding_result_path=GROUNDING_RESULT,
        grounding_result_id="academic-factual-qa-ambiguity-safe-comparison-002",
        selected_grounding_architecture_id=(
            "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ),
        runtime_grounding_architecture_id=(
            "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ),
        source_resolver=autonomy.source_fixture_for_case,
        engine_binding=engine,
        independent_scoring=True,
        canary_case_ids=(
            "fresh-trajectory-001-t0-grounded-control-seed-1",
            "fresh-trajectory-006-t1-v2-reactive-seed-1",
        ),
    )


def _autonomy_rows(path: Path) -> list[tuple[str, AutonomyEvaluationResponseV1]] | None:
    if not path.is_file():
        return None
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("status") != "completed" or metadata.get("response_count") != "820":
            return None
        rows = []
        for condition, serialized, expected_hash in connection.execute(
            "SELECT condition_id,payload_json,payload_sha256 FROM responses "
            "ORDER BY sequence"
        ):
            if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
                raise CrossEngineExecutionError("autonomy response hash drifted")
            rows.append(
                (
                    condition,
                    AutonomyEvaluationResponseV1.model_validate_json(serialized),
                )
            )
    finally:
        connection.close()
    return rows


def _canary_models_valid(
    engine: ProductEngineBindingV1,
    rows: list[tuple[str, AutonomyEvaluationResponseV1]],
) -> bool:
    if engine.provider == "deterministic":
        return all(response.provider_calls == 0 for _condition, response in rows)
    expected = {
        "t0-grounded-control": {engine.generator_model},
        "t1-v2-reactive": {engine.planner_model, engine.generator_model},
    }
    if len(rows) != 2:
        return False
    for condition, response in rows:
        observed = {
            call.provider_model
            for call in response.operational_metrics.call_records
            if call.status == "completed" and call.provider_model
        }
        if response.operational_status != "completed" or observed != expected[condition]:
            return False
    return True


async def _execute_autonomy_engine(
    *,
    engine: ProductEngineBindingV1,
    maximum_cost_usd: float,
    resume: bool,
    maximum_concurrency: int = 8,
) -> dict[str, Any]:
    context = _autonomy_context(engine)
    root = OUTPUT_ROOT / "autonomy" / engine.engine_id
    response_path = root / "responses.sqlite3"
    result_path = root / "result.json"
    if result_path.is_file():
        if not resume:
            raise CrossEngineExecutionError("exclusive autonomy result exists")
        return json.loads(result_path.read_text(encoding="utf-8"))
    binding = {
        "program_id": PROGRAM_ID,
        "program_sha256": hashlib.sha256(builder.INSTRUMENT.read_bytes()).hexdigest(),
        "engine": engine.model_dump(mode="json"),
        "public_sha256": autonomy.public_payload()["content_sha256"],
        "code_revision": _git_revision(),
    }
    existing = _autonomy_rows(response_path)
    if existing is None:
        arm_resume = resume and response_path.exists()
        ledger = shared._ResponseLedger(  # noqa: SLF001
            response_path,
            binding=binding,
            resume=arm_resume,
            context=context,
        )
        completed = ledger.completed_ids()
        contract = shared._ordered_contract(context)  # noqa: SLF001
        provider_backed = engine.provider != "deterministic"
        try:
            canary_ids = set(context.canary_case_ids)
            for condition, case, _gold in contract[:2]:
                if case.case_id in completed:
                    continue
                response = await shared._run_case(  # noqa: SLF001
                    root / "runtime",
                    condition,
                    case,
                    provider_backed=provider_backed,
                    remaining_cost_usd=max(0.02, maximum_cost_usd),
                    context=context,
                )
                ledger.record(condition, response)
                completed.add(case.case_id)
            canaries = [
                row for row in ledger.responses() if row[1].case_id in canary_ids
            ]
            if not _canary_models_valid(engine, canaries):
                raise CrossEngineExecutionError(
                    f"{engine.engine_id} provider canary identity failed"
                )
            pending = [row for row in contract[2:] if row[1].case_id not in completed]
            for offset in range(0, len(pending), maximum_concurrency):
                batch = pending[offset : offset + maximum_concurrency]
                remaining = maximum_cost_usd - float(ledger.totals()["cost_usd"])
                if remaining <= 0:
                    raise CrossEngineExecutionError("autonomy engine cost stop reached")

                async def run_one(item):
                    condition, case, _gold = item
                    response = await shared._run_case(  # noqa: SLF001
                        root / "runtime",
                        condition,
                        case,
                        provider_backed=provider_backed,
                        remaining_cost_usd=max(0.02, remaining / len(batch)),
                        context=context,
                    )
                    return condition, response

                tasks = [asyncio.create_task(run_one(item)) for item in batch]
                try:
                    for task in asyncio.as_completed(tasks):
                        condition, response = await task
                        ledger.record(condition, response)
                except BaseException:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    raise
            ledger.mark_complete()
            existing = ledger.responses()
        except BaseException:
            ledger.mark_interrupted()
            raise
        finally:
            ledger.close()
    if existing is None or len(existing) != 820:
        raise CrossEngineExecutionError("autonomy engine response ledger is incomplete")
    contract_by_id = {
        case.case_id: (case, gold)
        for _condition, case, gold in autonomy.build_contract()
    }
    scores = []
    for _condition, response in existing:
        case, gold = contract_by_id[response.case_id]
        evidence = AutonomyRawEvidenceV2.model_validate(
            response.diagnostic_trace.get("independent_evidence_v2")
        )
        scores.append(
            score_autonomy_case_independently(case, gold, response, evidence)
        )
    summary = summarize_independent_autonomy_scores(scores)
    response_by_id = {response.case_id: response for _condition, response in existing}
    serialized_scores = []
    for score in scores:
        response = response_by_id[score.case_id]
        serialized_scores.append(
            {
                **score.model_dump(mode="json"),
                "cost_usd": response.cost_usd,
                "provider_calls": response.provider_calls,
            }
        )
    result = {
        "engine": engine.model_dump(mode="json"),
        "summary": summary,
        "case_scores": serialized_scores,
        "provider_calls": sum(row.provider_calls for _condition, row in existing),
        "cost_usd": sum(row.cost_usd for _condition, row in existing),
    }
    _atomic_json(result_path, result)
    return result


def _autonomy_hard_gates(result: dict[str, Any]) -> dict[str, bool]:
    summary = result["summary"]
    return {
        "safe_grounded_autonomous_success": summary[
            "safe_grounded_autonomous_success"
        ]
        == 1.0,
        "event_action_eligibility": summary["event_action_eligibility_rate"] == 1.0,
        "authority_preservation": summary["authority_preservation_rate"] == 1.0,
        "citation_lineage": summary["citation_lineage_rate"] == 1.0,
        "state_action_delivery": summary[
            "state_action_delivery_reconciliation_rate"
        ]
        == 1.0,
        "restart_consistency": summary["restart_consistency_rate"] == 1.0,
        "pedagogical_transition": summary["pedagogical_transition_rate"] >= 0.95,
        "goal_termination": summary["goal_termination_accuracy"] >= 0.98,
    }


def _paired_control_pass(
    candidate: dict[str, Any], control: dict[str, Any]
) -> dict[str, Any]:
    candidate_by_id = {row["case_id"]: row for row in candidate["case_scores"]}
    control_by_id = {row["case_id"]: row for row in control["case_scores"]}
    if not set(control_by_id).issubset(candidate_by_id):
        raise CrossEngineExecutionError("paired control identities drifted")
    answerable = [
        case_id for case_id, row in control_by_id.items() if row["answerable"]
    ]
    boundary = [
        case_id for case_id, row in control_by_id.items() if not row["answerable"]
    ]
    retention_delta = sum(
        float(candidate_by_id[case_id]["fully_grounded_success"])
        - float(control_by_id[case_id]["fully_grounded_success"])
        for case_id in answerable
    ) / len(answerable)
    candidate_boundary = sum(
        float(candidate_by_id[case_id]["boundary_safe"]) for case_id in boundary
    ) / len(boundary)
    control_boundary = sum(
        float(control_by_id[case_id]["boundary_safe"]) for case_id in boundary
    ) / len(boundary)
    return {
        "supported_answer_retention_delta": retention_delta,
        "candidate_boundary_safety": candidate_boundary,
        "control_boundary_safety": control_boundary,
        "passed": retention_delta >= -0.03 and candidate_boundary >= control_boundary,
    }


def _record_stage_cases(
    ledger: CrossEngineProgramLedgerV1,
    *,
    stage_id: str,
    engine_id: str,
    condition_id: str,
    rows: list[dict[str, Any]],
) -> None:
    for row in rows:
        case_id = str(row["case_id"])
        if ledger.has_case(
            stage_id=stage_id,
            engine_id=engine_id,
            condition_id=condition_id,
            case_id=case_id,
        ):
            continue
        ledger.record_case(
            stage_id=stage_id,
            engine_id=engine_id,
            condition_id=condition_id,
            case_id=case_id,
            response={"case_id": case_id, "engine_id": engine_id},
            score=row,
            cost_usd=float(row.get("cost_usd", 0.0)),
        )


def _load_factual_rows(
    public_path: Path,
    gold_path: Path,
) -> tuple[list[EvaluationCaseV1], dict[str, EvaluationGoldV1]]:
    public = builder.factual._load_hashed(public_path)  # noqa: SLF001
    hidden = builder.factual._load_hashed(gold_path)  # noqa: SLF001
    cases = [
        EvaluationCaseV1.model_validate(row) for row in public["cases"]
    ]
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(item)
            for item in hidden["gold"]
        )
    }
    if {row.case_id for row in cases} != set(gold):
        raise CrossEngineExecutionError("factual package identities drifted")
    return cases, gold


def _write_or_verify_json(path: Path, payload: dict[str, Any]) -> None:
    if path.is_file():
        if json.loads(path.read_text(encoding="utf-8")) != payload:
            raise CrossEngineExecutionError(f"resume artifact drifted: {path.name}")
        return
    _atomic_json(path, payload)


async def execute_sealed_confirmation(
    *,
    ledger: CrossEngineProgramLedgerV1,
    top_two: list[str],
    resume: bool,
) -> dict[str, Any]:
    program = builder.load_program()
    engines = {row.engine_id: row for row in program.engines}
    if len(top_two) != 2 or any(engine_id not in engines for engine_id in top_two):
        raise CrossEngineExecutionError("sealed confirmation requires two bound engines")
    cases, gold = _load_factual_rows(builder.SEALED_PUBLIC, builder.SEALED_GOLD)
    ranking = builder.sealed_rankings()
    statuses = {row["stage_id"]: row["status"] for row in ledger.snapshot()["stages"]}
    recording = statuses["sealed-confirmation-1000"] != "passed"
    if statuses["sealed-confirmation-1000"] == "quality-failed":
        raise CrossEngineExecutionError("sealed confirmation already quality-failed")
    if recording:
        ledger.begin_stage("sealed-confirmation-1000")
    results: dict[str, Any] = {}
    for engine_id in top_two:
        remaining = program.total_budget_usd - ledger.total_cost_usd()
        if remaining <= 0:
            raise CrossEngineExecutionError("program cost stop reached before sealed arm")
        result = await execute_factual_package(
            output_root=OUTPUT_ROOT,
            engine=engines[engine_id],
            package_id="sealed-confirmation-1000",
            cases=cases,
            gold=gold,
            source_package_path=builder.SEALED_SOURCES,
            ranking=ranking,
            control=False,
            code_revision=_git_revision(),
            maximum_cost_usd=remaining,
            resume=resume,
            known_benchmark=False,
            retriever="ambiguity-safe-source-semantic-evidence-atoms-v2",
            maximum_concurrency=8,
        )
        gates = factual_hard_gates(result)
        results[engine_id] = {
            "summary": result["summary"],
            "gates": gates,
            "passed": all(gates.values()),
            "cost_usd": result["cost_usd"],
        }
        if recording:
            _record_stage_cases(
                ledger,
                stage_id="sealed-confirmation-1000",
                engine_id=engine_id,
                condition_id="fresh-sealed-candidate",
                rows=result["case_scores"],
            )
    eligible = [engine_id for engine_id in top_two if results[engine_id]["passed"]]
    ranked = sorted(
        eligible,
        key=lambda engine_id: (
            -results[engine_id]["summary"]["metrics"][
                "fully_grounded_factual_success"
            ],
            results[engine_id]["cost_usd"],
            engine_id,
        ),
    )
    stage_result = {
        "engines": results,
        "eligible_engine_ids": ranked,
        "selected_engine_id": ranked[0] if ranked else None,
    }
    if not ranked:
        if recording:
            ledger.complete_stage(
                "sealed-confirmation-1000",
                result=stage_result,
                decision="quality-failed",
            )
        return {**stage_result, "status": "completed-refine"}
    if recording:
        ledger.complete_stage(
            "sealed-confirmation-1000", result=stage_result, decision="passed"
        )
    return {**stage_result, "status": "completed-keep"}


async def execute_known_regression(
    *,
    ledger: CrossEngineProgramLedgerV1,
    engine_id: str,
    resume: bool,
) -> dict[str, Any]:
    program = builder.load_program()
    engine = next(row for row in program.engines if row.engine_id == engine_id)
    candidate_cases, candidate_gold = _load_factual_rows(
        builder.KNOWN_PUBLIC, builder.KNOWN_GOLD
    )
    control_cases, control_gold = _load_factual_rows(
        builder.KNOWN_CONTROL_PUBLIC, builder.KNOWN_CONTROL_GOLD
    )
    semantic_source_path = OUTPUT_ROOT / "known-regression-semantic-sources.json"
    _write_or_verify_json(semantic_source_path, builder.known_semantic_source_payload())
    statuses = {row["stage_id"]: row["status"] for row in ledger.snapshot()["stages"]}
    recording = statuses["known-regression-10000-plus-1000"] != "passed"
    if statuses["known-regression-10000-plus-1000"] == "quality-failed":
        raise CrossEngineExecutionError("known regression already quality-failed")
    if recording:
        ledger.begin_stage("known-regression-10000-plus-1000")
    remaining = program.total_budget_usd - ledger.total_cost_usd()
    candidate = await execute_factual_package(
        output_root=OUTPUT_ROOT,
        engine=engine,
        package_id="known-regression-10000",
        cases=candidate_cases,
        gold=candidate_gold,
        source_package_path=semantic_source_path,
        ranking=builder.known_rankings(control=False),
        control=False,
        code_revision=_git_revision(),
        maximum_cost_usd=remaining,
        resume=resume,
        known_benchmark=True,
        retriever="ambiguity-safe-source-semantic-evidence-atoms-v2",
        maximum_concurrency=12,
    )
    remaining = program.total_budget_usd - ledger.total_cost_usd() - float(
        candidate["cost_usd"]
    )
    if remaining <= 0:
        raise CrossEngineExecutionError("program cost stop reached before known control")
    control = await execute_factual_package(
        output_root=OUTPUT_ROOT,
        engine=engine,
        package_id="known-regression-1000-control",
        cases=control_cases,
        gold=control_gold,
        source_package_path=semantic_source_path,
        ranking=builder.known_rankings(control=True),
        control=True,
        code_revision=_git_revision(),
        maximum_cost_usd=remaining,
        resume=resume,
        known_benchmark=True,
        retriever="source-semantic-evidence-atoms-v1",
        maximum_concurrency=12,
    )
    gates = factual_hard_gates(candidate)
    paired = _paired_control_pass(candidate, control)
    stage_result = {
        "engine_id": engine_id,
        "candidate": candidate["summary"],
        "control": control["summary"],
        "gates": gates,
        "paired": paired,
        "passed": all(gates.values()) and paired["passed"],
        "cost_usd": candidate["cost_usd"] + control["cost_usd"],
    }
    if recording:
        _record_stage_cases(
            ledger,
            stage_id="known-regression-10000-plus-1000",
            engine_id=engine_id,
            condition_id="known-candidate",
            rows=candidate["case_scores"],
        )
        _record_stage_cases(
            ledger,
            stage_id="known-regression-10000-plus-1000",
            engine_id=engine_id,
            condition_id="known-control",
            rows=control["case_scores"],
        )
        ledger.complete_stage(
            "known-regression-10000-plus-1000",
            result=stage_result,
            decision="passed" if stage_result["passed"] else "quality-failed",
        )
    return {
        **stage_result,
        "status": "completed-keep" if stage_result["passed"] else "completed-refine",
    }


def execute_supplementary_proxies(
    *,
    ledger: CrossEngineProgramLedgerV1,
    selected_engine_id: str,
    selected_autonomy: dict[str, Any],
) -> dict[str, Any]:
    profile_record_path = ROOT / (
        "research/05_evaluation/records/"
        "course-digital-twin-synthetic-profile-c0-c2-002.json"
    )
    profile_record = json.loads(profile_record_path.read_text(encoding="utf-8"))
    statuses = {row["stage_id"]: row["status"] for row in ledger.snapshot()["stages"]}
    recording = statuses["supplementary-proxies"] != "passed"
    if recording:
        ledger.begin_stage("supplementary-proxies")
    result = {
        "selected_engine_id": selected_engine_id,
        "professor_profile_proxy": {
            "evidence_id": "course-digital-twin-synthetic-profile-c0-c2-002",
            "decision": profile_record.get("decision"),
            "authoritative": False,
            "claim": "synthetic LLM-only professor-profile proxy",
        },
        "learning_proxy": {
            "source": "selected-engine 820-case actual-product autonomy evaluation",
            "safe_grounded_autonomous_success": selected_autonomy["summary"][
                "safe_grounded_autonomous_success"
            ],
            "goal_termination_accuracy": selected_autonomy["summary"][
                "goal_termination_accuracy"
            ],
            "authoritative": False,
            "claim": "simulated learner-process proxy, not real learning improvement",
        },
        "visual_proxy": {
            "evidence_id": "academic-factual-qa-visual-supplement-001",
            "status": "separate-go-deeper-track",
            "authoritative": False,
            "claim": "text/OCR fallback only in the selected R1",
        },
        "usability_proxy": {
            "status": "agent-and-automated-workflow-proxy",
            "authoritative": False,
            "claim": "not external human usability evidence",
        },
        "stage_completed": True,
    }
    if recording:
        for proxy_id, payload in (
            ("professor-profile", result["professor_profile_proxy"]),
            ("learning", result["learning_proxy"]),
            ("visual", result["visual_proxy"]),
            ("usability", result["usability_proxy"]),
        ):
            ledger.record_case(
                stage_id="supplementary-proxies",
                engine_id=selected_engine_id,
                condition_id="llm-only-or-agent-proxy",
                case_id=proxy_id,
                response=payload,
                score=payload,
                cost_usd=0,
            )
        ledger.complete_stage(
            "supplementary-proxies", result=result, decision="passed"
        )
    return result


def execute_local_release_qualification(
    *,
    ledger: CrossEngineProgramLedgerV1,
    selected_engine_id: str,
) -> dict[str, Any]:
    from scripts.run_autonomous_tutoring_r1_local_confirmation import (
        validate as validate_local_r1,
    )
    from scripts.run_r1_public_preview import validate as validate_preview

    statuses = {row["stage_id"]: row["status"] for row in ledger.snapshot()["stages"]}
    recording = statuses["local-release-qualification"] != "passed"
    if statuses["local-release-qualification"] == "quality-failed":
        raise CrossEngineExecutionError("local release already quality-failed")
    if recording:
        ledger.begin_stage("local-release-qualification")
    local = validate_local_r1()
    preview = validate_preview()
    focused = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/test_run_autonomous_tutoring_graph_development.py",
            "tests/digital_twin/test_learning_gap.py",
            "tests/digital_twin/test_proactive_outreach.py",
            "tests/api/test_publication_api.py",
            "tests/services/test_runtime_backup.py",
            "-q",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    passed = (
        focused.returncode == 0
        and local.get("status") in {"passed", "validated"}
        and str(preview.get("status", "")).startswith("passed")
    )
    result = {
        "selected_engine_id": selected_engine_id,
        "qualified_local_r1": local,
        "preview_contract": preview,
        "focused_test_exit_code": focused.returncode,
        "focused_test_output_tail": focused.stdout[-4_000:],
        "focused_test_error_tail": focused.stderr[-2_000:],
        "t0_rollback_retained": True,
        "passed": passed,
    }
    if recording:
        ledger.record_case(
            stage_id="local-release-qualification",
            engine_id=selected_engine_id,
            condition_id="immutable-local-release",
            case_id="local-r1-release-qualification",
            response={"selected_engine_id": selected_engine_id},
            score=result,
            cost_usd=0,
        )
        ledger.complete_stage(
            "local-release-qualification",
            result=result,
            decision="passed" if passed else "quality-failed",
        )
    return result


def _program_binding() -> dict[str, Any]:
    program = builder.load_program()
    return {
        "program": program.model_dump(mode="json"),
        "instrument_sha256": hashlib.sha256(builder.INSTRUMENT.read_bytes()).hexdigest(),
        "code_revision": _git_revision(),
    }


def _save_terminal_result(payload: dict[str, Any]) -> dict[str, Any]:
    if PROGRAM_RESULT.is_file():
        existing = json.loads(PROGRAM_RESULT.read_text(encoding="utf-8"))
        if existing != payload:
            raise CrossEngineExecutionError("terminal program result drifted")
        saved = existing
    else:
        _atomic_json(PROGRAM_RESULT, payload)
        saved = payload
    write_report_artifacts(saved)
    return saved


def write_report_artifacts(result: dict[str, Any]) -> dict[str, str]:
    import matplotlib.pyplot as plt

    development = result.get("development", {}).get("development", {})
    engine_ids = sorted(development)
    factual = [
        development[engine_id]["candidate"]["metrics"][
            "fully_grounded_factual_success"
        ]
        for engine_id in engine_ids
    ]
    autonomy_rows = result.get("development", {}).get("autonomy", {})
    autonomous = [
        autonomy_rows.get(engine_id, {}).get("summary", {}).get(
            "safe_grounded_autonomous_success", 0
        )
        for engine_id in engine_ids
    ]
    chart_path = OUTPUT_ROOT / "professor-ready-kpis.png"
    if not chart_path.exists() and engine_ids:
        figure, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
        axes[0].bar(engine_ids, factual, color="#2563eb")
        axes[0].axhline(0.95, color="#b91c1c", linestyle="--", linewidth=1)
        axes[0].set_title("500-case grounded factual success")
        axes[0].set_ylim(0, 1.02)
        axes[0].set_ylabel("Rate")
        axes[1].bar(engine_ids, autonomous, color="#0f766e")
        axes[1].axhline(1.0, color="#b91c1c", linestyle="--", linewidth=1)
        axes[1].set_title("820-case safe autonomous success")
        axes[1].set_ylim(0, 1.02)
        figure.suptitle("Cross-engine Course Digital Twin evaluation")
        figure.savefig(chart_path, dpi=180)
        plt.close(figure)
    selected = result.get("selected_engine_id") or result.get(
        "sealed_confirmation", {}
    ).get("selected_engine_id")
    known = result.get("known_regression", {})
    known_metric = known.get("candidate", {}).get("metrics", {}).get(
        "fully_grounded_factual_success"
    )
    lines = [
        f"# {PROGRAM_ID} result",
        "",
        f"- Decision: **{result.get('decision', 'unknown')}**",
        f"- Selected engine: `{selected or 'none'}`",
        f"- Reported program cost: USD {result.get('ledger', {}).get('cost_usd', 0):.4f}",
    ]
    if known_metric is not None:
        lines.append(
            f"- Known 10,000-case grounded factual success: {known_metric:.1%}"
        )
    lines.extend(
        [
            "",
            "Deterministic source, action, claim, citation, policy, persistence, and "
            "delivery checks are authoritative. Model review is advisory.",
            "",
            "The professor-profile, usability, and learning results are LLM/agent "
            "proxies. They do not establish real-professor fidelity, real-student "
            "usability, or real learning improvement.",
        ]
    )
    summary_path = OUTPUT_ROOT / "professor-ready-summary.md"
    if not summary_path.exists():
        summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    manifest_path = OUTPUT_ROOT / "selected-system-manifest.json"
    _write_or_verify_json(
        manifest_path,
        {
            "program_id": PROGRAM_ID,
            "selected_engine_id": selected,
            "code_revision": _git_revision(),
            "instrument_sha256": hashlib.sha256(builder.INSTRUMENT.read_bytes()).hexdigest(),
            "factual_method": "ambiguity-safe-source-semantic-evidence-atoms-v2",
            "autonomy_graph": "governed-full-autonomy-v2.1",
            "result_status": result.get("status"),
        },
    )
    return {
        "summary": str(summary_path),
        "chart": str(chart_path) if chart_path.exists() else "not-generated",
        "manifest": str(manifest_path),
    }


async def execute_program(*, resume: bool) -> dict[str, Any]:
    development = await execute_development_and_autonomy(resume=resume)
    if development["status"] == "completed-refine":
        return _save_terminal_result(development)
    program = builder.load_program()
    ledger = CrossEngineProgramLedgerV1(
        PROGRAM_LEDGER,
        program_id=PROGRAM_ID,
        binding=_program_binding(),
        maximum_cost_usd=program.total_budget_usd,
        resume=True,
    )
    try:
        sealed_result = await execute_sealed_confirmation(
            ledger=ledger,
            top_two=development["top_two_engine_ids"],
            resume=resume,
        )
        if sealed_result["status"] == "completed-refine":
            return _save_terminal_result(
                {
                    "program_id": PROGRAM_ID,
                    "status": "completed-refine",
                    "decision": "Refine",
                    "development": development,
                    "sealed_confirmation": sealed_result,
                    "ledger": ledger.snapshot(),
                }
            )
        selected_engine_id = str(sealed_result["selected_engine_id"])
        known_result = await execute_known_regression(
            ledger=ledger,
            engine_id=selected_engine_id,
            resume=resume,
        )
        if known_result["status"] == "completed-refine":
            return _save_terminal_result(
                {
                    "program_id": PROGRAM_ID,
                    "status": "completed-refine",
                    "decision": "Refine",
                    "development": development,
                    "sealed_confirmation": sealed_result,
                    "known_regression": known_result,
                    "ledger": ledger.snapshot(),
                }
            )
        selected_autonomy = development["autonomy"][selected_engine_id]
        proxies = execute_supplementary_proxies(
            ledger=ledger,
            selected_engine_id=selected_engine_id,
            selected_autonomy=selected_autonomy,
        )
        release = execute_local_release_qualification(
            ledger=ledger,
            selected_engine_id=selected_engine_id,
        )
        if not release["passed"]:
            return _save_terminal_result(
                {
                    "program_id": PROGRAM_ID,
                    "status": "completed-refine",
                    "decision": "Refine",
                    "selected_engine_id": selected_engine_id,
                    "development": development,
                    "sealed_confirmation": sealed_result,
                    "known_regression": known_result,
                    "supplementary_proxies": proxies,
                    "local_release": release,
                    "ledger": ledger.snapshot(),
                }
            )
        ledger.finish()
        return _save_terminal_result(
            {
                "program_id": PROGRAM_ID,
                "status": "completed-keep",
                "decision": "Keep",
                "release_decision": "qualified-local-r1-release-candidate",
                "selected_engine_id": selected_engine_id,
                "development": development,
                "sealed_confirmation": sealed_result,
                "known_regression": known_result,
                "supplementary_proxies": proxies,
                "local_release": release,
                "ledger": ledger.snapshot(),
            }
        )
    finally:
        ledger.close()


async def execute_development_and_autonomy(*, resume: bool) -> dict[str, Any]:
    program = builder.load_program()
    binding = {
        "program": program.model_dump(mode="json"),
        "instrument_sha256": hashlib.sha256(builder.INSTRUMENT.read_bytes()).hexdigest(),
        "code_revision": _git_revision(),
    }
    ledger = CrossEngineProgramLedgerV1(
        PROGRAM_LEDGER,
        program_id=PROGRAM_ID,
        binding=binding,
        maximum_cost_usd=program.total_budget_usd,
        resume=resume,
    )
    development_results: dict[str, Any] = {}
    autonomy_results: dict[str, Any] = {}
    try:
        stage_status = {
            row["stage_id"]: row["status"] for row in ledger.snapshot()["stages"]
        }
        development_recording = stage_status["development-500-plus-100"] != "passed"
        if development_recording:
            ledger.begin_stage("development-500-plus-100")
        for engine in program.engines:
            remaining = program.total_budget_usd - ledger.total_cost_usd()
            if remaining <= 0:
                raise CrossEngineExecutionError("program cost stop reached before factual arm")
            candidate = await execute_factual_arm(
                output_root=OUTPUT_ROOT,
                engine=engine,
                control=False,
                code_revision=_git_revision(),
                maximum_cost_usd=remaining / 2,
                resume=resume,
            )
            remaining_control = (
                program.total_budget_usd
                - ledger.total_cost_usd()
                - float(candidate["cost_usd"])
            )
            if remaining_control <= 0:
                raise CrossEngineExecutionError(
                    "program cost stop reached before factual control"
                )
            control = await execute_factual_arm(
                output_root=OUTPUT_ROOT,
                engine=engine,
                control=True,
                code_revision=_git_revision(),
                maximum_cost_usd=remaining_control,
                resume=resume,
            )
            gates = factual_hard_gates(candidate)
            paired = _paired_control_pass(candidate, control)
            development_results[engine.engine_id] = {
                "candidate": candidate["summary"],
                "control": control["summary"],
                "gates": gates,
                "paired": paired,
                "passed": all(gates.values()) and paired["passed"],
                "cost_usd": candidate["cost_usd"] + control["cost_usd"],
            }
            if development_recording:
                _record_stage_cases(
                    ledger,
                    stage_id="development-500-plus-100",
                    engine_id=engine.engine_id,
                    condition_id="candidate",
                    rows=candidate["case_scores"],
                )
                _record_stage_cases(
                    ledger,
                    stage_id="development-500-plus-100",
                    engine_id=engine.engine_id,
                    condition_id="control",
                    rows=control["case_scores"],
                )
        if development_recording:
            ledger.complete_stage(
                "development-500-plus-100",
                result={"engines": development_results},
                decision="passed",
            )

        stage_status = {
            row["stage_id"]: row["status"] for row in ledger.snapshot()["stages"]
        }
        autonomy_recording = stage_status["autonomy-820"] != "passed"
        if stage_status["autonomy-820"] == "quality-failed":
            raise CrossEngineExecutionError("terminal quality-failed program cannot resume")
        if autonomy_recording:
            ledger.begin_stage("autonomy-820")
        for engine in program.engines:
            remaining = program.total_budget_usd - ledger.total_cost_usd()
            if remaining <= 0:
                raise CrossEngineExecutionError("program cost stop reached before autonomy")
            result = await _execute_autonomy_engine(
                engine=engine,
                maximum_cost_usd=remaining,
                resume=resume,
            )
            gates = _autonomy_hard_gates(result)
            autonomy_results[engine.engine_id] = {
                "summary": result["summary"],
                "gates": gates,
                "passed": all(gates.values()),
                "provider_calls": result["provider_calls"],
                "cost_usd": result["cost_usd"],
            }
            if autonomy_recording:
                _record_stage_cases(
                    ledger,
                    stage_id="autonomy-820",
                    engine_id=engine.engine_id,
                    condition_id="all-autonomy-conditions",
                    rows=result["case_scores"],
                )
        eligible = [
            engine.engine_id
            for engine in program.engines
            if development_results[engine.engine_id]["passed"]
            and autonomy_results[engine.engine_id]["passed"]
        ]
        ranked = sorted(
            eligible,
            key=lambda engine_id: (
                -development_results[engine_id]["candidate"]["metrics"][
                    "fully_grounded_factual_success"
                ],
                -autonomy_results[engine_id]["summary"][
                    "safe_grounded_autonomous_success"
                ],
                development_results[engine_id]["cost_usd"]
                + autonomy_results[engine_id]["cost_usd"],
                engine_id,
            ),
        )
        stage_result = {
            "engines": autonomy_results,
            "eligible_engine_ids": ranked,
            "top_two_engine_ids": ranked[:2],
        }
        if len(ranked) < 2:
            if autonomy_recording:
                ledger.complete_stage(
                    "autonomy-820", result=stage_result, decision="quality-failed"
                )
            return {
                "program_id": PROGRAM_ID,
                "status": "completed-refine",
                "decision": "Refine",
                "development": development_results,
                "autonomy": autonomy_results,
                "eligible_engine_ids": ranked,
                "ledger": ledger.snapshot(),
                "next_stage": None,
            }
        if autonomy_recording:
            ledger.complete_stage("autonomy-820", result=stage_result, decision="passed")
        return {
            "program_id": PROGRAM_ID,
            "status": "completed-go-deeper",
            "decision": "Go Deeper",
            "development": development_results,
            "autonomy": autonomy_results,
            "eligible_engine_ids": ranked,
            "top_two_engine_ids": ranked[:2],
            "ledger": ledger.snapshot(),
            "next_stage": "sealed-confirmation-1000",
        }
    finally:
        ledger.close()


def preflight() -> dict[str, Any]:
    load_dotenv(ROOT / ".env")
    program = builder.load_program()
    blockers = []
    if not program.paid_execution_authorized:
        blockers.append("program-paid-execution-not-authorized")
    for name in sorted(
        {
            item.credential_environment_variable
            for item in program.engines
            if item.credential_environment_variable is not None
        }
    ):
        if not os.getenv(name, "").strip():
            blockers.append(f"credential-missing:{name}")
    if program.status != "frozen-pending-authorization":
        blockers.append("program-not-frozen-for-execution")
    verified_at = program.freshness.get("verified_at")
    freshness_hours = program.freshness.get(
        "refresh_within_hours_before_paid_execution"
    )
    try:
        verified = datetime.fromisoformat(str(verified_at))
        if verified.tzinfo is None:
            raise ValueError("metadata timestamp is not timezone-aware")
        maximum_age = timedelta(hours=float(freshness_hours))
        if datetime.now(timezone.utc) - verified.astimezone(timezone.utc) > maximum_age:
            blockers.append("provider-metadata-stale")
    except (TypeError, ValueError):
        blockers.append("provider-metadata-invalid")
    if _git_dirty():
        blockers.append("worktree-dirty")
    if PROGRAM_RESULT.exists():
        blockers.append("terminal-result-already-exists")
    return {
        "program_id": PROGRAM_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "hidden_gold_opened": False,
    }


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        ready = preflight()
        allowed_resume = arguments.resume and PROGRAM_LEDGER.is_file()
        actionable_blockers = [
            blocker
            for blocker in ready["blockers"]
            if not (allowed_resume and blocker == "terminal-result-already-exists")
        ]
        if actionable_blockers:
            raise CrossEngineExecutionError(
                "paid preflight blocked: " + ", ".join(actionable_blockers)
            )
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            PROGRAM_ID, "method_evaluation_execution"
        )
        result = asyncio.run(execute_program(resume=arguments.resume))
    elif arguments.preflight:
        result = preflight()
    elif arguments.simulate:
        result = simulate(limit=arguments.limit)
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
