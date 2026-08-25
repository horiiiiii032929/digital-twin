from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.validate_multimodal_retrieval_dataset import (
    DEFAULT_DATASET,
    load_json,
    validate_dataset,
)


def test_synthetic_multimodal_fixture_is_valid() -> None:
    summary = validate_dataset(load_json(DEFAULT_DATASET))

    assert summary["assets"] == 9
    assert summary["cases"] == 21
    assert summary["slices"] == {
        "adversarial_integrity": 2,
        "no_evidence": 4,
        "text_control": 2,
        "visual_answerable": 13,
    }
    assert summary["model_called"] is False
    assert summary["private_source_read"] is False


def test_visual_answerable_case_requires_gold_region() -> None:
    dataset = deepcopy(load_json(DEFAULT_DATASET))
    dataset["cases"][0]["gold_region_ids"] = []

    with pytest.raises(ValueError, match="has no gold regions"):
        validate_dataset(dataset)


def test_synthetic_fixture_requires_each_core_modality() -> None:
    dataset = deepcopy(load_json(DEFAULT_DATASET))
    dataset["cases"] = [
        case for case in dataset["cases"] if case["modality"] != "equation"
    ]

    with pytest.raises(ValueError, match="missing a required modality"):
        validate_dataset(dataset)


def test_asset_integrity_is_hash_bound() -> None:
    dataset = deepcopy(load_json(DEFAULT_DATASET))
    dataset["source_assets"][0]["sha256"] = "0" * 64

    with pytest.raises(ValueError, match="asset hash mismatch"):
        validate_dataset(dataset)
