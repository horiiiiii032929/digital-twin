#!/usr/bin/env python3
"""Validate and simulate the non-human C0-C3 professor-fidelity proxy harness."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.digital_twin.evaluation.professor_fidelity_proxy import (
    CONDITIONS,
    FIDELITY_DIMENSIONS,
    build_blinded_packet,
    score_reviews,
    validate_dataset,
    validate_instrument,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT / "research/05_evaluation/datasets/professor_fidelity_proxy_packet_001.json"
INSTRUMENT_PATH = ROOT / "research/05_evaluation/instruments/professor_fidelity_proxy_harness_001.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path.name}")
    return value


def validate() -> dict[str, Any]:
    dataset = _load(DATASET_PATH)
    instrument = _load(INSTRUMENT_PATH)
    return {
        "status": "passed-build-only",
        **validate_dataset(dataset),
        **validate_instrument(instrument),
        "provider_calls": 0,
        "real_professor_fidelity_claim": False,
    }


def _simulated_responses(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in dataset["cases"]:
        for condition in CONDITIONS:
            action = case["expected_action"]
            answer = case["canonical_answer"] or {
                "clarify": "Could you identify the concept or earlier step you mean?",
                "abstain": "I cannot support that request from the approved course evidence.",
                "refuse": "I cannot provide a submission-ready answer, but I can discuss your attempt.",
            }[action]
            if condition == "C0" and action == "answer":
                answer = "A generic explanation without course evidence."
            if condition in {"C2", "C3"}:
                answer = f"Let's identify the key idea first. {answer} What would you check next?"
            rows.append(
                {
                    "case_id": case["case_id"],
                    "condition": condition,
                    "action": action,
                    "text": answer,
                    "citations": (
                        [case["evidence"]]
                        if condition in {"C1", "C2", "C3"} and case["evidence"]["source_id"]
                        else []
                    ),
                }
            )
    return rows


def simulate() -> dict[str, Any]:
    dataset = _load(DATASET_PATH)
    instrument = _load(INSTRUMENT_PATH)
    validate_dataset(dataset)
    validate_instrument(instrument)
    packet = build_blinded_packet(
        dataset,
        _simulated_responses(dataset),
        seed=instrument["review_design"]["response_order_seed"],
    )
    reviews: list[dict[str, Any]] = []
    for reviewer_id in ("simulated-reviewer-a", "simulated-reviewer-b"):
        for item in packet["items"]:
            mapping = packet["mapping"][item["item_id"]]
            preferred_alias = next(alias for alias, condition in mapping.items() if condition == "C2")
            reviews.append(
                {
                    "reviewer_id": reviewer_id,
                    "item_id": item["item_id"],
                    "preferred_alias": preferred_alias,
                    "ratings": {dimension: 5 for dimension in FIDELITY_DIMENSIONS},
                }
            )
    return {
        **score_reviews(packet, reviews),
        "simulation": True,
        "provider_calls": 0,
        "packet_item_count": len(packet["items"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    arguments = parser.parse_args()
    result = simulate() if arguments.simulate else validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
