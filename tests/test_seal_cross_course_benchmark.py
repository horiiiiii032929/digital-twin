import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.seal_cross_course_benchmark import (
    build_seal_artifacts,
    write_exclusive,
)


def _case(case_id: str, split: str, second_reviewed: bool) -> dict:
    return {
        "case_id": case_id,
        "split": split,
        "review": {
            "researcher_verified": True,
            "second_reviewed": second_reviewed,
        },
    }


def _dataset() -> dict:
    cases = [
        _case(f"development-{index}", "development", index < 10)
        for index in range(40)
    ]
    cases.extend(
        _case(f"heldout-{index}", "heldout_draft", index < 10)
        for index in range(60)
    )
    return {
        "dataset_id": "cross-course-retrieval-v1",
        "dataset_version": "draft-6",
        "dataset_status": "approved",
        "corpus_id": "cross-course-portfolio-v2",
        "cases": cases,
    }


def _artifacts(dataset: dict, output_dir: Path):
    return build_seal_artifacts(
        dataset,
        source_dataset_sha256="a" * 64,
        corpus_manifest_sha256="b" * 64,
        output_dir=output_dir,
        sealed_at="2026-07-30T04:00:00+00:00",
    )


def test_builds_disjoint_hashed_splits_and_unopened_ledger(
    tmp_path: Path,
) -> None:
    original = _dataset()
    dataset = copy.deepcopy(original)
    artifacts = _artifacts(dataset, tmp_path)
    development = json.loads(artifacts["development.json"][1])
    heldout = json.loads(artifacts["heldout.json"][1])
    ledger = json.loads(artifacts["heldout_once_ledger.json"][1])
    seal = json.loads(artifacts["seal.json"][1])

    assert dataset == original
    assert development["dataset_status"] == "sealed"
    assert heldout["dataset_status"] == "sealed"
    assert len(development["cases"]) == 40
    assert len(heldout["cases"]) == 60
    assert {
        case["case_id"] for case in development["cases"]
    }.isdisjoint(case["case_id"] for case in heldout["cases"])
    assert seal["development_sha256"] == hashlib.sha256(
        artifacts["development.json"][1]
    ).hexdigest()
    assert seal["heldout_sha256"] == hashlib.sha256(
        artifacts["heldout.json"][1]
    ).hexdigest()
    assert ledger["heldout_sha256"] == seal["heldout_sha256"]
    assert ledger["status"] == "unopened"
    assert ledger["attempts"] == []
    assert seal["heldout_access_allowed"] is False


def test_rejects_unapproved_or_under_reviewed_dataset(tmp_path: Path) -> None:
    dataset = _dataset()
    dataset["dataset_status"] = "researcher_review"
    with pytest.raises(ValueError, match="approved"):
        _artifacts(dataset, tmp_path)

    dataset = _dataset()
    for case in dataset["cases"]:
        case["review"]["second_reviewed"] = False
    with pytest.raises(ValueError, match="20 cases"):
        _artifacts(dataset, tmp_path)


def test_exclusive_write_refuses_to_replace_a_seal(tmp_path: Path) -> None:
    artifacts = _artifacts(_dataset(), tmp_path)
    write_exclusive(artifacts)

    assert all(path.stat().st_mode & 0o077 == 0 for path, _ in artifacts.values())
    with pytest.raises(FileExistsError, match="already exist"):
        write_exclusive(artifacts)
