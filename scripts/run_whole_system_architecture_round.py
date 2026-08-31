#!/usr/bin/env python3
"""Run one finite, network-free whole-system architecture development round."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from src.digital_twin.action_router import (
    DeterministicActionRouterV1,
    DeterministicActionRouterV2,
    required_atomic_claim_count,
)
from src.digital_twin.evaluation.architecture_evolution import (
    ArchitectureDevelopmentFreezeV1,
    ArchitecturePlane,
    ArchitectureRoundInstrumentV1,
    ArchitectureSystemManifestV1,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    EvaluationUsageV1,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.evaluation.factual_qa_scoring import (
    normalize_semantic_source_text,
    score_case,
    summarize_scores,
)
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    PlanObserveRetrieverV1,
    StructuredHierarchicalCoverageEvidenceGate,
    StructuredHierarchicalRetriever,
    SourceRangeCandidateRetrieverV2,
    SourceRangeEvidenceGateV2,
    TargetAwareEvidenceRetrieverV1,
    TargetEvidenceGateV1,
    canonicalize_source_claim,
)
from src.digital_twin.grounding.models import RetrievalHit
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "course_digital_twin_whole_system_architecture_round_1_001.json"
)


class ArchitectureRoundExecutionError(RuntimeError):
    """Raised when a frozen architecture round violates its run boundary."""


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repository_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ArchitectureRoundExecutionError("round paths must be repository relative")
    resolved = ROOT / path
    if not resolved.is_file():
        raise ArchitectureRoundExecutionError(f"round artifact is missing: {value}")
    return resolved


def _load_hashed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ArchitectureRoundExecutionError(f"JSON root is not an object: {path}")
    observed = canonical_json_sha256(
        {key: row for key, row in value.items() if key != "content_sha256"}
    )
    if value.get("content_sha256") != observed:
        raise ArchitectureRoundExecutionError(f"content hash drifted: {path.name}")
    return value


def _load_instrument(path: Path) -> ArchitectureRoundInstrumentV1:
    return ArchitectureRoundInstrumentV1.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def _load_inputs(
    instrument: ArchitectureRoundInstrumentV1,
) -> tuple[list[EvaluationCaseV1], list[DocumentChunk], Path]:
    freeze_path = _repository_path(instrument.development_freeze.path)
    if _raw_sha256(freeze_path) != instrument.development_freeze.sha256:
        raise ArchitectureRoundExecutionError("development freeze hash drifted")
    freeze = ArchitectureDevelopmentFreezeV1.model_validate_json(
        freeze_path.read_text(encoding="utf-8")
    )
    tranche = next(
        (row for row in freeze.tranches if row.tranche_id == instrument.development_tranche_id),
        None,
    )
    if tranche is None or tranche.round_number != instrument.round_number:
        raise ArchitectureRoundExecutionError("round tranche binding drifted")
    for artifact in (tranche.source, tranche.public_cases, tranche.hidden_gold):
        if _raw_sha256(_repository_path(artifact.path)) != artifact.sha256:
            raise ArchitectureRoundExecutionError(f"tranche hash drifted: {artifact.path}")
    public = _load_hashed(_repository_path(tranche.public_cases.path))
    source = _load_hashed(_repository_path(tranche.source.path))
    cases = [EvaluationCaseV1.model_validate(row) for row in public.get("rows", [])]
    chunks = [DocumentChunk.model_validate(row) for row in source.get("chunks", [])]
    if len(cases) != tranche.case_count or not chunks:
        raise ArchitectureRoundExecutionError("round case/source count drifted")
    return cases, chunks, _repository_path(tranche.hidden_gold.path)


def _group_chunks(chunks: list[DocumentChunk]) -> dict[str, list[DocumentChunk]]:
    grouped: dict[str, list[DocumentChunk]] = {}
    for chunk in chunks:
        course_id = str(chunk.metadata.get("course_id", ""))
        if not course_id:
            raise ArchitectureRoundExecutionError("source chunk lacks course scope")
        grouped.setdefault(course_id, []).append(chunk)
    return grouped


def _build_retrievers(
    architecture: ArchitectureSystemManifestV1,
    chunks: list[DocumentChunk],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for course_id, course_chunks in _group_chunks(chunks).items():
        lexical = BM25Retriever(course_chunks)
        retrieval_binding = architecture.plane_bindings[ArchitecturePlane.RETRIEVAL]
        if retrieval_binding == "bm25-course-scoped-v1":
            result[course_id] = lexical
        elif retrieval_binding == "structured-hierarchical-coverage-retriever-v1":
            result[course_id] = StructuredHierarchicalRetriever(
                lexical,
                course_chunks,
                candidate_limit=30,
                adjacent_radius=1,
            )
        elif retrieval_binding == "deterministic-plan-observe-plus-hierarchical-v1":
            planned = PlanObserveRetrieverV1(
                lexical,
                maximum_subqueries=3,
                observation_limit=30,
            )
            result[course_id] = StructuredHierarchicalRetriever(
                planned,
                course_chunks,
                candidate_limit=30,
                adjacent_radius=1,
            )
        elif retrieval_binding == "target-aware-evidence-retriever-v1":
            result[course_id] = TargetAwareEvidenceRetrieverV1(
                lexical,
                course_chunks,
                candidate_limit=30,
                metadata_ranking_enabled=False,
            )
        elif retrieval_binding == "target-aware-section-retriever-v1":
            result[course_id] = TargetAwareEvidenceRetrieverV1(
                lexical,
                course_chunks,
                candidate_limit=30,
                metadata_ranking_enabled=True,
            )
        elif retrieval_binding in {
            "source-range-candidate-retriever-v2",
            "source-range-ambiguity-retriever-v2",
        }:
            result[course_id] = SourceRangeCandidateRetrieverV2(
                lexical,
                course_chunks,
                candidate_limit=30,
            )
        else:
            raise ArchitectureRoundExecutionError(
                f"unsupported architecture retriever: {retrieval_binding}"
            )
    return result


def _router(architecture: ArchitectureSystemManifestV1) -> Any:
    binding = architecture.plane_bindings[ArchitecturePlane.ACTION_ROUTING]
    if binding == "deterministic-tutor-action-router-v1":
        return DeterministicActionRouterV1()
    if binding == "deterministic-tutor-action-router-v2":
        return DeterministicActionRouterV2()
    raise ArchitectureRoundExecutionError(f"unsupported action router: {binding}")


def _evaluation_action(value: str) -> EvaluationAction:
    return {
        "redirect-graded-work": EvaluationAction.REFUSE,
        "no-evidence": EvaluationAction.ABSTAIN,
        "clarify": EvaluationAction.CLARIFY,
    }[value]


def _citation(hit: RetrievalHit) -> EvaluationCitationV1:
    chunk = hit.chunk
    metadata = chunk.metadata
    return EvaluationCitationV1(
        source_artifact_id=chunk.source_artifact_id or chunk.document_id,
        source_version=chunk.source_version,
        source_sha256=chunk.source_checksum,
        char_start=int(metadata["char_start"]),
        char_end=int(metadata["char_end"]),
        region_id=chunk.region_id,
    )


def _response(
    *,
    architecture: ArchitectureSystemManifestV1,
    case: EvaluationCaseV1,
    retriever: Any,
    router: Any,
) -> EvaluationResponseV1:
    started = time.perf_counter()
    route = router.route(case.question)
    if route is not None:
        action = _evaluation_action(route.action)
        content = {
            EvaluationAction.REFUSE: "I cannot provide a submission-ready answer to graded work.",
            EvaluationAction.CLARIFY: "Please clarify which concept and step you mean.",
            EvaluationAction.ABSTAIN: "The approved course evidence does not establish that.",
        }[action]
        return EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=architecture.architecture_id,
            action=action,
            answer=content,
            operational_status="completed-boundary-route",
            usage=EvaluationUsageV1(
                latency_ms=(time.perf_counter() - started) * 1_000
            ),
            trace={"router_rule": route.matched_rule, "provider_calls": 0},
        )

    try:
        hits = list(retriever.retrieve(case.question, limit=5))
        claim_binding = architecture.plane_bindings[ArchitecturePlane.CLAIM_CITATION]
        if claim_binding == "single-hit-extractive-lineage-v1":
            selected = hits[:1]
            sufficient = bool(selected)
            gate_reason = "any-hit lexical control"
        elif claim_binding == "target-aware-atomic-extractive-lineage-v1":
            decision = TargetEvidenceGateV1().assess(case.question, hits)
            selected_ids = set(decision.selected_hit_ids)
            selected = [row for row in hits if row.chunk.id in selected_ids]
            sufficient = decision.sufficient
            gate_reason = decision.reason
        elif claim_binding in {
            "source-range-canonical-claim-lineage-v2",
            "source-range-ambiguity-aware-claim-lineage-v2",
        }:
            decision = SourceRangeEvidenceGateV2(
                clarify_ambiguous=(
                    claim_binding
                    == "source-range-ambiguity-aware-claim-lineage-v2"
                )
            ).assess(case.question, hits)
            selected_ids = set(decision.selected_hit_ids)
            selected = [row for row in hits if row.chunk.id in selected_ids]
            sufficient = decision.sufficient
            gate_reason = decision.reason
        else:
            decision = StructuredHierarchicalCoverageEvidenceGate().assess(
                case.question, hits
            )
            selected_ids = set(decision.selected_hit_ids)
            required = required_atomic_claim_count(case.question)
            selected = [row for row in hits if row.chunk.id in selected_ids][:required]
            sufficient = decision.sufficient and len(selected) >= required
            gate_reason = decision.reason
        if not sufficient:
            action = (
                EvaluationAction.CLARIFY
                if "ambiguous" in gate_reason
                else EvaluationAction.ABSTAIN
            )
            content = (
                "Please clarify which source detail or concept you mean."
                if action == EvaluationAction.CLARIFY
                else "The approved course evidence does not establish that."
            )
            return EvaluationResponseV1(
                case_id=case.case_id,
                flow_id=architecture.architecture_id,
                action=action,
                answer=content,
                retrieved_evidence=[_citation(row) for row in hits],
                operational_status="completed-evidence-abstention",
                usage=EvaluationUsageV1(
                    latency_ms=(time.perf_counter() - started) * 1_000
                ),
                trace={"gate_reason": gate_reason, "provider_calls": 0},
            )
        citations = [_citation(row) for row in selected]
        canonical_claims = claim_binding in {
            "source-range-canonical-claim-lineage-v2",
            "source-range-ambiguity-aware-claim-lineage-v2",
        }
        claims = [
            EvaluationAtomicClaimV1(
                text=(
                    canonicalize_source_claim(
                        row.chunk.text,
                        modality=str(row.chunk.metadata.get("modality", "")),
                    )
                    if canonical_claims
                    else row.chunk.text
                ),
                citations=[_citation(row)],
            )
            for row in selected
        ]
        trace: dict[str, str | int | float | bool | None] = {
            "gate_reason": gate_reason,
            "provider_calls": 0,
            "selected_hit_count": len(selected),
        }
        planned = getattr(retriever, "base", None)
        plan_trace = getattr(planned, "last_trace", None)
        if plan_trace is not None:
            trace["planned_query_count"] = len(plan_trace.queries)
        return EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=architecture.architecture_id,
            action=EvaluationAction.ANSWER,
            answer="\n\n".join(row.text for row in claims),
            atomic_claims=claims,
            citations=citations,
            retrieved_evidence=[_citation(row) for row in hits],
            operational_status="completed-answer",
            usage=EvaluationUsageV1(
                latency_ms=(time.perf_counter() - started) * 1_000
            ),
            trace=trace,
        )
    except Exception as error:  # noqa: BLE001 - preserve per-case operational failure
        return EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=architecture.architecture_id,
            action=EvaluationAction.OPERATIONAL_FAILURE,
            answer="The tutoring service could not complete this request safely.",
            operational_status=f"failed:{type(error).__name__}",
            usage=EvaluationUsageV1(
                latency_ms=(time.perf_counter() - started) * 1_000
            ),
            trace={"error_type": type(error).__name__, "provider_calls": 0},
        )


def _response_package(
    architecture: ArchitectureSystemManifestV1,
    cases: list[EvaluationCaseV1],
    chunks: list[DocumentChunk],
) -> dict[str, Any]:
    retrievers = _build_retrievers(architecture, chunks)
    router = _router(architecture)
    responses = [
        _response(
            architecture=architecture,
            case=case,
            retriever=retrievers[case.course_id],
            router=router,
        ).model_dump(mode="json")
        for case in cases
    ]
    payload: dict[str, Any] = {
        "schema_version": 1,
        "architecture_id": architecture.architecture_id,
        "case_count": len(cases),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
        "responses": responses,
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ArchitectureRoundExecutionError(f"exclusive output exists: {path}")
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _score_packages(
    *,
    cases: list[EvaluationCaseV1],
    gold_path: Path,
    response_paths: dict[str, Path],
    scoring_profile: str = "lexical-token-v1",
) -> dict[str, Any]:
    gold_payload = _load_hashed(gold_path)
    gold_by_id = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value)
            for value in gold_payload.get("rows", [])
        )
    }
    if set(gold_by_id) != {row.case_id for row in cases}:
        raise ArchitectureRoundExecutionError("hidden gold case IDs drifted")
    results: dict[str, Any] = {}
    for architecture_id, path in response_paths.items():
        package = _load_hashed(path)
        responses = {
            row.case_id: row
            for row in (
                EvaluationResponseV1.model_validate(value)
                for value in package.get("responses", [])
            )
        }
        if set(responses) != set(gold_by_id):
            raise ArchitectureRoundExecutionError("response case IDs drifted")
        scores = []
        for case in cases:
            arguments: dict[str, Any] = {}
            if scoring_profile == "source-semantic-token-v2":
                arguments["normalizer"] = normalize_semantic_source_text
            scores.append(
                score_case(
                    case,
                    gold_by_id[case.case_id],
                    responses[case.case_id],
                    **arguments,
                )
            )
        results[architecture_id] = {
            "aggregate": summarize_scores(scores),
            "case_scores": [row.model_dump(mode="json") for row in scores],
        }
    return results


def _gate_results(
    instrument: ArchitectureRoundInstrumentV1,
    aggregate: dict[str, Any],
) -> dict[str, bool]:
    metrics = aggregate["metrics"]
    return {
        name: (
            aggregate[name] <= threshold
            if name == "severe_unsupported_release_count"
            else metrics[name] >= threshold
        )
        for name, threshold in instrument.hard_gates.items()
    }


def _selection_key(result: dict[str, Any]) -> tuple[float, ...]:
    aggregate = result["aggregate"]
    metrics = aggregate["metrics"]
    return (
        -float(aggregate["severe_unsupported_release_count"]),
        float(metrics["boundary_action_accuracy"]),
        float(metrics["fully_grounded_factual_success"]),
        float(metrics["citation_recall"]),
        float(metrics["evidence_recall_at_5"]),
        -float(aggregate["latency_ms_p95"]),
    )


def validate(instrument_path: Path) -> dict[str, Any]:
    instrument = _load_instrument(instrument_path)
    cases, chunks, _ = _load_inputs(instrument)
    for candidate in instrument.candidates:
        _build_retrievers(candidate, chunks)
        _router(candidate)
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed-build-only",
        "round_number": instrument.round_number,
        "case_count": len(cases),
        "candidate_count": len(instrument.candidates),
        "source_chunk_count": len(chunks),
        "network_free_execution_authorized": instrument.network_free_execution_authorized,
        "provider_execution_authorized": False,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded": False,
    }


def simulate(instrument_path: Path) -> dict[str, Any]:
    instrument = _load_instrument(instrument_path)
    cases, chunks, gold_path = _load_inputs(instrument)
    selected_cases = cases[:12]
    response_packages = {
        candidate.architecture_id: _response_package(candidate, selected_cases, chunks)
        for candidate in instrument.candidates
    }
    gold_payload = _load_hashed(gold_path)
    gold_by_id = {
        row["case_id"]: row
        for row in gold_payload["rows"]
        if row["case_id"] in {case.case_id for case in selected_cases}
    }
    if len(gold_by_id) != len(selected_cases):
        raise ArchitectureRoundExecutionError("simulation gold subset drifted")
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed-network-free-simulation",
        "case_count": len(selected_cases),
        "candidate_count": len(response_packages),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded_after_responses": True,
    }


def execute(instrument_path: Path) -> dict[str, Any]:
    instrument = _load_instrument(instrument_path)
    if not instrument.network_free_execution_authorized:
        raise ArchitectureRoundExecutionError("network-free execution is not authorized")
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    if dirty:
        raise ArchitectureRoundExecutionError("architecture execution requires a clean worktree")
    output_root = ROOT / instrument.output_directory
    if output_root.exists():
        raise ArchitectureRoundExecutionError("exclusive round output directory exists")
    cases, chunks, gold_path = _load_inputs(instrument)
    response_paths: dict[str, Path] = {}
    for candidate in instrument.candidates:
        package = _response_package(candidate, cases, chunks)
        response_path = output_root / f"{candidate.architecture_id}-responses.json"
        _atomic_write(response_path, package)
        response_paths[candidate.architecture_id] = response_path
    scored = _score_packages(
        cases=cases,
        gold_path=gold_path,
        response_paths=response_paths,
        scoring_profile=instrument.scoring_profile,
    )
    gate_results = {
        architecture_id: _gate_results(instrument, result["aggregate"])
        for architecture_id, result in scored.items()
    }
    selected_id = max(scored, key=lambda architecture_id: _selection_key(scored[architecture_id]))
    all_gates_passed = all(gate_results[selected_id].values())
    result_payload: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": instrument.instrument_id,
        "round_number": instrument.round_number,
        "status": "completed-keep" if all_gates_passed else "completed-refine",
        "code_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "selected_architecture_id": selected_id,
        "case_count": len(cases),
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "hidden_gold_loaded_after_all_responses": True,
        "scoring_profile": instrument.scoring_profile,
        "candidates": {
            architecture_id: {
                "aggregate": result["aggregate"],
                "hard_gates": gate_results[architecture_id],
            }
            for architecture_id, result in scored.items()
        },
        "limitations": [
            "This is a network-free development comparison, not the one-time final confirmation.",
            "Extractive deterministic wording isolates architecture behavior and does not estimate provider generation quality.",
            "The result cannot establish professor fidelity, real usability, or student learning improvement.",
        ],
    }
    result_payload["content_sha256"] = canonical_json_sha256(result_payload)
    _atomic_write(output_root / "result.json", result_payload)
    return result_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(
            _load_instrument(args.instrument).instrument_id,
            "method_evaluation_execution",
        )
    if args.validate:
        result = validate(args.instrument)
    elif args.simulate:
        result = simulate(args.instrument)
    else:
        result = execute(args.instrument)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
