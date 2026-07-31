#!/usr/bin/env python3
"""Validate multimodal retrieval instruments without running a model."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import jsonschema


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "research/05_evaluation/multimodal_retrieval_v1.schema.json"
DEFAULT_DATASET = (
    ROOT / "research/05_evaluation/multimodal_retrieval_v1_synthetic.json"
)
REQUIRED_SYNTHETIC_MODALITIES = {
    "diagram",
    "chart",
    "table",
    "equation",
    "screenshot",
    "scanned_page",
}
REQUIRED_SYNTHETIC_SLICES = {
    "visual_answerable",
    "text_control",
    "no_evidence",
    "adversarial_integrity",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_schema(dataset: dict[str, Any]) -> None:
    validator = jsonschema.Draft202012Validator(load_json(SCHEMA_PATH))
    errors = sorted(
        validator.iter_errors(dataset),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "<root>"
        raise ValueError(f"schema error at {location}: {error.message}")


def validate_assets(dataset: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    assets = dataset["source_assets"]
    asset_ids = [asset["asset_id"] for asset in assets]
    require(len(asset_ids) == len(set(asset_ids)), "asset IDs are not unique")

    all_region_ids: list[str] = []
    for asset in assets:
        path = root / asset["path"]
        require(path.is_file(), f"asset is absent: {asset['path']}")
        require(
            sha256_file(path) == asset["sha256"],
            f"asset hash mismatch: {asset['asset_id']}",
        )
        for region in asset["regions"]:
            x, y, width, height = region["bbox"]
            require(x + width <= 1, f"region exceeds horizontal bounds: {region['region_id']}")
            require(y + height <= 1, f"region exceeds vertical bounds: {region['region_id']}")
            all_region_ids.append(region["region_id"])
    require(
        len(all_region_ids) == len(set(all_region_ids)),
        "region IDs are not globally unique",
    )
    return {asset["asset_id"]: asset for asset in assets}


def validate_cases(dataset: dict[str, Any], assets: dict[str, Any]) -> None:
    cases = dataset["cases"]
    case_ids = [case["case_id"] for case in cases]
    queries = [" ".join(case["query"].casefold().split()) for case in cases]
    require(len(case_ids) == len(set(case_ids)), "case IDs are not unique")
    require(len(queries) == len(set(queries)), "queries are not unique")

    for case in cases:
        require(case["asset_id"] in assets, f"unknown asset: {case['asset_id']}")
        region_ids = {region["region_id"] for region in assets[case["asset_id"]]["regions"]}
        require(
            set(case["gold_region_ids"]) <= region_ids,
            f"{case['case_id']} has gold regions from another asset",
        )
        if case["slice"] in {"visual_answerable", "text_control"}:
            require(case["expected_action"] == "retrieve", f"{case['case_id']} action mismatch")
            require(bool(case["required_claims"]), f"{case['case_id']} has no required claims")
            require(bool(case["gold_region_ids"]), f"{case['case_id']} has no gold regions")
        else:
            require(not case["required_claims"], f"{case['case_id']} boundary case has claims")
            require(not case["gold_region_ids"], f"{case['case_id']} boundary case has gold regions")
        if case["slice"] == "visual_answerable":
            require(
                case["visual_dependency"] != "text_sufficient",
                f"{case['case_id']} is not visually dependent",
            )
        if case["slice"] == "text_control":
            require(
                case["visual_dependency"] == "text_sufficient",
                f"{case['case_id']} text control is visually dependent",
            )
        if case["slice"] == "no_evidence":
            require(case["expected_action"] == "abstain", f"{case['case_id']} must abstain")
        if case["slice"] == "adversarial_integrity":
            require(case["expected_action"] == "refuse", f"{case['case_id']} must refuse")


def validate_status_and_coverage(dataset: dict[str, Any]) -> None:
    cases = dataset["cases"]
    if dataset["dataset_kind"] == "synthetic":
        require(dataset["dataset_status"] == "synthetic_fixture", "synthetic status mismatch")
        require(
            all(asset["permission"] == "synthetic-approved" for asset in dataset["source_assets"]),
            "synthetic dataset contains a private asset",
        )
        modalities = {case["modality"] for case in cases}
        slices = {case["slice"] for case in cases}
        require(
            REQUIRED_SYNTHETIC_MODALITIES <= modalities,
            "synthetic fixture is missing a required modality",
        )
        require(
            REQUIRED_SYNTHETIC_SLICES <= slices,
            "synthetic fixture is missing a required slice",
        )
    else:
        require(
            all(asset["permission"] == "course-approved-local-only" for asset in dataset["source_assets"]),
            "private dataset contains an asset without the local-only permission",
        )
        if dataset["dataset_status"] in {"approved", "sealed"}:
            require(
                all(case["review"]["researcher_verified"] for case in cases),
                "approved private dataset has an unverified case",
            )


def validate_dataset(dataset: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    validate_schema(dataset)
    assets = validate_assets(dataset, root=root)
    validate_cases(dataset, assets)
    validate_status_and_coverage(dataset)
    return {
        "status": "passed",
        "dataset_id": dataset["dataset_id"],
        "assets": len(assets),
        "cases": len(dataset["cases"]),
        "modalities": dict(sorted(Counter(case["modality"] for case in dataset["cases"]).items())),
        "slices": dict(sorted(Counter(case["slice"] for case in dataset["cases"]).items())),
        "model_called": False,
        "private_source_read": dataset["dataset_kind"] == "private_course",
    }


def main() -> int:
    args = parse_args()
    try:
        summary = validate_dataset(load_json(args.dataset))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal retrieval validation failed: {error}")
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
