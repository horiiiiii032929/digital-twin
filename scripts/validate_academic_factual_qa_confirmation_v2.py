#!/usr/bin/env python3
"""Validate the calibration-authorized LLM-panel factual-QA protocol."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from scripts.validate_academic_factual_qa_confirmation import (
    ANSWERABLE_STRATA,
    BOUNDARY_STRATA,
    CONDITION_IDS,
    zero_event_upper_bound,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_confirmation_002.json"
)
REVIEWER_BINDINGS = (
    ROOT
    / "research/05_evaluation/instruments/"
    "academic_factual_qa_confirmation_002_reviewer_bindings.json"
)
PREDECESSOR_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_confirmation_001.json"
)
DECISION_LOG = ROOT / "research/00_admin/decision-log.md"
INSTRUMENT_ID = "academic-factual-qa-confirmation-002"
STATUS = "frozen-pending-execution"
DECISION_IDS = tuple(f"AFQC-{index:03d}" for index in range(7, 18))
REVIEWER_IDS = (
    "codex-isolated-task-blinded-reviewer",
    "mistral-small-4-blinded-reviewer",
    "deepseek-v4-pro-blinded-reviewer",
)
MODEL_FAMILIES = ("openai", "mistral", "deepseek")


class LlmPanelProtocolError(ValueError):
    """Raised when the preregistered LLM-panel protocol drifts."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise LlmPanelProtocolError(message)


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    _require(instrument.get("instrument_id") == INSTRUMENT_ID, "instrument ID drifted")
    _require(instrument.get("status") == STATUS, "protocol status drifted")
    _require(
        tuple(instrument.get("decision_memory_ids", ())) == DECISION_IDS,
        "decision memory drifted",
    )
    _require(
        instrument["predecessor"]
        == {
            "instrument_id": "academic-factual-qa-confirmation-001",
            "disposition": "superseded-before-source-opening-or-execution",
            "reason": "No feasible external human reviewers were available; the replacement preserves deterministic truth and uses a diverse blinded LLM panel plus bounded researcher audit.",
        },
        "predecessor disposition drifted",
    )
    _require(
        instrument["claim_level"]
        == "deterministic-source-derived-llm-panel-reviewed-researcher-audited-silver-reference",
        "claim level drifted",
    )
    _require(
        instrument["scope"]["independent_human_ground_truth_claim"] is False,
        "external human ground-truth claim must remain false",
    )

    predecessor = json.loads(PREDECESSOR_INSTRUMENT.read_text(encoding="utf-8"))
    _require(
        predecessor["instrument_id"] == "academic-factual-qa-confirmation-001"
        and predecessor["reference_label_contract"]["human_reviewer_a_case_count"]
        == 200,
        "historical human-review protocol was not preserved",
    )

    sampling = instrument["sampling_plan"]
    _require(sampling["answerable_strata"] == ANSWERABLE_STRATA, "answerable allocation drifted")
    _require(sampling["boundary_strata"] == BOUNDARY_STRATA, "boundary allocation drifted")
    _require(
        sampling["confirmation_case_count"] == 200
        and sampling["cluster_count"] == 100
        and sampling["cases_per_cluster"] == 2,
        "confirmation sampling drifted",
    )
    _require(
        sampling["answerable_case_count"]
        == sum(ANSWERABLE_STRATA.values())
        == 100,
        "answerable total drifted",
    )
    _require(
        sampling["boundary_case_count"] == sum(BOUNDARY_STRATA.values()) == 100,
        "boundary total drifted",
    )
    _require(
        sampling["course_count"] * sampling["clusters_per_course"] == 100
        and sampling["course_count"] * sampling["cases_per_course"] == 200,
        "course allocation drifted",
    )
    _require(
        sampling["final_tranche_case_count"] == 600
        and sampling["final_tranche_cluster_count"] == 300
        and sampling["final_tranche_authorized"] is False,
        "final tranche drifted",
    )

    independence = instrument["independence_contract"]
    _require(
        independence["primary_unit"] == "source-and-question-family-cluster",
        "independence unit drifted",
    )
    _require(
        independence["exactly_one_answerable_and_one_boundary_per_cluster"] is True,
        "paired cluster contract drifted",
    )
    for key in (
        "source_artifact_reuse_across_clusters",
        "source_family_reuse_across_clusters",
        "underlying_fact_reuse_across_clusters",
        "question_family_reuse_across_clusters",
        "development_cluster_overlap_allowed",
        "confirmation_tuning_allowed",
        "final_tuning_allowed",
    ):
        _require(independence[key] is False, f"{key} must remain false")

    source = instrument["source_contract"]
    _require(
        source["confirmation_scope"] == "eligible-public-computing-materials-only",
        "source scope drifted",
    )
    _require(source["academia_vault_opening_authorized"] is False, "private source opening must remain closed")
    _require(source["source_manifest_bound"] is True, "source manifest must be bound")
    for path_key, hash_key in (
        ("source_manifest_path", "source_manifest_sha256"),
        ("confirmation_dataset_path", "confirmation_dataset_sha256"),
    ):
        artifact = json.loads((ROOT / source[path_key]).read_text(encoding="utf-8"))
        _require(artifact["content_sha256"] == source[hash_key], f"{path_key} binding drifted")
        _require(
            artifact["content_sha256"]
            == canonical_sha256(
                {key: value for key, value in artifact.items() if key != "content_sha256"}
            ),
            f"{path_key} content hash is invalid",
        )
    _require(source["full_raw_source_artifacts_committed"] is False, "raw sources cannot be committed")
    _require(source["source_and_question_family_overlap_count"] == 0, "source-family overlap detected")

    truth = instrument["truth_authority_contract"]
    _require(
        truth["canonical_truth_method"] == "deterministic-source-derived-construction",
        "truth method drifted",
    )
    _require(truth["llm_may_create_authoritative_truth"] is False, "LLM cannot create truth")
    _require(truth["llm_may_mutate_authoritative_truth"] is False, "LLM cannot mutate truth")
    _require(truth["model_question_paraphrase_allowed"] is False, "model paraphrasing must remain disabled")
    _require(truth["deterministic_canonical_question_required"] is True, "deterministic question is required")

    panel = instrument["reviewer_panel_contract"]
    reviewers = panel["reviewers"]
    _require(panel["panel_size"] == len(reviewers) == 3, "reviewer panel size drifted")
    _require(tuple(row["reviewer_id"] for row in reviewers) == REVIEWER_IDS, "reviewer identities drifted")
    _require(tuple(row["model_family"] for row in reviewers) == MODEL_FAMILIES, "model-family diversity drifted")
    _require(len(set(MODEL_FAMILIES)) == panel["minimum_distinct_model_families"] == 3, "reviewer families are not distinct")
    _require(all(row["planned_case_count"] == 200 for row in reviewers), "reviewer coverage drifted")
    _require(all(row["binding_fresh"] is True for row in reviewers), "reviewer bindings are not frozen")
    _require(
        all(
            panel[key] is True
            for key in (
                "all_reviewers_cover_all_cases",
                "candidate_output_model_identity_blinded",
                "condition_identity_blinded",
                "other_reviewer_votes_blinded",
                "canonical_authoritative_label_blinded",
                "answer_order_randomized_where_pairwise",
            )
        ),
        "reviewer blinding drifted",
    )
    _require(reviewers[0]["designer_conflict_disclosed"] is True, "Codex design conflict must be disclosed")
    _require(reviewers[0]["exact_api_snapshot_reproducible"] is False, "Codex reproducibility limitation must be disclosed")
    _require(
        reviewers[0]["provider_model"] == "gpt-5.6-sol"
        and reviewers[0]["reasoning_effort"] == "medium"
        and reviewers[0]["runtime_identity_verification_pending"] is True,
        "Codex runtime binding drifted",
    )
    _require(
        reviewers[1]["provider_model"] == "mistralai/mistral-small-2603"
        and reviewers[1]["endpoint_provider"] == "Mistral"
        and reviewers[1]["endpoint_tag"] == "mistral/zdr",
        "Mistral reviewer binding drifted",
    )
    _require(reviewers[2]["same_family_as_product_generator"] is True, "DeepSeek dependence must be disclosed")
    _require(
        reviewers[2]["provider_model"] == "deepseek-v4-pro"
        and reviewers[2]["documented_revision"] == "DeepSeek-V4-Pro-0813",
        "DeepSeek reviewer binding drifted",
    )
    _require(panel["reviewer_confidence_is_authoritative"] is False, "confidence cannot be authoritative")
    _require(panel["reviewer_votes_are_ground_truth"] is False, "panel votes cannot be ground truth")

    calibration = instrument["reviewer_calibration_contract"]
    _require(
        calibration["control_case_count"]
        == calibration["clean_control_count"] + calibration["corrupted_control_count"]
        == 40,
        "calibration allocation drifted",
    )
    for key in (
        "each_reviewer_action_accuracy_min",
        "each_reviewer_mutation_sensitivity_min",
        "each_reviewer_specificity_min",
        "each_reviewer_citation_defect_sensitivity_min",
    ):
        _require(calibration[key] == 0.9, f"{key} drifted")
    _require(calibration["failed_reviewer_may_vote"] is False, "failed reviewer cannot vote")
    _require(calibration["calibration_controls_sealed"] is True, "controls must be sealed")
    for path_key, hash_key in (
        ("calibration_dataset_path", "calibration_dataset_sha256"),
        ("blinded_packet_path", "blinded_packet_sha256"),
    ):
        artifact = json.loads((ROOT / calibration[path_key]).read_text(encoding="utf-8"))
        _require(artifact["content_sha256"] == calibration[hash_key], f"{path_key} binding drifted")

    audit = instrument["consensus_and_researcher_audit"]
    _require(audit["automatic_semantic_acceptance_requires_unanimity"] is True, "unanimity rule drifted")
    _require(audit["automatic_semantic_acceptance_also_requires_deterministic_pass"] is True, "deterministic gate drifted")
    _require(audit["majority_vote_is_authoritative"] is False, "majority vote cannot be authoritative")
    _require(audit["any_disagreement_requires_researcher_audit"] is True, "disagreement audit drifted")
    _require(
        audit["fixed_unanimous_audit_case_count"]
        == audit["fixed_unanimous_audit_answerable_count"]
        + audit["fixed_unanimous_audit_boundary_count"]
        == 20,
        "fixed researcher audit sample drifted",
    )
    _require(
        audit["maximum_disagreement_cases_before_panel_failure"] == 40
        and audit["maximum_researcher_packet_case_count"] == 60,
        "researcher workload bound drifted",
    )
    _require(audit["researcher_is_independent_annotator"] is False, "researcher independence cannot be claimed")
    _require(audit["researcher_audit_complete"] is False, "researcher audit cannot be complete")

    panel_gates = instrument["panel_quality_gates"]
    _require(panel_gates["unanimous_semantic_agreement_rate_min"] == 0.8, "unanimity gate drifted")
    _require(panel_gates["action_krippendorff_alpha_min"] == 0.67, "agreement gate drifted")
    _require(panel_gates["correlated_error_caveat_required"] is True, "correlated-error caveat is required")

    _require(
        tuple(row["condition_id"] for row in instrument["conditions"]) == CONDITION_IDS,
        "condition contract drifted",
    )
    system = instrument["system_freeze"]
    _require(
        system["product_revision_bound"] is False
        and system["profile_hash_bound"] is False
        and system["reviewer_bindings_bound"] is True,
        "system reviewer binding state drifted",
    )
    binding_contract = instrument["reviewer_binding_contract"]
    binding_artifact = json.loads(REVIEWER_BINDINGS.read_text(encoding="utf-8"))
    _require(
        binding_contract["path"]
        == "research/05_evaluation/instruments/academic_factual_qa_confirmation_002_reviewer_bindings.json",
        "reviewer binding path drifted",
    )
    _require(
        binding_artifact["content_sha256"]
        == binding_contract["content_sha256"]
        == canonical_sha256(
            {
                key: value
                for key, value in binding_artifact.items()
                if key != "content_sha256"
            }
        ),
        "reviewer binding content hash drifted",
    )
    _require(
        binding_artifact["binding_id"] == binding_contract["binding_id"]
        and binding_artifact["instrument_id"] == INSTRUMENT_ID
        and binding_contract["maximum_age_hours_for_execution"] == 24,
        "reviewer binding identity or freshness window drifted",
    )
    execution_contract = binding_artifact["execution_contract"]
    _require(
        execution_contract["provider_batch_size"]
        == binding_contract["provider_batch_size"]
        == 4
        and execution_contract["maximum_provider_calls"]
        == binding_contract["maximum_provider_calls"]
        == 120
        and execution_contract["retries"] == binding_contract["retries"] == 0,
        "review execution limits drifted",
    )
    cost = binding_artifact["cost_guard"]
    _require(
        cost["conservative_peak_reservation_usd"]
        == binding_contract["conservative_peak_reservation_usd"]
        == 1.563034
        and cost["emergency_hard_stop_usd"]
        == binding_contract["emergency_hard_stop_usd"]
        == 3.0,
        "review cost guard drifted",
    )
    _require(
        binding_artifact["authorization"]
        == {
            "codex_review_authorized": True,
            "provider_review_authorized": True,
            "paid_execution_authorized": True,
            "confirmation_review_authorized": False,
        },
        "binding artifact calibration authority drifted",
    )

    analysis = instrument["analysis_plan"]
    _require(
        analysis["bootstrap_replicates"] == 10000
        and analysis["bootstrap_seed"] == 20260825,
        "bootstrap plan drifted",
    )
    _require(
        math.isclose(analysis["confirmation_zero_event_upper_bound"], zero_event_upper_bound(100), abs_tol=5e-7),
        "confirmation zero-event bound drifted",
    )
    _require(
        math.isclose(analysis["final_zero_event_upper_bound"], zero_event_upper_bound(300), abs_tol=5e-7),
        "final zero-event bound drifted",
    )

    safety = instrument["execution_safety"]
    _require(
        safety
        == {
            "source_download_authorized": False,
            "question_construction_authorized": False,
            "calibration_execution_authorized": True,
            "codex_review_authorized": True,
            "provider_review_authorized": True,
            "paid_execution_authorized": True,
            "private_source_execution_authorized": False,
            "confirmation_execution_authorized": False,
            "researcher_audit_authorized": False,
            "final_execution_authorized": False,
            "product_binding_authorized": False,
            "automatic_promotion": False,
        },
        "calibration execution authorities drifted",
    )
    build = instrument["build_checkpoint"]
    _require(
        all(
            build[key] is True
            for key in (
                "source_download_completed",
                "source_license_and_revision_validation_completed",
                "deterministic_case_construction_completed",
                "calibration_control_construction_completed",
                "blinded_packet_construction_completed",
                "reviewer_bindings_frozen",
            )
        ),
        "build checkpoint is incomplete",
    )
    _require(
        build["confirmation_case_count"] == 200
        and build["calibration_control_count"] == 40
        and build["source_section_count"] == 160,
        "build checkpoint counts drifted",
    )
    _require(
        build["provider_calls"] == 0
        and build["private_data_read"] is False
        and build["review_execution_started"] is False,
        "build-only execution boundary drifted",
    )
    progression = instrument["progression_rule"]
    _require(progression["external_human_ground_truth_may_be_claimed"] is False, "human ground truth claim must remain false")
    _require(progression["failed_confirmation_tuning_permitted"] is False, "confirmation tuning must remain prohibited")
    _require(progression["final_tranche_automatic"] is False, "final tranche cannot be automatic")

    decision_log = DECISION_LOG.read_text(encoding="utf-8")
    _require(all(decision_id in decision_log for decision_id in DECISION_IDS), "decision log is incomplete")
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    source = instrument["source_contract"]
    panel = instrument["reviewer_panel_contract"]
    calibration = instrument["reviewer_calibration_contract"]
    audit = instrument["consensus_and_researcher_audit"]
    system = instrument["system_freeze"]
    safety = instrument["execution_safety"]
    blockers: list[str] = []
    if not source["source_manifest_bound"]:
        blockers.append("source-manifest-not-bound")
    if not all(row["binding_fresh"] for row in panel["reviewers"]):
        blockers.append("reviewer-bindings-not-fresh")
    if not calibration["calibration_controls_sealed"]:
        blockers.append("calibration-controls-not-sealed")
    if not system["reviewer_bindings_bound"]:
        blockers.append("reviewer-bindings-not-frozen")
    if panel["reviewers"][0]["runtime_identity_verification_pending"]:
        blockers.append("codex-isolated-runtime-not-verified")
    if not safety["calibration_execution_authorized"]:
        blockers.append("calibration-execution-authorized-false")
    if not safety["codex_review_authorized"]:
        blockers.append("codex-review-authorized-false")
    if not safety["provider_review_authorized"]:
        blockers.append("provider-review-authorized-false")
    if not safety["paid_execution_authorized"]:
        blockers.append("paid-execution-authorized-false")
    if audit["researcher_audit_complete"]:
        blockers.append("unexpected-researcher-audit-state")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "blocked-build-only" if blockers else "ready",
        "blockers": blockers,
        "planned_case_count": 200,
        "planned_cluster_count": 100,
        "planned_reviewer_count": 3,
        "planned_reviewer_judgments": 600,
        "planned_calibration_judgments": 120,
        "maximum_provider_calls": 120,
        "conservative_peak_reservation_usd": 1.563034,
        "emergency_hard_stop_usd": 3.0,
        "maximum_researcher_packet_case_count": 60,
        "provider_calls": 0,
        "private_data_read": False,
        "source_manifest_opened": True,
        "reviewer_outputs_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    instrument = validate_instrument()
    result = (
        {
            "instrument_id": INSTRUMENT_ID,
            "status": "validated-calibration-authorized-confirmation-unauthorized",
        }
        if args.validate
        else preflight(instrument)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
