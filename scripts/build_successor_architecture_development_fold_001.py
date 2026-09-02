#!/usr/bin/env python3
"""Build the first fresh, gold-isolated autonomy architecture fold."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.student.autonomy_eligibility import (
    event_scoped_eligible_actions,
)
from src.digital_twin.student.autonomy_models import (
    AutonomousActionKind,
    AutonomousEventKind,
)
from src.digital_twin.student.planning_architectures import PlanningStateCardV1


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_PATH = ROOT / (
    "research/05_evaluation/"
    "successor_architecture_development_fold_001_public.json"
)
GOLD_PATH = ROOT / (
    "research/05_evaluation/"
    "successor_architecture_development_fold_001_gold.json"
)
DATASET_ID = "successor-architecture-development-fold-001"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _hidden_knows(case_id: str, mastery: float) -> bool:
    draw = int(hashlib.sha256(case_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return draw < mastery


def _expected_action(
    event_kind: AutonomousEventKind,
    state: PlanningStateCardV1,
) -> AutonomousActionKind:
    if event_kind == AutonomousEventKind.STUDENT_MESSAGE:
        return (
            AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
            if state.uncertainty >= 0.55
            else AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
        )
    if event_kind == AutonomousEventKind.MISCONCEPTION:
        return (
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
            if state.recent_incorrect_streak >= 2 and state.uncertainty <= 0.7
            else AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
        )
    if event_kind == AutonomousEventKind.REPEATED_CONFUSION:
        return AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
    if event_kind == AutonomousEventKind.PRACTICE_INCOMPLETE:
        return (
            AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE
            if state.recent_incorrect_streak >= 2
            else AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION
        )
    raise ValueError(f"unsupported choice event: {event_kind}")


def _realized_action_utilities(
    event_kind: AutonomousEventKind,
    state: PlanningStateCardV1,
    *,
    learner_knows: bool,
) -> dict[str, float]:
    """Score realized pedagogical utility without exposing latent state.

    The architecture sees only ``PlanningStateCardV1``.  The evaluator also
    samples one reproducible latent learner outcome and uses it to distinguish
    an intervention that was merely rubric-acceptable from one that was useful
    for that simulated learner.  This keeps policy utility independent from the
    binary acceptable-move label.
    """

    eligible = event_scoped_eligible_actions(event_kind, list(AutonomousActionKind))
    utilities = {action.value: -1.0 for action in AutonomousActionKind}
    utilities[AutonomousActionKind.NO_ACTION.value] = 0.0
    if AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION in eligible:
        diagnostic = 0.45 + 0.30 * state.uncertainty
        diagnostic += 0.15 if not learner_knows else 0.0
        if event_kind == AutonomousEventKind.MISCONCEPTION:
            diagnostic += 0.08
        utilities[AutonomousActionKind.ASK_DIAGNOSTIC_QUESTION.value] = min(
            1.0, diagnostic
        )
    if AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE in eligible:
        hint = 0.40 + 0.25 * (1.0 - state.mastery_probability)
        hint += 0.15 if state.recent_incorrect_streak >= 2 else 0.0
        hint += 0.15 if not learner_knows else 0.0
        if event_kind == AutonomousEventKind.REPEATED_CONFUSION:
            hint += 0.08
        utilities[AutonomousActionKind.PROVIDE_HINT_OR_EXAMPLE.value] = min(1.0, hint)
    return utilities


def _choice_rows(
    *, fold_number: int = 1
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    events = (
        AutonomousEventKind.STUDENT_MESSAGE,
        AutonomousEventKind.MISCONCEPTION,
        AutonomousEventKind.REPEATED_CONFUSION,
        AutonomousEventKind.PRACTICE_INCOMPLETE,
    )
    shift = 0 if fold_number == 1 else 7
    for event_index, event_kind in enumerate(events):
        for index in range(30):
            case_id = f"fold-{fold_number:03d}-{event_kind.value}-{index + 1:03d}"
            shifted_index = index + shift
            band = shifted_index % 5
            mastery = (0.15, 0.35, 0.55, 0.75, 0.9)[band]
            uncertainty = (0.85, 0.7, 0.5, 0.3, 0.15)[band]
            incorrect_streak = (
                (shifted_index % 3) + 1
                if event_kind
                in {
                    AutonomousEventKind.MISCONCEPTION,
                    AutonomousEventKind.PRACTICE_INCOMPLETE,
                }
                else 2 if event_kind == AutonomousEventKind.REPEATED_CONFUSION else 0
            )
            state = PlanningStateCardV1(
                concept_id=(
                    f"concept-{event_index + 1:02d}-{index % 10:02d}"
                    if fold_number == 1
                    else f"fold-{fold_number:03d}-concept-{event_index + 1:02d}-{shifted_index % 10:02d}"
                ),
                mastery_probability=mastery,
                uncertainty=uncertainty,
                assessed_evidence_count=shifted_index % 6,
                recent_incorrect_streak=incorrect_streak,
                days_since_last_observation=float((shifted_index % 8) + 1),
                goal_progress=min(0.9, (shifted_index % 10) / 10),
                goal_attempts_remaining=max(1, 3 - (shifted_index % 3)),
            )
            expected = _expected_action(event_kind, state)
            learner_knows = _hidden_knows(case_id, mastery)
            public.append(
                {
                    "case_id": case_id,
                    "event_kind": event_kind.value,
                    "state_card": state.model_dump(mode="json"),
                    "guard": "eligible",
                    "membership_active": True,
                    "consent_active": True,
                    "current_release_matches": True,
                    "within_quiet_hours": False,
                    "recent_message_count": 0,
                    "same_concept_cooldown_active": False,
                    "evidence_ready": True,
                    "objective": (
                        "Explain why a durable checkpoint prevents a committed "
                        f"action from repeating ({event_index + 1:02d}-{index % 10:02d})."
                        if fold_number == 1
                        else "Choose an evidence-grounded teaching move for "
                        f"fold {fold_number:03d}, concept {event_index + 1:02d}-{shifted_index % 10:02d}."
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
                        event_kind,
                        state,
                        learner_knows=learner_knows,
                    ),
                    "reference_kind": "synthetic-pedagogical-policy-oracle-v1",
                }
            )
    return public, gold


def _boundary_rows(
    *, fold_number: int = 1
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public: list[dict[str, Any]] = []
    gold: list[dict[str, Any]] = []
    guards = (
        "consent-withdrawn",
        "membership-inactive",
        "release-mismatch",
        "quiet-hours",
        "frequency-or-cooldown",
        "evidence-incomplete",
    )
    shift = 0 if fold_number == 1 else 2
    for guard_index, guard in enumerate(guards):
        for index in range(5):
            case_id = (
                f"fold-{fold_number:03d}-boundary-"
                f"{guard_index + 1:02d}-{index + 1:02d}"
            )
            shifted_index = index + shift
            state = PlanningStateCardV1(
                concept_id=(
                    f"boundary-concept-{guard_index + 1:02d}"
                    if fold_number == 1
                    else f"fold-{fold_number:03d}-boundary-concept-{guard_index + 1:02d}"
                ),
                mastery_probability=0.2 + (shifted_index % 5) * 0.15,
                uncertainty=0.8 - (shifted_index % 5) * 0.12,
                assessed_evidence_count=shifted_index % 5,
                recent_incorrect_streak=2,
                days_since_last_observation=float((shifted_index % 5) + 1),
                goal_progress=(shifted_index % 5) * 0.15,
                goal_attempts_remaining=3 - min(shifted_index % 5, 2),
            )
            public.append(
                {
                    "case_id": case_id,
                    "event_kind": AutonomousEventKind.MISCONCEPTION.value,
                    "state_card": state.model_dump(mode="json"),
                    "guard": guard,
                    "membership_active": guard != "membership-inactive",
                    "consent_active": guard != "consent-withdrawn",
                    "current_release_matches": guard != "release-mismatch",
                    "within_quiet_hours": guard == "quiet-hours",
                    "recent_message_count": 3 if guard == "frequency-or-cooldown" else 0,
                    "same_concept_cooldown_active": guard == "frequency-or-cooldown",
                    "evidence_ready": guard != "evidence-incomplete",
                    "objective": (
                        "Explain why a durable checkpoint prevents a committed "
                        f"action from repeating (boundary-{guard_index + 1:02d})."
                        if fold_number == 1
                        else "Respect the deterministic authority boundary for "
                        f"fold {fold_number:03d}, guard {guard_index + 1:02d}."
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


def build_packages(
    *, fold_number: int = 1
) -> tuple[dict[str, Any], dict[str, Any]]:
    if fold_number not in {1, 2}:
        raise ValueError("only preregistered development folds 001 and 002 are supported")
    choice_public, choice_gold = _choice_rows(fold_number=fold_number)
    boundary_public, boundary_gold = _boundary_rows(fold_number=fold_number)
    public_rows = choice_public + boundary_public
    gold_rows = choice_gold + boundary_gold
    dataset_id = f"successor-architecture-development-fold-{fold_number:03d}"
    fold_id = f"development-fold-{fold_number:03d}"
    public = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "fold_id": fold_id,
        "case_count": len(public_rows),
        "model_visible_fields_exclude_gold": True,
        "rows": public_rows,
    }
    gold = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "fold_id": fold_id,
        "case_count": len(gold_rows),
        "gold_opening_rule": "after-all-architecture-responses-are-durable",
        "rows": gold_rows,
    }
    public["content_sha256"] = canonical_hash(public)
    gold["content_sha256"] = canonical_hash(gold)
    return public, gold


def validate(*, fold_number: int = 1) -> dict[str, Any]:
    public, gold = build_packages(fold_number=fold_number)
    public_ids = [row["case_id"] for row in public["rows"]]
    gold_ids = [row["case_id"] for row in gold["rows"]]
    if public_ids != gold_ids or len(public_ids) != len(set(public_ids)):
        raise ValueError("development fold case identities drifted")
    if len(public_ids) != 150:
        raise ValueError("development fold must contain 150 cases")
    serialized_public = json.dumps(public, sort_keys=True)
    if any(
        forbidden in serialized_public
        for forbidden in (
            "expected_action",
            "acceptable_actions",
            "hidden_learner_knows",
            "action_utilities",
        )
    ):
        raise ValueError("public development package contains hidden gold")
    return {
        "dataset_id": f"successor-architecture-development-fold-{fold_number:03d}",
        "case_count": 150,
        "choice_case_count": 120,
        "boundary_case_count": 30,
        "public_sha256": public["content_sha256"],
        "gold_sha256": gold["content_sha256"],
        "gold_isolated": True,
        "provider_calls": 0,
        "status": "passed",
    }


def write(*, fold_number: int = 1) -> dict[str, Any]:
    public, gold = build_packages(fold_number=fold_number)
    public_path = (
        PUBLIC_PATH
        if fold_number == 1
        else ROOT
        / "research/05_evaluation/successor_architecture_development_fold_002_public.json"
    )
    gold_path = (
        GOLD_PATH
        if fold_number == 1
        else ROOT
        / "research/05_evaluation/successor_architecture_development_fold_002_gold.json"
    )
    public_path.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n")
    gold_path.write_text(json.dumps(gold, indent=2, sort_keys=True) + "\n")
    return validate(fold_number=fold_number)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--fold", choices=(1, 2), type=int, default=1)
    args = parser.parse_args()
    print(
        json.dumps(
            write(fold_number=args.fold)
            if args.write
            else validate(fold_number=args.fold),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
