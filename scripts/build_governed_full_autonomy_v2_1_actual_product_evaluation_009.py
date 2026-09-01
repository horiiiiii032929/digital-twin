#!/usr/bin/env python3
"""Build the fresh event-scoped-action autonomy confirmation package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_008 as predecessor,
)
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-evaluation-009"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_evaluation_009.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
canonical_hash = predecessor.canonical_hash


def _base_number(case_id: str) -> int:
    match = re.search(r"(?:trajectory|long-horizon|opportunity)-(\d{3})", case_id)
    if match is None:
        raise ValueError(f"fresh case lacks a source-template identity: {case_id}")
    return int(match.group(1))


def fresh_source_number(case_id: str) -> int:
    """Map the fresh package to source identities 051–100."""

    return 51 + ((_base_number(case_id) - 1) % 50)


def source_fixture_for_case(case_id: str) -> dict[str, str]:
    number = fresh_source_number(case_id)
    concept = f"epoch-validation-{number:03d}"
    statement = (
        f"Protocol {number:03d} prevents stale replicas by checking the update epoch "
        "before accepting a synchronized state transition."
    )
    return {
        "source_id": f"synthetic-public-source-{number:03d}",
        "concept_id": concept,
        "objective": (
            f"Explain why Protocol {number:03d} checks an update epoch before commit."
        ),
        "statement": statement,
        "label": f"Protocol {number:03d}",
    }


def _fresh_message(case_id: str, turn_kind: str) -> str:
    source = source_fixture_for_case(case_id)
    number = fresh_source_number(case_id)
    statement = source["statement"]
    return {
        "direct": (
            f"According to the approved source, what does Protocol {number:03d} "
            "check before accepting a synchronized transition?"
        ),
        "partial-attempt": (
            f"My attempt is: {statement} Is the epoch check the important step?"
        ),
        "confusion": (
            f"I am confused about how Protocol {number:03d} prevents stale replicas "
            "by checking the update epoch before accepting a synchronized transition. "
            "Can you give me a source-grounded hint?"
        ),
        "repeated-confusion": (
            f"I am still confused after reading that {statement} "
            "What should I inspect next?"
        ),
    }[turn_kind]


def _fresh_id(value: str) -> str:
    return value if value.startswith("fresh-") else f"fresh-{value}"


def build_contract():
    rows = []
    for condition, old_case, old_gold in predecessor.build_contract():
        case_id = _fresh_id(old_case.case_id)
        course_id = _fresh_id(old_case.course_id)
        release_id = _fresh_id(old_case.release_id)
        learner_id = _fresh_id(old_case.learner_id)
        events = []
        for old_event in old_case.events:
            payload = dict(old_event.payload)
            if old_event.kind == "student-message":
                payload["message"] = _fresh_message(
                    case_id,
                    str(payload["turn_kind"]),
                )
            elif old_event.kind == "practice-outcome":
                payload["message"] = _fresh_message(case_id, "partial-attempt")
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
            update={"case_id": case_id, "expected_actions": expected},
            deep=True,
        )
        rows.append((condition, case, gold))
    return rows


def public_payload() -> dict[str, Any]:
    rows = [
        {"condition": condition, "case": case.model_dump(mode="json")}
        for condition, case, _gold in build_contract()
    ]
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": len(rows),
        "source_family_range": [51, 100],
        "source_disjoint_from_attempt_008": True,
        "rows": rows,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def hidden_gold_payload() -> dict[str, Any]:
    rows = [gold.model_dump(mode="json") for _condition, _case, gold in build_contract()]
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": len(rows),
        "gold": rows,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ValueError("fresh autonomy confirmation identity drifted")
    if instrument.get("status") != "frozen-pending-paid-authorization":
        raise ValueError("fresh autonomy confirmation freeze status drifted")
    authority = instrument["authority"]
    if authority["provider_execution_authorized"] or authority["paid_execution_authorized"]:
        raise ValueError("fresh autonomy confirmation is unexpectedly authorized")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("event action eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("event action contract drifted")
    public = public_payload()
    hidden = hidden_gold_payload()
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("fresh public package hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("fresh hidden-gold package hash drifted")
    old_source_ids = {
        predecessor.source_fixture(number)["source_id"] for number in range(1, 51)
    }
    fresh_source_ids = {
        source_fixture_for_case(case.case_id)["source_id"]
        for _condition, case, _gold in build_contract()
    }
    if old_source_ids & fresh_source_ids:
        raise ValueError("fresh autonomy sources overlap attempt 008")
    if len(fresh_source_ids) != 50:
        raise ValueError("fresh autonomy source-family count drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-frozen-provider-unauthorized",
        "case_count": len(build_contract()),
        "source_family_count": len(fresh_source_ids),
        "source_disjoint_from_attempt_008": True,
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
