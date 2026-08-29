import json
from pathlib import Path

import pytest

from scripts.score_academic_factual_qa_open_10000 import (
    OpenBenchmarkScoringError,
    _validate_pairing_manifest,
)
from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256


def _package(dataset_id: str, split: str, rows_key: str) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "split": split,
        "case_count": 2,
        rows_key: [{"case_id": "case-1"}, {"case_id": "case-2"}],
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    return payload


def _write_pairing(
    path: Path,
    public: dict[str, object],
    gold: dict[str, object],
) -> None:
    payload: dict[str, object] = {
        "schema_version": 1,
        "pairing_id": "pairing-test-v1",
        "public_package": {
            key: public[key] for key in ("dataset_id", "split", "content_sha256")
        },
        "hidden_gold_package": {
            key: gold[key] for key in ("dataset_id", "split", "content_sha256")
        },
        "case_count": 2,
        "case_ids_sha256": canonical_json_sha256(["case-1", "case-2"]),
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_explicit_pairing_accepts_distinct_public_and_hidden_identities(
    tmp_path: Path,
) -> None:
    public = _package("public-dataset", "development", "cases")
    gold = _package("hidden-dataset", "development-gold", "gold")
    pairing_path = tmp_path / "pairing.json"
    _write_pairing(pairing_path, public, gold)

    pairing = _validate_pairing_manifest(
        pairing_path,
        cases_package=public,
        gold_package=gold,
    )

    assert pairing["pairing_id"] == "pairing-test-v1"


def test_explicit_pairing_rejects_package_hash_drift(tmp_path: Path) -> None:
    public = _package("public-dataset", "development", "cases")
    gold = _package("hidden-dataset", "development-gold", "gold")
    pairing_path = tmp_path / "pairing.json"
    _write_pairing(pairing_path, public, gold)
    public["content_sha256"] = "0" * 64

    with pytest.raises(OpenBenchmarkScoringError, match="public package drifted"):
        _validate_pairing_manifest(
            pairing_path,
            cases_package=public,
            gold_package=gold,
        )
