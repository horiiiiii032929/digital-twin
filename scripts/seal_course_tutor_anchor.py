#!/usr/bin/env python3
"""Seal the reviewed private course-tutor anchor without overstating review."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from scripts.validate_course_tutor_dataset import (
    load_json,
    validate_dataset,
    validate_schema,
)


ROOT = Path(__file__).resolve().parents[1]
DRAFT_ROOT = ROOT / "data/processed/course_tutor_v1/anchor"
OUTPUT_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v1"
EVIDENCE_ROOT = ROOT / "data/interim/course_tutor_v1/evidence"
MANIFEST_PATH = ROOT / "research/05_evaluation/it5002_lectures_v1.manifest.json"
CASE_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
REVIEWED_AT = "2026-08-10T17:45:00+07:00"
REVIEWER_ID = "codex-research-review-2026-08-10"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")


def seal_anchor() -> dict[str, Any]:
    dataset = copy.deepcopy(
        load_json(DRAFT_ROOT / "course_tutor_v1_anchor_draft.json")
    )
    conditions = copy.deepcopy(
        load_json(DRAFT_ROOT / "course_tutor_v1_anchor_conditions_draft.json")
    )
    manifest = load_json(MANIFEST_PATH)
    approved_documents = {
        document["document_id"]
        for document in manifest["documents"]
        if document["tutoring_permission"]
        == "approved_research_evaluation_2026-08-10"
    }
    decisions = []
    for case in dataset["cases"]:
        reviewed_evidence = []
        for evidence in case["ground_truth"]["evidence_units"]:
            if evidence["source_artifact_id"] in approved_documents:
                evidence["permission_status"] = "approved"
            reviewed_evidence.append(
                {
                    "evidence_unit_id": evidence["evidence_unit_id"],
                    "source_artifact_id": evidence["source_artifact_id"],
                    "locator": evidence["locator"],
                    "permission_status": evidence["permission_status"],
                    "content_sha256": evidence["content_sha256"],
                }
            )
        annotation = case["annotation"]
        annotation.update(
            {
                "status": "adjudicated",
                "reviewer_ids": [REVIEWER_ID],
                "professor_decision": "pending",
                "revision": annotation["revision"] + 1,
                "updated_at": REVIEWED_AT,
                "change_summary": (
                    "Codex-assisted researcher review verified question-policy "
                    "coherence and exact claim support against the hash-bound "
                    "lecture passages. This is not professor or independent-human approval."
                ),
            }
        )
        decisions.append(
            {
                "case_id": case["case_id"],
                "decision": "keep",
                "claim_evidence_review": "passed",
                "policy_review": "passed",
                "evidence": reviewed_evidence,
                "limitations": [
                    "Codex-assisted researcher review only",
                    "Professor decision remains pending",
                ],
            }
        )

    version = "course-tutor-v1.0.2-anchor"
    dataset.update(
        {
            "dataset_version": version,
            "dataset_status": "approved",
            "created_at": REVIEWED_AT,
            "data_boundary": {
                **dataset["data_boundary"],
                "provider_use": "approved_external_allowed",
                "permission_status": "approved",
            },
        }
    )
    conditions.update(
        {
            "dataset_version": version,
            "condition_set_version": "course-tutor-v1-conditions.1.1-anchor",
            "created_at": REVIEWED_AT,
        }
    )
    validate_schema(dataset, load_json(CASE_SCHEMA_PATH))
    validate_schema(conditions, load_json(CONDITION_SCHEMA_PATH))
    summary = validate_dataset(
        dataset, conditions, manifest, EVIDENCE_ROOT, expected_cases=12
    )
    write_json(OUTPUT_ROOT / "anchor.json", dataset)
    write_json(OUTPUT_ROOT / "anchor_conditions.json", conditions)
    write_json(
        OUTPUT_ROOT / "anchor_review.json",
        {
            "review_id": "course-tutor-v1-anchor-codex-research-review-001",
            "reviewed_at": REVIEWED_AT,
            "reviewer_id": REVIEWER_ID,
            "review_type": "codex_assisted_researcher_review",
            "professor_review": False,
            "independent_human_review": False,
            "case_decisions": decisions,
        },
    )
    return summary


def main() -> None:
    print(json.dumps(seal_anchor(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
