#!/usr/bin/env python3
"""Build the realistic-time, flow-independent autonomy successor contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from src.digital_twin.evaluation import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyEvaluationGoldV1,
    ExpectedAutonomyActionV1,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-evaluation-002"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_evaluation_002.json"
)
CONDITIONS = (
    "t0-grounded-control",
    "t1-v1-reactive-control",
    "t1-v2-reactive",
    "t1-v2-autonomous",
)
DAY = 86_400
INVARIANTS = [
    "no-unsupported-action",
    "correct-recipient",
    "correct-course-release",
    "valid-citation-lineage",
    "consent-respected",
    "quiet-hours-respected",
    "frequency-respected",
    "no-duplicate-delivery",
    "bounded-loop",
    "restart-consistent",
    "no-model-owned-authority-mutation",
]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
    ).hexdigest()


def source_template_number(case_id: str) -> int:
    match = re.search(r"(?:trajectory|long-horizon|opportunity)-(\d{3})", case_id)
    if match is None:
        raise ValueError(f"case lacks a source-template identity: {case_id}")
    return (int(match.group(1)) - 1) % 50 + 1


def source_fixture(number: int) -> dict[str, str]:
    if not 1 <= number <= 50:
        raise ValueError("source template number must be between 1 and 50")
    concept = f"versioned-update-{number:03d}"
    statement = (
        f"Protocol {number:03d} preserves replicated state consistency by validating "
        "each versioned update before commit."
    )
    return {
        "source_id": f"synthetic-public-source-{number:03d}",
        "concept_id": concept,
        "objective": f"Explain why Protocol {number:03d} validates versioned updates.",
        "statement": statement,
    }


def _question(case_id: str, turn_kind: str) -> str:
    source = source_fixture(source_template_number(case_id))
    statement = source["statement"]
    return {
        "direct": f"According to the course source, what does Protocol {source_template_number(case_id):03d} do?",
        "partial-attempt": f"My attempt is: {statement} Is that the key idea?",
        "confusion": f"I am confused about Protocol {source_template_number(case_id):03d}. Please give a source-grounded hint.",
        "repeated-confusion": f"I am still confused after reading that {statement} What should I check next?",
    }[turn_kind]


def _expected(
    *,
    case: AutonomyEvaluationCaseV1,
    number: int,
    action: str,
    earliest: int,
    latest: int,
) -> ExpectedAutonomyActionV1:
    return ExpectedAutonomyActionV1(
        expectation_id=f"expected-{case.case_id}-{number:03d}",
        action=action,
        earliest_seconds=earliest,
        latest_seconds=latest,
        recipient_id=case.learner_id,
        course_id=case.course_id,
        release_id=case.release_id,
        must_have_valid_lineage=action != "no-action",
    )


def _trajectory_cases() -> list[
    tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]
]:
    rows = []
    turn_schedule = (
        (0, "direct"),
        (600, "partial-attempt"),
        (1_800, "confusion"),
        (3_600, "repeated-confusion"),
    )
    for trajectory in range(1, 51):
        for condition in CONDITIONS:
            for seed in range(1, 4):
                case_id = f"trajectory-{trajectory:03d}-{condition}-seed-{seed}"
                course_id = f"public-course-{(trajectory - 1) % 4 + 1}"
                release_id = f"public-release-{course_id}-v1"
                learner_id = f"public-student-trajectory-{trajectory:03d}-{seed}"
                events = [
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-{kind}",
                        kind="student-message",
                        at_seconds=at_seconds,
                        payload={
                            "turn_kind": kind,
                            "message": _question(case_id, kind),
                        },
                    )
                    for at_seconds, kind in turn_schedule
                ]
                if trajectory <= 10:
                    events.append(
                        AutonomyEvaluationEventV1(
                            event_id=f"{case_id}-restart",
                            kind="runtime-restart",
                            at_seconds=1_200,
                        )
                    )
                if trajectory <= 5:
                    events.append(
                        AutonomyEvaluationEventV1(
                            event_id=f"{case_id}-provider-failure",
                            kind="provider-failure",
                            at_seconds=2_400,
                        )
                    )
                duration = 7_200
                if condition == "t1-v2-autonomous":
                    events.append(
                        AutonomyEvaluationEventV1(
                            event_id=f"{case_id}-day-1",
                            kind="time-advanced",
                            at_seconds=DAY,
                        )
                    )
                    duration = DAY + 21_600
                events.sort(key=lambda event: (event.at_seconds, event.event_id))
                case = AutonomyEvaluationCaseV1(
                    case_id=case_id,
                    course_id=course_id,
                    release_id=release_id,
                    learner_id=learner_id,
                    duration_seconds=duration,
                    events=events,
                )
                expected = []
                for number, (at_seconds, _kind) in enumerate(turn_schedule, start=1):
                    if trajectory <= 5 and number == 4:
                        action = "no-action"
                    else:
                        action = (
                            "ask-diagnostic-question"
                            if condition
                            in {
                                "t1-v1-reactive-control",
                                "t1-v2-reactive",
                                "t1-v2-autonomous",
                            }
                            and number == 1
                            else "provide-hint-or-example"
                        )
                    expected.append(
                        _expected(
                            case=case,
                            number=number,
                            action=action,
                            earliest=at_seconds,
                            latest=at_seconds,
                        )
                    )
                if condition == "t1-v2-autonomous" and trajectory > 5:
                    expected.append(
                        _expected(
                            case=case,
                            number=5,
                            action="send-in-app-check-in",
                            earliest=DAY,
                            latest=DAY + 21_600,
                        )
                    )
                rows.append(
                    (
                        condition,
                        case,
                        AutonomyEvaluationGoldV1(
                            case_id=case_id,
                            expected_actions=expected,
                            expected_terminal_goal_status=(
                                "active" if condition == "t1-v2-autonomous" else "none"
                            ),
                            required_invariants=INVARIANTS,
                        ),
                    )
                )
    return rows


def _long_horizon_cases() -> list[
    tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]
]:
    rows = []
    for learner in range(1, 101):
        case_id = f"long-horizon-{learner:03d}"
        events = [
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-practice",
                kind="practice-outcome",
                at_seconds=0,
                payload={
                    "outcome": "incomplete",
                    "message": _question(case_id, "partial-attempt"),
                },
            ),
            *[
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-day-{day:02d}",
                    kind="time-advanced",
                    at_seconds=day * DAY,
                )
                for day in range(1, 31)
            ],
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-restart",
                kind="runtime-restart",
                at_seconds=15 * DAY + 60,
            ),
        ]
        terminal = "expired"
        expected_specs: list[tuple[str, int, int]] = [("provide-hint-or-example", 0, 0)]
        if learner <= 25:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-consent-off",
                    kind="consent-changed",
                    at_seconds=43_200,
                    payload={"enabled": False},
                )
            )
            terminal = "cancelled"
        elif learner <= 50:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-membership-off",
                    kind="membership-changed",
                    at_seconds=43_200,
                    payload={"active": False},
                )
            )
            terminal = "cancelled"
        elif learner <= 75:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-release-change",
                    kind="release-changed",
                    at_seconds=43_200,
                    payload={"new_release": "future-release"},
                )
            )
            terminal = "cancelled"
        else:
            expected_specs.extend(
                ("send-in-app-check-in", day * DAY, day * DAY + 21_600)
                for day in (1, 2, 3)
            )
        events.sort(key=lambda event: (event.at_seconds, event.event_id))
        case = AutonomyEvaluationCaseV1(
            case_id=case_id,
            course_id="public-course-long-horizon",
            release_id="public-release-long-horizon-v1",
            learner_id=f"public-student-long-{learner:03d}",
            duration_seconds=30 * DAY + 300,
            events=events,
        )
        expected = [
            _expected(
                case=case,
                number=number,
                action=action,
                earliest=earliest,
                latest=latest,
            )
            for number, (action, earliest, latest) in enumerate(expected_specs, start=1)
        ]
        rows.append(
            (
                "t1-v2-autonomous",
                case,
                AutonomyEvaluationGoldV1(
                    case_id=case_id,
                    expected_actions=expected,
                    expected_terminal_goal_status=terminal,
                    required_invariants=INVARIANTS,
                ),
            )
        )
    return rows


def _opportunity_cases() -> list[
    tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]
]:
    rows = []
    for number in range(1, 121):
        case_id = f"opportunity-{number:03d}"
        events = [
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-practice",
                kind="practice-outcome",
                at_seconds=0,
                payload={
                    "outcome": "incomplete",
                    "message": _question(case_id, "partial-attempt"),
                },
            ),
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-day-1",
                kind="time-advanced",
                at_seconds=DAY,
            ),
        ]
        expected_specs: list[tuple[str, int, int]] = [("provide-hint-or-example", 0, 0)]
        if number <= 80:
            expected_specs.append(("send-in-app-check-in", DAY, DAY + 21_600))
            terminal = "active"
        elif number <= 100:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-consent-off",
                    kind="consent-changed",
                    at_seconds=43_200,
                    payload={"enabled": False},
                )
            )
            terminal = "cancelled"
        elif number <= 110:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-release-change",
                    kind="release-changed",
                    at_seconds=43_200,
                    payload={"new_release": "future-release"},
                )
            )
            terminal = "cancelled"
        else:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-provider-failure",
                    kind="provider-failure",
                    at_seconds=82_800,
                )
            )
            terminal = "active"
        events.sort(key=lambda event: (event.at_seconds, event.event_id))
        case = AutonomyEvaluationCaseV1(
            case_id=case_id,
            course_id="public-course-opportunity",
            release_id="public-release-opportunity-v1",
            learner_id=f"public-student-opportunity-{number:03d}",
            duration_seconds=DAY + 21_600,
            events=events,
        )
        expected = [
            _expected(
                case=case,
                number=index,
                action=action,
                earliest=earliest,
                latest=latest,
            )
            for index, (action, earliest, latest) in enumerate(expected_specs, start=1)
        ]
        rows.append(
            (
                "t1-v2-autonomous",
                case,
                AutonomyEvaluationGoldV1(
                    case_id=case_id,
                    expected_actions=expected,
                    expected_terminal_goal_status=terminal,
                    required_invariants=INVARIANTS,
                ),
            )
        )
    return rows


def build_contract() -> list[
    tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]
]:
    return [*_trajectory_cases(), *_long_horizon_cases(), *_opportunity_cases()]


def public_payload() -> dict[str, Any]:
    rows = [
        {"condition": condition, "case": case.model_dump(mode="json")}
        for condition, case, _gold in build_contract()
    ]
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": len(rows),
        "rows": rows,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def hidden_gold_payload() -> dict[str, Any]:
    rows = [
        gold.model_dump(mode="json") for _condition, _case, gold in build_contract()
    ]
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
        raise ValueError("actual-product evaluation instrument identity drifted")
    if instrument.get("status") not in {
        "reviewed-build-only",
        "frozen-pending-execution",
    }:
        raise ValueError("actual-product evaluation status is invalid")
    authority = instrument["authority"]
    if instrument["status"] == "reviewed-build-only" and any(
        authority[key]
        for key in (
            "provider_execution_authorized",
            "paid_execution_authorized",
            "automatic_promotion",
        )
    ):
        raise ValueError("actual-product build gained execution authority")
    if instrument["status"] == "frozen-pending-execution" and (
        authority["provider_execution_authorized"] is not True
        or authority["paid_execution_authorized"] is not True
        or authority["automatic_promotion"] is not False
    ):
        raise ValueError("actual-product frozen authority drifted")
    contract = build_contract()
    case_ids = [case.case_id for _condition, case, _gold in contract]
    gold_ids = [gold.case_id for _condition, _case, gold in contract]
    if (
        len(contract) != 820
        or len(case_ids) != len(set(case_ids))
        or set(case_ids) != set(gold_ids)
    ):
        raise ValueError("820-case identity contract drifted")
    public = public_payload()
    hidden = hidden_gold_payload()
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("public package hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("hidden-gold package hash drifted")
    trajectory_rows = [
        row for row in contract if row[1].case_id.startswith("trajectory-")
    ]
    long_rows = [row for row in contract if row[1].case_id.startswith("long-horizon-")]
    opportunity_rows = [
        row for row in contract if row[1].case_id.startswith("opportunity-")
    ]
    if (len(trajectory_rows), len(long_rows), len(opportunity_rows)) != (600, 100, 120):
        raise ValueError("portfolio distribution drifted")
    if not all(
        any(event.at_seconds >= DAY for event in case.events)
        for _condition, case, _gold in long_rows + opportunity_rows
    ):
        raise ValueError("long-horizon contract bypasses the real +24h boundary")
    if {source_template_number(case_id) for case_id in case_ids} != set(range(1, 51)):
        raise ValueError("source-disjoint template coverage drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "passed-frozen-pending-execution"
            if instrument["status"] == "frozen-pending-execution"
            else "passed-build-only"
        ),
        "case_count": 820,
        "trajectory_case_count": 600,
        "long_horizon_case_count": 100,
        "proactive_opportunity_case_count": 120,
        "source_template_count": 50,
        "public_sha256": public["content_sha256"],
        "hidden_gold_sha256": hidden["content_sha256"],
        "provider_execution_authorized": authority[
            "provider_execution_authorized"
        ],
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
