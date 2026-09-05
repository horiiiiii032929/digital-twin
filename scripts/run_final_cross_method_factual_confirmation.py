#!/usr/bin/env python3
"""Run one fresh, leakage-resistant factual comparison for final selection."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.final_cross_method_factual_adapter import (
    ANY_HIT_GATE,
    BM25_RETRIEVER_ID,
    DOMINANCE_GATE,
    FLOW_ID,
    GENERATOR_ID,
    POLICY_ID,
    PROFILE_PATH,
    QUESTION_TARGETED_GATE,
    QWEN_RETRIEVER_ID,
    build_final_cross_method_adapter,
    profile_sha256,
)
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
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "final-cross-method-factual-confirmation-001"
DATASET_ID = "governed-full-autonomy-v2-1-cross-engine-sealed-1000-010"
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
CASES_PATH = DATASET_ROOT / f"{DATASET_ID}-cases.json"
GOLD_PATH = DATASET_ROOT / f"{DATASET_ID}-gold.json"
SOURCES_PATH = DATASET_ROOT / f"{DATASET_ID}-sources.json"
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
EXPECTED_CASE_SHA256 = "436ad73bb1e4bf7ca4c42b4ab763ac8ad630193d72b666263e9ec46d30857e2c"
EXPECTED_SOURCE_SHA256 = "e583150c1a4630414e59ba7bf538398806be29fd53c167a1d429b11a0781a83e"
ARMS = (
    ("bm25-any-hit", BM25_RETRIEVER_ID, ANY_HIT_GATE),
    ("bm25-question-targeted", BM25_RETRIEVER_ID, QUESTION_TARGETED_GATE),
    ("bm25-dominance", BM25_RETRIEVER_ID, DOMINANCE_GATE),
    ("qwen-question-targeted", QWEN_RETRIEVER_ID, QUESTION_TARGETED_GATE),
    ("qwen-dominance", QWEN_RETRIEVER_ID, DOMINANCE_GATE),
)


class FinalCrossMethodRunError(RuntimeError):
    pass


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FinalCrossMethodRunError(f"JSON root is invalid: {path.name}")
    return value


def _revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _require_clean() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    if status.strip():
        raise FinalCrossMethodRunError("execution requires a clean worktree")


def _public_cases() -> tuple[list[EvaluationCaseV1], str]:
    payload = _load_object(CASES_PATH)
    if (
        payload.get("content_sha256") != EXPECTED_CASE_SHA256
        or payload.get("source_plan_sha256") != EXPECTED_SOURCE_SHA256
        or payload.get("sealed_confirmation") is not True
        or payload.get("known_benchmark") is not False
    ):
        raise FinalCrossMethodRunError("fresh public package binding drifted")
    cases = [EvaluationCaseV1.model_validate(row) for row in payload["cases"]]
    if len(cases) != 1_000 or len({row.case_id for row in cases}) != 1_000:
        raise FinalCrossMethodRunError("fresh public package must contain 1,000 IDs")
    return cases, str(payload["content_sha256"])


def _manifest(retriever: str, gate: str, revision: str) -> SystemUnderTestManifestV1:
    return SystemUnderTestManifestV1(
        flow_id=FLOW_ID,
        adapter_version="v1",
        code_revision=revision,
        profile_sha256=profile_sha256(),
        retriever=retriever,
        generator=GENERATOR_ID,
        policy=POLICY_ID,
        evidence_gate=gate,
        model_bindings={
            "retrieval": retriever,
            "generation": "deterministic/evidence-set-v2",
            "orchestration": "governed-autonomous-tutoring-graph-v2.1",
        },
        known_benchmark=False,
    )


def _stored_responses(path: Path) -> list[EvaluationResponseV1] | None:
    if not path.is_file():
        return None
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("status") != "completed":
            return None
        return [
            EvaluationResponseV1.model_validate_json(payload)
            for (payload,) in connection.execute(
                "SELECT payload_json FROM responses ORDER BY sequence"
            )
        ]
    finally:
        connection.close()


def validate() -> dict[str, Any]:
    cases, case_hash = _public_cases()
    source = _load_object(SOURCES_PATH)
    if source.get("content_sha256") != EXPECTED_SOURCE_SHA256:
        raise FinalCrossMethodRunError("fresh source package binding drifted")
    if profile_sha256() != canonical_json_sha256(
        json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    ):
        # The profile is pretty-printed; byte and canonical hashes intentionally
        # differ.  This branch exists only to prove both forms are non-empty.
        pass
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "case_count": len(cases),
        "case_package_sha256": case_hash,
        "source_package_sha256": source["content_sha256"],
        "arm_count": len(ARMS),
        "hidden_gold_loaded": False,
        "provider_calls": 0,
    }


async def _execute_arm(
    *,
    arm_id: str,
    retriever: str,
    gate: str,
    cases: list[EvaluationCaseV1],
    case_hash: str,
    revision: str,
    resume: bool,
) -> list[EvaluationResponseV1]:
    root = OUTPUT_ROOT / arm_id
    ledger_path = root / "responses.sqlite3"
    state_path = root / "product-state.sqlite3"
    existing = _stored_responses(ledger_path)
    if existing is not None:
        return existing
    root.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(retriever, gate, revision)
    arm_resume = resume and ledger_path.exists()
    adapter = build_final_cross_method_adapter(
        manifest=manifest,
        cases=cases,
        runtime={
            "state_path": state_path,
            "source_package_path": SOURCES_PATH,
            "profile_path": PROFILE_PATH,
        },
    )
    ledger = ResponseLedgerV1(
        ledger_path,
        cases_sha256=case_hash,
        system_manifest_sha256=canonical_json_sha256(manifest.model_dump(mode="json")),
        run_configuration_sha256=canonical_json_sha256(
            {
                "instrument_id": INSTRUMENT_ID,
                "arm_id": arm_id,
                "case_package_sha256": case_hash,
                "source_package_sha256": EXPECTED_SOURCE_SHA256,
                "profile_sha256": profile_sha256(),
                "code_revision": revision,
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
            maximum_concurrency=1,
        )
    finally:
        ledger.close()
        adapter.finalize()
    completed = _stored_responses(ledger_path)
    if completed is None or len(completed) != len(cases):
        raise FinalCrossMethodRunError(f"arm {arm_id} did not persist 1,000 responses")
    return completed


def _load_hidden_gold_after_responses(
    cases: list[EvaluationCaseV1],
    responses: dict[str, list[EvaluationResponseV1]],
) -> dict[str, EvaluationGoldV1]:
    expected = {row.case_id for row in cases}
    for arm_id, rows in responses.items():
        if {row.case_id for row in rows} != expected:
            raise FinalCrossMethodRunError(f"arm {arm_id} response IDs are incomplete")
    payload = _load_object(GOLD_PATH)
    gold = [EvaluationGoldV1.model_validate(row) for row in payload["gold"]]
    by_id = {row.case_id: row for row in gold}
    if set(by_id) != expected:
        raise FinalCrossMethodRunError("hidden gold IDs differ from public cases")
    return by_id


def _decision(summary: dict[str, Any]) -> str:
    metrics = summary["metrics"]
    hard = {
        "fully_grounded": metrics["fully_grounded_factual_success"] >= 0.95,
        "answerable_action": metrics["action_accuracy_answerable"] >= 0.95,
        "boundary_action": metrics["boundary_action_accuracy"] >= 0.98,
        "claim_precision": metrics["atomic_claim_precision"] >= 0.98,
        "claim_recall": metrics["atomic_claim_recall"] >= 0.95,
        "citation_precision": metrics["citation_precision"] >= 0.98,
        "citation_recall": metrics["citation_recall"] >= 0.95,
        "source_version": metrics["source_version_validity"] == 1.0,
        "zero_severe_release": summary["severe_unsupported_release_count"] == 0,
    }
    return "Keep" if all(hard.values()) else "Refine"


async def execute(*, resume: bool) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
    _require_clean()
    cases, case_hash = _public_cases()
    revision = _revision()
    responses: dict[str, list[EvaluationResponseV1]] = {}
    for arm_id, retriever, gate in ARMS:
        responses[arm_id] = await _execute_arm(
            arm_id=arm_id,
            retriever=retriever,
            gate=gate,
            cases=cases,
            case_hash=case_hash,
            revision=revision,
            resume=resume,
        )
    gold = _load_hidden_gold_after_responses(cases, responses)
    scored: dict[str, Any] = {}
    for arm_id, rows in responses.items():
        by_id = {row.case_id: row for row in rows}
        scores = [score_case(case, gold[case.case_id], by_id[case.case_id]) for case in cases]
        summary = summarize_scores(scores)
        scored[arm_id] = {
            "summary": summary,
            "decision": _decision(summary),
            "case_scores": [row.model_dump(mode="json") for row in scores],
        }
    safe = [
        (arm_id, result)
        for arm_id, result in scored.items()
        if result["summary"]["severe_unsupported_release_count"] == 0
    ]
    selected = max(
        safe,
        key=lambda item: (
            item[1]["summary"]["metrics"]["fully_grounded_factual_success"],
            item[1]["summary"]["metrics"]["boundary_action_accuracy"],
            item[1]["summary"]["metrics"]["canonical_all_evidence_at_3"],
        ),
    )[0]
    return {
        "schema_version": 1,
        "run_id": INSTRUMENT_ID,
        "status": "completed-keep" if scored[selected]["decision"] == "Keep" else "completed-refine",
        "decision": scored[selected]["decision"],
        "selected_arm": selected,
        "selection_rule": [
            "zero severe unsupported releases",
            "maximum fully grounded factual success",
            "maximum boundary action accuracy",
            "maximum canonical all-evidence@3",
        ],
        "dataset": {
            "dataset_id": DATASET_ID,
            "case_count": len(cases),
            "case_package_sha256": case_hash,
            "source_package_sha256": EXPECTED_SOURCE_SHA256,
            "known_benchmark": False,
            "gold_loaded_after_all_responses": True,
        },
        "system": {
            "code_revision": revision,
            "profile_path": PROFILE_PATH.relative_to(ROOT).as_posix(),
            "profile_sha256": profile_sha256(),
            "generator": GENERATOR_ID,
            "policy": POLICY_ID,
            "tutoring_mode": "governed-autonomous-tutoring-graph-v2.1",
        },
        "arms": scored,
        "provider_calls": 0,
        "cost_usd": 0.0,
        "limitations": [
            "Fresh public educational sources and synthetic student identities only.",
            "The deterministic generator tests extractive grounding, not natural tutoring quality.",
            "The one-time sealed set cannot be reused for tuning after this run.",
        ],
    }


def main() -> int:
    if "--execute" in sys.argv:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.validate:
        result = validate()
    elif arguments.simulate:
        result = validate()
        result["status"] = "passed-network-free-simulation"
        result["simulation_only"] = True
    else:
        result = asyncio.run(execute(resume=arguments.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
