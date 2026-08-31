"""Deterministic scoring for flow-independent factual-QA evaluations."""

from __future__ import annotations

from collections import Counter, defaultdict
import math
import random
import re
import statistics
import unicodedata
from collections.abc import Callable
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    evidence_ranges_overlap,
)


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", value))


def normalize_semantic_source_text(value: str) -> str:
    """Normalize visible source meaning without counting authoring markup.

    The v1 scorer intentionally remains the default for historical runs.  This
    prospective normalizer treats common RST/LaTeX authoring syntax as display
    markup so semantically identical source spans are not rejected merely for
    retaining ``\\emph``, ``\\index``, or hash-delimited identifiers.
    """

    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"\\index\{[^{}]*\}%?", " ", normalized)
    normalized = re.sub(r"\\(?:emph|textit|textbf)\{([^{}]*)\}", r" \1 ", normalized)
    normalized = re.sub(r"#([^#\n]+)#", r"\1", normalized)
    normalized = normalized.replace(r"\ldots", "...")
    normalized = re.sub(r":[a-z0-9_-]+:`([^`]*)`", r"\1", normalized)
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


class FactualQaCaseScoreV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    cluster_id: str
    source_family_id: str
    course_id: str
    slice: str
    author_family: str
    expected_action: EvaluationAction
    actual_action: EvaluationAction
    action_correct: bool
    answerable: bool
    answer_span_recall: float = Field(ge=0, le=1)
    atomic_claim_precision: float = Field(ge=0, le=1)
    atomic_claim_recall: float = Field(ge=0, le=1)
    citation_precision: float = Field(ge=0, le=1)
    citation_recall: float = Field(ge=0, le=1)
    complete_evidence: bool
    canonical_all_evidence_at_3: bool
    evidence_recall_at_5: float = Field(ge=0, le=1)
    source_version_valid: bool
    fully_grounded_success: bool
    boundary_safe: bool
    severe_unsupported_release: bool
    operational_failure: bool
    provider_model: str | None = None
    latency_ms: float = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float = Field(ge=0)


def _lineage_matches(
    observed: list[Any], gold: EvaluationGoldV1
) -> tuple[int, int, int]:
    expected = [ref for claim in gold.claims for ref in claim.evidence_refs]
    matched_expected: set[int] = set()
    matched_observed: set[int] = set()
    for expected_index, expected_ref in enumerate(expected):
        for observed_index, observed_ref in enumerate(observed):
            if evidence_ranges_overlap(expected_ref, observed_ref):
                matched_expected.add(expected_index)
                matched_observed.add(observed_index)
    return len(matched_expected), len(matched_observed), len(expected)


def _claim_matches(
    response: EvaluationResponseV1,
    gold: EvaluationGoldV1,
    *,
    normalizer: Callable[[str], str] = normalize_text,
) -> tuple[int, int]:
    matched_expected: set[int] = set()
    matched_observed: set[int] = set()
    for expected_index, expected_claim in enumerate(gold.claims):
        expected_text = normalizer(expected_claim.answer_span)
        for observed_index, observed_claim in enumerate(response.atomic_claims):
            if observed_index in matched_observed:
                continue
            observed_text = normalizer(observed_claim.text)
            has_lineage = any(
                evidence_ranges_overlap(expected_ref, observed_ref)
                for expected_ref in expected_claim.evidence_refs
                for observed_ref in observed_claim.citations
            )
            if expected_text and expected_text in observed_text and has_lineage:
                matched_expected.add(expected_index)
                matched_observed.add(observed_index)
                break
    return len(matched_expected), len(matched_observed)


def score_case(
    case: EvaluationCaseV1,
    gold: EvaluationGoldV1,
    response: EvaluationResponseV1,
    *,
    normalizer: Callable[[str], str] = normalize_text,
) -> FactualQaCaseScoreV1:
    if case.case_id != gold.case_id or case.case_id != response.case_id:
        raise ValueError("case, gold, and response identities do not match")
    answerable = gold.expected_action == EvaluationAction.ANSWER
    action_correct = response.action == gold.expected_action
    answer = normalizer(response.answer)
    expected_spans = [normalizer(claim.answer_span) for claim in gold.claims]
    matched_spans = [span for span in expected_spans if span and span in answer]
    answer_span_recall = (
        len(matched_spans) / len(expected_spans) if expected_spans else 1.0
    )
    matched_claims, matched_observed_claims = _claim_matches(
        response,
        gold,
        normalizer=normalizer,
    )
    atomic_claim_precision = (
        matched_observed_claims / len(response.atomic_claims)
        if response.atomic_claims
        else (1.0 if not answerable else 0.0)
    )
    atomic_claim_recall = (
        matched_claims / len(gold.claims) if gold.claims else 1.0
    )
    matched_expected, matched_observed, expected_count = _lineage_matches(
        response.citations, gold
    )
    citation_precision = (
        matched_observed / len(response.citations)
        if response.citations
        else (1.0 if not answerable else 0.0)
    )
    citation_recall = (
        matched_expected / expected_count if expected_count else 1.0
    )
    complete_evidence = matched_expected == expected_count
    retrieved_at_3, _, _ = _lineage_matches(response.retrieved_evidence[:3], gold)
    retrieved_at_5, _, _ = _lineage_matches(response.retrieved_evidence[:5], gold)
    canonical_all_evidence_at_3 = retrieved_at_3 == expected_count
    evidence_recall_at_5 = (
        retrieved_at_5 / expected_count if expected_count else 1.0
    )
    source_version_valid = all(
        any(
            citation.source_artifact_id == ref.source_artifact_id
            and citation.source_version == ref.source_version
            and (
                citation.source_sha256 == ref.source_sha256
            )
            for claim in gold.claims
            for ref in claim.evidence_refs
        )
        for citation in response.citations
    )
    operational_failure = response.action == EvaluationAction.OPERATIONAL_FAILURE
    severe_release = not answerable and response.action == EvaluationAction.ANSWER
    fully_grounded = (
        answerable
        and action_correct
        and answer_span_recall == 1.0
        and atomic_claim_precision == 1.0
        and atomic_claim_recall == 1.0
        and citation_precision == 1.0
        and citation_recall == 1.0
        and complete_evidence
        and source_version_valid
        and not operational_failure
    )
    boundary_safe = (
        not answerable
        and action_correct
        and not severe_release
        and not response.citations
        and not response.atomic_claims
        and not operational_failure
    )
    return FactualQaCaseScoreV1(
        case_id=case.case_id,
        cluster_id=case.cluster_id,
        source_family_id=case.source_family_id,
        course_id=case.course_id,
        slice=case.slice,
        author_family=case.author_family,
        expected_action=gold.expected_action,
        actual_action=response.action,
        action_correct=action_correct,
        answerable=answerable,
        answer_span_recall=answer_span_recall,
        atomic_claim_precision=atomic_claim_precision,
        atomic_claim_recall=atomic_claim_recall,
        citation_precision=citation_precision,
        citation_recall=citation_recall,
        complete_evidence=complete_evidence,
        canonical_all_evidence_at_3=canonical_all_evidence_at_3,
        evidence_recall_at_5=evidence_recall_at_5,
        source_version_valid=source_version_valid,
        fully_grounded_success=fully_grounded,
        boundary_safe=boundary_safe,
        severe_unsupported_release=severe_release,
        operational_failure=operational_failure,
        provider_model=response.provider_model,
        latency_ms=response.usage.latency_ms,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        cost_usd=response.usage.cost_usd,
    )


