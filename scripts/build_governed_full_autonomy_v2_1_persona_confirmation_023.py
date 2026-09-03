#!/usr/bin/env python3
"""Build the fresh T0/T1-v2 persona-selection confirmation 023."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_021 as predecessor,
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
INSTRUMENT_ID = "governed-full-autonomy-v2-1-persona-confirmation-023"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_persona_confirmation_023.json"
)
CONDITIONS = (
    "t0-grounded-control",
    "t1-v2-reactive",
    "t1-v2-autonomous",
)
SELECTED_CONDITIONS = set(CONDITIONS)
canonical_hash = predecessor.canonical_hash


def fresh_source_number(case_id: str) -> int:
    return 501 + ((source_base._base_number(case_id) - 1) % 50)  # noqa: SLF001


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    return {
        "source_id": f"synthetic-persona-confirmation-source-{number:03d}",
        "concept_id": f"adaptive-review-{number:03d}",
        "objective": (
            f"Explain how adaptive review protocol {number:03d} preserves a "
            "bounded, evidence-linked learning step across an interruption."
        ),
        "statement": (
            f"Adaptive review protocol {number:03d} records the approved "
            "evidence and learner-goal version before an interruption, then "
            "resumes with one policy-bounded review step."
        ),
        "label": f"Adaptive review protocol {number:03d}",
    }


def _message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    label = source["label"]
    statement = source["statement"]
    return {
        "direct": f"How does {label} resume safely after an interruption?",
        "partial-attempt": (
            f"My current explanation is: {statement} What should I verify next?"
        ),
        "confusion": (
            f"I do not yet see why the recorded versions in {label} keep the "
            "next review step bounded. Please help me reason through it."
        ),
        "repeated-confusion": (
            f"I am still stuck on {label}. Ask one diagnostic question or give "
            "one cited hint so I can correct my own explanation."
        ),
    }[turn_kind]


def _replace(value: str) -> str:
    return value.replace("release-decision-h-e1-", "release-persona-confirm-h-e1-", 1)


def build_contract():
    rows = []
    for condition, old_case, old_gold in predecessor.build_contract():
        if condition not in SELECTED_CONDITIONS:
            continue
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
                        "event_id": old_event.event_id.replace(old_case.case_id, case_id, 1),
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
        "case_count": 670,
        "source_family_range": [501, 550],
        "source_disjoint_from_confirmations_012_through_021": True,
        "wording_disjoint_from_confirmation_021": True,
        "conditions": list(CONDITIONS),
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
        "case_count": 670,
        "action_gold_contract": "set-valued-valid-actions-v2",
        "preference_is_non_blocking": True,
        "gold": [gold.model_dump(mode="json") for _, _, gold in build_contract()],
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    public = public_payload()
    hidden = hidden_gold_payload()
    rows = build_contract()
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 023 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 023 hidden-gold hash drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("confirmation 023 eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("confirmation 023 event-action contract drifted")
    if len(rows) != 670 or len({row[1].case_id for row in rows}) != 670:
        raise ValueError("confirmation 023 requires 670 unique cases")
    counts = {condition: sum(row[0] == condition for row in rows) for condition in SELECTED_CONDITIONS}
    if counts != {
        "t0-grounded-control": 150,
        "t1-v2-reactive": 150,
        "t1-v2-autonomous": 370,
    }:
        raise ValueError(f"confirmation 023 condition distribution drifted: {counts}")
    if len({source_fixture_for_case(row[1].case_id)["source_id"] for row in rows}) != 50:
        raise ValueError("confirmation 023 requires 50 fresh source identities")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "case_count": len(rows),
        "condition_counts": counts,
        "source_family_count": 50,
        "public_sha256": public["content_sha256"],
        "hidden_gold_sha256": hidden["content_sha256"],
        "provider_execution_authorized": authority["provider_execution_authorized"],
        "paid_execution_authorized": authority["paid_execution_authorized"],
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
