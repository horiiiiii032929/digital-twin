#!/usr/bin/env python3
"""Build the fresh structured-intent release confirmation 021."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_020 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as source_base,
)
from src.digital_twin.evaluation import AutonomyEvaluationGoldV2
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-021"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_confirmation_021.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
canonical_hash = predecessor.canonical_hash


def fresh_source_number(case_id: str) -> int:
    """Map scenarios to source identities unused by confirmations 012–020."""

    return 451 + ((source_base._base_number(case_id) - 1) % 50)  # noqa: SLF001


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    return {
        "source_id": f"synthetic-release-decision-source-{number:03d}",
        "concept_id": f"durable-learning-{number:03d}",
        "objective": (
            f"Explain how durable learning protocol {number:03d} maintains a "
            "policy-approved next step after a planning interruption."
        ),
        "statement": (
            f"Durable learning protocol {number:03d} records the approved "
            "evidence state before a planning interruption and resumes with one "
            "bounded, source-linked learning step."
        ),
        "label": f"Durable learning protocol {number:03d}",
    }


def _message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    label = source["label"]
    statement = source["statement"]
    return {
        "direct": (
            f"When planning is interrupted, how does {label} keep the next "
            "learning step safe?"
        ),
        "partial-attempt": (
            f"My attempt is that {statement} Which claim should I verify first?"
        ),
        "confusion": (
            f"I am confused about why the recorded evidence in {label} keeps "
            "the resumed step bounded. Please guide my reasoning."
        ),
        "repeated-confusion": (
            f"I am still confused about the two parts of {label} after my attempt. "
            "Could you ask a diagnostic question or offer one cited clue while I "
            "test my own reasoning?"
        ),
    }[turn_kind]


def _replace(value: str) -> str:
    return value.replace("release-final-h-e1-", "release-decision-h-e1-", 1)


def build_contract():
    rows = []
    for condition, old_case, old_gold in predecessor.build_contract():
        case_id = _replace(old_case.case_id)
        course_id = _replace(old_case.course_id)
        release_id = _replace(old_case.release_id)
        learner_id = _replace(old_case.learner_id)
        events = []
        for old_event in old_case.events:
            payload = dict(old_event.payload)
            if old_event.kind == "student-message":
                payload["message"] = _message(case_id, str(payload["turn_kind"]))
            elif old_event.kind == "practice-outcome":
                payload["message"] = _message(case_id, "partial-attempt")
            events.append(
                old_event.model_copy(
                    update={
                        "event_id": old_event.event_id.replace(
                            old_case.case_id, case_id, 1
                        ),
                        "payload": payload,
                    },
                    deep=True,
                )
            )
        case = old_case.model_copy(
            update={
                "case_id": case_id,
                "course_id": course_id,
                "release_id": release_id,
                "learner_id": learner_id,
                "events": events,
            },
            deep=True,
        )
        gold = AutonomyEvaluationGoldV2(
            case_id=case_id,
            expected_actions=[
                item.model_copy(
                    update={
                        "expectation_id": item.expectation_id.replace(
                            old_case.case_id, case_id, 1
                        ),
                        "recipient_id": learner_id,
                        "course_id": course_id,
                        "release_id": release_id,
                    },
                    deep=True,
                )
                for item in old_gold.expected_actions
            ],
            expected_terminal_goal_status=old_gold.expected_terminal_goal_status,
            required_invariants=old_gold.required_invariants,
        )
        rows.append((condition, case, gold))
    return rows


def public_payload() -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": 820,
        "source_family_range": [451, 500],
        "source_disjoint_from_confirmations_012_through_020": True,
        "wording_disjoint_from_confirmation_020": True,
        "rows": [
            {"condition": condition, "case": case.model_dump(mode="json")}
            for condition, case, _gold in build_contract()
        ],
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def hidden_gold_payload() -> dict[str, Any]:
    payload = {
        "schema_version": 2,
        "dataset_id": INSTRUMENT_ID,
        "case_count": 820,
        "action_gold_contract": "set-valued-valid-actions-v2",
        "preference_is_non_blocking": True,
        "gold": [
            gold.model_dump(mode="json")
            for _condition, _case, gold in build_contract()
        ],
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    public = public_payload()
    hidden = hidden_gold_payload()
    if instrument["instrument_id"] != INSTRUMENT_ID:
        raise ValueError("confirmation 021 identity drifted")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 021 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 021 hidden-gold hash drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("confirmation 021 eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("confirmation 021 event-action contract drifted")
    rows = build_contract()
    if len(rows) != 820 or len({row[1].case_id for row in rows}) != 820:
        raise ValueError("confirmation 021 requires 820 unique cases")
    if len({source_fixture_for_case(row[1].case_id)["source_id"] for row in rows}) != 50:
        raise ValueError("confirmation 021 requires 50 source identities")
    alternative_count = sum(
        len(expectation.acceptable_actions) > 1
        for _condition, _case, gold in rows
        for expectation in gold.expected_actions
    )
    if alternative_count != 600:
        raise ValueError("confirmation 021 requires 600 repeated-confusion alternatives")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "provider_execution_authorized": authority["provider_execution_authorized"],
        "paid_execution_authorized": authority["paid_execution_authorized"],
        "case_count": len(rows),
        "source_family_count": 50,
        "set_valued_expectation_count": alternative_count,
        "public_sha256": public["content_sha256"],
        "hidden_gold_sha256": hidden["content_sha256"],
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
