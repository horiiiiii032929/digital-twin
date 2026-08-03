"""Validate and preflight the frozen professor-fidelity experiment.

This command deliberately prepares a sanitized run manifest only. Decision-
bearing execution remains blocked until an exact generator/runtime adapter and
the private course-tutor split are explicitly bound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INSTRUMENT = (
    ROOT / "research/05_evaluation/instruments/professor_fidelity_v1.json"
)
COURSE_SCHEMA = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA = (
    ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
)
EXPECTED_CONDITIONS = ("C0", "C1", "C2", "C3")


class ProfessorFidelityPlanError(ValueError):
    """Raised when a frozen plan or supplied split is not safe to run."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProfessorFidelityPlanError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise ProfessorFidelityPlanError(f"JSON root must be an object: {path}")
    return value


def load_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = load_json(path)
    _validate_instrument(instrument)
    return instrument


def _validate_instrument(instrument: dict[str, Any]) -> None:
    if instrument.get("schema_version") != 1:
        raise ProfessorFidelityPlanError("unsupported professor-fidelity schema")
    if instrument.get("instrument_id") != "professor-fidelity-v1":
        raise ProfessorFidelityPlanError("unexpected professor-fidelity instrument")
    if instrument.get("status") != "frozen-preflight":
        raise ProfessorFidelityPlanError("instrument is not in frozen preflight state")
    conditions = instrument.get("conditions")
    if not isinstance(conditions, list):
        raise ProfessorFidelityPlanError("conditions must be a list")
    condition_ids = tuple(condition.get("condition_id") for condition in conditions)
    if condition_ids != EXPECTED_CONDITIONS:
        raise ProfessorFidelityPlanError(
            f"conditions must remain ordered as {EXPECTED_CONDITIONS}"
        )
    if instrument.get("generator_binding", {}).get("status") != (
        "pending-qualification"
    ):
        raise ProfessorFidelityPlanError(
            "generator binding must remain pending until qualification"
        )
    if instrument.get("analysis", {}).get("bootstrap_seed") != 5002:
        raise ProfessorFidelityPlanError("bootstrap seed drifted from frozen value")
    if instrument.get("analysis", {}).get("human_outcome_claims_allowed") is not False:
        raise ProfessorFidelityPlanError("human outcome claims must remain disabled")


def validate_dataset_and_conditions(
    dataset_path: Path,
    conditions_path: Path,
    *,
    split: str,
    confirm_heldout: bool = False,
) -> dict[str, Any]:
    dataset = load_json(dataset_path)
    conditions = load_json(conditions_path)
    _validate_schema(dataset, COURSE_SCHEMA, "course-tutor dataset")
    _validate_schema(conditions, CONDITION_SCHEMA, "course-tutor conditions")

    if dataset.get("split") != split or conditions.get("split") != split:
        raise ProfessorFidelityPlanError("dataset and conditions split mismatch")
    if split == "heldout" and not confirm_heldout:
        raise ProfessorFidelityPlanError(
            "held-out preparation requires explicit one-time confirmation"
        )
    if dataset.get("dataset_status") not in {"approved", "sealed", "opened"}:
        raise ProfessorFidelityPlanError("course-tutor dataset is not approved/sealed")

    case_ids = {case["case_id"] for case in dataset["cases"]}
    condition_records = conditions["records"]
    condition_case_ids = {record["case_id"] for record in condition_records}
    if case_ids != condition_case_ids:
        raise ProfessorFidelityPlanError(
            "every dataset case must have exactly one condition record"
        )
    return {
        "dataset_path": str(dataset_path),
        "conditions_path": str(conditions_path),
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "split": split,
        "case_count": len(case_ids),
        "dataset_sha256": _sha256_file(dataset_path),
        "conditions_sha256": _sha256_file(conditions_path),
    }


def build_preflight_manifest(
    instrument: dict[str, Any],
    *,
    dataset_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "run_type": "professor-fidelity-v1-preflight",
        "status": "blocked-pending-generator-qualification",
        "instrument_id": instrument["instrument_id"],
        "instrument_schema_version": instrument["schema_version"],
        "conditions": [
            {
                "condition_id": condition["condition_id"],
                "evidence": condition["evidence"],
                "policy": condition["policy"],
            }
            for condition in instrument["conditions"]
        ],
        "dataset": dataset_summary,
        "generator_binding": instrument["generator_binding"],
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "private_text_emitted": False,
        "execution_enabled": False,
        "blocked_reasons": [
            "exact generator and prompt binding is not qualified",
            "sealed execution adapter is not bound",
        ],
    }


def _validate_schema(
    value: dict[str, Any],
    schema_path: Path,
    label: str,
) -> None:
    schema = load_json(schema_path)
    errors = sorted(
        jsonschema.Draft202012Validator(
            schema,
            format_checker=jsonschema.FormatChecker(),
        ).iter_errors(value),
        key=lambda error: list(error.path),
    )
    if errors:
        location = ".".join(str(part) for part in errors[0].path) or "root"
        raise ProfessorFidelityPlanError(
            f"{label} schema error at {location}: {errors[0].message}"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--conditions", type=Path)
    parser.add_argument("--split", choices=("anchor", "development", "heldout"))
    parser.add_argument("--confirm-heldout-once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if (arguments.dataset is None) != (arguments.conditions is None):
        parser.error("--dataset and --conditions must be provided together")
    if arguments.dataset is not None and arguments.split is None:
        parser.error("--split is required when a dataset is supplied")
    if not arguments.dry_run:
        parser.error(
            "execution is intentionally disabled until the exact generator and "
            "sealed runtime adapter are qualified; use --dry-run for preflight"
        )
    return arguments


def main() -> None:
    arguments = _arguments()
    instrument = load_instrument(arguments.instrument)
    dataset_summary = None
    if arguments.dataset is not None:
        dataset_summary = validate_dataset_and_conditions(
            arguments.dataset,
            arguments.conditions,
            split=arguments.split,
            confirm_heldout=arguments.confirm_heldout_once,
        )
    manifest = build_preflight_manifest(
        instrument,
        dataset_summary=dataset_summary,
    )
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if arguments.output is None:
        print(rendered, end="")
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
