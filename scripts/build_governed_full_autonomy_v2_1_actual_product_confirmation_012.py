#!/usr/bin/env python3
"""Build the fresh hybrid-planner release confirmation package 012."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as predecessor,
)
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-012"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_confirmation_012.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
canonical_hash = predecessor.canonical_hash


def fresh_source_number(case_id: str) -> int:
    return 101 + ((predecessor._base_number(case_id) - 1) % 50)  # noqa: SLF001


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    return {
        "source_id": f"synthetic-release-source-{number:03d}",
        "concept_id": f"bounded-recovery-{number:03d}",
        "objective": (
            f"Explain why bounded recovery protocol {number:03d} verifies its "
            "checkpoint before resuming work."
        ),
        "statement": (
            f"Bounded recovery protocol {number:03d} verifies the durable checkpoint "
            "before resuming work so the same committed action is not repeated."
        ),
        "label": f"Bounded recovery protocol {number:03d}",
    }


def _message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    number = fresh_source_number(case_id)
    statement = source["statement"]
    return {
        "direct": (
            f"According to the approved source, what does bounded recovery protocol "
            f"{number:03d} verify before resuming work?"
        ),
        "partial-attempt": (
            f"My attempt is: {statement} Is checking the durable checkpoint the key step?"
        ),
        "confusion": (
            f"I am confused about why bounded recovery protocol {number:03d} checks "
            "the durable checkpoint before resuming. Can you give a grounded hint?"
        ),
        "repeated-confusion": (
            f"I am still confused after reading that {statement} What should I inspect next?"
        ),
    }[turn_kind]


def build_contract():
    rows = []
    for condition, old_case, old_gold in predecessor.build_contract():
        case_id = f"release-{old_case.case_id}"
        course_id = f"release-{old_case.course_id}"
        release_id = f"release-{old_case.release_id}"
        learner_id = f"release-{old_case.learner_id}"
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
        expected = [
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
        ]
        gold = old_gold.model_copy(
            update={"case_id": case_id, "expected_actions": expected}, deep=True
        )
        rows.append((condition, case, gold))
    return rows


def public_payload() -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": 820,
        "source_family_range": [101, 150],
        "source_disjoint_from_evaluation_009": True,
        "rows": [
            {"condition": condition, "case": case.model_dump(mode="json")}
            for condition, case, _gold in build_contract()
        ],
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def hidden_gold_payload() -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": 820,
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
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ValueError("confirmation identity drifted")
    if instrument.get("status") not in {
        "frozen-pending-paid-authorization",
        "frozen-authorized",
    }:
        raise ValueError("confirmation freeze status drifted")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation hidden-gold hash drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("action eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("event action contract drifted")
    if len(build_contract()) != 820:
        raise ValueError("confirmation requires 820 cases")
    case_ids = [case.case_id for _condition, case, _gold in build_contract()]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("confirmation case IDs must be unique")
    prior_source_ids = {
        predecessor.source_fixture_for_case(case.case_id)["source_id"]
        for _condition, case, _gold in predecessor.build_contract()
    }
    release_source_ids = {
        source_fixture_for_case(case.case_id)["source_id"]
        for _condition, case, _gold in build_contract()
    }
    if prior_source_ids & release_source_ids:
        raise ValueError("confirmation source identities overlap evaluation 009")
    authority = instrument["authority"]
    authorized = bool(
        authority["provider_execution_authorized"]
        and authority["paid_execution_authorized"]
    )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "passed-frozen-authorized"
            if authorized
            else "passed-frozen-provider-unauthorized"
        ),
        "case_count": 820,
        "source_family_count": len(release_source_ids),
        "source_disjoint_from_evaluation_009": True,
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
