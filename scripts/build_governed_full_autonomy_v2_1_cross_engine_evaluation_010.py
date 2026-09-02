#!/usr/bin/env python3
"""Validate the finite cross-engine Professor Digital Twin evaluation program."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as autonomy,
)
from scripts import build_cross_engine_sealed_confirmation_010 as sealed
from scripts import run_academic_factual_qa_ambiguity_safe_comparison as factual
from src.digital_twin.evaluation import CrossEngineEvaluationProgramV1
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationGoldV1,
)
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.semantic_evidence_atoms import (
    materialize_semantic_evidence_atoms,
)


ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "governed-full-autonomy-v2-1-cross-engine-evaluation-010"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_cross_engine_evaluation_010.json"
)
FACTUAL_PUBLIC = ROOT / (
    "research/05_evaluation/datasets/"
    "academic-factual-qa-ambiguity-safe-successor-001-cases.json"
)
FACTUAL_GOLD = ROOT / (
    "research/05_evaluation/datasets/"
    "academic-factual-qa-ambiguity-safe-successor-001-gold.json"
)
FACTUAL_SOURCES = ROOT / (
    "research/05_evaluation/datasets/"
    "academic-factual-qa-ambiguity-safe-successor-001-sources.json"
)
SEALED_PUBLIC = sealed.CASES_PATH
SEALED_GOLD = sealed.GOLD_PATH
SEALED_SOURCES = sealed.SOURCE_PATH
KNOWN_ROOT = ROOT / (
    "reports/generated/course-digital-twin-evaluation-program-011/"
    "stages/final-construction-10000"
)
KNOWN_EXECUTION_ROOT = ROOT / (
    "reports/generated/course-digital-twin-evaluation-program-011/"
    "stages/final-product-10000-plus-1000"
)
KNOWN_PUBLIC = KNOWN_ROOT / "final-public-cases.json"
KNOWN_GOLD = KNOWN_ROOT / "final-hidden-gold.json"
KNOWN_CONTROL_PUBLIC = KNOWN_ROOT / "control-public-cases.json"
KNOWN_CONTROL_GOLD = KNOWN_ROOT / "control-hidden-gold.json"
KNOWN_SOURCES = KNOWN_ROOT / "final-source-corpus.json"
KNOWN_CANDIDATE_RANKINGS = KNOWN_EXECUTION_ROOT / "selected-final-rankings.json"
KNOWN_CONTROL_RANKINGS = KNOWN_EXECUTION_ROOT / "control-rankings.json"
SHARED_PROMPT = {
    "version": "cross-engine-shared-product-contract-v1",
    "planner_schema": "ReactiveSemanticProposalV2/AutonomousPlannerOutputV1",
    "generator_schema": "ModelTutorOutputV2",
    "reasoning_effort": "low",
    "max_output_tokens": 600,
    "temperature": "provider-contract-default",
    "model_specific_prompt_changes": False,
}
SHARED_POLICY = {
    "version": "governed-autonomy-policy-v2.1",
    "action_eligibility": "event-scoped-action-eligibility-v1",
    "retrieval": "ambiguity-safe-source-semantic-evidence-atoms-v2",
    "claim_validator": "exact-quote-atomic-claim-v1",
    "scorer": "independent-autonomy-scorer-v2",
    "virtual_clock": True,
}


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_program() -> CrossEngineEvaluationProgramV1:
    return CrossEngineEvaluationProgramV1.model_validate_json(
        INSTRUMENT.read_text(encoding="utf-8")
    )


def factual_inputs() -> tuple[
    list[EvaluationCaseV1], list[EvaluationGoldV1], list[DocumentChunk]
]:
    public = factual._load_hashed(FACTUAL_PUBLIC)  # noqa: SLF001
    hidden = factual._load_hashed(FACTUAL_GOLD)  # noqa: SLF001
    sources = factual._load_hashed(FACTUAL_SOURCES)  # noqa: SLF001
    cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in hidden["gold"]]
    chunks = [DocumentChunk.model_validate(row) for row in sources["chunks"]]
    if len(cases) != 500 or len(gold) != 500 or len(chunks) != 300:
        raise ValueError("cross-engine factual package count drifted")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise ValueError("cross-engine factual public/gold identities drifted")
    return cases, gold, chunks


def sealed_inputs() -> tuple[
    list[EvaluationCaseV1], list[EvaluationGoldV1], list[DocumentChunk]
]:
    public = factual._load_hashed(SEALED_PUBLIC)  # noqa: SLF001
    hidden = factual._load_hashed(SEALED_GOLD)  # noqa: SLF001
    sources = factual._load_hashed(SEALED_SOURCES)  # noqa: SLF001
    cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in hidden["gold"]]
    chunks = [DocumentChunk.model_validate(row) for row in sources["chunks"]]
    if len(cases) != 1_000 or len(gold) != 1_000 or len(chunks) != 600:
        raise ValueError("cross-engine sealed package count drifted")
    if {row.case_id for row in cases} != {row.case_id for row in gold}:
        raise ValueError("cross-engine sealed public/gold identities drifted")
    return cases, gold, chunks


def factual_control_case_ids() -> list[str]:
    """Freeze five complete clusters per course for the 100-case V1 control."""

    cases, _gold, _chunks = factual_inputs()
    cases_by_cluster: dict[str, list[EvaluationCaseV1]] = {}
    for case in cases:
        cases_by_cluster.setdefault(case.cluster_id, []).append(case)
    clusters_by_course: dict[str, list[str]] = {}
    for cluster_id, rows in sorted(cases_by_cluster.items()):
        counts = {
            course_id: sum(row.course_id == course_id for row in rows)
            for course_id in {row.course_id for row in rows}
        }
        primary_course = min(
            counts,
            key=lambda course_id: (-counts[course_id], course_id),
        )
        clusters_by_course.setdefault(primary_course, []).append(cluster_id)
    selected_clusters = {
        cluster_id
        for course_id in sorted(clusters_by_course)
        for cluster_id in sorted(clusters_by_course[course_id])[:5]
    }
    selected = [
        case.case_id
        for case in sorted(cases, key=lambda row: row.case_id)
        if case.cluster_id in selected_clusters
    ]
    if len(selected) != 100:
        raise ValueError("cross-engine factual control is not exactly 100 cases")
    return selected


def _rankings_for(
    cases: list[EvaluationCaseV1],
    chunks: list[DocumentChunk],
    *,
    architecture_id: str,
) -> dict[str, Any]:
    instrument = factual._instrument(factual.DEFAULT_INSTRUMENT)  # noqa: SLF001
    architecture = next(
        row for row in instrument.candidates if row.architecture_id == architecture_id
    )
    package = factual._response_package(architecture, cases, chunks)  # noqa: SLF001
    chunk_by_lineage = {
        (
            row.source_artifact_id,
            row.source_version,
            row.source_checksum,
            int(row.metadata["char_start"]),
            int(row.metadata["char_end"]),
        ): row.id
        for row in chunks
    }
    rankings: dict[str, list[str]] = {}
    for response in package["responses"]:
        identifiers = []
        for citation in response["retrieved_evidence"]:
            key = (
                citation["source_artifact_id"],
                citation["source_version"],
                citation["source_sha256"],
                citation["char_start"],
                citation["char_end"],
            )
            try:
                identifiers.append(chunk_by_lineage[key])
            except KeyError as error:
                raise ValueError("factual ranking lacks one canonical source atom") from error
        rankings[response["case_id"]] = identifiers
    payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "architecture_id": architecture_id,
        "ranked_chunk_ids": rankings,
    }
    payload["content_sha256"] = _canonical_sha(payload)
    return payload


def factual_rankings(*, control: bool) -> dict[str, Any]:
    """Rebuild public-question-only V2/V1 rankings without opening gold."""

    cases, _gold, chunks = factual_inputs()
    if control:
        selected = set(factual_control_case_ids())
        cases = [row for row in cases if row.case_id in selected]
    return _rankings_for(
        cases,
        chunks,
        architecture_id=factual.BASELINE_ID if control else factual.CANDIDATE_ID,
    )


def sealed_rankings() -> dict[str, Any]:
    cases, _gold, chunks = sealed_inputs()
    return _rankings_for(cases, chunks, architecture_id=factual.CANDIDATE_ID)


def known_rankings(*, control: bool) -> dict[str, Any]:
    path = KNOWN_CONTROL_RANKINGS if control else KNOWN_CANDIDATE_RANKINGS
    imported = factual._load_hashed(path)  # noqa: SLF001
    rankings = imported.get("ranked_chunk_ids")
    expected = 1_000 if control else 10_000
    if not isinstance(rankings, dict) or len(rankings) != expected:
        raise ValueError("known regression ranking package drifted")
    payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": PROGRAM_ID,
        "architecture_id": (
            factual.BASELINE_ID if control else factual.CANDIDATE_ID
        ),
        "imported_program_id": imported["program_id"],
        "imported_content_sha256": imported["content_sha256"],
        "ranked_chunk_ids": rankings,
    }
    payload["content_sha256"] = _canonical_sha(payload)
    return payload


def known_semantic_source_payload() -> dict[str, Any]:
    imported = factual._load_hashed(KNOWN_SOURCES)  # noqa: SLF001
    chunks = [DocumentChunk.model_validate(row) for row in imported["chunks"]]
    semantic_chunks = materialize_semantic_evidence_atoms(chunks)
    payload = {
        **{key: value for key, value in imported.items() if key not in {"content_sha256", "chunks"}},
        "program_id": PROGRAM_ID,
        "imported_program_id": imported["program_id"],
        "imported_content_sha256": imported["content_sha256"],
        "construction_method": (
            "known-program-011-source-regions-plus-deterministic-semantic-atom-metadata"
        ),
        "chunks": [row.model_dump(mode="json") for row in semantic_chunks],
    }
    payload["content_sha256"] = _canonical_sha(payload)
    return payload


def validate() -> dict[str, Any]:
    program = load_program()
    if program.program_id != PROGRAM_ID:
        raise ValueError("cross-engine program identity drifted")
    if (program.status, program.paid_execution_authorized) not in {
        ("build-only", False),
        ("frozen-pending-authorization", True),
        ("completed-keep", False),
        ("completed-refine", False),
        ("invalid-execution", False),
    }:
        raise ValueError("cross-engine authorization state is incoherent")
    expected_hashes = {
        "factual_public_sha256": _file_sha(FACTUAL_PUBLIC),
        "factual_gold_sha256": _file_sha(FACTUAL_GOLD),
        "factual_source_sha256": _file_sha(FACTUAL_SOURCES),
        "factual_control_selection_sha256": _canonical_sha(
            factual_control_case_ids()
        ),
        "sealed_public_sha256": _file_sha(SEALED_PUBLIC),
        "sealed_gold_sha256": _file_sha(SEALED_GOLD),
        "sealed_source_sha256": _file_sha(SEALED_SOURCES),
        "known_public_sha256": _file_sha(KNOWN_PUBLIC),
        "known_gold_sha256": _file_sha(KNOWN_GOLD),
        "known_control_public_sha256": _file_sha(KNOWN_CONTROL_PUBLIC),
        "known_control_gold_sha256": _file_sha(KNOWN_CONTROL_GOLD),
        "known_source_sha256": _file_sha(KNOWN_SOURCES),
        "known_candidate_rankings_sha256": _file_sha(KNOWN_CANDIDATE_RANKINGS),
        "known_control_rankings_sha256": _file_sha(KNOWN_CONTROL_RANKINGS),
        "autonomy_public_sha256": autonomy.public_payload()["content_sha256"],
        "autonomy_gold_sha256": autonomy.hidden_gold_payload()["content_sha256"],
        "shared_prompt_sha256": _canonical_sha(SHARED_PROMPT),
        "shared_policy_sha256": _canonical_sha(SHARED_POLICY),
    }
    for field, expected in expected_hashes.items():
        if getattr(program, field) != expected:
            raise ValueError(f"cross-engine binding drifted: {field}")
    factual_inputs()
    sealed_inputs()
    candidate_rankings = factual_rankings(control=False)
    control_rankings = factual_rankings(control=True)
    confirmation_rankings = sealed_rankings()
    known_candidate_rankings = known_rankings(control=False)
    known_control_rankings = known_rankings(control=True)
    if len(candidate_rankings["ranked_chunk_ids"]) != 500:
        raise ValueError("candidate factual rankings drifted")
    if len(control_rankings["ranked_chunk_ids"]) != 100:
        raise ValueError("control factual rankings drifted")
    if len(confirmation_rankings["ranked_chunk_ids"]) != 1_000:
        raise ValueError("sealed confirmation rankings drifted")
    if len(known_candidate_rankings["ranked_chunk_ids"]) != 10_000:
        raise ValueError("known candidate rankings drifted")
    if len(known_control_rankings["ranked_chunk_ids"]) != 1_000:
        raise ValueError("known control rankings drifted")
    serialized = json.dumps(
        [item.model_dump(mode="json") for item in program.engines],
        sort_keys=True,
    ).casefold()
    for prohibited in ("gpt-5.6-sol", "openrouter", "gemma", "claude"):
        if prohibited in serialized:
            raise ValueError(f"prohibited active engine is present: {prohibited}")
    if program.protocol.get("quality_failure_rerun_allowed") is not False:
        raise ValueError("quality-failure rerun boundary drifted")
    return {
        "program_id": PROGRAM_ID,
        "status": (
            (
                f"passed-terminal-{program.status}-provider-unauthorized"
                if program.status.startswith("completed-")
                or program.status == "invalid-execution"
                else "passed-build-only-provider-unauthorized"
            )
            if not program.paid_execution_authorized
            else "passed-frozen-provider-authorized"
        ),
        "engine_ids": [item.engine_id for item in program.engines],
        "condition_count": len(program.conditions),
        "development_factual_cases": program.development_factual_cases,
        "development_control_cases": program.development_control_cases,
        "autonomy_cases_per_engine": program.autonomy_cases,
        "sealed_confirmation_cases": program.sealed_confirmation_cases,
        "known_regression_cases": (
            program.known_regression_candidate_cases
            + program.known_regression_control_cases
        ),
        "provider_calls": 0,
        "paid_execution_authorized": program.paid_execution_authorized,
        "independent_scorer": program.shared_scorer,
        "hashes": expected_hashes,
        "factual_rankings": {
            "candidate_sha256": candidate_rankings["content_sha256"],
            "control_sha256": control_rankings["content_sha256"],
            "sealed_sha256": confirmation_rankings["content_sha256"],
            "known_candidate_sha256": known_candidate_rankings["content_sha256"],
            "known_control_sha256": known_control_rankings["content_sha256"],
        },
    }


def simulate() -> dict[str, Any]:
    """Exercise only stage ordering and immutable bindings; make no model calls."""

    validated = validate()
    stages = [
        "cross-engine-500-plus-100-development",
        "cross-engine-820-autonomy",
        "top-two-sealed-1000-confirmation",
        "winner-known-10000-plus-1000-regression",
        "llm-only-supplementary-proxies",
        "local-immutable-release-qualification",
    ]
    return {
        **validated,
        "status": "passed-network-free-program-simulation",
        "stages": [
            {
                "stage": stage,
                "state": "simulated-not-executed",
                "automatic_advance_on_pass": index < len(stages) - 1,
            }
            for index, stage in enumerate(stages)
        ],
        "finite_stop_rules": {
            "quality_failure": "publish-and-stop-branch",
            "harness_correction_max": 1,
            "sealed_set_tuning": False,
        },
        "quality_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    arguments = parser.parse_args()
    result = simulate() if arguments.simulate else validate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
