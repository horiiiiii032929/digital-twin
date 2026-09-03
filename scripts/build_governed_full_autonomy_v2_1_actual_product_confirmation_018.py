#!/usr/bin/env python3
"""Build the fresh provider-route-safe H+E1 actual-product confirmation 018."""

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
    build_governed_full_autonomy_v2_1_actual_product_confirmation_016 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as source_base,
)
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-018"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_confirmation_018.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
canonical_hash = predecessor.canonical_hash


def fresh_source_number(case_id: str) -> int:
    """Map scenarios to source identities unused by confirmations 012–017."""

    return 351 + ((source_base._base_number(case_id) - 1) % 50)  # noqa: SLF001


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    return {
        "source_id": f"synthetic-route-confirmation-source-{number:03d}",
        "concept_id": f"durable-guidance-{number:03d}",
        "objective": (
            f"Explain how durable guidance method {number:03d} preserves a "
            "learner checkpoint during a planning-service interruption."
        ),
        "statement": (
            f"Durable guidance method {number:03d} uses the approved grounded "
            "fallback during a planning-service interruption and preserves the "
            "learner checkpoint for the next tutoring step."
        ),
        "label": f"Durable guidance method {number:03d}",
    }


def _message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    number = fresh_source_number(case_id)
    label = source["label"]
    statement = source["statement"]
    variant = number % 5
    confusion = (
        f"I can repeat the fallback rule for {label}, but I do not understand "
        "why preserving the checkpoint changes the next tutoring step. Guide me."
        if variant == 0
        else f"I need a hint: why does {label} keep the learner checkpoint when planning stops?"
        if variant == 1
        else f"I am still uncertain how {label} connects its fallback to the next learning step."
        if variant == 2
        else f"My explanation of {label} is incomplete. Help me connect the outage response and saved checkpoint."
        if variant == 3
        else f"I am stuck on {label}. Which part of the checkpoint-preservation reasoning should I test?"
    )
    return {
        "direct": (
            f"According to the approved material, what does {label} do when "
            "the planning service is interrupted?"
        ),
        "partial-attempt": (
            f"My current explanation is: {statement} Which part should I verify next?"
        ),
        "confusion": confusion,
        "repeated-confusion": (
            f"I am still unsure after reading that {statement} Please give me "
            "one diagnostic question or hint."
        ),
    }[turn_kind]


def _replace(value: str) -> str:
    return value.replace("release-grounded-h-e1-", "release-fresh-h-e1-", 1)


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
        "source_family_range": [351, 400],
        "source_disjoint_from_confirmations_012_through_017": True,
        "instructional_wording_family_disjoint_from_confirmation_016": True,
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
        "provider_failure_reference_contract": (
            "prospective-v2-deterministic-t1-v1-t0-fallback-v1"
        ),
        "reference_action_accuracy_is_release_gate": True,
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
        raise ValueError("confirmation 018 identity drifted")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 018 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 018 hidden-gold hash drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("confirmation 018 eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("confirmation 018 event-action contract drifted")
    contract = build_contract()
    case_ids = [case.case_id for _condition, case, _gold in contract]
    sources = {
        source_fixture_for_case(case.case_id)["source_id"]
        for _condition, case, _gold in contract
    }
    if len(contract) != 820 or len(case_ids) != len(set(case_ids)):
        raise ValueError("confirmation 018 requires 820 unique cases")
    if len(sources) != 50:
        raise ValueError("confirmation 018 requires 50 source identities")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "provider_execution_authorized": authority["provider_execution_authorized"],
        "paid_execution_authorized": authority["paid_execution_authorized"],
        "case_count": 820,
        "source_family_count": 50,
        "source_disjoint_from_confirmations_012_through_017": True,
        "instructional_wording_family_disjoint_from_confirmation_016": True,
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
