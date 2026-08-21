#!/usr/bin/env python3
"""Prepare and validate the provider-unauthorized v2 independent review packet."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.build_evidence_sufficiency_v2_decision_draft import (
    load_and_validate_draft,
)
from src.digital_twin.repository_freeze import (
    require_pre_evaluation_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/evidence_sufficiency_v2_independent_review_001.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "reports/generated/evidence-sufficiency-v2-independent-review-packet-001.json"
)
INSTRUMENT_ID = "evidence-sufficiency-v2-independent-review-001"
PACKET_ID = "evidence-sufficiency-v2-independent-review-packet-001"
VERDICTS = {"approve", "revise", "escalate"}
RESPONSE_FIELDS = {
    "item_id",
    "verdict",
    "failed_dimensions",
    "reason",
    "suggested_correction",
}
DEFECT_CLASSES = {
    "fabricated-evidence-quote",
    "missing-required-evidence",
    "stale-source-version",
    "wrong-action",
    "wrong-claim-statement",
    "wrong-course-lineage",
}


class IndependentReviewError(ValueError):
    """Raised when the review workflow no longer matches its frozen contract."""


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise IndependentReviewError("unexpected independent-review instrument ID")
    if instrument.get("status") != "build-only-provider-unauthorized":
        raise IndependentReviewError("independent-review build status drifted")
    dataset = instrument.get("decision_dataset", {})
    if (
        dataset.get("dataset_id") != "evidence-sufficiency-v2-decision-draft-001"
        or dataset.get("case_count") != 120
        or dataset.get("opened_for_candidate_evaluation") is not False
        or dataset.get("frozen") is not False
    ):
        raise IndependentReviewError("decision-dataset review boundary drifted")
    safety = instrument.get("execution_safety", {})
    required_false = {
        "provider_execution_authorized",
        "fallback_routing_allowed",
        "private_source_execution_authorized",
        "candidate_evaluation_authorized",
        "automatic_dataset_freeze",
        "automatic_ground_truth_mutation",
        "gemma_allowed",
        "claude_allowed",
    }
    if any(safety.get(key) is not False for key in required_false):
        raise IndependentReviewError("independent-review execution safety drifted")
    if (
        safety.get("reviewer_provider") is not None
        or safety.get("reviewer_model") is not None
        or safety.get("reviewer_verified_at") is not None
        or safety.get("retries") != 0
        or safety.get("maximum_calls") != 13
        or safety.get("maximum_cost_usd") is not None
    ):
        raise IndependentReviewError("reviewer binding must remain absent")
    decision_rule = instrument.get("decision_rule", {})
    if any(
        decision_rule.get(key) is not False
        for key in (
            "authorize_provider_execution",
            "authorize_dataset_freeze",
            "authorize_candidate_evaluation",
        )
    ):
        raise IndependentReviewError("review instrument cannot self-authorize")
    required_response_fields = set(
        instrument.get("review_contract", {}).get("required_response_fields", [])
    )
    if required_response_fields != RESPONSE_FIELDS:
        raise IndependentReviewError("review response contract drifted")
    if instrument.get("quality_gates") != {
        "response_contract_valid_rate_min": 1.0,
        "sensitivity_clean_specificity_min": 1.0,
        "sensitivity_defect_detection_min": 1.0,
        "review_case_coverage_min": 1.0,
        "unresolved_case_count_max": 0,
        "unreviewed_case_count_max": 0,
        "duplicate_judgment_count_max": 0,
        "ground_truth_override_count_max": 0,
        "priority_packet_count_max": 12,
    }:
        raise IndependentReviewError("independent-review quality gates drifted")
    return instrument


def _review_item(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": case["case_id"],
        "course_id": case["course_id"],
        "question": case["question"],
        "proposed_action": case["expected_action"],
        "proposed_required_claims": copy.deepcopy(case["required_claims"]),
        "proposed_evidence": copy.deepcopy(case["evidence"]),
        "proposed_boundary_reason": case["boundary_reason"],
        "tempting_source_ids": copy.deepcopy(case["tempting_source_ids"]),
    }


def _mutation_items(
    case_map: dict[str, dict[str, Any]],
    source_map: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    clean_case_ids = (
        "esv2-direct-01",
        "esv2-multi-01",
        "esv2-permission-01",
        "esv2-multimodal-01",
        "esv2-near-abstain-01",
        "esv2-cross-01",
    )
    items: list[dict[str, Any]] = []
    scoring_key: dict[str, dict[str, str]] = {}
    for index, case_id in enumerate(clean_case_ids, start=1):
        item = _review_item(case_map[case_id])
        item["item_id"] = f"esv2-review-clean-{index:02d}"
        item["base_case_id"] = case_id
        items.append(item)
        scoring_key[item["item_id"]] = {
            "expected_verdict": "approve",
            "defect_class": "clean-control",
        }

    wrong_action = _review_item(case_map["esv2-direct-02"])
    wrong_action.update(
        {
            "item_id": "esv2-review-defect-01",
            "base_case_id": "esv2-direct-02",
            "proposed_action": "abstain",
            "proposed_required_claims": [],
            "proposed_evidence": [],
            "proposed_boundary_reason": "no-approved-evidence",
        }
    )

    missing = _review_item(case_map["esv2-multi-02"])
    missing.update(
        {
            "item_id": "esv2-review-defect-02",
            "base_case_id": "esv2-multi-02",
            "proposed_evidence": missing["proposed_evidence"][:1],
        }
    )

    stale = _review_item(case_map["esv2-permission-02"])
    active_source = source_map[stale["proposed_evidence"][0]["source_unit_id"]]
    stale_source = next(
        source
        for source in source_map.values()
        if source["logical_source_id"] == active_source["logical_source_id"]
        and not source["active"]
    )
    stale["item_id"] = "esv2-review-defect-03"
    stale["base_case_id"] = "esv2-permission-02"
    stale["proposed_evidence"][0]["source_unit_id"] = stale_source[
        "source_unit_id"
    ]
    stale["proposed_evidence"][0]["quote"] = stale_source["content"]

    wrong_course = _review_item(case_map["esv2-direct-03"])
    foreign_source = next(
        source
        for source in source_map.values()
        if source["active"]
        and source["course_id"] != wrong_course["course_id"]
        and source["claims"]
    )
    wrong_course["item_id"] = "esv2-review-defect-04"
    wrong_course["base_case_id"] = "esv2-direct-03"
    wrong_course["proposed_evidence"][0] = {
        "source_unit_id": foreign_source["source_unit_id"],
        "claim_id": foreign_source["claims"][0]["claim_id"],
        "quote": foreign_source["claims"][0]["evidence_quote"],
    }

    fabricated = _review_item(case_map["esv2-multimodal-02"])
    fabricated["item_id"] = "esv2-review-defect-05"
    fabricated["base_case_id"] = "esv2-multimodal-02"
    fabricated["proposed_evidence"][0]["quote"] += " Fabricated extension."

    wrong_claim = _review_item(case_map["esv2-paraphrase-02"])
    wrong_claim["item_id"] = "esv2-review-defect-06"
    wrong_claim["base_case_id"] = "esv2-paraphrase-02"
    wrong_claim["proposed_required_claims"][0]["statement"] = (
        "The opposite rule applies under the approved source."
    )

    defects = (
        (wrong_action, "wrong-action"),
        (missing, "missing-required-evidence"),
        (stale, "stale-source-version"),
        (wrong_course, "wrong-course-lineage"),
        (fabricated, "fabricated-evidence-quote"),
        (wrong_claim, "wrong-claim-statement"),
    )
    for item, defect_class in defects:
        items.append(item)
        scoring_key[item["item_id"]] = {
            "expected_verdict": "revise",
            "defect_class": defect_class,
        }
    return items, scoring_key


def build_review_packet(
    instrument: dict[str, Any] | None = None,
) -> dict[str, Any]:
    instrument = instrument or load_instrument()
    dataset_path = ROOT / instrument["decision_dataset"]["path"]
    draft_summary = load_and_validate_draft(dataset_path)
    if draft_summary["content_sha256"] != instrument["decision_dataset"][
        "content_sha256"
    ]:
        raise IndependentReviewError("decision draft hash drifted")
    draft = json.loads(dataset_path.read_text(encoding="utf-8"))
    source_map = {source["source_unit_id"]: source for source in draft["sources"]}
    case_map = {case["case_id"]: case for case in draft["cases"]}
    review_items = [_review_item(case) for case in draft["cases"]]
    batch_size = instrument["review_packet"]["batch_size"]
    batches = [
        {
            "batch_id": f"esv2-review-batch-{index // batch_size + 1:02d}",
            "items": review_items[index : index + batch_size],
        }
        for index in range(0, len(review_items), batch_size)
    ]
    sensitivity_items, scoring_key = _mutation_items(case_map, source_map)
    core = {
        "schema_version": 1,
        "packet_id": PACKET_ID,
        "instrument_id": INSTRUMENT_ID,
        "dataset_id": draft["dataset_id"],
        "dataset_content_sha256": draft["content_sha256"],
        "status": "build-only-provider-unauthorized",
        "provider_or_model_calls": 0,
        "private_data_read": False,
        "candidate_evaluation_opened": False,
        "source_catalog": copy.deepcopy(draft["sources"]),
        "sensitivity_items": sensitivity_items,
        "sensitivity_scoring_key": scoring_key,
        "review_batches": batches,
        "response_contract": copy.deepcopy(instrument["review_contract"]),
    }
    return {**core, "content_sha256": _canonical_sha256(core)}


def validate_review_packet(
    packet: dict[str, Any],
    instrument: dict[str, Any] | None = None,
) -> dict[str, Any]:
    instrument = instrument or load_instrument()
    content_sha256 = packet.get("content_sha256")
    core = {key: value for key, value in packet.items() if key != "content_sha256"}
    if content_sha256 != _canonical_sha256(core):
        raise IndependentReviewError("review packet content hash drifted")
    expected_hash = instrument["review_packet"]["expected_content_sha256"]
    if content_sha256 != expected_hash:
        raise IndependentReviewError("review packet instrument binding drifted")
    if (
        packet.get("packet_id") != PACKET_ID
        or packet.get("provider_or_model_calls") != 0
        or packet.get("private_data_read") is not False
        or packet.get("candidate_evaluation_opened") is not False
    ):
        raise IndependentReviewError("review packet data boundary drifted")

    draft_path = ROOT / instrument["decision_dataset"]["path"]
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    source_map = {source["source_unit_id"]: source for source in packet["source_catalog"]}
    if packet["source_catalog"] != draft["sources"] or len(source_map) != 40:
        raise IndependentReviewError("review source catalog drifted")
    expected_items = {case["case_id"]: _review_item(case) for case in draft["cases"]}
    review_items = [
        item for batch in packet["review_batches"] for item in batch["items"]
    ]
    if (
        len(packet["review_batches"]) != 12
        or any(len(batch["items"]) != 10 for batch in packet["review_batches"])
        or len(review_items) != 120
        or len({item["item_id"] for item in review_items}) != 120
    ):
        raise IndependentReviewError("review batch grain drifted")
    if any(expected_items.get(item["item_id"]) != item for item in review_items):
        raise IndependentReviewError("review item changed authoritative draft truth")

    sensitivity_items = packet["sensitivity_items"]
    scoring_key = packet["sensitivity_scoring_key"]
    if (
        len(sensitivity_items) != 12
        or len(scoring_key) != 12
        or set(scoring_key) != {item["item_id"] for item in sensitivity_items}
    ):
        raise IndependentReviewError("sensitivity packet grain drifted")
    counts = Counter(value["expected_verdict"] for value in scoring_key.values())
    defect_classes = {
        value["defect_class"]
        for value in scoring_key.values()
        if value["expected_verdict"] == "revise"
    }
    if counts != Counter({"approve": 6, "revise": 6}) or defect_classes != DEFECT_CLASSES:
        raise IndependentReviewError("sensitivity scoring key drifted")
    if any(
        "expected_verdict" in item or "defect_class" in item
        for item in sensitivity_items
    ):
        raise IndependentReviewError("sensitivity answer leaked into reviewer payload")
    return {
        "instrument_id": INSTRUMENT_ID,
        "packet_id": PACKET_ID,
        "content_sha256": content_sha256,
        "source_count": len(source_map),
        "review_case_count": len(review_items),
        "review_batch_count": len(packet["review_batches"]),
        "sensitivity_clean_count": counts["approve"],
        "sensitivity_defect_count": counts["revise"],
        "provider_or_model_calls": 0,
        "private_data_read": False,
        "candidate_evaluation_opened": False,
        "status": "validated-build-only",
    }


def validate_judgments(
    packet: dict[str, Any],
    judgments: list[dict[str, Any]],
    *,
    simulation: bool,
) -> dict[str, Any]:
    instrument = load_instrument()
    validate_review_packet(packet, instrument)
    expected_ids = {
        item["item_id"]
        for batch in packet["review_batches"]
        for item in batch["items"]
    } | {item["item_id"] for item in packet["sensitivity_items"]}
    seen: set[str] = set()
    invalid_count = 0
    duplicate_count = 0
    invalid_item_ids: set[str] = set()
    allowed_dimensions = set(instrument["review_contract"]["dimensions"])
    for judgment in judgments:
        if not isinstance(judgment, dict):
            invalid_count += 1
            continue
        item_id = judgment.get("item_id")
        verdict = judgment.get("verdict")
        failed_dimensions = judgment.get("failed_dimensions")
        reason = judgment.get("reason")
        correction = judgment.get("suggested_correction")
        if item_id in seen:
            duplicate_count += 1
            continue
        seen.add(item_id)
        if (
            set(judgment) != RESPONSE_FIELDS
            or item_id not in expected_ids
            or verdict not in VERDICTS
            or not isinstance(failed_dimensions, list)
            or any(
                not isinstance(value, str)
                or value not in allowed_dimensions
                for value in failed_dimensions
            )
            or len(failed_dimensions) != len(set(failed_dimensions))
            or not isinstance(reason, str)
            or len(reason.strip()) < instrument["review_contract"][
                "reason_minimum_characters"
            ]
            or not isinstance(correction, str)
            or (verdict == "revise" and not correction.strip())
            or (verdict == "approve" and failed_dimensions)
        ):
            invalid_count += 1
            if item_id in expected_ids:
                invalid_item_ids.add(item_id)
    missing = expected_ids - seen
    scoring_key = packet["sensitivity_scoring_key"]
    sensitivity = {
        judgment.get("item_id"): judgment.get("verdict")
        for judgment in judgments
        if judgment.get("item_id") in scoring_key
    }
    clean_correct = sum(
        sensitivity.get(item_id) == "approve"
        for item_id, key in scoring_key.items()
        if key["expected_verdict"] == "approve"
    )
    defects_correct = sum(
        sensitivity.get(item_id) in {"revise", "escalate"}
        for item_id, key in scoring_key.items()
        if key["expected_verdict"] == "revise"
    )
    review_case_ids = expected_ids - set(scoring_key)
    review_judgments = [
        judgment
        for judgment in judgments
        if judgment.get("item_id") in review_case_ids
    ]
    unresolved = [
        judgment.get("item_id")
        for judgment in review_judgments
        if judgment.get("verdict") != "approve"
    ]
    priority_candidates = list(
        dict.fromkeys(
            unresolved
            + sorted(missing & review_case_ids)
            + sorted(invalid_item_ids & review_case_ids)
        )
    )
    priority_limit = instrument["quality_gates"]["priority_packet_count_max"]
    priority_case_ids = priority_candidates[:priority_limit]
    gates = {
        "response_contract_valid": (
            invalid_count == 0 and duplicate_count == 0 and not missing
        ),
        "clean_specificity": clean_correct == 6,
        "defect_detection": defects_correct == 6,
        "review_coverage": len(review_judgments) == 120,
        "unresolved_clear": not unresolved,
    }
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "simulation-passed-not-evidence"
            if simulation and all(gates.values())
            else "simulation-refine-not-evidence"
            if simulation
            else "review-complete" if all(gates.values()) else "review-refine"
        ),
        "judgment_count": len(judgments),
        "invalid_judgment_count": invalid_count,
        "duplicate_judgment_count": duplicate_count,
        "missing_judgment_count": len(missing),
        "clean_specificity": clean_correct / 6,
        "defect_detection": defects_correct / 6,
        "review_case_coverage": len(review_judgments) / 120,
        "unresolved_case_ids": unresolved,
        "priority_case_ids": priority_case_ids,
        "priority_packet_truncated": len(priority_candidates) > priority_limit,
        "gates": gates,
        "simulation": simulation,
        "provider_or_model_calls": 0 if simulation else None,
        "freeze_eligible": False,
    }


def simulated_judgments(packet: dict[str, Any]) -> list[dict[str, Any]]:
    scoring_key = packet["sensitivity_scoring_key"]
    item_ids = [
        item["item_id"] for item in packet["sensitivity_items"]
    ] + [
        item["item_id"]
        for batch in packet["review_batches"]
        for item in batch["items"]
    ]
    return [
        {
            "item_id": item_id,
            "verdict": scoring_key.get(item_id, {}).get("expected_verdict", "approve"),
            "failed_dimensions": (
                []
                if scoring_key.get(item_id, {}).get("expected_verdict", "approve")
                == "approve"
                else ["claim-support"]
            ),
            "reason": "Network-free synthetic response used only to verify orchestration.",
            "suggested_correction": (
                "Restore the deterministic source-linked proposal."
                if scoring_key.get(item_id, {}).get("expected_verdict") == "revise"
                else ""
            ),
        }
        for item_id in item_ids
    ]


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    safety = instrument["execution_safety"]
    blockers = []
    if safety["reviewer_model"] is None:
        blockers.append("independent-reviewer-not-bound")
    if safety["reviewer_verified_at"] is None:
        blockers.append("reviewer-metadata-not-fresh")
    if safety["maximum_cost_usd"] is None:
        blockers.append("review-cost-ceiling-not-frozen")
    if not safety["provider_execution_authorized"]:
        blockers.append("provider-review-not-authorized")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "blocked-not-authorized" if blockers else "ready",
        "blockers": blockers,
        "provider_or_model_calls": 0,
        "private_data_read": False,
        "candidate_evaluation_opened": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    if arguments.write:
        require_pre_evaluation_operation_allowed("dataset_generation")
    instrument = load_instrument()
    packet = build_review_packet(instrument)
    summary = validate_review_packet(packet, instrument)
    if arguments.preflight:
        payload = preflight(instrument)
    elif arguments.simulate:
        payload = validate_judgments(
            packet,
            simulated_judgments(packet),
            simulation=True,
        )
    else:
        payload = summary
    if arguments.write:
        if arguments.output.exists():
            raise IndependentReviewError(
                f"refusing to overwrite existing output: {arguments.output}"
            )
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(packet, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
