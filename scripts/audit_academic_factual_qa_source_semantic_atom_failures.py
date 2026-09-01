#!/usr/bin/env python3
"""Audit whether the 16 semantic-atom failures are valid release findings."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.architecture_evolution import BoundArtifactV1  # noqa: E402
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    evidence_ranges_overlap,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_scoring import (  # noqa: E402
    normalize_semantic_source_text,
    score_case,
)
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.grounding.source_range_evidence import (  # noqa: E402
    canonicalize_source_claim,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-source-semantic-atom-failure-validity-audit-001"
DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "academic_factual_qa_source_semantic_atom_failure_validity_audit_001.json"
)


class FailureValidityAuditError(RuntimeError):
    """Raised when immutable audit evidence or adjudication constraints drift."""


class FailureAdjudicationV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question_uniquely_identifies_gold: Literal[False]
    corrected_expected_action: Literal[EvaluationAction.CLARIFY]
    selected_answer_relationship: Literal[
        "alternative-supported",
        "partial-supported",
        "conflicting-supported",
        "unrelated-supported",
    ]
    plausible_region_ids: list[str] = Field(min_length=2)
    reference_valid_for_release_scoring: Literal[False]
    product_behavior_valid_under_corrected_action: Literal[False]
    disposition: Literal["dual-reference-and-product-ambiguity-defect"]
    rationale: str = Field(min_length=30, max_length=500)

    @model_validator(mode="after")
    def unique_regions(self) -> "FailureAdjudicationV1":
        if len(self.plausible_region_ids) != len(set(self.plausible_region_ids)):
            raise ValueError("plausible regions must be unique")
        return self


class FailureValidityAuditInstrumentV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    instrument_id: Literal[
        "academic-factual-qa-source-semantic-atom-failure-validity-audit-001"
    ]
    status: Literal["frozen-network-free"]
    original_result: BoundArtifactV1
    candidate_responses: BoundArtifactV1
    source: BoundArtifactV1
    public_cases: BoundArtifactV1
    hidden_gold: BoundArtifactV1
    adjudications: BoundArtifactV1
    expected_failure_count: Literal[16]
    prior_result_immutable: Literal[True]
    official_rescoring_prohibited: Literal[True]
    provider_execution_authorized: Literal[False]
    paid_execution_authorized: Literal[False]
    network_free_execution_authorized: Literal[True]
    semantic_review_method: Literal[
        "deterministic-lineage-plus-codex-assisted-case-audit-v1"
    ]
    external_human_annotation: Literal[False]
    output_directory: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def safe_output(self) -> "FailureValidityAuditInstrumentV1":
        output = Path(self.output_directory)
        if output.is_absolute() or ".." in output.parts:
            raise ValueError("audit output directory must be repository relative")
        return self


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bound_path(binding: BoundArtifactV1) -> Path:
    path = ROOT / binding.path
    if not path.is_file() or _sha256(path) != binding.sha256:
        raise FailureValidityAuditError(f"bound artifact drifted: {binding.path}")
    return path


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FailureValidityAuditError(f"JSON object required: {path}")
    return value


def _instrument(path: Path) -> FailureValidityAuditInstrumentV1:
    payload = _load(path)
    observed = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed:
        raise FailureValidityAuditError("audit instrument hash drifted")
    return FailureValidityAuditInstrumentV1.model_validate(payload)


def _citation_key(value: Any) -> tuple[Any, ...]:
    return (
        value.source_artifact_id,
        value.source_version,
        value.source_sha256,
        value.char_start,
        value.char_end,
        value.region_id,
    )


def _chunk_key(value: DocumentChunk) -> tuple[Any, ...]:
    metadata = value.metadata
    return (
        value.source_artifact_id,
        value.source_version,
        value.source_checksum,
        int(metadata["char_start"]),
        int(metadata["char_end"]),
        value.region_id,
    )


def _selected_claims_are_source_supported(
    response: EvaluationResponseV1,
    chunks_by_key: dict[tuple[Any, ...], DocumentChunk],
) -> bool:
    for claim in response.atomic_claims:
        if not claim.citations:
            return False
        for citation in claim.citations:
            chunk = chunks_by_key.get(_citation_key(citation))
            if chunk is None:
                return False
            expected = canonicalize_source_claim(
                chunk.text,
                modality=str(chunk.metadata.get("modality", "")),
            )
            if normalize_semantic_source_text(
                expected
            ) != normalize_semantic_source_text(claim.text):
                return False
    return bool(response.atomic_claims)


def _gold_in_top_three(
    response: EvaluationResponseV1,
    gold: EvaluationGoldV1,
) -> bool:
    expected = [ref for claim in gold.claims for ref in claim.evidence_refs]
    return all(
        any(
            evidence_ranges_overlap(reference, observed)
            for observed in response.retrieved_evidence[:3]
        )
        for reference in expected
    )


def _audit(instrument: FailureValidityAuditInstrumentV1) -> dict[str, Any]:
    original_result = _load(_bound_path(instrument.original_result))
    if original_result.get("status") != "completed-refine":
        raise FailureValidityAuditError(
            "original result is not the frozen Refine result"
        )

    source_payload = _load(_bound_path(instrument.source))
    cases_payload = _load(_bound_path(instrument.public_cases))
    gold_payload = _load(_bound_path(instrument.hidden_gold))
    response_payload = _load(_bound_path(instrument.candidate_responses))
    adjudication_payload = _load(_bound_path(instrument.adjudications))

    cases = {
        row.case_id: row
        for row in (
            EvaluationCaseV1.model_validate(value)
            for value in cases_payload.get("cases", [])
        )
    }
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value)
            for value in gold_payload.get("gold", [])
        )
    }
    responses = {
        row.case_id: row
        for row in (
            EvaluationResponseV1.model_validate(value)
            for value in response_payload.get("responses", [])
        )
    }
    chunks = [
        DocumentChunk.model_validate(value)
        for value in source_payload.get("chunks", [])
    ]
    chunks_by_key = {_chunk_key(row): row for row in chunks}
    adjudications = {
        row.case_id: row
        for row in (
            FailureAdjudicationV1.model_validate(value)
            for value in adjudication_payload.get("adjudications", [])
        )
    }
    if set(cases) != set(gold) or set(cases) != set(responses):
        raise FailureValidityAuditError("case, gold, and response IDs drifted")

    failed_ids: list[str] = []
    for case_id, case in cases.items():
        score = score_case(
            case,
            gold[case_id],
            responses[case_id],
            normalizer=normalize_semantic_source_text,
        )
        if score.answerable and not score.fully_grounded_success:
            failed_ids.append(case_id)
    failed_ids.sort()
    if len(failed_ids) != instrument.expected_failure_count:
        raise FailureValidityAuditError("original answerable failure count drifted")
    if set(adjudications) != set(failed_ids):
        raise FailureValidityAuditError("adjudications do not cover the exact failures")

    audited_cases: list[dict[str, Any]] = []
    for case_id in failed_ids:
        case = cases[case_id]
        expected = gold[case_id]
        response = responses[case_id]
        judgement = adjudications[case_id]
        if expected.expected_action != EvaluationAction.ANSWER:
            raise FailureValidityAuditError("audited original gold was not answerable")
        if response.action != EvaluationAction.ANSWER:
            raise FailureValidityAuditError("audited candidate did not answer")
        supported = _selected_claims_are_source_supported(response, chunks_by_key)
        gold_top_three = _gold_in_top_three(response, expected)
        observed_regions = {row.region_id for row in response.retrieved_evidence[:3]}
        if not supported or not gold_top_three:
            raise FailureValidityAuditError("deterministic audit evidence drifted")
        if not set(judgement.plausible_region_ids).issubset(observed_regions):
            raise FailureValidityAuditError(
                "semantic adjudication cites a region outside retrieved top three"
            )
        audited_cases.append(
            {
                **judgement.model_dump(mode="json"),
                "course_id": case.course_id,
                "slice": case.slice,
                "original_expected_action": expected.expected_action.value,
                "actual_action": response.action.value,
                "gold_in_retrieved_top_3": gold_top_three,
                "selected_claim_source_supported": supported,
            }
        )

    original_case_count = len(cases)
    corrected_boundary_count = sum(
        row.expected_action != EvaluationAction.ANSWER for row in gold.values()
    ) + len(audited_cases)
    unaffected_correct_actions = original_case_count - len(audited_cases)
    result: dict[str, Any] = {
        "schema_version": 1,
        "audit_id": instrument.instrument_id,
        "status": "completed-refine",
        "decision": "dual-reference-and-product-ambiguity-correction-required",
        "prior_result_status_unchanged": original_result["status"],
        "official_prior_metrics_changed": False,
        "failure_count": len(audited_cases),
        "aggregate": {
            "gold_in_retrieved_top_3": len(audited_cases),
            "selected_claim_source_supported": len(audited_cases),
            "reference_invalid_for_release_scoring": len(audited_cases),
            "corrected_expected_action_clarify": len(audited_cases),
            "product_answered_instead_of_clarified": len(audited_cases),
            "dual_reference_and_product_defect": len(audited_cases),
            "evaluator_only_false_positive": 0,
            "product_only_failure": 0,
        },
        "descriptive_sensitivity_only": {
            "corrected_overall_action_accuracy": unaffected_correct_actions
            / original_case_count,
            "corrected_boundary_action_accuracy": (
                corrected_boundary_count - len(audited_cases)
            )
            / corrected_boundary_count,
            "corrected_boundary_count": corrected_boundary_count,
            "official_rescoring_prohibited": True,
        },
        "interpretation": {
            "thresholds_shown_too_strict": False,
            "exact_single-reference_gold_shown_incomplete": True,
            "original_boundary_metric_shown_optimistic": True,
            "product_ambiguity_router_shown_incomplete": True,
            "release_decision": "no-release-remains",
        },
        "next_method": {
            "reference": "pre-seal uniqueness validation plus alternate valid source ranges",
            "product": "fail-closed clarify on non-unique evidence targets or low evidence margin",
            "evaluation": "versioned successor on new source-disjoint cases with planted ambiguity controls",
        },
        "provider_calls": 0,
        "paid_cost_usd": 0.0,
        "external_human_annotation": False,
        "limitations": [
            "Semantic uniqueness was adjudicated by Codex in the current session, not by an independent external human.",
            "The sensitivity rates are diagnostic and do not replace the frozen official result.",
            "All audited content is from the already opened public-source development result.",
        ],
        "audited_cases": audited_cases,
    }
    result["content_sha256"] = canonical_json_sha256(result)
    return result


def validate(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
    result = _audit(instrument)
    return {
        "audit_id": instrument.instrument_id,
        "status": "passed",
        "failure_count": result["failure_count"],
        "provider_calls": 0,
        "paid_cost_usd": 0.0,
        "official_prior_metrics_changed": False,
    }


def _write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FailureValidityAuditError(f"exclusive audit output exists: {path}")
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def execute(path: Path) -> dict[str, Any]:
    instrument = _instrument(path)
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise FailureValidityAuditError("failure-validity audit requires a clean tree")
    result = _audit(instrument)
    output = ROOT / instrument.output_directory / "result.json"
    _write_exclusive(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
        )
        result = execute(arguments.instrument)
    else:
        result = validate(arguments.instrument)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
