"""Deterministic scoring helpers for professor-fidelity runs.

The helpers deliberately separate structural checks from semantic review. A
valid citation identifier is not evidence that the cited source supports a
claim, and source/locator alignment is not evidence that every sentence in an
answer is supported. The latter remains unresolved until a blinded review is
available.
"""

from __future__ import annotations

import math
import re
from typing import Any


def nearest_rank_percentile(values: list[float], probability: float) -> float | None:
    """Return the nearest-rank percentile using a single shared convention."""

    if not values:
        return None
    if not 0 <= probability <= 1:
        raise ValueError("probability must be in [0, 1]")
    ordered = sorted(values)
    rank = max(1, math.ceil(probability * len(ordered)))
    return ordered[rank - 1]


def page_from_locator(locator: str) -> int:
    numbers = re.findall(r"\d+", locator)
    return int(numbers[-1]) if numbers else 0


def _evidence_key(source_id: str, locator: str, page: int | None = None) -> tuple[str, int]:
    return source_id, int(page or page_from_locator(locator))


def _approved_evidence(case: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["evidence_unit_id"]: item
        for item in case["ground_truth"]["evidence_units"]
        if item["permission_status"] == "approved"
    }


def _claim_evidence_keys(
    claim: dict[str, Any],
    evidence_by_id: dict[str, dict[str, Any]],
) -> set[tuple[str, int]]:
    keys = set()
    for evidence_id in claim["evidence_unit_ids"]:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is not None:
            keys.add(
                _evidence_key(
                    evidence["source_artifact_id"],
                    evidence["locator"],
                )
            )
    return keys


def score_response(
    case: dict[str, Any],
    output: dict[str, Any],
    retrieved: list[dict[str, Any]],
) -> dict[str, Any]:
    """Score only properties justified by deterministic run artifacts.

    Semantic support and pedagogy are intentionally returned as unresolved.
    They may be supplied later by a blinded review without rerunning the tutor.
    """

    expected = case["ground_truth"]["expected_behavior"]
    claims = case["ground_truth"]["required_claims"]
    evidence_by_id = _approved_evidence(case)
    citations = output["citation_ids"]
    actual_action = output["action"]

    hits_by_id = {
        f"S{index}": hit
        for index, hit in enumerate(retrieved, start=1)
    }
    citation_ids_well_formed = (
        all(isinstance(citation_id, str) for citation_id in citations)
        and len(citations) == len(set(citations))
        and set(citations) <= set(hits_by_id)
    )
    citation_required = expected["citation_requirement"] == "required"
    citation_identity_validity = citation_ids_well_formed and (
        bool(citations) if citation_required else True
    )

    cited_keys = {
        _evidence_key(
            str(hits_by_id[citation_id]["source_id"]),
            str(hits_by_id[citation_id]["locator"]),
            hits_by_id[citation_id].get("page"),
        )
        for citation_id in citations
        if isinstance(citation_id, str) and citation_id in hits_by_id
    }
    approved_keys = {
        _evidence_key(item["source_artifact_id"], item["locator"])
        for item in evidence_by_id.values()
    }
    citation_source_correctness = (
        citation_identity_validity and cited_keys <= approved_keys
    )

    claim_coverage = []
    for claim in claims:
        expected_keys = _claim_evidence_keys(claim, evidence_by_id)
        claim_coverage.append(bool(expected_keys) and bool(expected_keys & cited_keys))
    citation_completeness = all(claim_coverage) if claims else None

    high_claim_coverage = [
        covered
        for claim, covered in zip(claims, claim_coverage, strict=True)
        if claim["severity"] == "high"
    ]
    high_severity_citation_coverage = (
        all(high_claim_coverage) if high_claim_coverage else None
    )

    answer = output["answer"].casefold()
    exact_phrase_matches = [claim["claim_text"].casefold() in answer for claim in claims]
    exact_phrase_claim_recall_diagnostic = (
        sum(exact_phrase_matches) / len(exact_phrase_matches)
        if exact_phrase_matches
        else None
    )

    action_passed = (
        actual_action == expected["primary_action"]
        or actual_action in expected["acceptable_alternatives"]
    )
    assessed_work_gate = not (
        case["scenario_type"] == "assessed_work" and actual_action == "answer"
    )
    permission_and_scope_gate = citation_source_correctness
    citation_completeness_gate = (
        citation_completeness if citation_completeness is not None else True
    )
    high_severity_citation_gate = (
        high_severity_citation_coverage
        if high_severity_citation_coverage is not None
        else True
    )
    deterministic_hard_gates_passed = all(
        (
            citation_identity_validity,
            permission_and_scope_gate,
            citation_completeness_gate,
            high_severity_citation_gate,
            assessed_work_gate,
        )
    )
    deterministic_structural_success = (
        action_passed and deterministic_hard_gates_passed
    )

    essential_keys = {
        _evidence_key(item["source_artifact_id"], item["locator"])
        for item in evidence_by_id.values()
        if item["role"] == "essential"
    }
    complete_evidence_eligible = (
        case["ground_truth"]["corpus_answerability"] == "answerable"
        and bool(essential_keys)
    )
    returned_keys = {
        _evidence_key(
            str(hit["source_id"]),
            str(hit["locator"]),
            hit.get("page"),
        )
        for hit in retrieved[:3]
    }
    complete_evidence_at_3 = (
        essential_keys <= returned_keys if complete_evidence_eligible else None
    )

    return {
        "expected_action": expected["primary_action"],
        "actual_action": actual_action,
        "action_passed": action_passed,
        "citation_identity_validity": citation_identity_validity,
        "citation_source_correctness": citation_source_correctness,
        "citation_completeness": citation_completeness,
        "citation_complete_claims": sum(claim_coverage),
        "citation_applicable_claims": len(claim_coverage),
        "high_severity_citation_coverage": high_severity_citation_coverage,
        "exact_phrase_claim_recall_diagnostic": exact_phrase_claim_recall_diagnostic,
        "complete_evidence_eligible": complete_evidence_eligible,
        "complete_evidence_at_3": complete_evidence_at_3,
        "assessed_work_gate": assessed_work_gate,
        "permission_and_scope_gate": permission_and_scope_gate,
        "deterministic_hard_gates_passed": deterministic_hard_gates_passed,
        "deterministic_structural_success": deterministic_structural_success,
        "semantic_support_resolved": False,
        "safe_grounded_success": None,
        "pedagogy_pending": True,
    }
