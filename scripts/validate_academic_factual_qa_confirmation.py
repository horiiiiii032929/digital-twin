#!/usr/bin/env python3
"""Validate the build-only academic factual-QA confirmation protocol."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_confirmation_001.json"
)
DECISION_LOG = ROOT / "research/00_admin/decision-log.md"
INSTRUMENT_ID = "academic-factual-qa-confirmation-001"
STATUS = "protocol-frozen-source-and-labels-pending"
DECISION_IDS = tuple(f"AFQC-{index:03d}" for index in range(1, 7))

ANSWERABLE_STRATA = {
    "direct-text": 20,
    "paraphrase-text": 20,
    "multi-source": 20,
    "code": 10,
    "table": 10,
    "diagram": 10,
    "equation": 10,
}
BOUNDARY_STRATA = {
    "no-evidence": 20,
    "cross-course-confusion": 20,
    "ambiguous": 15,
    "stale-version": 10,
    "academic-integrity": 15,
    "permission-filtered": 10,
    "unsupported-premise": 10,
}
CONDITION_IDS = (
    "T0-ANY-HIT-CONFIRMATION-CONTROL",
    "T0-STRUCTURED-COVERAGE-CONFIRMATION-ABLATION",
    "T0-TWO-BOUNDARY-CONFIRMATION-CANDIDATE",
)


class ConfirmationProtocolError(ValueError):
    """Raised when the preregistered confirmation protocol drifts."""


def zero_event_upper_bound(sample_size: int, confidence: float = 0.95) -> float:
    """Return the one-sided exact binomial upper bound after zero events."""

    if sample_size <= 0 or not 0 < confidence < 1:
        raise ValueError("sample size and confidence must be valid")
    return 1 - (1 - confidence) ** (1 / sample_size)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ConfirmationProtocolError(message)


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    _require(instrument.get("instrument_id") == INSTRUMENT_ID, "instrument ID drifted")
    _require(instrument.get("status") == STATUS, "protocol status drifted")
    _require(
        tuple(instrument.get("decision_memory_ids", ())) == DECISION_IDS,
        "decision memory drifted",
    )

    sampling = instrument["sampling_plan"]
    _require(
        sampling["answerable_strata"] == ANSWERABLE_STRATA,
        "answerable allocation drifted",
    )
    _require(
        sampling["boundary_strata"] == BOUNDARY_STRATA,
        "boundary allocation drifted",
    )
    _require(
        sum(ANSWERABLE_STRATA.values())
        == sampling["answerable_case_count"]
        == 100,
        "answerable total drifted",
    )
    _require(
        sum(BOUNDARY_STRATA.values()) == sampling["boundary_case_count"] == 100,
        "boundary total drifted",
    )
    _require(sampling["confirmation_case_count"] == 200, "confirmation size drifted")
    _require(
        sampling["cluster_count"] == 100 and sampling["cases_per_cluster"] == 2,
        "cluster plan drifted",
    )
    _require(
        sampling["course_count"] * sampling["clusters_per_course"] == 100,
        "course cluster allocation drifted",
    )
    _require(
        sampling["course_count"] * sampling["cases_per_course"] == 200,
        "course case allocation drifted",
    )
    _require(
        sampling["final_tranche_case_count"] == 600
        and sampling["final_tranche_cluster_count"] == 300,
        "final tranche plan drifted",
    )
    _require(
        sampling["final_tranche_authorized"] is False,
        "final tranche must remain unauthorized",
    )

    independence = instrument["independence_contract"]
    independence_fields = (
        "exactly_one_answerable_and_one_boundary_per_cluster",
        "source_artifact_reuse_across_clusters",
        "source_family_reuse_across_clusters",
        "underlying_fact_reuse_across_clusters",
        "question_family_reuse_across_clusters",
        "development_cluster_overlap_allowed",
        "confirmation_tuning_allowed",
        "final_tuning_allowed",
    )
    _require(
        tuple(independence[key] for key in independence_fields)
        == (True, False, False, False, False, False, False, False),
        "independence contract drifted",
    )

    source = instrument["source_contract"]
    _require(
        source["confirmation_scope"] == "eligible-public-computing-materials-only",
        "source scope drifted",
    )
    _require(
        source["academia_vault_opening_authorized"] is False,
        "private source opening must remain closed",
    )
    _require(
        source["source_manifest_bound"] is False
        and source["source_manifest_path"] is None,
        "source manifest must remain unopened",
    )

    labels = instrument["reference_label_contract"]
    _require(
        labels["author_may_set_authoritative_label"] is False,
        "case author cannot own truth",
    )
    _require(
        labels["author_may_validate_own_case"] is False,
        "self-validation is not independent",
    )
    _require(
        labels["llm_review_is_authoritative"] is False,
        "LLM review must remain advisory",
    )
    _require(labels["human_reviewer_a_case_count"] == 200, "reviewer A coverage drifted")
    _require(labels["human_reviewer_b_fixed_case_count"] == 60, "reviewer B sample drifted")
    _require(
        labels["human_reviewer_b_answerable_count"]
        == labels["human_reviewer_b_boundary_count"]
        == 30,
        "double-review balance drifted",
    )
    _require(
        labels["reference_labels_complete"] is False,
        "reference labels cannot be complete at build-only stage",
    )
    _require(
        labels["reference_manifest_path"] is None,
        "reference manifest must remain unopened",
    )

    _require(
        tuple(row["condition_id"] for row in instrument["conditions"])
        == CONDITION_IDS,
        "condition contract drifted",
    )
    _require(
        instrument["system_freeze"]["provider_or_model_bound"] is False,
        "provider must not be bound before final freeze",
    )

    expected_gates = {
        "severe_unsupported_release_count_max": 0,
        "source_version_valid_citation_rate_min": 1.0,
        "supported_answer_retention_min": 0.95,
        "action_accuracy_overall_min": 0.95,
        "action_accuracy_answerable_min": 0.9,
        "action_accuracy_boundary_min": 0.9,
        "atomic_claim_precision_min": 0.98,
        "atomic_claim_recall_min": 0.95,
        "citation_precision_min": 0.98,
        "citation_recall_min": 0.95,
        "complete_evidence_rate_min": 0.95,
        "evidence_recall_at_5_min": 0.95,
        "all_evidence_at_3_min": 0.9,
        "exact_normalized_duplicate_count_max": 0,
        "unreviewed_near_duplicate_count_max": 0,
        "malformed_response_count_max": 1,
        "identity_drift_count_max": 0,
        "persistence_mismatch_count_max": 0,
        "supported_retention_paired_delta_lower_95_min": -0.03,
    }
    _require(
        instrument["prospective_gates"] == expected_gates,
        "prospective gates drifted",
    )

    analysis = instrument["analysis_plan"]
    _require(
        analysis["bootstrap_replicates"] == 10000
        and analysis["bootstrap_seed"] == 20260825,
        "bootstrap plan drifted",
    )
    _require(
        math.isclose(
            analysis["confirmation_zero_event_upper_bound"],
            zero_event_upper_bound(100),
            abs_tol=5e-7,
        ),
        "confirmation zero-event bound drifted",
    )
    _require(
        math.isclose(
            analysis["final_zero_event_upper_bound"],
            zero_event_upper_bound(300),
            abs_tol=5e-7,
        ),
        "final zero-event bound drifted",
    )

    safety = instrument["execution_safety"]
    _require(
        all(value is False for value in safety.values()),
        "all execution authorities must remain false",
    )
    _require(
        instrument["progression_rule"]["failed_confirmation_tuning_permitted"]
        is False,
        "confirmation tuning must remain prohibited",
    )

    decision_log = DECISION_LOG.read_text(encoding="utf-8")
    _require(
        all(decision_id in decision_log for decision_id in DECISION_IDS),
        "decision log is incomplete",
    )
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    source = instrument["source_contract"]
    labels = instrument["reference_label_contract"]
    system = instrument["system_freeze"]
    safety = instrument["execution_safety"]
    blockers: list[str] = []
    if not source["source_manifest_bound"]:
        blockers.append("source-manifest-not-bound")
    if not labels["reference_labels_complete"]:
        blockers.append("independent-reference-labels-incomplete")
    if not system["product_revision_bound"] or not system["profile_hash_bound"]:
        blockers.append("product-revision-and-profile-not-frozen")
    if not safety["confirmation_execution_authorized"]:
        blockers.append("confirmation-execution-authorized-false")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "blocked-build-only" if blockers else "ready",
        "blockers": blockers,
        "planned_case_count": 200,
        "planned_cluster_count": 100,
        "provider_calls": 0,
        "private_data_read": False,
        "source_manifest_opened": False,
        "reference_labels_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    instrument = validate_instrument()
    result = (
        {"instrument_id": INSTRUMENT_ID, "status": "validated-build-only"}
        if args.validate
        else preflight(instrument)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
