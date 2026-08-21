"""Validate the build-only T0/T1 tutoring-graph evaluation contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/autonomous_tutoring_graph_contract_v1.json"
)
EXPECTED_CATEGORIES = {
    "direct-question",
    "repeated-confusion",
    "partial-attempt",
    "misconception",
    "ambiguity",
    "no-evidence",
    "academic-integrity",
    "course-boundary",
    "provider-failure",
    "restart-consistency",
}
EXPECTED_INTENTS = {
    "clarify_request",
    "diagnose_understanding",
    "ask_next_step",
    "give_hint",
    "correct_misconception",
    "explain_concept",
    "refuse_and_redirect",
    "abstain_no_evidence",
}


def validate_instrument(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    require(
        payload.get("instrument_id") == "autonomous-tutoring-graph-contract-v1",
        "instrument ID drifted",
    )
    require(
        payload.get("status") == "frozen-network-free-development",
        "instrument must remain frozen and network-free",
    )
    conditions = payload.get("conditions", {})
    require(conditions.get("control") == "T0-grounded-assistant", "T0 is missing")
    require(
        conditions.get("candidate") == "T1-bounded-tutoring-graph",
        "T1 is missing",
    )
    execution = payload.get("execution", {})
    require(execution.get("provider_calls_authorized") is False, "provider calls enabled")
    require(execution.get("paid_execution_authorized") is False, "paid run enabled")
    require(execution.get("held_out_execution_authorized") is False, "held-out run enabled")
    require(execution.get("network_required") is False, "network dependency introduced")
    require(
        execution.get("network_free_development_authorized") is True,
        "network-free development execution is not authorized",
    )
    require(execution.get("automatic_promotion") is False, "automatic promotion enabled")
    require(execution.get("maximum_repairs_per_turn") == 1, "repair bound drifted")
    require(execution.get("maximum_graph_steps_per_turn") == 12, "step bound drifted")

    trajectories = payload.get("development_trajectories", [])
    identifiers = [item.get("id") for item in trajectories]
    categories = {item.get("category") for item in trajectories}
    require(len(trajectories) == 10, "expected exactly ten development trajectories")
    require(len(identifiers) == len(set(identifiers)), "trajectory IDs must be unique")
    require(categories == EXPECTED_CATEGORIES, "trajectory category coverage drifted")
    observed_intents = {
        turn.get("expected_intent")
        for trajectory in trajectories
        for turn in trajectory.get("turns", [])
    }
    require(observed_intents <= EXPECTED_INTENTS, "unknown expected tutoring intent")
    require(EXPECTED_INTENTS <= observed_intents, "required intent coverage is incomplete")
    require(
        all(
            turn.get("expected_t0_action") and turn.get("expected_t1_action")
            for trajectory in trajectories
            for turn in trajectory.get("turns", [])
        ),
        "condition action expectations are incomplete",
    )
    require(
        any(turn.get("restart_before_turn") for item in trajectories for turn in item.get("turns", [])),
        "restart trajectory is missing",
    )
    require(
        any(turn.get("forced_failure") for item in trajectories for turn in item.get("turns", [])),
        "forced provider failure is missing",
    )
    gates = payload.get("hard_gates", {})
    require(len(gates) >= 9, "hard product gates are incomplete")
    require(
        payload.get("decision_rule", {}).get("prompt_only_repeat_loop_allowed") is False,
        "prompt-only repeat loop must remain prohibited",
    )
    result = payload.get("result_contract", {})
    require(
        result.get("run_id") == "autonomous-tutoring-graph-development-001",
        "development run identity drifted",
    )
    require(result.get("expected_trajectory_count") == 10, "trajectory count drifted")
    require(
        result.get("expected_turn_count_per_condition") == 13,
        "condition turn count drifted",
    )
    require(
        set(result.get("allowed_statuses", []))
        == {"invalid-execution", "completed-refine", "completed-go-deeper"},
        "result status contract drifted",
    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=DEFAULT_PATH)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text(encoding="utf-8"))
    errors = validate_instrument(payload)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("Autonomous tutoring graph instrument: passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
