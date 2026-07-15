"""Validate a versioned component profile and its evaluation evidence."""

import argparse
import json
from pathlib import Path

from src.digital_twin.evaluation import (
    ComponentStatus,
    SystemReleaseProfile,
    load_evaluation_record,
    load_release_profile,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = (
    ROOT / "research" / "05_evaluation" / "profiles" / "student-tutor-v0.json"
)


def main() -> None:
    arguments = _arguments()
    profile = load_release_profile(arguments.profile)
    summary = validate_profile_evidence(profile, root=ROOT)
    print(json.dumps(summary, indent=2, sort_keys=True))


def validate_profile_evidence(
    profile: SystemReleaseProfile,
    *,
    root: Path,
) -> dict[str, object]:
    evaluated_components: list[str] = []
    selections: dict[str, str] = {}

    for entry in profile.components:
        for evidence_path in entry.evidence_paths:
            _require_repository_file(root, evidence_path)

        if entry.status == ComponentStatus.SELECTED:
            if entry.implementation is None:
                raise ValueError("selected profile entry has no implementation")
            selections[entry.component.value] = (
                f"{entry.implementation.implementation_id}@"
                f"{entry.implementation.version}"
            )

        if entry.evaluation_record_path is None:
            continue
        record_path = _require_repository_file(root, entry.evaluation_record_path)
        record = load_evaluation_record(record_path)
        if record.component != entry.component:
            raise ValueError("evaluation record component does not match profile")
        if record.dataset_id != entry.evaluation_dataset:
            raise ValueError("evaluation dataset does not match profile")
        record_hard_gates = {
            gate.name
            for candidate in record.candidates
            for gate in candidate.hard_gates
        }
        if record_hard_gates != set(entry.hard_gates):
            raise ValueError("evaluation hard gates do not match profile")
        if entry.status == ComponentStatus.SELECTED:
            if entry.implementation is None or (
                record.decision.selected_implementation_id
                != entry.implementation.implementation_id
            ):
                raise ValueError(
                    "evaluation decision does not match selected implementation"
                )
        elif record.decision.selected_implementation_id is not None:
            raise ValueError("disabled component evaluation must select nothing")
        evaluated_components.append(entry.component.value)

    counts = {
        status.value: sum(entry.status == status for entry in profile.components)
        for status in ComponentStatus
    }
    return {
        "status": "passed",
        "profile": f"{profile.profile_id}@{profile.profile_version}",
        "stage": profile.stage.value,
        "component_count": len(profile.components),
        "component_status_counts": counts,
        "evaluated_components": sorted(evaluated_components),
        "selections": selections,
    }


def _require_repository_file(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("evidence paths must stay relative to the repository")
    resolved = root / path
    if not resolved.is_file():
        raise ValueError(f"profile evidence file does not exist: {relative_path}")
    return resolved


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    return parser.parse_args()


if __name__ == "__main__":
    main()
