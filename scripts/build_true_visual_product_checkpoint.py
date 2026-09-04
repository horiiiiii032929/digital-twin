#!/usr/bin/env python3
"""Build the physically separated actual-product visual checkpoint package."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DATASET = (
    ROOT / "research/05_evaluation/datasets/true_visual_colpali_confirmation_001.json"
)
PUBLIC_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_product_checkpoint_001_public.json"
)
GOLD_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_product_checkpoint_001_gold.json"
)
SOURCES_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_product_checkpoint_001_sources.json"
)
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/true_visual_product_checkpoint_001.json"
)
DATASET_ID = "true-visual-product-checkpoint-001"
INSTRUMENT_ID = "true-visual-product-checkpoint-001"
QUALIFIED_COMPONENT_LEDGER_SHA256 = (
    "a2e59f3d00b25827e3a6e4c0c97ca69a155e44b809ecdc768941a1d4fd30e184"
)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _with_hash(value: dict[str, Any]) -> dict[str, Any]:
    value = dict(value)
    value["content_sha256"] = _canonical_sha256(value)
    return value


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path.name}")
    expected = value.get("content_sha256")
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    if expected != _canonical_sha256(payload):
        raise ValueError(f"content hash drifted: {path.name}")
    return value


def build() -> dict[str, dict[str, Any]]:
    source = _load(SOURCE_DATASET)
    assets = source.get("assets")
    cases = source.get("cases")
    if not isinstance(assets, list) or len(assets) != 30:
        raise ValueError("visual source package must contain 30 assets")
    if not isinstance(cases, list) or len(cases) != 60:
        raise ValueError("visual source package must contain 60 cases")
    assets_by_id = {row["asset_id"]: row for row in assets}
    if len(assets_by_id) != 30:
        raise ValueError("visual source assets must be unique")
    answer_by_cluster = {
        row["cluster_id"]: row for row in cases if row["expected_action"] == "answer"
    }
    if len(answer_by_cluster) != 30:
        raise ValueError("visual source package must contain 30 answerable cases")

    public = _with_hash(
        {
            "schema_version": "1.0.0",
            "dataset_id": DATASET_ID,
            "source_dataset_id": source["dataset_id"],
            "split": "development",
            "cases": [
                {
                    "case_id": row["case_id"],
                    "cluster_id": row["cluster_id"],
                    "course_id": row["course_id"],
                    "question": row["question"],
                    "slice": row["modality"],
                }
                for row in cases
            ],
        }
    )
    gold = _with_hash(
        {
            "schema_version": "1.0.0",
            "dataset_id": DATASET_ID,
            "cases": [
                {
                    "case_id": row["case_id"],
                    "expected_action": row["expected_action"],
                    "canonical_answer": row["canonical_answer"],
                    "atomic_claims": row["atomic_claims"],
                    "boundary_reason": row["boundary_reason"],
                    "required_asset_ids": row["required_asset_ids"],
                    "required_region_ids": row["required_region_ids"],
                }
                for row in cases
            ],
        }
    )
    sources = _with_hash(
        {
            "schema_version": "1.0.0",
            "dataset_id": DATASET_ID,
            "source_role": "product-visible-approved-course-evidence",
            "assets": [
                {
                    **asset,
                    "source_version_number": 1,
                    "approved_source_claim": answer_by_cluster[
                        asset["asset_id"].replace("asset", "cluster")
                    ]["canonical_answer"],
                }
                for asset in assets
            ],
        }
    )
    instrument = _with_hash(
        {
            "schema_version": "1.0.0",
            "instrument_id": INSTRUMENT_ID,
            "status": "built-provider-unauthorized",
            "owner_issue": 210,
            "related_issue": 131,
            "conditions": {
                "control": "text-ocr-fallback",
                "candidate": "jina-v4-late-interaction",
            },
            "public_path": str(PUBLIC_PATH.relative_to(ROOT)),
            "gold_path": str(GOLD_PATH.relative_to(ROOT)),
            "sources_path": str(SOURCES_PATH.relative_to(ROOT)),
            "public_sha256": public["content_sha256"],
            "gold_sha256": gold["content_sha256"],
            "sources_sha256": sources["content_sha256"],
            "component_ledger": (
                "reports/generated/true-visual-colpali-confirmation-001/"
                "provider-ledger.sqlite3"
            ),
            "component_ledger_sha256": QUALIFIED_COMPONENT_LEDGER_SHA256,
            "provider": {
                "name": "Jina AI",
                "model": "jina-embeddings-v4",
                "max_query_calls": 60,
                "retries": 0,
                "account_token_limit": 10_000_000,
                "imported_tokens": 144_639,
            },
            "hard_gates": {
                "fully_grounded_visual_success": {"minimum": 0.9},
                "boundary_releases": {"maximum": 0},
                "unsupported_claims": {"maximum": 0},
                "invalid_or_wrong_version_citations": {"maximum": 0},
                "original_region_lineage": {"minimum": 1.0},
                "wrong_course_retrieval": {"maximum": 0},
                "visual_retrieval_p95_seconds": {"maximum": 8.0},
                "text_path_regressions": {"maximum": 0},
            },
            "gold_opening_rule": (
                "score only after all control and candidate responses are durable"
            ),
            "provider_execution_authorized": False,
            "paid_execution_authorized": False,
            "same_case_tuning_allowed": False,
        }
    )
    return {
        "public": public,
        "gold": gold,
        "sources": sources,
        "instrument": instrument,
    }


def validate(packages: dict[str, dict[str, Any]]) -> dict[str, object]:
    public = packages["public"]
    gold = packages["gold"]
    sources = packages["sources"]
    instrument = packages["instrument"]
    public_ids = [row["case_id"] for row in public["cases"]]
    gold_ids = [row["case_id"] for row in gold["cases"]]
    if len(public_ids) != len(set(public_ids)) or public_ids != gold_ids:
        raise ValueError("public/gold case identity drifted")
    if set(public["cases"][0]) != {
        "case_id",
        "cluster_id",
        "course_id",
        "question",
        "slice",
    }:
        raise ValueError("public cases expose fields outside the product contract")
    actions = Counter(row["expected_action"] for row in gold["cases"])
    modalities = Counter(
        row["slice"] for row in public["cases"] if row["case_id"].endswith("-a")
    )
    if actions["answer"] != 30 or sum(actions.values()) != 60:
        raise ValueError("visual answer/boundary allocation drifted")
    if modalities != {"table": 10, "equation": 10, "diagram": 10}:
        raise ValueError("visual modality allocation drifted")
    if len(sources["assets"]) != 30:
        raise ValueError("visual source count drifted")
    if instrument["provider_execution_authorized"] is not False:
        raise ValueError("visual checkpoint must remain provider unauthorized")
    return {
        "status": "passed",
        "instrument_id": INSTRUMENT_ID,
        "case_count": 60,
        "answerable_count": 30,
        "boundary_count": 30,
        "asset_count": 30,
        "provider_calls": 0,
        "public_sha256": public["content_sha256"],
        "gold_sha256": gold["content_sha256"],
        "sources_sha256": sources["content_sha256"],
        "instrument_sha256": instrument["content_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    packages = build()
    result = validate(packages)
    if args.write:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID,
            "dataset_generation",
        )
        for key, path in (
            ("public", PUBLIC_PATH),
            ("gold", GOLD_PATH),
            ("sources", SOURCES_PATH),
            ("instrument", INSTRUMENT_PATH),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(packages[key], indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
