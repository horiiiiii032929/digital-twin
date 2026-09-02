#!/usr/bin/env python3
"""Build the fresh policy-value successor architecture fold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.build_successor_architecture_development_fold_001 import (
    _boundary_rows,
    _choice_rows,
    canonical_hash,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "successor-architecture-policy-value-fold-004"
PUBLIC_PATH = ROOT / (
    "research/05_evaluation/successor_architecture_policy_value_fold_004_public.json"
)
GOLD_PATH = ROOT / (
    "research/05_evaluation/successor_architecture_policy_value_fold_004_gold.json"
)


def build_packages() -> tuple[dict[str, Any], dict[str, Any]]:
    """Build a source-disjoint successor without reopening folds 001--003."""

    choice_public, choice_gold = _choice_rows(fold_number=4)
    boundary_public, boundary_gold = _boundary_rows(fold_number=4)
    public_rows = choice_public + boundary_public
    gold_rows = choice_gold + boundary_gold
    public = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "fold_id": "policy-value-successor-fold-004",
        "case_count": len(public_rows),
        "model_visible_fields_exclude_gold": True,
        "rows": public_rows,
    }
    gold = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "fold_id": "policy-value-successor-fold-004",
        "case_count": len(gold_rows),
        "gold_opening_rule": "after-all-successor-responses-are-durable",
        "preferred_action_is_diagnostic_not_transition_validity": True,
        "rows": gold_rows,
    }
    public["content_sha256"] = canonical_hash(public)
    gold["content_sha256"] = canonical_hash(gold)
    return public, gold


def validate() -> dict[str, Any]:
    public, gold = build_packages()
    public_ids = [row["case_id"] for row in public["rows"]]
    gold_ids = [row["case_id"] for row in gold["rows"]]
    if public_ids != gold_ids or len(public_ids) != len(set(public_ids)):
        raise ValueError("successor fold case identities drifted")
    if len(public_ids) != 150:
        raise ValueError("successor fold must contain 150 cases")
    serialized_public = json.dumps(public, sort_keys=True)
    for forbidden in (
        "expected_action",
        "acceptable_actions",
        "hidden_learner_knows",
        "action_utilities",
    ):
        if forbidden in serialized_public:
            raise ValueError(f"public successor package contains hidden gold: {forbidden}")
    prior_ids: set[str] = set()
    for fold in (1, 2, 3):
        prior_public = ROOT / (
            "research/05_evaluation/"
            f"successor_architecture_development_fold_{fold:03d}_public.json"
        )
        prior = json.loads(prior_public.read_text(encoding="utf-8"))
        prior_ids.update(str(row["case_id"]) for row in prior["rows"])
    if prior_ids & set(public_ids):
        raise ValueError("successor cases overlap historical development folds")
    return {
        "dataset_id": DATASET_ID,
        "case_count": 150,
        "choice_case_count": 120,
        "boundary_case_count": 30,
        "public_sha256": public["content_sha256"],
        "gold_sha256": gold["content_sha256"],
        "gold_isolated": True,
        "historical_case_ids_disjoint": True,
        "provider_calls": 0,
        "status": "passed",
    }


def write() -> dict[str, Any]:
    public, gold = build_packages()
    PUBLIC_PATH.write_text(
        json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    GOLD_PATH.write_text(
        json.dumps(gold, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return validate()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = write() if args.write else validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
