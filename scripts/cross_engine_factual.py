"""Flow-independent factual execution for the cross-engine program."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_cross_engine_evaluation_010 as builder,
)
from scripts.academic_factual_qa_open_10000_t0_adapter import build_live_t0_adapter
from src.digital_twin.evaluation.cross_engine_program import ProductEngineBindingV1
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)
from src.digital_twin.evaluation.factual_qa_scoring import score_case, summarize_scores


class CrossEngineFactualError(RuntimeError):
    pass


def _atomic_json(path: Path, payload: dict[str, Any], *, resume: bool) -> None:
    if resume and path.is_file():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != payload:
            raise CrossEngineFactualError("resume ranking package drifted")
        return
    if path.exists():
        raise CrossEngineFactualError("exclusive factual artifact already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def factual_cases_and_gold(*, control: bool) -> tuple[
    list[EvaluationCaseV1], dict[str, EvaluationGoldV1]
]:
    cases, gold, _chunks = builder.factual_inputs()
    if control:
        selected = set(builder.factual_control_case_ids())
        cases = [row for row in cases if row.case_id in selected]
        gold = [row for row in gold if row.case_id in selected]
    return cases, {row.case_id: row for row in gold}


def factual_manifest(
    engine: ProductEngineBindingV1,
    *,
    control: bool,
    code_revision: str,
    package_id: str = "development-500",
    retriever: str | None = None,
    known_benchmark: bool = True,
    program_id: str = builder.PROGRAM_ID,
    profile_sha256: str | None = None,
    deterministic_generator: str = "deterministic-grounded-generator-v1",
) -> SystemUnderTestManifestV1:
    selected_retriever = retriever or (
        "source-semantic-evidence-atoms-v1"
        if control
        else "ambiguity-safe-source-semantic-evidence-atoms-v2"
    )
    return SystemUnderTestManifestV1(
        flow_id=(
            f"{program_id}-{package_id}-control-{engine.engine_id}"
            if control
            else f"{program_id}-{package_id}-candidate-{engine.engine_id}"
        ),
        adapter_version="v1",
        code_revision=code_revision,
        profile_sha256=(
            profile_sha256 or builder.load_program().shared_policy_sha256
        ),
        retriever=selected_retriever,
        generator=(
            deterministic_generator
            if engine.provider == "deterministic"
            else "cross-engine-live-extractive-boundary-v1"
        ),
        policy="governed-autonomy-policy-v2.1",
        evidence_gate=selected_retriever,
        model_bindings={
            "planner": engine.planner_model,
            "product-generator": engine.generator_model,
        },
        known_benchmark=known_benchmark,
    )


def _responses(path: Path) -> list[EvaluationResponseV1] | None:
    if not path.is_file():
        return None
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("status") != "completed":
            return None
        rows = [
            EvaluationResponseV1.model_validate_json(serialized)
            for (serialized,) in connection.execute(
                "SELECT payload_json FROM responses ORDER BY sequence"
            )
        ]
    finally:
        connection.close()
    return rows


async def execute_factual_package(
    *,
    output_root: Path,
    engine: ProductEngineBindingV1,
    package_id: str,
    cases: list[EvaluationCaseV1],
    gold: dict[str, EvaluationGoldV1],
    source_package_path: Path,
    ranking: dict[str, Any],
    control: bool,
    code_revision: str,
    maximum_cost_usd: float,
    resume: bool,
    known_benchmark: bool,
    retriever: str,
    maximum_concurrency: int = 4,
    program_id: str = builder.PROGRAM_ID,
    profile_sha256: str | None = None,
    deterministic_generator: str = "deterministic-grounded-generator-v1",
) -> dict[str, Any]:
    condition = "control" if control else "candidate"
    root = output_root / "factual" / package_id / engine.engine_id / condition
    response_path = root / "responses.sqlite3"
    provider_path = root / "provider.sqlite3"
    state_path = root / "product-state.sqlite3"
    ranking_path = root / "precomputed-rankings.json"
    _atomic_json(ranking_path, ranking, resume=resume)
    manifest = factual_manifest(
        engine,
        control=control,
        code_revision=code_revision,
        package_id=package_id,
        retriever=retriever,
        known_benchmark=known_benchmark,
        program_id=program_id,
        profile_sha256=profile_sha256,
        deterministic_generator=deterministic_generator,
    )
    case_hash = canonical_json_sha256(
        [row.model_dump(mode="json") for row in cases]
    )
    existing = _responses(response_path)
    if existing is None:
        arm_resume = resume and response_path.exists()
        adapter = build_live_t0_adapter(
            manifest=manifest,
            cases=cases,
            runtime={
                "instrument_id": program_id,
                "cases_sha256": case_hash,
                "code_revision": code_revision,
                "provider_ledger_path": str(provider_path),
                "state_path": str(state_path),
                "resume": arm_resume,
                "maximum_calls": len(cases),
                "maximum_cost_usd": maximum_cost_usd,
                "product_engine_binding": engine.model_dump(mode="json"),
                "source_package_path": str(source_package_path),
                "precomputed_retrieval_path": str(ranking_path),
                "conversation_scope": "cluster",
            },
        )
        ledger = ResponseLedgerV1(
            response_path,
            cases_sha256=case_hash,
            system_manifest_sha256=canonical_json_sha256(
                manifest.model_dump(mode="json")
            ),
            run_configuration_sha256=canonical_json_sha256(
                {
                    "program_id": program_id,
                    "package_id": package_id,
                    "engine": engine.model_dump(mode="json"),
                    "condition": condition,
                    "ranking_sha256": ranking["content_sha256"],
                }
            ),
            resume=arm_resume,
        )
        try:
            await execute_cases(
                cases=cases,
                adapter=adapter,
                manifest=manifest,
                ledger=ledger,
                maximum_concurrency=maximum_concurrency,
            )
        finally:
            ledger.close()
        existing = _responses(response_path)
    if existing is None or len(existing) != len(cases):
        raise CrossEngineFactualError("factual response ledger is incomplete")
    by_id = {row.case_id: row for row in existing}
    if set(by_id) != {row.case_id for row in cases}:
        raise CrossEngineFactualError("factual response identities drifted")
    scores = [score_case(case, gold[case.case_id], by_id[case.case_id]) for case in cases]
    summary = summarize_scores(scores)
    serialized_scores = [
        {
            **row.model_dump(mode="json"),
            "cost_usd": by_id[row.case_id].usage.cost_usd,
            "provider_calls": int(by_id[row.case_id].provider_model is not None),
        }
        for row in scores
    ]
    return {
        "engine": engine.model_dump(mode="json"),
        "condition": condition,
        "manifest": manifest.model_dump(mode="json"),
        "summary": summary,
        "case_scores": serialized_scores,
        "response_count": len(existing),
        "provider_calls": (
            0
            if engine.provider == "deterministic"
            else sum(int(row.provider_model is not None) for row in existing)
        ),
        "cost_usd": sum(row.usage.cost_usd for row in existing),
    }


async def execute_factual_arm(
    *,
    output_root: Path,
    engine: ProductEngineBindingV1,
    control: bool,
    code_revision: str,
    maximum_cost_usd: float,
    resume: bool,
    maximum_concurrency: int = 4,
) -> dict[str, Any]:
    cases, gold = factual_cases_and_gold(control=control)
    return await execute_factual_package(
        output_root=output_root,
        engine=engine,
        package_id="development-500",
        cases=cases,
        gold=gold,
        source_package_path=builder.FACTUAL_SOURCES,
        ranking=builder.factual_rankings(control=control),
        control=control,
        code_revision=code_revision,
        maximum_cost_usd=maximum_cost_usd,
        resume=resume,
        known_benchmark=True,
        retriever=(
            "source-semantic-evidence-atoms-v1"
            if control
            else "ambiguity-safe-source-semantic-evidence-atoms-v2"
        ),
        maximum_concurrency=maximum_concurrency,
    )


def factual_hard_gates(result: dict[str, Any]) -> dict[str, bool]:
    summary = result["summary"]
    metrics = summary["metrics"]
    return {
        "fully_grounded_factual_success": metrics["fully_grounded_factual_success"]
        >= 0.95,
        "answerable_action": metrics["action_accuracy_answerable"] >= 0.95,
        "boundary_action": metrics["boundary_action_accuracy"] >= 0.98,
        "claim_precision": metrics["atomic_claim_precision"] >= 0.98,
        "claim_recall": metrics["atomic_claim_recall"] >= 0.95,
        "citation_precision": metrics["citation_precision"] >= 0.98,
        "citation_recall": metrics["citation_recall"] >= 0.95,
        "source_version": metrics["source_version_validity"] == 1.0,
        "zero_severe_release": summary["severe_unsupported_release_count"] == 0,
        "provider_completion": metrics["provider_completion"] >= 0.995,
    }
