"""Validate the immutable evidence-sufficiency decision-data freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.build_evidence_sufficiency_v2_decision_draft_002 import (
    _validate_corrected,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FREEZE = (
    ROOT
    / "research/05_evaluation/instruments/evidence_sufficiency_v2_decision_freeze_001.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_freeze(path: Path = DEFAULT_FREEZE) -> dict[str, Any]:
    freeze = json.loads(path.read_text(encoding="utf-8"))
    if freeze.get("freeze_id") != "evidence-sufficiency-v2-decision-freeze-001":
        raise ValueError("decision freeze ID drifted")
    if freeze.get("status") != "frozen-not-opened":
        raise ValueError("decision data must remain frozen and unopened")

    dataset_binding = freeze["dataset"]
    dataset_path = ROOT / dataset_binding["path"]
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    summary = _validate_corrected(dataset)
    if dataset_binding["dataset_id"] != summary["dataset_id"]:
        raise ValueError("dataset ID binding drifted")
    if dataset_binding["content_sha256"] != summary["content_sha256"]:
        raise ValueError("dataset content hash binding drifted")
    if dataset_binding["file_sha256"] != _sha256(dataset_path):
        raise ValueError("dataset file hash binding drifted")
    expected_counts = {
        "case_count": len(dataset["cases"]),
        "source_count": len(dataset["sources"]),
        "answer_count": sum(
            case["expected_action"] == "answer" for case in dataset["cases"]
        ),
        "abstain_count": sum(
            case["expected_action"] == "abstain" for case in dataset["cases"]
        ),
    }
    for field, expected in expected_counts.items():
        if dataset_binding[field] != expected:
            raise ValueError(f"dataset {field} binding drifted")
    if dataset_binding.get("opened_for_candidate_evaluation") is not False:
        raise ValueError("decision dataset must remain unopened")

    confirmation_binding = freeze["human_confirmation"]
    confirmation_path = ROOT / confirmation_binding["path"]
    confirmation = json.loads(confirmation_path.read_text(encoding="utf-8"))
    if confirmation_binding["packet_id"] != confirmation["packet_id"]:
        raise ValueError("human confirmation packet ID drifted")
    if confirmation_binding["file_sha256"] != _sha256(confirmation_path):
        raise ValueError("human confirmation hash binding drifted")
    if confirmation["dataset_id"] != dataset["dataset_id"]:
        raise ValueError("human confirmation dataset binding drifted")
    if confirmation["content_sha256"] != dataset["content_sha256"]:
        raise ValueError("human confirmation content binding drifted")
    if not confirmation.get("human_review_completed"):
        raise ValueError("human confirmation remains incomplete")
    if (
        confirmation.get("confirmed_count") != 4
        or confirmation.get("pending_count") != 0
    ):
        raise ValueError("four human confirmations are required")
    if any(case.get("status") != "confirmed" for case in confirmation["cases"]):
        raise ValueError("a human confirmation case remains pending")

    safety = freeze["execution_safety"]
    if safety.get("dataset_frozen") is not True:
        raise ValueError("dataset freeze must be explicit")
    unauthorized = {
        key: value
        for key, value in safety.items()
        if key != "dataset_frozen" and value is not False
    }
    if unauthorized:
        raise ValueError(f"downstream authority opened: {sorted(unauthorized)}")
    return {
        "freeze_id": freeze["freeze_id"],
        "status": "passed",
        "dataset_id": dataset["dataset_id"],
        "content_sha256": dataset["content_sha256"],
        "case_count": len(dataset["cases"]),
        "human_confirmations": confirmation["confirmed_count"],
        "opened_for_candidate_evaluation": False,
        "provider_or_model_calls": 0,
        "private_data_read": False,
    }


def main() -> int:
    print(json.dumps(validate_freeze(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
