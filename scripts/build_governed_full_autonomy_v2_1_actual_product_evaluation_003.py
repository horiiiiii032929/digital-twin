#!/usr/bin/env python3
"""Bind the 820-case product portfolio to the selected ambiguity-safe V2."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_002 as legacy,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-evaluation-003"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_evaluation_003.json"
)
CONDITIONS = legacy.CONDITIONS
DAY = legacy.DAY
INVARIANTS = legacy.INVARIANTS
source_fixture = legacy.source_fixture
source_template_number = legacy.source_template_number
canonical_hash = legacy.canonical_hash


def build_contract():
    """Add public source scope without exposing answer or gold fields."""

    rows = []
    for condition, case, gold in legacy.build_contract():
        source = source_fixture(source_template_number(case.case_id))
        source_path = f"{source['source_id']}.md"
        section = f"Protocol {source_template_number(case.case_id):03d}"
        events = []
        for event in case.events:
            if event.kind == "student-message":
                payload = dict(event.payload)
                payload["message"] = (
                    f'Using source "{source_path}" in section "{section}", '
                    f"{payload['message']}"
                )
                event = event.model_copy(update={"payload": payload})
            events.append(event)
        rows.append((condition, case.model_copy(update={"events": events}), gold))
    return rows


def public_payload() -> dict[str, Any]:
    rows = [
        {"condition": condition, "case": case.model_dump(mode="json")}
        for condition, case, _gold in build_contract()
    ]
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": len(rows),
        "rows": rows,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def hidden_gold_payload() -> dict[str, Any]:
    rows = [gold.model_dump(mode="json") for _condition, _case, gold in build_contract()]
    payload = {
        "schema_version": 1,
        "dataset_id": INSTRUMENT_ID,
        "case_count": len(rows),
        "gold": rows,
    }
    payload["content_sha256"] = canonical_hash(payload)
    return payload


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ValueError("actual-product successor identity drifted")
    if instrument.get("status") not in {
        "reviewed-build-only",
        "frozen-pending-execution",
        "completed-authorization-revoked",
        "invalid-execution-authorization-revoked",
    }:
        raise ValueError("actual-product successor status is invalid")
    authority = instrument["authority"]
    authorized = instrument["status"] == "frozen-pending-execution"
    if authority["provider_execution_authorized"] is not authorized:
        raise ValueError("provider authority and status disagree")
    if authority["paid_execution_authorized"] is not authorized:
        raise ValueError("paid authority and status disagree")
    if authority["automatic_promotion"] is not False:
        raise ValueError("actual-product successor cannot auto-promote")
    selected = instrument["selected_grounding"]
    if selected != {
        "result_id": "academic-factual-qa-ambiguity-safe-comparison-002",
        "result_path": "research/05_evaluation/records/academic-factual-qa-ambiguity-safe-comparison-002.json",
        "result_sha256": "c957c1ec6d665b1b46f08d3a112eef291a3becef95c47db66b3855c40e6fddd6",
        "architecture_id": "ambiguity-safe-source-semantic-evidence-atoms-v2",
        "rollback_architecture_id": "source-semantic-evidence-atoms-v1",
    }:
        raise ValueError("selected grounding binding drifted")
    result_path = ROOT / selected["result_path"]
    if hashlib.sha256(result_path.read_bytes()).hexdigest() != selected[
        "result_sha256"
    ]:
        raise ValueError("selected grounding result hash drifted")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if (
        result.get("status") != "completed-keep"
        or result.get("decision", {}).get("selected_architecture_id")
        != selected["architecture_id"]
    ):
        raise ValueError("selected grounding result is not Keep")
    contract = build_contract()
    case_ids = [case.case_id for _condition, case, _gold in contract]
    gold_ids = [gold.case_id for _condition, _case, gold in contract]
    if len(contract) != 820 or len(case_ids) != len(set(case_ids)):
        raise ValueError("820-case identity contract drifted")
    if set(case_ids) != set(gold_ids):
        raise ValueError("public and hidden-gold identities drifted")
    public = public_payload()
    hidden = hidden_gold_payload()
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("public package hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("hidden-gold package hash drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "passed-frozen-pending-execution" if authorized else "passed-build-only"
        ),
        "case_count": 820,
        "trajectory_case_count": 600,
        "long_horizon_case_count": 100,
        "proactive_opportunity_case_count": 120,
        "source_template_count": 50,
        "public_sha256": public["content_sha256"],
        "hidden_gold_sha256": hidden["content_sha256"],
        "provider_execution_authorized": authority["provider_execution_authorized"],
        "paid_execution_authorized": authority["paid_execution_authorized"],
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
