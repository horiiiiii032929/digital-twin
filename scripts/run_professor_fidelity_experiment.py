"""Validate the frozen professor-fidelity plan and emit a sanitized manifest.

This module never executes a provider call. The separate v2 execution adapter
performs its own fail-closed checks for the reviewed dataset, conditions,
retrieval/chunker, policy/prompt, credential, and output boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import jsonschema
from dotenv import load_dotenv

from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
DEFAULT_INSTRUMENT = (
    ROOT / "research/05_evaluation/instruments/professor_fidelity_v1.json"
)
COURSE_SCHEMA = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA = ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
EXPECTED_CONDITIONS = ("C0", "C1", "C2", "C3")
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
GENERATOR_REVIEW_PATH = (
    ROOT / "research/05_evaluation/judgments/"
    "generator-qualification-v1-heldout-001-second-review.json"
)
EXPECTED_GENERATOR_ID = "litellm-deepseek-v4-flash-nonthinking-v1"
EXPECTED_PROMPT_ID = "strict-evidence-grounded-prompt-v3"
EXPECTED_QUALIFICATION_VERSION = "generator-qualification-v1-heldout-001"


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
    if instrument.get("generator_binding", {}).get("status") != "qualified-selected":
        raise ProfessorFidelityPlanError("generator binding is not qualified and selected")
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
    qualification = load_selected_generator_qualification()
    missing_dataset = dataset_summary is None
    return {
        "run_type": "professor-fidelity-v1-preflight",
        "status": (
            "validation-only-pending-reviewed-v2-dataset"
            if missing_dataset
            else "validation-only-dataset-bound"
        ),
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
        "prospective_generator_binding_requirement": instrument[
            "generator_binding"
        ],
        "generator_binding": qualification["generator"],
        "prompt_binding": qualification["prompt"],
        "generator_qualification": qualification["qualification"],
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "private_text_emitted": False,
        "execution_enabled": False,
        "selection_blockers": [
            *(("reviewed v2 dataset is not supplied",) if missing_dataset else ()),
            "condition-blinded semantic and pedagogy review is required before selection",
        ],
        "execution_command": "python -m scripts.execute_professor_fidelity",
    }


def load_selected_generator_qualification() -> dict[str, Any]:
    profile = load_json(PROFILE_PATH)
    review = load_json(GENERATOR_REVIEW_PATH)
    components = {
        component.get("component"): component
        for component in profile.get("components", [])
    }
    generator = components.get("generator", {})
    prompt = components.get("prompt", {})
    generator_implementation = generator.get("implementation", {})
    prompt_implementation = prompt.get("implementation", {})
    if generator.get("status") != "selected" or (
        generator_implementation.get("implementation_id") != EXPECTED_GENERATOR_ID
        or generator_implementation.get("version") != EXPECTED_QUALIFICATION_VERSION
    ):
        raise ProfessorFidelityPlanError(
            "experimental profile has no exact qualified generator selection"
        )
    if prompt.get("status") != "selected" or (
        prompt_implementation.get("implementation_id") != EXPECTED_PROMPT_ID
        or prompt_implementation.get("version") != EXPECTED_QUALIFICATION_VERSION
    ):
        raise ProfessorFidelityPlanError(
            "experimental profile has no exact qualified prompt selection"
        )
    summary = review.get("summary", {})
    if review.get("review_status") != "complete" or (
        summary.get("cases_passed") != 20 or summary.get("cases_failed") != 0
    ):
        raise ProfessorFidelityPlanError(
            "generator qualification second review is incomplete"
        )
    configuration = generator_implementation.get("configuration", {})
    required_configuration = {
        "provider_model",
        "provider_revision",
        "thinking",
        "temperature",
        "max_output_tokens",
        "timeout_seconds",
        "max_attempts",
        "data_boundary",
    }
    if not required_configuration.issubset(configuration):
        raise ProfessorFidelityPlanError(
            "qualified generator configuration is incomplete"
        )
    return {
        "generator": {
            **generator_implementation,
            "control": generator.get("control"),
        },
        "prompt": {
            **prompt_implementation,
            "control": prompt.get("control"),
        },
        "qualification": {
            "result_id": EXPECTED_QUALIFICATION_VERSION,
            "status": "qualified-selected",
            "decision": "keep",
            "candidate_binding": EXPECTED_GENERATOR_ID,
            "prompt_binding": EXPECTED_PROMPT_ID,
            "credential_environment_variable": "DEEPSEEK_API_KEY",
            "credential_present": bool(os.environ.get("DEEPSEEK_API_KEY", "").strip()),
            "credential_value_emitted": False,
            "heldout_execution_completed": True,
            "rerun_allowed": False,
            "second_review": review["decision"],
        },
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
    if arguments.split == "heldout":
        require_pre_evaluation_operation_allowed("heldout_execution")
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
