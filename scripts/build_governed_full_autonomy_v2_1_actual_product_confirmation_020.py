#!/usr/bin/env python3
"""Build the fresh set-valued, minimal-schema release confirmation 020."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_018 as predecessor,
)
from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_009 as source_base,
)
from src.digital_twin.evaluation import (
    AutonomyEvaluationGoldV2,
    ExpectedAutonomyActionV2,
)
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-020"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_confirmation_020.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
canonical_hash = predecessor.canonical_hash


def fresh_source_number(case_id: str) -> int:
    """Map scenarios to source identities unused by confirmations 012–019."""

    return 401 + ((source_base._base_number(case_id) - 1) % 50)  # noqa: SLF001


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    return {
        "source_id": f"synthetic-final-confirmation-source-{number:03d}",
        "concept_id": f"resilient-learning-{number:03d}",
        "objective": (
            f"Explain how resilient learning method {number:03d} preserves an "
            "approved learning step when semantic planning is unavailable."
        ),
        "statement": (
            f"Resilient learning method {number:03d} uses a policy-approved "
            "grounded fallback when semantic planning is unavailable and "
            "preserves the committed learner state for the next learning step."
        ),
        "label": f"Resilient learning method {number:03d}",
    }


def _message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    label = source["label"]
    statement = source["statement"]
    return {
        "direct": f"What does {label} do if semantic planning is unavailable?",
        "partial-attempt": (
            f"My explanation is: {statement} Which part should I check next?"
        ),
        "confusion": (
            f"I understand the fallback in {label}, but I am unsure how it "
            "preserves the next learning step. Please guide me."
        ),
        "repeated-confusion": (
            f"I am still stuck on {label}. Ask one diagnostic question or give "
            "one grounded hint that helps me test my explanation."
        ),
    }[turn_kind]


def _replace(value: str) -> str:
    return value.replace("release-fresh-h-e1-", "release-final-h-e1-", 1)


def build_contract():
    rows = []
    for condition, old_case, old_gold in predecessor.build_contract():
        case_id = _replace(old_case.case_id)
        course_id = _replace(old_case.course_id)
        release_id = _replace(old_case.release_id)
        learner_id = _replace(old_case.learner_id)
        repeated_confusion_times: set[int] = set()
        events = []
        for old_event in old_case.events:
            payload = dict(old_event.payload)
            if old_event.kind == "student-message":
                turn_kind = str(payload["turn_kind"])
                payload["message"] = _message(case_id, turn_kind)
                if turn_kind == "repeated-confusion":
                    repeated_confusion_times.add(old_event.at_seconds)
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
        expectations = []
        for item in old_gold.expected_actions:
            alternatives = [item.action]
            if (
                item.action == "provide-hint-or-example"
                and item.earliest_seconds == item.latest_seconds
                and item.earliest_seconds in repeated_confusion_times
            ):
                alternatives = [
                    "ask-diagnostic-question",
                    "provide-hint-or-example",
                ]
            expectations.append(
                ExpectedAutonomyActionV2(
                    expectation_id=item.expectation_id.replace(
                        old_case.case_id, case_id, 1
                    ),
                    acceptable_actions=alternatives,
                    preferred_action=item.action,
                    earliest_seconds=item.earliest_seconds,
                    latest_seconds=item.latest_seconds,
                    recipient_id=learner_id,
                    course_id=course_id,
                    release_id=release_id,
                    must_have_valid_lineage=item.must_have_valid_lineage,
                )
            )
        gold = AutonomyEvaluationGoldV2(
            case_id=case_id,
            expected_actions=expectations,
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
        "source_family_range": [401, 450],
        "source_disjoint_from_confirmations_012_through_019": True,
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
        raise ValueError("confirmation 020 identity drifted")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 020 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 020 hidden-gold hash drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("confirmation 020 eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("confirmation 020 event-action contract drifted")
    rows = build_contract()
    if len(rows) != 820 or len({row[1].case_id for row in rows}) != 820:
        raise ValueError("confirmation 020 requires 820 unique cases")
    if len({source_fixture_for_case(row[1].case_id)["source_id"] for row in rows}) != 50:
        raise ValueError("confirmation 020 requires 50 source identities")
    alternative_count = sum(
        len(expectation.acceptable_actions) > 1
        for _condition, _case, gold in rows
        for expectation in gold.expected_actions
    )
    if alternative_count != 600:
        raise ValueError("confirmation 020 requires 600 repeated-confusion alternatives")
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
