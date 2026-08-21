#!/usr/bin/env python3
"""Validate the build-only evidence-sufficiency v2 release boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.build_evidence_sufficiency_v2_decision_draft import (
    DecisionDraftError,
    load_and_validate_draft,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = (
    ROOT / "research/05_evaluation/instruments/evidence_sufficiency_v2.json"
)
INSTRUMENT_ID = "evidence-sufficiency-v2-build-001"


class EvidenceSufficiencyV2ValidationError(ValueError):
    """Raised when the prospective release-gate contract drifts."""


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    try:
        instrument = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceSufficiencyV2ValidationError(
            f"cannot load v2 instrument: {path}"
        ) from error

    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise EvidenceSufficiencyV2ValidationError("unexpected instrument ID")
    if instrument.get("status") != "build-only-dataset-review-pending":
        raise EvidenceSufficiencyV2ValidationError("build-only status drifted")
    if instrument.get("model_leaderboard") is not False:
        raise EvidenceSufficiencyV2ValidationError(
            "evidence sufficiency cannot become a model leaderboard"
        )

    ownership = instrument.get("boundary_ownership", {})
    if ownership.get("owned_actions") != ["answer", "abstain"]:
        raise EvidenceSufficiencyV2ValidationError("answerability ownership drifted")
    if ownership.get("academic_integrity_is_answerability_label") is not False:
        raise EvidenceSufficiencyV2ValidationError(
            "academic integrity must remain a separate policy boundary"
        )

    development = instrument.get("historical_development_data", {})
    sources = development.get("sources", [])
    if development.get("case_count") != 80 or sum(
        int(source.get("case_count", 0)) for source in sources
    ) != 80:
        raise EvidenceSufficiencyV2ValidationError(
            "historical development count drifted"
        )
    if development.get("selection_eligible") is not False:
        raise EvidenceSufficiencyV2ValidationError(
            "consumed v1 data cannot select v2"
        )
    for source in sources:
        source_path = ROOT / str(source.get("path", ""))
        if not source_path.is_file():
            raise EvidenceSufficiencyV2ValidationError(
                f"missing development source: {source_path}"
            )
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        if len(payload.get("cases", [])) != source.get("case_count"):
            raise EvidenceSufficiencyV2ValidationError(
                f"development source count drifted: {source_path}"
            )

    decision = instrument.get("prospective_decision_dataset", {})
    action_counts = decision.get("action_counts", {})
    slice_counts = decision.get("slice_counts", {})
    if decision.get("case_count") != 120:
        raise EvidenceSufficiencyV2ValidationError("decision case count drifted")
    if action_counts != {"answer": 80, "abstain": 40}:
        raise EvidenceSufficiencyV2ValidationError("decision action counts drifted")
    if sum(slice_counts.values()) != 120:
        raise EvidenceSufficiencyV2ValidationError("decision slices do not sum to 120")
    decision_path_value = decision.get("path")
    if not isinstance(decision_path_value, str) or not decision_path_value:
        raise EvidenceSufficiencyV2ValidationError(
            "decision draft path is required during review-pending work"
        )
    try:
        draft_summary = load_and_validate_draft(ROOT / decision_path_value)
    except (OSError, json.JSONDecodeError, DecisionDraftError) as error:
        raise EvidenceSufficiencyV2ValidationError(
            "decision draft failed deterministic validation"
        ) from error
    if (
        draft_summary.get("dataset_id") != decision.get("dataset_id")
        or draft_summary.get("content_sha256") != decision.get("content_sha256")
        or draft_summary.get("case_count") != decision.get("case_count")
        or draft_summary.get("action_counts") != action_counts
        or draft_summary.get("slice_counts") != slice_counts
    ):
        raise EvidenceSufficiencyV2ValidationError(
            "decision draft binding drifted"
        )
    if decision.get("frozen") is not False:
        raise EvidenceSufficiencyV2ValidationError(
            "decision draft cannot be frozen before independent review"
        )
    if (
        decision.get("status") != "draft-pending-independent-review"
        or decision.get("structural_validation") != "passed"
        or decision.get("independent_advisory_review") != "pending"
        or decision.get("human_priority_review") != "pending"
    ):
        raise EvidenceSufficiencyV2ValidationError("decision review state drifted")
    if decision.get("opened") is not False:
        raise EvidenceSufficiencyV2ValidationError("decision split was opened")

    candidates = instrument.get("candidate_families", [])
    controls = [candidate for candidate in candidates if candidate.get("id") == "any-hit-control"]
    if len(controls) != 1 or controls[0].get("selectable") is not False:
        raise EvidenceSufficiencyV2ValidationError("AnyHit became selectable")

    runtime = instrument.get("runtime_contract", {})
    required_runtime = {
        "verifier_owns_final_decision": False,
        "unknown_hit_id_fails_closed": True,
        "malformed_output_fails_closed": True,
        "verifier_error_fails_closed": True,
        "original_evidence_remains_authoritative": True,
    }
    if any(runtime.get(key) is not value for key, value in required_runtime.items()):
        raise EvidenceSufficiencyV2ValidationError("runtime fail-closed contract drifted")

    freshness = instrument.get("freshness_policy", {})
    if (
        freshness.get("metadata_max_age_hours") != 24
        or freshness.get("selected_provider") is not None
        or freshness.get("selected_model") is not None
        or freshness.get("verified_at") is not None
        or freshness.get("fallback_routing_allowed") is not False
    ):
        raise EvidenceSufficiencyV2ValidationError("freshness boundary drifted")

    safety = instrument.get("execution_safety", {})
    required_false = {
        "provider_execution_authorized",
        "calibration_execution_authorized",
        "decision_split_execution_authorized",
        "private_source_execution_authorized",
        "automatic_selection",
        "automatic_release_promotion",
        "gemma_allowed",
        "claude_allowed",
    }
    if any(safety.get(key) is not False for key in required_false):
        raise EvidenceSufficiencyV2ValidationError("execution safety drifted")

    if instrument.get("decision_rule", {}).get("authorize_release") is not False:
        raise EvidenceSufficiencyV2ValidationError("instrument cannot authorize release")
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    decision = instrument["prospective_decision_dataset"]
    blockers: list[str] = []
    if decision["path"] is None or not decision["frozen"]:
        blockers.append("decision-dataset-not-frozen")
    freshness = instrument["freshness_policy"]
    if freshness["selected_model"] is None:
        blockers.append("candidate-model-not-bound")
    safety = instrument["execution_safety"]
    if not safety["calibration_execution_authorized"]:
        blockers.append("calibration-not-authorized")
    if not safety["decision_split_execution_authorized"]:
        blockers.append("decision-split-not-authorized")
    return {
        "instrument_id": instrument["instrument_id"],
        "status": "blocked-dataset-not-frozen" if blockers else "ready",
        "provider_calls": 0,
        "private_data_read": False,
        "decision_split_opened": False,
        "blockers": blockers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    parser.add_argument("--preflight", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    instrument = validate_instrument(arguments.instrument)
    payload = (
        preflight(instrument)
        if arguments.preflight
        else {
            "instrument_id": instrument["instrument_id"],
            "status": "validated-build-only",
            "historical_development_case_count": instrument[
                "historical_development_data"
            ]["case_count"],
            "prospective_decision_case_count": instrument[
                "prospective_decision_dataset"
            ]["case_count"],
            "provider_calls": 0,
            "private_data_read": False,
            "decision_split_opened": False,
        }
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
