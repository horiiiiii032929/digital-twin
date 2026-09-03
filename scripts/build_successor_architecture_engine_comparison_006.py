#!/usr/bin/env python3
"""Build the 300-context E1-E4 engine-allocation comparison package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.build_successor_architecture_development_fold_001 import (
    _expected_action,
    _hidden_knows,
    _realized_action_utilities,
    canonical_hash,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)
from src.digital_twin.student.planning_architectures import PlanningStateCardV1


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "successor-architecture-engine-comparison-006"
PUBLIC_PATH = ROOT / (
    "research/05_evaluation/"
    "successor_architecture_engine_comparison_006_public.json"
)
GOLD_PATH = ROOT / (
    "research/05_evaluation/"
    "successor_architecture_engine_comparison_006_gold.json"
)
EVENTS = (
    AutonomousEventKind.STUDENT_MESSAGE,
    AutonomousEventKind.MISCONCEPTION,
    AutonomousEventKind.REPEATED_CONFUSION,
    AutonomousEventKind.PRACTICE_INCOMPLETE,
)
GUARDS = (
    "consent-withdrawn",
    "membership-inactive",
    "release-mismatch",
    "quiet-hours",
    "frequency-or-cooldown",
    "evidence-incomplete",
)


def _state(index: int, event_index: int, *, boundary: bool) -> PlanningStateCardV1:
    mastery_band = (index * 5 + event_index * 7 + (3 if boundary else 0)) % 9
    uncertainty_band = (index * 13 + event_index * 2 + (4 if boundary else 0)) % 9
    event = EVENTS[event_index]
    streak = (
        (index % 4) + 1
        if event
        in {AutonomousEventKind.MISCONCEPTION, AutonomousEventKind.PRACTICE_INCOMPLETE}
        else 2
        if event == AutonomousEventKind.REPEATED_CONFUSION
        else index % 2
    )
    return PlanningStateCardV1(
        concept_id=f"engine-006-concept-{event_index + 1:02d}-{index + 1:03d}",
        mastery_probability=0.1 + mastery_band * 0.1,
        uncertainty=0.1 + uncertainty_band * 0.1,
        assessed_evidence_count=(index * 5 + event_index) % 8,
        recent_incorrect_streak=streak,
        days_since_last_observation=float((index * 7 + event_index) % 14 + 1),
        goal_progress=((index * 11 + event_index * 3) % 19) / 20,
        goal_attempts_remaining=(index * 2 + event_index) % 3 + 1,
    )


def _eligible_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for event_index, event in enumerate(EVENTS):
        for index in range(60):
            case_id = f"engine-006-{event.value}-{index + 1:03d}"
            state = _state(index, event_index, boundary=False)
            expected = _expected_action(event, state)
            learner_knows = _hidden_knows(case_id, state.mastery_probability)
            evidence = (
                f"The approved source identifies {state.concept_id} as the current "
                "learning target for this activity."
            )
            public.append(
                {
                    "case_id": case_id,
                    "scenario_cluster_id": (
                        f"engine-006-cluster-{event_index + 1:02d}-{index + 1:03d}"
                    ),
                    "event_kind": event.value,
                    "state_card": state.model_dump(mode="json"),
                    "guard": "eligible",
                    "membership_active": True,
                    "consent_active": True,
                    "current_release_matches": True,
                    "within_quiet_hours": False,
                    "recent_message_count": 0,
                    "same_concept_cooldown_active": False,
                    "evidence_ready": True,
                    "evidence_quote": evidence,
                    "objective": (
                        "Choose and phrase one source-grounded next teaching move for "
                        f"engine context {event_index + 1:02d}-{index + 1:03d}."
                    ),
                }
            )
            gold.append(
                {
                    "case_id": case_id,
                    "expected_action": expected.value,
                    "acceptable_actions": [expected.value],
                    "hidden_learner_knows": learner_knows,
                    "action_utilities": _realized_action_utilities(
                        event, state, learner_knows=learner_knows
                    ),
                    "reference_kind": "synthetic-pedagogical-policy-oracle-v1",
                }
            )
    return public, gold


def _boundary_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    for index in range(60):
        guard = GUARDS[index % len(GUARDS)]
        event_index = (index * 3) % len(EVENTS)
        event = EVENTS[event_index]
        case_id = f"engine-006-boundary-{index + 1:03d}"
        state = _state(index, event_index, boundary=True)
        public.append(
            {
                "case_id": case_id,
                "scenario_cluster_id": f"engine-006-boundary-cluster-{index + 1:03d}",
                "event_kind": event.value,
                "state_card": state.model_dump(mode="json"),
                "guard": guard,
                "membership_active": guard != "membership-inactive",
                "consent_active": guard != "consent-withdrawn",
                "current_release_matches": guard != "release-mismatch",
                "within_quiet_hours": guard == "quiet-hours",
                "recent_message_count": 3 if guard == "frequency-or-cooldown" else 0,
                "same_concept_cooldown_active": guard == "frequency-or-cooldown",
                "evidence_ready": guard != "evidence-incomplete",
                "evidence_quote": None,
                "objective": (
                    "Respect the deterministic authority boundary for engine context "
                    f"{index + 1:03d}."
                ),
            }
        )
        gold.append(
            {
                "case_id": case_id,
                "expected_action": AutonomousActionKind.NO_ACTION.value,
                "acceptable_actions": [AutonomousActionKind.NO_ACTION.value],
                "hidden_learner_knows": _hidden_knows(
                    case_id, state.mastery_probability
                ),
                "action_utilities": {
                    action.value: (
                        1.0 if action == AutonomousActionKind.NO_ACTION else -1.0
                    )
                    for action in AutonomousActionKind
                },
                "reference_kind": "deterministic-authority-boundary-v1",
            }
        )
    return public, gold


def build_packages() -> tuple[dict[str, Any], dict[str, Any]]:
    eligible_public, eligible_gold = _eligible_rows()
    boundary_public, boundary_gold = _boundary_rows()
    public_rows = eligible_public + boundary_public
    gold_rows = eligible_gold + boundary_gold
    public = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "fold_id": "fresh-engine-allocation-comparison-006",
        "case_count": len(public_rows),
        "scenario_cluster_count": len(public_rows),
        "model_visible_fields_exclude_gold": True,
        "rows": public_rows,
    }
    gold = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "fold_id": "fresh-engine-allocation-comparison-006",
        "case_count": len(gold_rows),
        "gold_opening_rule": "after-all-engine-allocation-responses-are-durable",
        "preferred_action_is_diagnostic_not_transition_validity": True,
        "rows": gold_rows,
    }
    public["content_sha256"] = canonical_hash(public)
    gold["content_sha256"] = canonical_hash(gold)
    return public, gold


def validate() -> dict[str, Any]:
    public, gold = build_packages()
    public_ids = [str(row["case_id"]) for row in public["rows"]]
    gold_ids = [str(row["case_id"]) for row in gold["rows"]]
    clusters = [str(row["scenario_cluster_id"]) for row in public["rows"]]
    if public_ids != gold_ids or len(public_ids) != len(set(public_ids)):
        raise ValueError("engine-comparison case identities drifted")
    if len(public_ids) != 300 or len(clusters) != len(set(clusters)):
        raise ValueError("engine comparison requires 300 unique scenario clusters")
    if sum(row["guard"] == "eligible" for row in public["rows"]) != 240:
        raise ValueError("engine comparison requires 240 eligible cases")
    serialized = json.dumps(public, sort_keys=True)
    for forbidden in (
        "expected_action",
        "acceptable_actions",
        "hidden_learner_knows",
        "action_utilities",
    ):
        if forbidden in serialized:
            raise ValueError(f"public engine package contains hidden gold: {forbidden}")
    historical_ids: set[str] = set()
    for path in (ROOT / "research/05_evaluation").glob(
        "successor_architecture_*_public.json"
    ):
        if path == PUBLIC_PATH:
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        historical_ids.update(str(row["case_id"]) for row in value.get("rows", []))
    if historical_ids & set(public_ids):
        raise ValueError("engine comparison overlaps a historical architecture package")
    return {
        "dataset_id": DATASET_ID,
        "case_count": 300,
        "eligible_case_count": 240,
        "boundary_case_count": 60,
        "scenario_cluster_count": 300,
        "engine_allocation_cell_count": 1200,
        "public_sha256": public["content_sha256"],
        "gold_sha256": gold["content_sha256"],
        "gold_isolated": True,
        "historical_case_ids_disjoint": True,
        "provider_calls": 0,
        "status": "passed",
    }


def write() -> dict[str, Any]:
    public, gold = build_packages()
    PUBLIC_PATH.write_text(
        json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    GOLD_PATH.write_text(
        json.dumps(gold, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return validate()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = write() if args.write else validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
