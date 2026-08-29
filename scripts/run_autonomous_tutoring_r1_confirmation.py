#!/usr/bin/env python3
"""Validate the finite T0/T1 R1 confirmation before model selection."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / (
    "research/05_evaluation/instruments/"
    "autonomous_tutoring_r1_confirmation_001.json"
)
CASCADE_RESULT_PATH = ROOT / "reports/generated/r1-model-cascade-001/cascade-state.json"
INSTRUMENT_ID = "autonomous-tutoring-r1-confirmation-001"


class R1ConfirmationError(RuntimeError):
    """Raised when the prospective T0/T1 contract has drifted."""


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise R1ConfirmationError(f"JSON root is not an object: {path.name}")
    return payload


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_package(instrument: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / instrument["trajectory_contract"]["source_package"]
    package = _load(path)
    expected = _canonical_sha256(
        {key: value for key, value in package.items() if key != "content_sha256"}
    )
    if package.get("content_sha256") != expected:
        raise R1ConfirmationError("trajectory source package hash drifted")
    return package


def build_trajectory_contract(instrument: dict[str, Any]) -> list[dict[str, Any]]:
    """Select 50 source-family-disjoint clusters with a frozen course balance."""

    rows = _source_package(instrument)["cases"]
    by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_cluster[str(row["cluster_id"])].append(row)
    candidates = []
    for cluster_id, cases in by_cluster.items():
        ordered = sorted(cases, key=lambda row: row["case_id"])
        if len(ordered) != 5:
            raise R1ConfirmationError("each trajectory cluster must have five cases")
        candidates.append(
            {
                "cluster_id": cluster_id,
                "course_id": ordered[0]["course_id"],
                "source_family_id": ordered[0]["source_family_id"],
                "cases": ordered,
            }
        )
    seed = int(instrument["trajectory_contract"]["selection_seed"])
    candidates.sort(
        key=lambda row: hashlib.sha256(
            f"{seed}:{row['cluster_id']}".encode("utf-8")
        ).hexdigest()
    )
    targets = instrument["trajectory_contract"]["course_distribution"]
    counts: dict[str, int] = defaultdict(int)
    source_families: set[str] = set()
    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        course_id = candidate["course_id"]
        source_family = candidate["source_family_id"]
        if counts[course_id] >= int(targets[course_id]):
            continue
        if source_family in source_families:
            continue
        selected.append(candidate)
        counts[course_id] += 1
        source_families.add(source_family)
    if counts != {key: int(value) for key, value in targets.items()}:
        raise R1ConfirmationError("source-disjoint course allocation is impossible")
    if len(selected) != int(instrument["trajectory_contract"]["trajectory_count"]):
        raise R1ConfirmationError("trajectory count drifted")

    trajectories: list[dict[str, Any]] = []
    for number, selected_cluster in enumerate(selected, start=1):
        cases = selected_cluster.pop("cases")
        turns = [
            {**cases[0], "message": cases[0]["question"], "turn_kind": "direct"},
            {
                **cases[1],
                "message": f"My attempt is incomplete. {cases[1]['question']}",
                "turn_kind": "partial-attempt",
            },
            {
                **cases[2],
                "message": f"I am confused about this. {cases[2]['question']}",
                "turn_kind": "confusion",
                "restart_before_turn": number <= 5,
            },
            (
                {
                    **cases[3],
                    "message": f"I am still confused. {cases[3]['question']}",
                    "turn_kind": "repeated-confusion",
                    "forced_provider_failure": number <= 5,
                }
                if number <= 25
                else {**cases[4], "message": cases[4]["question"], "turn_kind": "boundary"}
            ),
        ]
        trajectories.append(
            {
                **selected_cluster,
                "trajectory_id": f"r1-trajectory-{number:03d}",
                "release_change_check": 6 <= number <= 10,
                "turns": turns,
            }
        )
    return trajectories


def validate() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise R1ConfirmationError("instrument identity drifted")
    if instrument.get("status") != "reviewed-pending-model-selection":
        raise R1ConfirmationError("prospective confirmation status drifted")
    execution = instrument["execution"]
    if any(
        execution[key]
        for key in (
            "provider_calls_authorized",
            "paid_execution_authorized",
            "held_out_execution_authorized",
            "automatic_promotion",
        )
    ):
        raise R1ConfirmationError("build-only confirmation gained execution authority")
    trajectories = build_trajectory_contract(instrument)
    turns = [turn for row in trajectories for turn in row["turns"]]
    if len(turns) != 200 or len({row["case_id"] for row in turns}) != 200:
        raise R1ConfirmationError("confirmation turn identity drifted")
    if len({row["source_family_id"] for row in trajectories}) != 50:
        raise R1ConfirmationError("confirmation sources are not disjoint")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-build-only",
        "trajectory_count": len(trajectories),
        "turn_count_per_condition": len(turns),
        "source_family_count": 50,
        "provider_failure_trajectory_count": sum(
            any(turn.get("forced_provider_failure") for turn in row["turns"])
            for row in trajectories
        ),
        "restart_trajectory_count": sum(
            any(turn.get("restart_before_turn") for turn in row["turns"])
            for row in trajectories
        ),
        "contract_sha256": _canonical_sha256(trajectories),
        "paid_execution_authorized": False,
        "provider_calls": 0,
    }


def preflight() -> dict[str, Any]:
    result = validate()
    blockers = ["paid-execution-not-authorized"]
    selected_model = None
    if not CASCADE_RESULT_PATH.is_file():
        blockers.append("r1-model-cascade-not-completed")
    else:
        cascade = _load(CASCADE_RESULT_PATH)
        if cascade.get("status") != "completed-keep":
            blockers.append("r1-model-cascade-did-not-pass")
        elif not isinstance(cascade.get("selected_candidate"), dict):
            blockers.append("r1-model-cascade-selection-missing")
        else:
            selected_model = cascade["selected_candidate"].get("provider_model")
    return {
        **result,
        "status": "blocked-not-authorized",
        "blockers": blockers,
        "selected_model": selected_model,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    if args.preflight:
        result = preflight()
    else:
        result = validate()
        if args.simulate:
            result = {
                **result,
                "status": "simulated-pass",
                "conditions": ["T0", "T1"],
                "hard_gates_passed": True,
            }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
