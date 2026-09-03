#!/usr/bin/env python3
"""Build the fresh reference-corrected H+E1 actual-product confirmation."""

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
    build_governed_full_autonomy_v2_1_actual_product_confirmation_014 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as source_base,
)
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-015"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_confirmation_015.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
canonical_hash = predecessor.canonical_hash
V2_CONDITIONS = {"t1-v2-reactive", "t1-v2-autonomous"}


def fresh_source_number(case_id: str) -> int:
    """Map scenarios to 50 source identities unused by confirmations 012–014."""

    return 251 + ((source_base._base_number(case_id) - 1) % 50)  # noqa: SLF001


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    return {
        "source_id": f"synthetic-final-h-e1-source-{number:03d}",
        "concept_id": f"durable-tutoring-{number:03d}",
        "objective": (
            f"Explain how durable tutoring protocol {number:03d} resumes safely "
            "after a planning-service failure."
        ),
        "statement": (
            f"Durable tutoring protocol {number:03d} falls back to the approved "
            "grounded tutoring path after a planning-service failure while "
            "preserving the learner-state checkpoint."
        ),
        "label": f"Durable tutoring protocol {number:03d}",
    }


def _message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    number = fresh_source_number(case_id)
    statement = source["statement"]
    return {
        "direct": (
            "According to the approved source, what does durable tutoring protocol "
            f"{number:03d} do after a planning-service failure?"
        ),
        "partial-attempt": (
            f"My attempt is: {statement} Is the grounded fallback the key step?"
        ),
        "confusion": (
            f"I am confused about how durable tutoring protocol {number:03d} "
            "preserves state during fallback. Can you give a grounded hint?"
        ),
        "repeated-confusion": (
            f"I am still confused after reading that {statement} "
            "What should I inspect next?"
        ),
    }[turn_kind]


def _align_provider_fallback_reference(condition, case, gold):
    """Align post-failure student turns to the approved deterministic fallback."""

    if condition not in V2_CONDITIONS:
        return gold, 0
    failure_times = [event.at_seconds for event in case.events if event.kind == "provider-failure"]
    if not failure_times:
        return gold, 0
    fallback_times = {
        event.at_seconds
        for event in case.events
        if event.kind == "student-message" and event.at_seconds > min(failure_times)
    }
    expected = []
    changed = 0
    for action in gold.expected_actions:
        if action.action == "no-action" and action.earliest_seconds in fallback_times:
            action = action.model_copy(
                update={
                    "action": "provide-hint-or-example",
                    "must_have_valid_lineage": True,
                }
            )
            changed += 1
        expected.append(action)
    if fallback_times and changed != len(fallback_times):
        raise ValueError(
            f"provider-fallback reference mismatch in {case.case_id}: "
            f"expected {len(fallback_times)}, changed {changed}"
        )
    return gold.model_copy(update={"expected_actions": expected}), changed


def build_contract():
    rows = []
    corrected = 0
    for condition, old_case, old_gold in predecessor.build_contract():
        case_id = old_case.case_id.replace(
            "release-h-e1-", "release-final-h-e1-", 1
        )
        course_id = old_case.course_id.replace(
            "release-h-e1-", "release-final-h-e1-", 1
        )
        release_id = old_case.release_id.replace(
            "release-h-e1-", "release-final-h-e1-", 1
        )
        learner_id = old_case.learner_id.replace(
            "release-h-e1-", "release-final-h-e1-", 1
        )
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
        gold, changed = _align_provider_fallback_reference(condition, case, gold)
        corrected += changed
        rows.append((condition, case, gold))
    if corrected != 30:
        raise ValueError(f"confirmation 015 requires 30 prospective corrections, got {corrected}")
    return rows


def public_payload() -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": 820,
        "source_family_range": [251, 300],
        "source_disjoint_from_confirmations_012_013_014": True,
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
        "prospectively_corrected_reference_count": 30,
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
        raise ValueError("confirmation 015 identity drifted")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 015 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 015 hidden-gold hash drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("confirmation 015 eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("confirmation 015 event-action contract drifted")
    contract = build_contract()
    case_ids = [case.case_id for _condition, case, _gold in contract]
    if len(contract) != 820 or len(case_ids) != len(set(case_ids)):
        raise ValueError("confirmation 015 requires 820 unique cases")
    current_sources = {
        source_fixture_for_case(case.case_id)["source_id"]
        for _condition, case, _gold in contract
    }
    if len(current_sources) != 50:
        raise ValueError("confirmation 015 requires 50 source identities")
    for condition, case, gold in contract:
        if condition not in V2_CONDITIONS:
            continue
        failure_times = [
            event.at_seconds for event in case.events if event.kind == "provider-failure"
        ]
        if not failure_times:
            continue
        post_failure_times = {
            event.at_seconds
            for event in case.events
            if event.kind == "student-message" and event.at_seconds > min(failure_times)
        }
        actions = {
            action.earliest_seconds: action.action for action in gold.expected_actions
        }
        if any(actions.get(instant) != "provide-hint-or-example" for instant in post_failure_times):
            raise ValueError("confirmation 015 provider-fallback gold drifted")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "provider_execution_authorized": authority["provider_execution_authorized"],
        "paid_execution_authorized": authority["paid_execution_authorized"],
        "case_count": 820,
        "source_family_count": 50,
        "prospectively_corrected_reference_count": 30,
        "source_disjoint_from_confirmations_012_013_014": True,
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
