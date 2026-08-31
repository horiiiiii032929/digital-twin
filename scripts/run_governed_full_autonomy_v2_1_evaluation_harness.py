"""Build and simulate the flow-independent full-autonomy evaluation harness."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation import (
    AutonomyEvaluationCaseV1,
    AutonomyEvaluationEventV1,
    AutonomyEvaluationGoldV1,
    AutonomyObservedActionV1,
    AutonomyStateSnapshotV1,
    AutonomySystemManifestV1,
    CallbackAutonomyEvaluationAdapterV1,
    ExpectedAutonomyActionV1,
    run_autonomy_case,
    score_autonomy_case,
    summarize_autonomy_scores,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_evaluation_harness_001.json"
)
INSTRUMENT_ID = "governed-full-autonomy-v2-1-evaluation-harness-001"
CONDITIONS = (
    "t0-grounded-control",
    "t1-v1-reactive-control",
    "t1-v2-reactive",
    "t1-v2-autonomous",
)
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


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _expected(
    *,
    case_id: str,
    number: int,
    action: str,
    at_seconds: int,
    course_id: str,
    release_id: str,
    learner_id: str,
) -> ExpectedAutonomyActionV1:
    return ExpectedAutonomyActionV1(
        expectation_id=f"expected-{case_id}-{number:03d}",
        action=action,
        earliest_seconds=at_seconds,
        latest_seconds=at_seconds + 300,
        recipient_id=learner_id,
        course_id=course_id,
        release_id=release_id,
        must_have_valid_lineage=action != "no-action",
    )


def _trajectory_cases() -> list[tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]]:
    rows = []
    for trajectory in range(1, 51):
        for condition in CONDITIONS:
            for seed in range(1, 4):
                case_id = f"trajectory-{trajectory:03d}-{condition}-seed-{seed}"
                course_id = f"course-{(trajectory - 1) % 4 + 1}"
                release_id = f"release-{course_id}-v1"
                learner_id = f"student-trajectory-{trajectory:03d}"
                events = [
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-direct",
                        kind="student-message",
                        at_seconds=0,
                        payload={"turn_kind": "direct"},
                    ),
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-partial",
                        kind="student-message",
                        at_seconds=60,
                        payload={"turn_kind": "partial-attempt"},
                    ),
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-confusion",
                        kind="student-message",
                        at_seconds=120,
                        payload={"turn_kind": "confusion"},
                    ),
                    AutonomyEvaluationEventV1(
                        event_id=f"{case_id}-repeated",
                        kind="student-message",
                        at_seconds=180,
                        payload={"turn_kind": "repeated-confusion"},
                    ),
                ]
                if trajectory <= 10:
                    events.append(
                        AutonomyEvaluationEventV1(
                            event_id=f"{case_id}-restart",
                            kind="runtime-restart",
                            at_seconds=90,
                        )
                    )
                if trajectory <= 5:
                    events.append(
                        AutonomyEvaluationEventV1(
                            event_id=f"{case_id}-provider-failure",
                            kind="provider-failure",
                            at_seconds=150,
                        )
                    )
                events.sort(key=lambda item: (item.at_seconds, item.event_id))
                expected = []
                for index, at_seconds in enumerate((0, 60, 120, 180), start=1):
                    if condition == "t0-grounded-control":
                        action = "provide-hint-or-example"
                    elif index <= 2:
                        action = "provide-hint-or-example"
                    else:
                        action = "ask-diagnostic-question"
                    expected.append(
                        _expected(
                            case_id=case_id,
                            number=index,
                            action=action,
                            at_seconds=at_seconds,
                            course_id=course_id,
                            release_id=release_id,
                            learner_id=learner_id,
                        )
                    )
                if condition == "t1-v2-autonomous":
                    expected.append(
                        _expected(
                            case_id=case_id,
                            number=5,
                            action="issue-retrieval-practice",
                            at_seconds=300,
                            course_id=course_id,
                            release_id=release_id,
                            learner_id=learner_id,
                        )
                    )
                case = AutonomyEvaluationCaseV1(
                    case_id=case_id,
                    course_id=course_id,
                    release_id=release_id,
                    learner_id=learner_id,
                    duration_seconds=600,
                    events=events,
                )
                gold = AutonomyEvaluationGoldV1(
                    case_id=case_id,
                    expected_actions=expected,
                    expected_terminal_goal_status=(
                        "active" if condition.startswith("t1-v2") else "none"
                    ),
                    required_invariants=INVARIANTS,
                )
                rows.append((condition, case, gold))
    return rows


def _long_horizon_cases() -> list[tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]]:
    rows = []
    day = 86_400
    for learner in range(1, 101):
        case_id = f"long-horizon-{learner:03d}"
        learner_id = f"student-long-{learner:03d}"
        events = [
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-practice",
                kind="practice-outcome",
                at_seconds=0,
                payload={"outcome": "incomplete"},
            ),
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-restart",
                kind="runtime-restart",
                at_seconds=15 * day,
            ),
        ]
        cancelled = learner <= 50
        if cancelled:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-consent-off",
                    kind="consent-changed",
                    at_seconds=21 * day,
                    payload={"enabled": False},
                )
            )
        if learner <= 25:
            events.append(
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-release-change",
                    kind="release-changed",
                    at_seconds=22 * day,
                    payload={"new_release": "future-release"},
                )
            )
        events.sort(key=lambda item: (item.at_seconds, item.event_id))
        expected = [
            _expected(
                case_id=case_id,
                number=index,
                action="issue-retrieval-practice",
                at_seconds=at_seconds,
                course_id="course-long",
                release_id="release-course-long-v1",
                learner_id=learner_id,
            )
            for index, at_seconds in enumerate((0, 7 * day, 14 * day), start=1)
        ]
        case = AutonomyEvaluationCaseV1(
            case_id=case_id,
            course_id="course-long",
            release_id="release-course-long-v1",
            learner_id=learner_id,
            duration_seconds=30 * day,
            events=events,
        )
        gold = AutonomyEvaluationGoldV1(
            case_id=case_id,
            expected_actions=expected,
            expected_terminal_goal_status="cancelled" if cancelled else "completed",
            required_invariants=INVARIANTS,
        )
        rows.append(("t1-v2-autonomous", case, gold))
    return rows


def _opportunity_cases() -> list[tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]]:
    rows = []
    for number in range(1, 121):
        case_id = f"opportunity-{number:03d}"
        learner_id = f"student-opportunity-{number:03d}"
        events = [
            AutonomyEvaluationEventV1(
                event_id=f"{case_id}-opportunity",
                kind="practice-outcome",
                at_seconds=0,
                payload={"outcome": "incomplete", "slice": number % 12},
            )
        ]
        eligible = number <= 80
        if 81 <= number <= 100:
            events.insert(
                0,
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-consent-off",
                    kind="consent-changed",
                    at_seconds=0,
                    payload={"enabled": False},
                ),
            )
        elif 101 <= number <= 110:
            events.insert(
                0,
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-release-change",
                    kind="release-changed",
                    at_seconds=0,
                    payload={"new_release": "future-release"},
                ),
            )
        elif number > 110:
            events.insert(
                0,
                AutonomyEvaluationEventV1(
                    event_id=f"{case_id}-provider-failure",
                    kind="provider-failure",
                    at_seconds=0,
                ),
            )
        events.sort(key=lambda item: item.event_id)
        expected = _expected(
            case_id=case_id,
            number=1,
            action="issue-retrieval-practice" if eligible else "no-action",
            at_seconds=0,
            course_id="course-opportunity",
            release_id="release-course-opportunity-v1",
            learner_id=learner_id,
        )
        case = AutonomyEvaluationCaseV1(
            case_id=case_id,
            course_id="course-opportunity",
            release_id="release-course-opportunity-v1",
            learner_id=learner_id,
            duration_seconds=600,
            events=events,
        )
        gold = AutonomyEvaluationGoldV1(
            case_id=case_id,
            expected_actions=[expected],
            expected_terminal_goal_status="active",
            required_invariants=INVARIANTS,
        )
        rows.append(("t1-v2-autonomous", case, gold))
    return rows


def build_contract() -> list[tuple[str, AutonomyEvaluationCaseV1, AutonomyEvaluationGoldV1]]:
    return [*_trajectory_cases(), *_long_horizon_cases(), *_opportunity_cases()]


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ValueError("full-autonomy harness instrument identity drifted")
    if instrument.get("status") != "reviewed-build-only":
        raise ValueError("full-autonomy harness status drifted")
    if tuple(instrument["conditions"]) != CONDITIONS:
        raise ValueError("full-autonomy condition order drifted")
    if any(instrument["authority"][key] for key in (
        "provider_execution_authorized",
        "paid_execution_authorized",
        "held_out_execution_authorized",
        "automatic_promotion",
        "provider_calls",
        "maximum_cost_usd",
    )):
        raise ValueError("build-only full-autonomy harness gained execution authority")
    contract = build_contract()
    expected_total = int(instrument["portfolio"]["total_cases"])
    if len(contract) != expected_total:
        raise ValueError("full-autonomy case count drifted")
    case_ids = [case.case_id for _, case, _ in contract]
    gold_ids = [gold.case_id for _, _, gold in contract]
    if len(case_ids) != len(set(case_ids)) or set(case_ids) != set(gold_ids):
        raise ValueError("full-autonomy public/gold identities drifted")
    public_payload = [case.model_dump(mode="json") for _, case, _ in contract]
    forbidden = {"expected_actions", "expected_terminal_goal_status", "required_invariants"}
    if any(forbidden & set(row) for row in public_payload):
        raise ValueError("full-autonomy public cases leaked gold fields")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "case_count": len(contract),
        "trajectory_case_count": 600,
        "long_horizon_case_count": 100,
        "proactive_opportunity_case_count": 120,
        "public_contract_sha256": _canonical_hash(public_payload),
        "gold_contract_sha256": _canonical_hash(
            [gold.model_dump(mode="json") for _, _, gold in contract]
        ),
        "provider_calls": 0,
        "paid_execution_authorized": False,
    }


class _ReferenceDriver:
    def __init__(self, condition: str, gold: AutonomyEvaluationGoldV1) -> None:
        self.condition = condition
        self.gold = gold
        self.case: AutonomyEvaluationCaseV1 | None = None
        self.elapsed = 0
        self.restart_count = 0

    async def reset(self, case: AutonomyEvaluationCaseV1) -> None:
        self.case = case
        self.elapsed = 0
        self.restart_count = 0

    async def submit_event(self, event: AutonomyEvaluationEventV1) -> None:
        del event

    async def advance_time(self, seconds: int) -> None:
        self.elapsed += seconds

    async def restart(self) -> None:
        self.restart_count += 1

    async def collect_actions(self) -> list[AutonomyObservedActionV1]:
        assert self.case is not None
        return [
            AutonomyObservedActionV1(
                action_id=f"reference-{item.expectation_id}",
                action=item.action,
                at_seconds=item.earliest_seconds,
                recipient_id=item.recipient_id,
                course_id=item.course_id,
                release_id=item.release_id,
                status="no-action" if item.action == "no-action" else "delivered",
                citation_lineage_valid=True,
                structured_reason="network-free reference behavior",
            )
            for item in self.gold.expected_actions
        ]

    async def snapshot_state(self) -> AutonomyStateSnapshotV1:
        assert self.case is not None
        actions = await self.collect_actions()
        return AutonomyStateSnapshotV1(
            captured_at_seconds=self.elapsed,
            active_goal_ids=(
                [f"goal-{self.case.case_id}"]
                if self.gold.expected_terminal_goal_status == "active"
                else []
            ),
            pending_opportunity_ids=[],
            delivered_action_ids=[
                item.action_id for item in actions if item.status == "delivered"
            ],
            learner_state_revision=len(actions),
            consent_active=not any(
                event.kind == "consent-changed"
                and not bool(event.payload.get("enabled"))
                for event in self.case.events
            ),
            release_id=self.case.release_id,
            policy_version=1,
            restart_count=self.restart_count,
            terminal_goal_status=self.gold.expected_terminal_goal_status,
        )

    async def collect_diagnostic_trace(self) -> dict[str, Any]:
        return {
            "condition": self.condition,
            "reference_driver": True,
            "invariant_results": {
                "bounded-loop": True,
                "restart-consistent": True,
                "no-model-owned-authority-mutation": True,
                "provider-failure-safe": True,
                "pedagogical-transition-valid": True,
            },
        }


def _adapter(condition: str, driver: _ReferenceDriver):
    manifest = AutonomySystemManifestV1(
        system_id=f"reference-{condition}",
        flow_id=condition,
        adapter_version="1.0.0",
        code_revision="network-free-harness",
        graph_version=condition,
        release_profile_sha256=hashlib.sha256(condition.encode()).hexdigest(),
        policy_version=1,
        model_bindings={"planner": "deterministic", "generator": "deterministic"},
        network_free=True,
    )
    return CallbackAutonomyEvaluationAdapterV1(
        manifest=manifest,
        reset=driver.reset,
        submit_event=driver.submit_event,
        advance_time=driver.advance_time,
        restart=driver.restart,
        collect_actions=driver.collect_actions,
        snapshot_state=driver.snapshot_state,
        collect_diagnostic_trace=driver.collect_diagnostic_trace,
    )


async def _simulate() -> dict[str, Any]:
    validation = validate()
    scores = []
    by_condition: dict[str, list] = {condition: [] for condition in CONDITIONS}
    for condition, case, gold in build_contract():
        driver = _ReferenceDriver(condition, gold)
        response = await run_autonomy_case(_adapter(condition, driver), case)
        score = score_autonomy_case(case, gold, response)
        scores.append(score)
        by_condition[condition].append(score)
    summary = summarize_autonomy_scores(scores)
    return {
        **validation,
        "status": "passed-harness-simulation"
        if summary["all_case_hard_gates_passed"]
        else "failed-harness-simulation",
        "summary": summary,
        "condition_summaries": {
            condition: summarize_autonomy_scores(condition_scores)
            for condition, condition_scores in by_condition.items()
        },
        "provider_calls": 0,
        "tokens": 0,
        "cost_usd": 0,
        "product_quality_claim": False,
    }


def simulate() -> dict[str, Any]:
    return asyncio.run(_simulate())


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    arguments = parser.parse_args()
    result = validate() if arguments.validate else simulate()
    print(json.dumps(result, indent=2, sort_keys=True))
    if str(result["status"]).startswith("failed"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
