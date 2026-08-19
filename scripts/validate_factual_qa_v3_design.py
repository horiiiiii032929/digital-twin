#!/usr/bin/env python3
"""Validate the frozen, no-model factual-QA v3 design boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/factual_qa_v3_design_001.json"
)

SOURCE_ROLES = {
    "authoritative_evidence",
    "supporting_context",
    "question_inspiration_only",
    "excluded_integrity_or_privacy",
    "excluded_duplicate_generated_tool_state",
    "review_or_conversion_required",
}
MANDATORY_EXCLUSIONS = {
    "solutions_and_answer_keys",
    "completed_or_graded_assessments",
    "student_or_participant_data",
    "credentials_and_secrets",
    "unrelated_content",
}
MUTATIONS = {
    "wrong_numeric_value",
    "reversed_comparison",
    "omitted_table_row",
    "wrong_diagram_edge",
    "changed_equation_symbol",
    "unsupported_claim",
    "wrong_citation",
    "incomplete_multi_source_evidence",
    "cross_course_confusion",
    "wrong_answer_vs_abstain",
    "over_refusal",
}
FAILURE_ROUTES = {
    "source_governance",
    "conversion_or_ocr",
    "chunking_or_evidence_units",
    "retrieval",
    "evidence_sufficiency",
    "generation",
    "citation_binding",
    "safety_policy",
    "integration",
    "operations",
}
NO_MODEL_GATES = {
    "complete_source_disposition",
    "mandatory_exclusion_and_path_sanitization",
    "conversion_lineage_and_checksum_stability",
    "oracle_control_mechanics",
    "response_schema",
    "exact_quote_and_citation_target",
    "content_deduplication_with_path_lineage",
    "mutation_sensitivity",
    "sanitized_human_audit_rendering",
}
AUDIT_FIELDS = {
    "original_page_or_crop",
    "extracted_text",
    "source_id",
    "page_and_region",
    "source_version_and_checksum",
    "requested_action",
    "atomic_claims",
    "exact_evidence_quotes",
    "deterministic_checks",
    "reviewer_disagreements",
    "mutation_outcomes",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError as error:
        raise ValueError(f"missing v3 design instrument: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid v3 design JSON: {error}") from error
    require(isinstance(payload, dict), "v3 design must be a JSON object")
    return payload


def validate_instrument(payload: dict[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == 1, "schema_version must be 1")
    require(
        payload.get("instrument_id") == "factual-qa-v3-design-001",
        "unexpected instrument_id",
    )
    require(
        payload.get("status") == "frozen-no-model-implementation",
        "design must remain frozen for no-model implementation",
    )
    require(payload.get("model_leaderboard") is False, "leaderboard framing prohibited")

    inventory = payload["source_inventory"]
    require(
        inventory.get("canonical_root") == "Documents/academia_vault",
        "canonical Academia Vault root changed",
    )
    require(
        inventory.get("prohibited_root") == "Downloads/academia_vault",
        "partial Downloads copy must remain prohibited",
    )
    require(
        inventory.get("all_regular_files_require_disposition") is True,
        "every regular source file requires a disposition",
    )
    require(inventory.get("contains_private_paths") is False, "private paths prohibited")
    require(inventory.get("contains_source_content") is False, "source content prohibited")
    counts = inventory["eligibility_counts"]
    require(sum(counts.values()) == inventory["regular_file_count"], "inventory counts do not sum")

    require(set(payload["source_roles"]) == SOURCE_ROLES, "source-role set is incomplete")
    require(
        set(payload["mandatory_exclusions"]) == MANDATORY_EXCLUSIONS,
        "mandatory exclusions changed",
    )
    notes = payload["personal_notes"]
    require(notes["default_role"] == "question_inspiration_only", "personal-note role changed")
    require(
        notes["authoritative_without_official_verification"] is False,
        "personal notes cannot establish authoritative evidence alone",
    )
    dedup = payload["deduplication"]
    require(dedup["process_unique_content_once"] is True, "content deduplication required")
    require(dedup["preserve_all_path_lineage"] is True, "duplicate path lineage required")

    lanes = payload["lanes"]
    require(
        lanes["primary"]["corpus"] == "all_eligible_academia_vault_files",
        "primary corpus must cover all eligible vault files",
    )
    require(
        lanes["primary"]["gold_evidence_injected_into_retrieval"] is False,
        "gold evidence cannot be injected into product retrieval",
    )
    require(
        lanes["oracle_control"]["hidden_structured_fact_manifest"] is True,
        "oracle control requires a hidden structured fact manifest",
    )
    require(
        lanes["oracle_control"]["may_establish_real_course_quality"] is False,
        "dummy control cannot establish real-course quality",
    )

    response = payload["response_contract"]
    require(set(response["actions"]) == {"answer", "clarify", "abstain", "refuse"}, "safe actions changed")
    require(response["atomic_claims_required"] is True, "atomic claims required")
    require(response["exact_quotes_required"] is True, "exact quotes required")
    require(set(response["claim_required_fields"]) == {"text", "evidence"}, "claim contract changed")
    require(set(response["evidence_required_fields"]) == {"citation_id", "quote"}, "evidence contract changed")

    require(set(payload["mutation_classes"]) == MUTATIONS, "mutation coverage changed")
    require(set(payload["failure_routes"]) == FAILURE_ROUTES, "failure routing changed")
    require(set(payload["no_model_gates"]) == NO_MODEL_GATES, "no-model gates changed")
    require(
        set(payload["human_audit_required_fields"]) == AUDIT_FIELDS,
        "audit packet contract is incomplete",
    )

    policy = payload["model_policy"]
    require(policy["external_execution_authorized"] is False, "external execution is not authorized")
    require(policy["paid_calls_allowed"] is False, "paid calls are not authorized")
    require(policy["scale_authorized"] is False, "scale is not authorized")
    require(policy["separate_provider_record_required"] is True, "provider record gate required")
    require(set(policy["prohibited_families"]) == {"gemma", "claude", "retired_local_general_qwen"}, "prohibited model policy changed")

    return {
        "instrument_id": payload["instrument_id"],
        "status": "passed",
        "regular_file_count": inventory["regular_file_count"],
        "source_roles": len(payload["source_roles"]),
        "no_model_gates": len(payload["no_model_gates"]),
        "external_execution_authorized": False,
    }


def main() -> int:
    print(json.dumps(validate_instrument(load_instrument()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
