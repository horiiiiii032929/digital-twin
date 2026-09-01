#!/usr/bin/env python3
"""Bind the one permitted schema-only correction for actual evaluation 004."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_evaluation_003 as predecessor,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-evaluation-004"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_evaluation_004.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS
source_fixture = predecessor.source_fixture
source_template_number = predecessor.source_template_number
canonical_hash = predecessor.canonical_hash


def build_contract():
    return predecessor.build_contract()


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
    predecessor.validate()
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise ValueError("actual-product correction identity drifted")
    if instrument.get("status") not in {
        "frozen-pending-execution",
        "completed-authorization-revoked",
        "invalid-execution-authorization-revoked",
    }:
        raise ValueError("actual-product correction status is invalid")
    authority = instrument["authority"]
    authorized = instrument["status"] == "frozen-pending-execution"
    if authority["provider_execution_authorized"] is not authorized:
        raise ValueError("provider authority and status disagree")
    if authority["paid_execution_authorized"] is not authorized:
        raise ValueError("paid authority and status disagree")
    if authority["automatic_promotion"] is not False:
        raise ValueError("actual-product correction cannot auto-promote")
    if instrument.get("corrects_invalid_execution") != (
        "governed-full-autonomy-v2-1-actual-product-evaluation-003"
    ):
        raise ValueError("invalid predecessor binding drifted")
    if instrument.get("harness_correction", {}).get("changed_surface") != [
        "provider-json-schema-transport"
    ]:
        raise ValueError("correction changed a non-harness surface")
    selected = instrument["selected_grounding"]
    result_path = ROOT / selected["result_path"]
    if hashlib.sha256(result_path.read_bytes()).hexdigest() != selected[
        "result_sha256"
    ]:
        raise ValueError("selected grounding result hash drifted")
    public = public_payload()
    hidden = hidden_gold_payload()
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("public package hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("hidden-gold package hash drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-frozen-pending-execution"
        if authorized
        else "passed-terminal",
        "case_count": len(build_contract()),
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
