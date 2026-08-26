#!/usr/bin/env python3
"""Validate and simulate the confirmation-002 LLM panel review.

Paid/provider execution is intentionally absent from this build-only runner.
The module implements strict vote parsing, calibration, agreement analysis,
bounded researcher-packet construction, and atomic resumable accounting so the
execution checkpoint can be frozen without changing analysis semantics.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.build_academic_factual_qa_confirmation_v2 import (
    CASES_PATH,
    CONTROLS_PATH,
    canonical_sha256,
)
from scripts.prepare_academic_factual_qa_panel_review_v2 import (
    PACKET_PATH,
    validate_packet,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/academic_factual_qa_confirmation_002.json"
)
REVIEWER_IDS = (
    "codex-isolated-task-blinded-reviewer",
    "mistral-small-4-blinded-reviewer",
    "deepseek-v4-pro-blinded-reviewer",
)
GEMINI_REVIEWER_IDS = (
    "codex-isolated-task-blinded-reviewer",
    "gemini-3.7-flash-blinded-reviewer",
    "deepseek-v4-pro-blinded-reviewer",
)
TWO_REVIEWER_IDS = (
    "codex-isolated-task-blinded-reviewer",
    "gemini-3.7-flash-blinded-reviewer",
)
VALID_REVIEWER_IDS = (
    frozenset(REVIEWER_IDS)
    | frozenset(GEMINI_REVIEWER_IDS)
    | frozenset(TWO_REVIEWER_IDS)
)
VALID_ACTIONS = {"answer", "abstain", "clarify", "refuse"}
VALID_CLAIM_SUPPORT = {
    "fully-supported",
    "partially-supported",
    "unsupported",
    "not-applicable",
}
VALID_CITATION_SUPPORT = {"complete-valid", "incomplete", "invalid", "not-applicable"}
REQUIRED_VOTE_KEYS = {
    "review_item_id",
    "case_semantically_valid",
    "expected_action",
    "question_answerable_from_supplied_sources",
    "atomic_claim_support",
    "citation_support",
    "boundary_reason",
    "ambiguity_detected",
    "evidence_ids",
    "defect_types",
    "concise_rationale",
}


class PanelReviewError(ValueError):
    """Raised when a reviewer run or checkpoint violates the frozen contract."""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_vote(vote: dict[str, Any], *, expected_item_id: str) -> dict[str, Any]:
    if set(vote) != REQUIRED_VOTE_KEYS:
        raise PanelReviewError(
            f"vote keys drifted for {expected_item_id}: {sorted(set(vote) ^ REQUIRED_VOTE_KEYS)}"
        )
    if vote["review_item_id"] != expected_item_id:
        raise PanelReviewError("review item identity drifted")
    if not isinstance(vote["case_semantically_valid"], bool):
        raise PanelReviewError("semantic-validity vote must be boolean")
    if vote["expected_action"] not in VALID_ACTIONS:
        raise PanelReviewError("invalid expected action")
    if not isinstance(vote["question_answerable_from_supplied_sources"], bool):
        raise PanelReviewError("answerability vote must be boolean")
    if vote["atomic_claim_support"] not in VALID_CLAIM_SUPPORT:
        raise PanelReviewError("invalid claim-support vote")
    if vote["citation_support"] not in VALID_CITATION_SUPPORT:
        raise PanelReviewError("invalid citation-support vote")
    if vote["boundary_reason"] is not None and not isinstance(vote["boundary_reason"], str):
        raise PanelReviewError("boundary reason must be string or null")
    if not isinstance(vote["ambiguity_detected"], bool):
        raise PanelReviewError("ambiguity vote must be boolean")
    if not isinstance(vote["evidence_ids"], list) or not all(
        isinstance(value, str) for value in vote["evidence_ids"]
    ):
        raise PanelReviewError("evidence IDs must be a string list")
    if len(vote["evidence_ids"]) != len(set(vote["evidence_ids"])):
        raise PanelReviewError("evidence IDs must be unique")
    if not isinstance(vote["defect_types"], list) or not all(
        isinstance(value, str) for value in vote["defect_types"]
    ):
        raise PanelReviewError("defect types must be a string list")
    if len(vote["defect_types"]) != len(set(vote["defect_types"])):
        raise PanelReviewError("defect types must be unique")
    rationale = vote["concise_rationale"]
    if not isinstance(rationale, str) or not rationale.strip() or len(rationale.split()) > 80:
        raise PanelReviewError("rationale must contain 1-80 words")
    return vote


def initialize_ledger(
    *,
    packet_sha256: str,
    instrument_sha256: str,
    reviewer_bindings_sha256: str,
    pricing_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "running",
        "packet_sha256": packet_sha256,
        "instrument_sha256": instrument_sha256,
        "reviewer_bindings_sha256": reviewer_bindings_sha256,
        "pricing_sha256": pricing_sha256,
        "provider_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "reported_cost_usd": 0.0,
        "malformed_response_count": 0,
        "votes": [],
    }


def validate_resume(
    ledger: dict[str, Any],
    *,
    packet_sha256: str,
    instrument_sha256: str,
    reviewer_bindings_sha256: str,
    pricing_sha256: str,
) -> None:
    expected = {
        "packet_sha256": packet_sha256,
        "instrument_sha256": instrument_sha256,
        "reviewer_bindings_sha256": reviewer_bindings_sha256,
        "pricing_sha256": pricing_sha256,
    }
    for key, value in expected.items():
        if ledger.get(key) != value:
            raise PanelReviewError(f"resume binding drifted: {key}")
    identities = [
        (row["reviewer_id"], row["review_item_id"]) for row in ledger.get("votes", ())
    ]
    if len(identities) != len(set(identities)):
        raise PanelReviewError("resume ledger contains duplicate votes")
    for key in (
        "provider_calls",
        "input_tokens",
        "output_tokens",
        "malformed_response_count",
    ):
        if not isinstance(ledger.get(key), int) or ledger[key] < 0:
            raise PanelReviewError(f"invalid resume accounting: {key}")
    if not isinstance(ledger.get("reported_cost_usd"), (int, float)) or ledger["reported_cost_usd"] < 0:
        raise PanelReviewError("invalid resume cost accounting")


def write_ledger_atomic(path: Path, ledger: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise PanelReviewError(f"output already exists: {path}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(ledger, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def append_vote(
    ledger: dict[str, Any],
    *,
    reviewer_id: str,
    vote: dict[str, Any],
    provider_call: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reported_cost_usd: float = 0.0,
) -> None:
    if reviewer_id not in VALID_REVIEWER_IDS:
        raise PanelReviewError("unknown reviewer identity")
    identity = (reviewer_id, vote["review_item_id"])
    if any(
        (row["reviewer_id"], row["review_item_id"]) == identity
        for row in ledger["votes"]
    ):
        raise PanelReviewError("duplicate reviewer vote")
    ledger["votes"].append({"reviewer_id": reviewer_id, **vote})
    ledger["provider_calls"] += int(provider_call)
    ledger["input_tokens"] += input_tokens
    ledger["output_tokens"] += output_tokens
    ledger["reported_cost_usd"] = round(
        ledger["reported_cost_usd"] + reported_cost_usd, 9
    )


def _truth_maps() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    cases = _load(CASES_PATH)["cases"]
    controls = _load(CONTROLS_PATH)["controls"]
    packet = _load(PACKET_PATH)
    # Review IDs are deterministic but deliberately not stored beside gold in
    # the blinded packet.
    from scripts.prepare_academic_factual_qa_panel_review_v2 import _review_item_id

    case_truth = {_review_item_id(row["case_id"]): row for row in cases}
    control_truth = {_review_item_id(row["control_id"]): row for row in controls}
    if set(case_truth) | set(control_truth) != {
        row["review_item_id"] for row in packet["items"]
    }:
        raise PanelReviewError("review packet and hidden truth mapping drifted")
    return case_truth, control_truth


def _ideal_vote(item: dict[str, Any], truth: dict[str, Any]) -> dict[str, Any]:
    if item["item_kind"] == "calibration":
        expected = truth["expected_review"]
        action = expected["expected_action"]
        valid = expected["case_semantically_valid"]
        defect_types = expected["defect_types"]
        evidence_ids = [
            row["evidence_id"] for row in truth["authoritative_truth"]["evidence"]
        ] if action == "answer" else []
        citation = "invalid" if "citation" in defect_types else (
            "complete-valid" if action == "answer" else "not-applicable"
        )
        claim = "unsupported" if "claim" in defect_types else (
            "fully-supported" if action == "answer" else "not-applicable"
        )
    else:
        action = truth["expected_action"]
        valid = True
        defect_types = []
        evidence_ids = [row["evidence_id"] for row in truth["evidence"]]
        citation = "complete-valid" if action == "answer" else "not-applicable"
        claim = "fully-supported" if action == "answer" else "not-applicable"
    return {
        "review_item_id": item["review_item_id"],
        "case_semantically_valid": valid,
        "expected_action": action,
        "question_answerable_from_supplied_sources": action == "answer",
        "atomic_claim_support": claim,
        "citation_support": citation,
        "boundary_reason": None if action == "answer" else f"expected-{action}-boundary",
        "ambiguity_detected": action == "clarify",
        "evidence_ids": evidence_ids,
        "defect_types": defect_types,
        "concise_rationale": "The visible question, candidate record, and supplied evidence determine this disposition.",
    }


def _calibration_metrics(
    votes: list[dict[str, Any]], controls: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    total = len(controls)
    action_correct = 0
    corrupted_detected = 0
    corrupted_total = 0
    clean_accepted = 0
    clean_total = 0
    citation_detected = 0
    citation_total = 0
    for vote in votes:
        truth = controls[vote["review_item_id"]]
        expected = truth["expected_review"]
        action_correct += vote["expected_action"] == expected["expected_action"]
        if truth["is_clean"]:
            clean_total += 1
            clean_accepted += vote["case_semantically_valid"] is True
        else:
            corrupted_total += 1
            corrupted_detected += vote["case_semantically_valid"] is False
        if truth["planted_mutation"] == "citation":
            citation_total += 1
            citation_detected += vote["citation_support"] == "invalid"
    metrics = {
        "action_accuracy": action_correct / total,
        "mutation_sensitivity": corrupted_detected / corrupted_total,
        "specificity": clean_accepted / clean_total,
        "citation_defect_sensitivity": citation_detected / citation_total,
    }
    metrics["passed"] = all(value >= 0.9 for value in metrics.values())
    return metrics


def _nominal_alpha(action_rows: list[list[str]]) -> float:
    values = [value for row in action_rows for value in row]
    if not values:
        return math.nan
    observed_pairs = 0
    observed_disagreements = 0
    for row in action_rows:
        for left_index in range(len(row)):
            for right_index in range(left_index + 1, len(row)):
                observed_pairs += 1
                observed_disagreements += row[left_index] != row[right_index]
    do = observed_disagreements / observed_pairs if observed_pairs else 0.0
    counts = Counter(values)
    total = len(values)
    de = 1.0 - sum((count / total) ** 2 for count in counts.values())
    return 1.0 if de == 0 else 1.0 - do / de


def _vote_signature(vote: dict[str, Any]) -> tuple[Any, ...]:
    return (
        vote["case_semantically_valid"],
        vote["expected_action"],
        vote["atomic_claim_support"],
        vote["citation_support"],
        tuple(sorted(vote["evidence_ids"])),
        tuple(sorted(vote["defect_types"])),
    )


def aggregate_panel(
    *,
    ledger: dict[str, Any],
    packet: dict[str, Any],
    reviewer_ids: tuple[str, ...] = REVIEWER_IDS,
) -> dict[str, Any]:
    if len(reviewer_ids) < 2 or len(reviewer_ids) != len(set(reviewer_ids)):
        raise PanelReviewError("panel requires at least two unique reviewers")
    case_truth, control_truth = _truth_maps()
    malformed = ledger["malformed_response_count"]
    by_reviewer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for vote in ledger["votes"]:
        by_reviewer[vote["reviewer_id"]].append(vote)
    calibration_metrics: dict[str, Any] = {}
    passing_reviewers = []
    for reviewer_id in reviewer_ids:
        controls = [
            vote for vote in by_reviewer[reviewer_id] if vote["review_item_id"] in control_truth
        ]
        if len(controls) != 40:
            calibration_metrics[reviewer_id] = {"passed": False, "reason": "incomplete-calibration"}
            continue
        metrics = _calibration_metrics(controls, control_truth)
        calibration_metrics[reviewer_id] = metrics
        if metrics["passed"]:
            passing_reviewers.append(reviewer_id)
    if malformed:
        return {
            "status": "invalid-execution",
            "reason": "malformed-reviewer-output",
            "malformed_response_count": malformed,
            "calibration": calibration_metrics,
        }
    if len(passing_reviewers) != len(reviewer_ids):
        return {
            "status": "panel-calibration-failed",
            "passing_reviewer_count": len(passing_reviewers),
            "calibration": calibration_metrics,
        }

    votes_by_item: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reviewer_id in passing_reviewers:
        for vote in by_reviewer[reviewer_id]:
            if vote["review_item_id"] in case_truth:
                votes_by_item[vote["review_item_id"]].append(vote)
    if len(votes_by_item) != 200 or any(
        len(rows) != len(reviewer_ids) for rows in votes_by_item.values()
    ):
        return {
            "status": "invalid-execution",
            "reason": "incomplete-confirmation-coverage",
            "covered_case_count": len(votes_by_item),
            "calibration": calibration_metrics,
        }
    disagreements = sorted(
        item_id
        for item_id, votes in votes_by_item.items()
        if len({_vote_signature(vote) for vote in votes}) != 1
    )
    unanimous = sorted(set(votes_by_item) - set(disagreements))
    action_rows = [
        [vote["expected_action"] for vote in votes_by_item[item_id]]
        for item_id in sorted(votes_by_item)
    ]
    rng = random.Random(20260825)
    unanimous_answerable = [
        item_id for item_id in unanimous if case_truth[item_id]["expected_action"] == "answer"
    ]
    unanimous_boundary = [
        item_id for item_id in unanimous if case_truth[item_id]["expected_action"] != "answer"
    ]
    rng.shuffle(unanimous_answerable)
    rng.shuffle(unanimous_boundary)
    seeded_audit = unanimous_answerable[:10] + unanimous_boundary[:10]
    researcher_ids = disagreements + seeded_audit
    agreement_rate = len(unanimous) / 200
    alpha = _nominal_alpha(action_rows)
    status = "ready-researcher-audit"
    if len(disagreements) > 40:
        status = "panel-disagreement-overflow"
    elif agreement_rate < 0.8 or alpha < 0.67:
        status = "panel-agreement-gate-failed"
    return {
        "status": status,
        "calibration": calibration_metrics,
        "passing_reviewer_count": len(reviewer_ids),
        "reviewer_ids": list(reviewer_ids),
        "confirmation_case_count": 200,
        "unanimous_case_count": len(unanimous),
        "unanimous_semantic_agreement_rate": agreement_rate,
        "disagreement_case_count": len(disagreements),
        "action_krippendorff_alpha": alpha,
        "researcher_packet_case_count": len(researcher_ids),
        "researcher_packet_review_item_ids": researcher_ids,
        "researcher_packet_bounded": len(researcher_ids) <= 60,
        "provider_calls": ledger["provider_calls"],
        "input_tokens": ledger["input_tokens"],
        "output_tokens": ledger["output_tokens"],
        "reported_cost_usd": ledger["reported_cost_usd"],
        "automatic_product_promotion": False,
    }


def build_researcher_packet(
    *,
    aggregate: dict[str, Any],
    packet: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    if aggregate.get("status") != "ready-researcher-audit":
        raise PanelReviewError("researcher packet requires a calibrated bounded panel")
    review_ids = aggregate["researcher_packet_review_item_ids"]
    if len(review_ids) > 60:
        raise PanelReviewError("researcher packet exceeds the frozen bound")
    visible_items = {row["review_item_id"]: row for row in packet["items"]}
    votes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ledger["votes"]:
        if row["review_item_id"] in review_ids:
            votes[row["review_item_id"]].append(row)
    cases = []
    for review_id in review_ids:
        item_votes = sorted(votes[review_id], key=lambda row: row["reviewer_id"])
        if len(item_votes) != aggregate["passing_reviewer_count"]:
            raise PanelReviewError("researcher packet is missing immutable reviewer votes")
        cases.append(
            {
                "review_item": visible_items[review_id],
                "reviewer_votes": item_votes,
                "researcher_disposition": {
                    "status": "pending",
                    "case_semantically_valid": None,
                    "expected_action": None,
                    "critical_error": None,
                    "material_error": None,
                    "rationale": None,
                },
            }
        )
    result: dict[str, Any] = {
        "schema_version": 1,
        "packet_id": "academic-factual-qa-confirmation-002-researcher-audit-packet",
        "status": "pending-researcher-audit",
        "source_panel_status": aggregate["status"],
        "case_count": len(cases),
        "maximum_case_count": 60,
        "researcher_is_independent_annotator": False,
        "original_reviewer_votes_immutable": True,
        "cases": cases,
    }
    result["content_sha256"] = canonical_sha256(result)
    return result


def build_simulated_ledger(
    scenario: str,
    *,
    reviewer_ids: tuple[str, ...] = REVIEWER_IDS,
) -> tuple[dict[str, Any], dict[str, Any]]:
    packet = _load(PACKET_PATH)
    validate_packet(packet)
    instrument = _load(INSTRUMENT_PATH)
    case_truth, control_truth = _truth_maps()
    ledger = initialize_ledger(
        packet_sha256=packet["content_sha256"],
        instrument_sha256=canonical_sha256(instrument),
        reviewer_bindings_sha256="simulated-bindings",
        pricing_sha256="simulated-pricing",
    )
    confirmation_index = 0
    for reviewer_id in reviewer_ids:
        for item in packet["items"]:
            truth = (
                control_truth[item["review_item_id"]]
                if item["item_kind"] == "calibration"
                else case_truth[item["review_item_id"]]
            )
            vote = _ideal_vote(item, truth)
            if scenario == "calibration-failure" and reviewer_id == reviewer_ids[0] and item["item_kind"] == "calibration" and len([row for row in ledger["votes"] if row["reviewer_id"] == reviewer_id]) < 5:
                vote["expected_action"] = "abstain"
                vote["case_semantically_valid"] = False
            if item["item_kind"] == "confirmation":
                if reviewer_id == reviewer_ids[0]:
                    confirmation_index += 1
                item_position = list(case_truth).index(item["review_item_id"]) if item["review_item_id"] in case_truth else -1
                if scenario == "disagreement-overflow" and reviewer_id == reviewer_ids[-1] and item_position < 41:
                    vote["expected_action"] = "clarify" if vote["expected_action"] != "clarify" else "abstain"
            if scenario == "malformed" and reviewer_id == reviewer_ids[1] and item == packet["items"][0]:
                ledger["malformed_response_count"] += 1
                continue
            validate_vote(vote, expected_item_id=item["review_item_id"])
            append_vote(
                ledger,
                reviewer_id=reviewer_id,
                vote=vote,
                provider_call=False,
            )
    ledger["status"] = "simulated-complete"
    return packet, ledger


def simulate(scenario: str) -> dict[str, Any]:
    packet, ledger = build_simulated_ledger(scenario)
    aggregate = aggregate_panel(ledger=ledger, packet=packet)
    aggregate["scenario"] = scenario
    aggregate["simulation"] = True
    aggregate["provider_calls"] = 0
    return aggregate


def validate_build() -> dict[str, Any]:
    packet = _load(PACKET_PATH)
    validate_packet(packet)
    instrument = _load(INSTRUMENT_PATH)
    reviewer_ids = tuple(
        row["reviewer_id"] for row in instrument["reviewer_panel_contract"]["reviewers"]
    )
    if reviewer_ids != REVIEWER_IDS:
        raise PanelReviewError(f"reviewer binding drifted: {reviewer_ids}")
    if any(instrument["execution_safety"].values()):
        raise PanelReviewError("invalid-attempt authority must remain revoked")
    return {
        "instrument_id": instrument["instrument_id"],
        "status": "validated-attempt-001-invalid-authorization-revoked",
        "packet_item_count": len(packet["items"]),
        "provider_calls": 0,
    }


def preflight() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    blockers = []
    panel = instrument["reviewer_panel_contract"]
    if not all(row["binding_fresh"] for row in panel["reviewers"]):
        blockers.append("reviewer-bindings-not-fresh")
    safety = instrument["execution_safety"]
    if not safety["codex_review_authorized"]:
        blockers.append("codex-review-not-authorized")
    if not safety["provider_review_authorized"]:
        blockers.append("provider-review-not-authorized")
    if not safety["paid_execution_authorized"]:
        blockers.append("paid-execution-not-authorized")
    if not instrument["reviewer_calibration_contract"]["calibration_controls_sealed"]:
        blockers.append("calibration-controls-not-sealed")
    if not safety["confirmation_execution_authorized"]:
        blockers.append("confirmation-execution-not-authorized")
    return {
        "instrument_id": instrument["instrument_id"],
        "status": "blocked-confirmation-not-authorized" if blockers else "ready",
        "blockers": blockers,
        "planned_review_items_per_reviewer": 240,
        "planned_provider_review_items": 480,
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    parser.add_argument(
        "--scenario",
        choices=("pass", "calibration-failure", "disagreement-overflow", "malformed"),
        default="pass",
    )
    args = parser.parse_args()
    if args.validate:
        result = validate_build()
    elif args.preflight:
        result = preflight()
    else:
        result = simulate(args.scenario)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
