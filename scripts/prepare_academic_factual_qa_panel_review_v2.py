#!/usr/bin/env python3
"""Prepare the blinded three-reviewer packet for confirmation 002.

The packet deliberately omits gold dispositions, case strata, product
conditions, generator identity, and other reviewer votes.  This build step is
network-free and makes no reviewer call.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from scripts.build_academic_factual_qa_confirmation_v2 import (
    CASES_PATH,
    CONTROLS_PATH,
    INSTRUMENT_ID,
    MANIFEST_PATH,
    canonical_sha256,
)
from src.digital_twin.repository_freeze import (
    require_pre_evaluation_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = (
    ROOT
    / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_blinded_review_packet.json"
)
PACKET_SEED = 2026082502

FORBIDDEN_PACKET_KEYS = {
    "case_id",
    "cluster_id",
    "slice",
    "canonical_answer",
    "atomic_claims",
    "boundary_transform",
    "label_provenance",
    "authoritative_truth",
    "expected_review",
    "planted_mutation",
    "is_clean",
    "condition_id",
    "generator_model",
}

REVIEW_SCHEMA = {
    "review_item_id": "string",
    "case_semantically_valid": "boolean",
    "expected_action": ["answer", "abstain", "clarify", "refuse"],
    "question_answerable_from_supplied_sources": "boolean",
    "atomic_claim_support": [
        "fully-supported",
        "partially-supported",
        "unsupported",
        "not-applicable",
    ],
    "citation_support": ["complete-valid", "incomplete", "invalid", "not-applicable"],
    "boundary_reason": "string-or-null",
    "ambiguity_detected": "boolean",
    "evidence_ids": "array-of-visible-evidence-ids",
    "defect_types": "array-of-action-claim-citation-ambiguity-boundary-or-other",
    "concise_rationale": "string-max-80-words",
}


class PanelPacketError(ValueError):
    """Raised when reviewer blinding or packet integrity drifts."""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _review_item_id(original_id: str) -> str:
    digest = hashlib.sha256(f"{PACKET_SEED}:{original_id}".encode()).hexdigest()
    return f"review-{digest[:20]}"


def _visible_sources(
    source_ids: list[str],
    evidence: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    evidence_by_source = {row["source_id"]: row for row in evidence}
    visible = []
    for source_id in source_ids:
        source = sources[source_id]
        evidence_row = evidence_by_source.get(source_id)
        repository_path = source["repository_url"].removeprefix("https://github.com/")
        visual_assets = [
            {
                **asset,
                "public_raw_url": (
                    f"https://raw.githubusercontent.com/{repository_path}/"
                    f"{source['commit']}/{asset['path']}"
                ),
            }
            for asset in source["dependent_assets"]
        ]
        visible.append(
            {
                "visible_source_id": source_id,
                "course_id": source["course_id"],
                "repository_url": source["repository_url"],
                "commit": source["commit"],
                "path": source["path"],
                "section_heading": source["section_heading"],
                "modalities": source["modalities"],
                "evidence_id": evidence_row["evidence_id"] if evidence_row else None,
                "evidence_excerpt": evidence_row["quote"] if evidence_row else None,
                "visual_assets": visual_assets,
                "embedded_visual_source": (
                    source["path"].endswith(".ipynb")
                    and "diagram" in source["modalities"]
                    and not visual_assets
                ),
            }
        )
    return visible


def _confirmation_items(
    dataset: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    items = []
    for case in dataset["cases"]:
        cited = [
            {
                "evidence_id": row["evidence_id"],
                "visible_source_id": row["source_id"],
                "quote": row["quote"],
            }
            for row in case["evidence"]
        ]
        items.append(
            {
                "review_item_id": _review_item_id(case["case_id"]),
                "item_kind": "confirmation",
                "course_id": case["course_id"],
                "question": case["question"],
                "provided_sources": _visible_sources(
                    case["required_source_ids"], case["evidence"], sources
                ),
                "candidate_record": {
                    "action": case["expected_action"],
                    "answer": case["canonical_answer"],
                    "citations": cited,
                },
            }
        )
    return items


def _control_items(
    calibration: dict[str, Any], sources: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    items = []
    for control in calibration["controls"]:
        truth_evidence = control["authoritative_truth"]["evidence"]
        citations = [
            {
                "evidence_id": row["evidence_id"],
                "visible_source_id": row["source_id"],
                "quote": row["quote"],
            }
            for row in control["candidate_evidence"]
        ]
        items.append(
            {
                "review_item_id": _review_item_id(control["control_id"]),
                "item_kind": "calibration",
                "course_id": control["course_id"],
                "question": control["question"],
                "provided_sources": _visible_sources(
                    [control["source_id"]], truth_evidence, sources
                ),
                "candidate_record": {
                    "action": control["candidate_action"],
                    "answer": control["candidate_answer"],
                    "citations": citations,
                },
            }
        )
    return items


def build_packet() -> dict[str, Any]:
    manifest = _load(MANIFEST_PATH)
    dataset = _load(CASES_PATH)
    calibration = _load(CONTROLS_PATH)
    sources = {row["source_id"]: row for row in manifest["sources"]}
    rng = random.Random(PACKET_SEED)
    controls = _control_items(calibration, sources)
    confirmation = _confirmation_items(dataset, sources)
    rng.shuffle(controls)
    rng.shuffle(confirmation)
    packet: dict[str, Any] = {
        "schema_version": 1,
        "packet_id": "academic-factual-qa-confirmation-002-blinded-review-packet",
        "instrument_id": INSTRUMENT_ID,
        "status": "built-unexecuted",
        "packet_seed": PACKET_SEED,
        "source_manifest_sha256": manifest["content_sha256"],
        "confirmation_dataset_sha256": dataset["content_sha256"],
        "calibration_dataset_sha256": calibration["content_sha256"],
        "calibration_must_pass_before_confirmation_votes_count": True,
        "reviewer_instructions": (
            "Assess only the visible sources, question, and candidate record. "
            "Do not infer hidden condition, generator, gold label, or other reviewer votes. "
            "Return one JSON object matching review_schema for every item."
        ),
        "review_schema": REVIEW_SCHEMA,
        "calibration_item_count": len(controls),
        "confirmation_item_count": len(confirmation),
        "items": controls + confirmation,
    }
    packet["content_sha256"] = canonical_sha256(packet)
    validate_packet(packet)
    return packet


def validate_packet(packet: dict[str, Any]) -> None:
    recorded_hash = packet.get("content_sha256")
    unhashed = {key: value for key, value in packet.items() if key != "content_sha256"}
    if recorded_hash != canonical_sha256(unhashed):
        raise PanelPacketError("packet content hash drifted")
    items = packet["items"]
    if len(items) != 240:
        raise PanelPacketError("packet must contain 240 items")
    if len({row["review_item_id"] for row in items}) != 240:
        raise PanelPacketError("review item IDs must be unique")
    if [row["item_kind"] for row in items[:40]] != ["calibration"] * 40:
        raise PanelPacketError("calibration controls must precede confirmation")
    if [row["item_kind"] for row in items[40:]] != ["confirmation"] * 200:
        raise PanelPacketError("confirmation allocation drifted")
    serialized = json.dumps(packet, sort_keys=True)
    for key in FORBIDDEN_PACKET_KEYS:
        if f'"{key}"' in serialized:
            raise PanelPacketError(f"blinded packet leaks {key}")
    if any("condition" in key.lower() or "generator" in key.lower() for item in items for key in item):
        raise PanelPacketError("condition or generator identity leaked")
    if any(
        source.get("evidence_excerpt") is None
        for item in items
        if item["candidate_record"]["action"] == "answer"
        for source in item["provided_sources"]
    ):
        raise PanelPacketError("answer candidate is missing visible evidence")


def _serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.write:
        require_pre_evaluation_operation_allowed("dataset_generation")
    packet = build_packet()
    rendered = _serialize(packet)
    if args.write:
        PACKET_PATH.write_text(rendered, encoding="utf-8")
        status = "written"
    else:
        if not PACKET_PATH.exists() or PACKET_PATH.read_text(encoding="utf-8") != rendered:
            raise PanelPacketError("committed blinded packet is missing or drifted")
        status = "verified"
    print(
        json.dumps(
            {
                "packet_id": packet["packet_id"],
                "status": status,
                "item_count": len(packet["items"]),
                "provider_calls": 0,
                "gold_labels_exposed": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
