#!/usr/bin/env python3
"""Seal course-tutor v1.2.3 after its frozen hybrid authoring review."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.build_course_tutor_splits import validate_split_isolation
from scripts.validate_course_tutor_dataset import (
    load_json,
    validate_dataset,
    validate_schema,
)
from scripts.run_course_tutor_hybrid_review import (
    CHECK_FIELDS,
    DEEPSEEK_CALL_LIMIT,
    DEEPSEEK_COST_STOP_USD,
    DEEPSEEK_PRIVATE_MAX_ATTEMPTS,
    DEEPSEEK_PUBLIC_PROBE_COUNT,
    ENSEMBLE_ID,
    HUMAN_AUDIT_ID,
    MAX_HUMAN_CASES,
    MODEL_BINDINGS,
    PLAN_ID,
    SAMPLE_SEED,
    required_human_case_ids,
    selection_commitment_sha256,
    select_baseline_case_ids,
    validate_model_decision,
    validate_transport_preflights,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/course_tutor_v1/review_v1_2_3"
DEFAULT_OUTPUT = ROOT / "data/processed/course_tutor_v1/sealed_v2"
MANIFEST_PATH = ROOT / "research/05_evaluation/it5002_lectures_v1.manifest.json"
EVIDENCE_ROOT = ROOT / "data/interim/course_tutor_v1/evidence"
CASE_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
REQUIRED_REVIEW_CHECKS = (
    "question_authentic_and_synthetic",
    "expected_behavior_correct",
    "claims_atomic_and_correct",
    "evidence_supports_claims",
    "permission_and_version_correct",
    "split_assignment_acceptable",
)
if REQUIRED_REVIEW_CHECKS != CHECK_FIELDS:
    raise RuntimeError("hybrid review and sealing checks differ")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")
    except FileExistsError as error:
        raise ValueError(f"refusing to overwrite sealed artifact: {path}") from error


def _aware_timestamp(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def _validate_ensemble(
    ensemble: dict[str, Any],
    datasets: dict[str, dict[str, Any]],
    draft_hashes: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    if not all(
        (
            ensemble.get("plan_id") == PLAN_ID,
            ensemble.get("ensemble_id") == ENSEMBLE_ID,
            ensemble.get("ensemble_status") == "complete",
            ensemble.get("protocol_status") == "awaiting_human_audit",
            ensemble.get("sample_seed") == SAMPLE_SEED,
            ensemble.get("draft_hashes") == draft_hashes,
            ensemble.get("models") == list(MODEL_BINDINGS),
            ensemble.get("local_only") is False,
            isinstance(ensemble.get("external_provider_calls"), int),
            DEEPSEEK_PUBLIC_PROBE_COUNT + len(datasets["development"]["cases"])
            + len(datasets["heldout"]["cases"])
            <= ensemble.get("external_provider_calls", -1)
            <= DEEPSEEK_CALL_LIMIT,
            isinstance(ensemble.get("external_provider_cost_usd"), (int, float)),
            0
            <= ensemble.get("external_provider_cost_usd", -1)
            < DEEPSEEK_COST_STOP_USD,
            isinstance(ensemble.get("external_provider_revision"), str),
            bool(ensemble.get("external_provider_revision", "").strip()),
            _aware_timestamp(ensemble.get("created_at")) is not None,
        )
    ):
        raise ValueError("ensemble does not match the frozen hybrid protocol")
    code = ensemble.get("code", {})
    if (
        not isinstance(code.get("revision"), str)
        or len(code["revision"]) != 40
        or code.get("dirty") is not False
    ):
        raise ValueError("ensemble must be bound to a clean 40-character revision")
    preflights = validate_transport_preflights(
        ensemble.get("transport_preflights")
    )
    external_preflight = next(
        row for row in preflights if row["endpoint_class"] == "external"
    )
    if (
        ensemble["external_provider_revision"]
        != external_preflight["provider_revision"]
    ):
        raise ValueError("ensemble provider revision differs from its preflight")

    cases_by_id = {
        case["case_id"]: case
        for dataset in datasets.values()
        for case in dataset["cases"]
    }
    expected_keys = {
        (binding["reviewer_id"], case_id)
        for binding in MODEL_BINDINGS
        for case_id in cases_by_id
    }
    rows = ensemble.get("model_decisions", [])
    if not isinstance(rows, list):
        raise ValueError("ensemble model decisions must be a list")
    actual_keys = [
        (row.get("reviewer_id"), row.get("case_id"))
        for row in rows
        if isinstance(row, dict)
    ]
    if len(actual_keys) != len(rows) or set(actual_keys) != expected_keys:
        raise ValueError("ensemble must contain all 456 reviewer-case records")
    if len(set(actual_keys)) != len(actual_keys):
        raise ValueError("ensemble contains duplicate reviewer-case records")

    bindings_by_id = {
        binding["reviewer_id"]: binding for binding in MODEL_BINDINGS
    }
    rows_by_case: dict[str, list[dict[str, Any]]] = {
        case_id: [] for case_id in cases_by_id
    }
    for row in rows:
        binding = bindings_by_id[row["reviewer_id"]]
        case = cases_by_id[row["case_id"]]
        if any(
            (
                row.get("model") != binding["model"],
                row.get("model_digest") != binding["digest"],
                row.get("documented_revision")
                != binding["documented_revision"],
                row.get("family") != binding["family"],
                row.get("endpoint_class") != binding["endpoint_class"],
                row.get("thinking") is not binding["thinking"],
                row.get("reasoning_effort") != binding["reasoning_effort"],
                row.get("split") != case["split"],
                row.get("scenario_type") != case["scenario_type"],
            )
        ):
            raise ValueError("ensemble row metadata differs from its frozen binding")
        if binding["endpoint_class"] == "external" and any(
            (
                row.get("provider_model") != binding["model"],
                row.get("provider_revision")
                != ensemble["external_provider_revision"],
            )
        ):
            raise ValueError("DeepSeek row differs from the frozen provider binding")
        if binding["endpoint_class"] == "external":
            attempts = row.get("attempts")
            if (
                not isinstance(attempts, list)
                or not 1 <= len(attempts) <= DEEPSEEK_PRIVATE_MAX_ATTEMPTS
            ):
                raise ValueError("DeepSeek row has an invalid attempt count")
            for attempt in attempts:
                if attempt.get("failure_class") == "transient_provider_error":
                    if any(
                        (
                            attempt.get("provider_model") is not None,
                            attempt.get("provider_revision") is not None,
                            attempt.get("usage") is not None,
                            attempt.get("finish_reason") is not None,
                            attempt.get("retryable") is not True,
                            attempt.get("hard_stop") is not False,
                        )
                    ):
                        raise ValueError("transient DeepSeek attempt is invalid")
                else:
                    usage = attempt.get("usage") or {}
                    if any(
                        (
                            attempt.get("provider_model") != binding["model"],
                            attempt.get("provider_revision")
                            != ensemble["external_provider_revision"],
                            not isinstance(attempt.get("usage"), dict),
                            not isinstance(attempt.get("finish_reason"), str),
                            not attempt.get("finish_reason", "").strip(),
                            not isinstance(usage.get("reasoning_tokens"), int),
                            usage.get("reasoning_tokens", -1) < 0,
                            attempt.get("hard_stop") is True,
                        )
                    ):
                        raise ValueError(
                            "DeepSeek attempt differs from its binding"
                        )
            if attempts[-1].get("status") != row.get("status"):
                raise ValueError("DeepSeek final attempt and decision status differ")
            expected_identity_source = (
                "response"
                if attempts[-1].get("provider_revision")
                else "frozen_request_binding"
            )
            if row.get("provider_identity_source") != expected_identity_source:
                raise ValueError("DeepSeek identity source is invalid")
            if row.get("finish_reason") != attempts[-1].get("finish_reason"):
                raise ValueError("DeepSeek final finish reason is invalid")
        if row.get("status") == "valid":
            validate_model_decision(row.get("decision"))
        elif row.get("status") != "invalid" or row.get("decision") is not None:
            raise ValueError("ensemble row status is invalid")
        rows_by_case[row["case_id"]].append(row)

    actual_external_calls = DEEPSEEK_PUBLIC_PROBE_COUNT + sum(
        len(row.get("attempts", []))
        for row in rows
        if row.get("endpoint_class") == "external"
    )
    if ensemble["external_provider_calls"] != actual_external_calls:
        raise ValueError("ensemble DeepSeek request count is not traceable")

    baseline = select_baseline_case_ids(datasets)
    selection = ensemble.get("selection", {})
    if selection.get("baseline_case_ids") != baseline:
        raise ValueError("ensemble baseline sample differs from the frozen sample")
    required, reasons = required_human_case_ids(rows, baseline)
    if (
        selection.get("required_human_case_ids") != required
        or selection.get("escalation_reasons") != reasons
        or selection.get("maximum_human_cases") != MAX_HUMAN_CASES
        or len(required) > MAX_HUMAN_CASES
    ):
        raise ValueError("ensemble human escalation set is invalid")

    required_set = set(required)
    for case_id, case_rows in rows_by_case.items():
        if case_id in required_set:
            continue
        deepseek_approve = any(
            row["endpoint_class"] == "external"
            and row["status"] == "valid"
            and row["decision"]["decision"] == "approve"
            for row in case_rows
        )
        local_approve = any(
            row["endpoint_class"] == "local"
            and row["status"] == "valid"
            and row["decision"]["decision"] == "approve"
            for row in case_rows
        )
        if not (deepseek_approve and local_approve):
            raise ValueError("unsampled case lacks two-family model approval")
    return rows_by_case, required


def _validate_human_audit(
    audit: dict[str, Any],
    *,
    ensemble_sha256: str,
    draft_hashes: dict[str, Any],
    baseline_case_ids: list[str],
    required_case_ids: list[str],
) -> dict[str, dict[str, Any]]:
    reviewer = audit.get("reviewer", {})
    reviewed_at = _aware_timestamp(audit.get("reviewed_at"))
    if not all(
        (
            audit.get("review_id") == HUMAN_AUDIT_ID,
            audit.get("plan_id") == PLAN_ID,
            audit.get("ensemble_id") == ENSEMBLE_ID,
            audit.get("ensemble_sha256") == ensemble_sha256,
            audit.get("status") == "complete",
            audit.get("draft_hashes") == draft_hashes,
            audit.get("selection_commitment_sha256")
            == selection_commitment_sha256(
                baseline_case_ids, required_case_ids
            ),
            audit.get("required_case_count") == len(required_case_ids),
            reviewed_at is not None,
            reviewer.get("human_review") is True,
            reviewer.get("independent_human_audit") is True,
            reviewer.get("codex_assisted") is False,
            reviewer.get("blinded_to_model_decisions") is True,
            reviewer.get("model_decisions_inspected") is False,
            reviewer.get("role") in {"researcher", "professor"},
            isinstance(reviewer.get("reviewer_id"), str),
            bool(reviewer.get("reviewer_id", "").strip()),
            reviewer.get("reviewer_id")
            not in {binding["reviewer_id"] for binding in MODEL_BINDINGS},
        )
    ):
        raise ValueError(
            "the exact completed, blinded, non-Codex human audit is required"
        )
    decision_rows = audit.get("case_decisions", [])
    if not isinstance(decision_rows, list):
        raise ValueError("human audit case decisions must be a list")
    decisions = {item["case_id"]: item for item in decision_rows}
    if len(decisions) != len(decision_rows):
        raise ValueError("human audit contains duplicate case decisions")
    if set(decisions) != set(required_case_ids):
        raise ValueError("human audit must cover the exact required case set")
    if any(
        item.get("decision") != "approve"
        or any(item.get(check) is not True for check in REQUIRED_REVIEW_CHECKS)
        or not isinstance(item.get("notes"), str)
        for item in decisions.values()
    ):
        raise ValueError("human audit contains an unapproved decision")
    return decisions


def validate_hybrid_reviews(
    *,
    ensemble: dict[str, Any],
    human_audit: dict[str, Any],
    ensemble_sha256: str,
    datasets: dict[str, dict[str, Any]],
    draft_hashes: dict[str, Any],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, dict[str, Any]],
]:
    rows_by_case, required = _validate_ensemble(
        ensemble, datasets, draft_hashes
    )
    decisions = _validate_human_audit(
        human_audit,
        ensemble_sha256=ensemble_sha256,
        draft_hashes=draft_hashes,
        baseline_case_ids=select_baseline_case_ids(datasets),
        required_case_ids=required,
    )
    return rows_by_case, decisions


def seal_splits(
    input_root: Path,
    output_root: Path,
    ensemble_path: Path,
    human_audit_path: Path,
    *,
    github_purge_confirmed: bool,
) -> dict[str, Any]:
    if not github_purge_confirmed:
        raise ValueError("GitHub Support purge confirmation is required")
    review_manifest = load_json(input_root / "review_manifest.json")
    ensemble = load_json(ensemble_path)
    human_audit = load_json(human_audit_path)
    if ensemble.get("draft_hashes") != review_manifest.get("splits"):
        raise ValueError("ensemble is not bound to the exact review draft")
    if human_audit.get("draft_hashes") != review_manifest.get("splits"):
        raise ValueError("human audit is not bound to the exact review draft")
    manifest = load_json(MANIFEST_PATH)
    case_schema = load_json(CASE_SCHEMA_PATH)
    condition_schema = load_json(CONDITION_SCHEMA_PATH)
    reviewer = human_audit["reviewer"]
    reviewed_at = human_audit["reviewed_at"]

    planned_paths = [
        output_root / name
        for name in (
            "development.json",
            "development_conditions.json",
            "heldout.json",
            "heldout_conditions.json",
            "seal.json",
            "heldout_once_ledger.json",
            "authoring_review.json",
        )
    ]
    existing = [path for path in planned_paths if path.exists()]
    if existing:
        raise ValueError(f"sealed target already exists: {existing[0]}")

    prepared: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for split, expected in (("development", 48), ("heldout", 104)):
        dataset_path = input_root / f"{split}.json"
        conditions_path = input_root / f"{split}_conditions.json"
        recorded = review_manifest["splits"][split]
        if sha256(dataset_path) != recorded["dataset_sha256"]:
            raise ValueError(f"{split} review draft hash drifted")
        if sha256(conditions_path) != recorded["conditions_sha256"]:
            raise ValueError(f"{split} condition hash drifted")
        dataset = copy.deepcopy(load_json(dataset_path))
        conditions = copy.deepcopy(load_json(conditions_path))
        validate_schema(dataset, case_schema)
        validate_schema(conditions, condition_schema)
        validate_dataset(dataset, conditions, manifest, EVIDENCE_ROOT, expected)
        prepared[split] = dataset, conditions

    datasets = {split: pair[0] for split, pair in prepared.items()}
    validate_split_isolation(datasets["development"], datasets["heldout"])
    model_rows, human_decisions = validate_hybrid_reviews(
        ensemble=ensemble,
        human_audit=human_audit,
        ensemble_sha256=sha256(ensemble_path),
        datasets=datasets,
        draft_hashes=review_manifest["splits"],
    )
    human_case_ids = set(human_decisions)
    model_reviewer_ids = [binding["reviewer_id"] for binding in MODEL_BINDINGS]

    for split, expected in (("development", 48), ("heldout", 104)):
        dataset, conditions = prepared[split]
        for case in dataset["cases"]:
            case_id = case["case_id"]
            was_human_audited = case_id in human_case_ids
            reviewer_ids = list(model_reviewer_ids)
            if was_human_audited:
                reviewer_ids.append(reviewer["reviewer_id"])
            annotation = case["annotation"]
            annotation.update(
                {
                    "status": "single_review",
                    "reviewer_ids": reviewer_ids,
                    "professor_decision": "pending",
                    "revision": annotation["revision"] + 1,
                    "updated_at": reviewed_at,
                    "change_summary": (
                        "Qualified after cross-provider three-model review and "
                        "blinded targeted independent-human validation under "
                        "the frozen hybrid protocol; this is not professor approval."
                        if was_human_audited
                        else "Qualified by cross-provider two-family model approval "
                        "under the frozen hybrid protocol; this is not full human "
                        "or professor approval."
                    ),
                }
            )
            if not was_human_audited:
                case_rows = model_rows[case_id]
                deepseek_approve = any(
                    row["endpoint_class"] == "external"
                    and row["status"] == "valid"
                    and row["decision"]["decision"] == "approve"
                    for row in case_rows
                )
                local_approve = any(
                    row["endpoint_class"] == "local"
                    and row["status"] == "valid"
                    and row["decision"]["decision"] == "approve"
                    for row in case_rows
                )
                if not (deepseek_approve and local_approve):
                    raise ValueError("unreviewed case lacks two-family approval")
        dataset["dataset_status"] = "approved" if split == "development" else "sealed"
        dataset["sealed_at"] = reviewed_at
        validate_schema(dataset, case_schema)
        validate_schema(conditions, condition_schema)
        validate_dataset(dataset, conditions, manifest, EVIDENCE_ROOT, expected)

    output_hashes = {}
    for split, (dataset, conditions) in prepared.items():
        dataset_path = output_root / f"{split}.json"
        conditions_path = output_root / f"{split}_conditions.json"
        write_json_exclusive(dataset_path, dataset)
        write_json_exclusive(conditions_path, conditions)
        output_hashes[split] = {
            "dataset_sha256": sha256(dataset_path),
            "conditions_sha256": sha256(conditions_path),
        }
    seal = {
        "seal_id": "course-tutor-v1.2.3-hybrid-seal-001",
        "created_at": reviewed_at,
        "authoring_review_id": human_audit["review_id"],
        "ensemble_review_id": ensemble["ensemble_id"],
        "review_plan_id": PLAN_ID,
        "review_claim": (
            "cross-provider two-family model review with targeted independent-human validation"
        ),
        "required_human_cases": len(human_case_ids),
        "github_support_purge_confirmed": True,
        "splits": output_hashes,
        "development_cases": 48,
        "heldout_cases": 104,
    }
    write_json_exclusive(output_root / "seal.json", seal)
    write_json_exclusive(
        output_root / "heldout_once_ledger.json",
        {
            "ledger_id": "course-tutor-v1.2.3-heldout-once-001",
            "status": "unopened",
            "dataset_sha256": output_hashes["heldout"]["dataset_sha256"],
            "conditions_sha256": output_hashes["heldout"]["conditions_sha256"],
            "opened_at": None,
            "run_id": None,
            "rerun_allowed": False,
        },
    )
    write_json_exclusive(
        output_root / "authoring_review.json",
        {"ensemble_review": ensemble, "human_audit": human_audit},
    )
    return seal


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ensemble-review", type=Path, required=True)
    parser.add_argument("--human-audit", type=Path, required=True)
    parser.add_argument("--github-purge-confirmed", action="store_true")
    arguments = parser.parse_args()
    print(
        json.dumps(
            seal_splits(
                arguments.input_root,
                arguments.output_root,
                arguments.ensemble_review,
                arguments.human_audit,
                github_purge_confirmed=arguments.github_purge_confirmed,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