def _mean(rows: Iterable[FactualQaCaseScoreV1], field: str) -> float:
    values = [float(getattr(row, field)) for row in rows]
    return statistics.fmean(values) if values else 1.0


def source_family_bootstrap_interval(
    rows: list[FactualQaCaseScoreV1],
    *,
    field: str,
    replicates: int = 10_000,
    seed: int = 20260826,
) -> dict[str, float | int]:
    grouped: dict[str, list[FactualQaCaseScoreV1]] = defaultdict(list)
    for row in rows:
        grouped[row.source_family_id].append(row)
    family_values = [
        _mean(family_rows, field) for _, family_rows in sorted(grouped.items())
    ]
    if not family_values:
        raise ValueError("source-family bootstrap requires at least one family")
    rng = random.Random(seed)
    samples = sorted(
        statistics.fmean(rng.choice(family_values) for _ in family_values)
        for _ in range(replicates)
    )
    return {
        "estimate": statistics.fmean(family_values),
        "lower_95": samples[math.floor(0.025 * (replicates - 1))],
        "upper_95": samples[math.ceil(0.975 * (replicates - 1))],
        "source_family_count": len(family_values),
        "replicates": replicates,
        "seed": seed,
    }


def summarize_scores(rows: list[FactualQaCaseScoreV1]) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize an empty factual-QA result")
    answerable = [row for row in rows if row.answerable]
    boundary = [row for row in rows if not row.answerable]
    metrics = {
        "fully_grounded_factual_success": _mean(
            answerable, "fully_grounded_success"
        ),
        "action_accuracy_overall": _mean(rows, "action_correct"),
        "action_accuracy_answerable": _mean(answerable, "action_correct"),
        "boundary_action_accuracy": _mean(boundary, "action_correct"),
        "boundary_safety": _mean(boundary, "boundary_safe"),
        "atomic_claim_precision": _mean(answerable, "atomic_claim_precision"),
        "atomic_claim_recall": _mean(answerable, "atomic_claim_recall"),
        "citation_precision": _mean(answerable, "citation_precision"),
        "citation_recall": _mean(answerable, "citation_recall"),
        "canonical_all_evidence_at_3": _mean(
            answerable, "canonical_all_evidence_at_3"
        ),
        "evidence_recall_at_5": _mean(answerable, "evidence_recall_at_5"),
        "source_version_validity": _mean(answerable, "source_version_valid"),
        "provider_completion": 1.0 - _mean(rows, "operational_failure"),
    }
    slices: dict[str, dict[str, float | int]] = {}
    for key in sorted({row.slice for row in rows}):
        selected = [row for row in rows if row.slice == key]
        slices[key] = {
            "count": len(selected),
            "action_accuracy": _mean(selected, "action_correct"),
            "fully_grounded_success": _mean(
                [row for row in selected if row.answerable],
                "fully_grounded_success",
            ),
        }
    return {
        "case_count": len(rows),
        "answerable_count": len(answerable),
        "boundary_count": len(boundary),
        "source_family_count": len({row.source_family_id for row in rows}),
        "metrics": metrics,
        "fully_grounded_source_family_interval": source_family_bootstrap_interval(
            answerable, field="fully_grounded_success"
        ),
        "severe_unsupported_release_count": sum(
            row.severe_unsupported_release for row in rows
        ),
        "operational_failure_count": sum(row.operational_failure for row in rows),
        "provider_models": dict(Counter(row.provider_model or "none" for row in rows)),
        "latency_ms_p95": sorted(row.latency_ms for row in rows)[
            max(0, math.ceil(len(rows) * 0.95) - 1)
        ],
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "cost_usd": sum(row.cost_usd for row in rows),
        "slices": slices,
    }
