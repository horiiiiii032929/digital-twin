#!/usr/bin/env python3
"""Bind the unchanged confirmation-023 package to harness-only attempt 024."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_persona_confirmation_023 as predecessor,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-persona-confirmation-024"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_persona_confirmation_024.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.predecessor.DAY
build_contract = predecessor.build_contract
public_payload = predecessor.public_payload
hidden_gold_payload = predecessor.hidden_gold_payload
source_fixture_for_case = predecessor.source_fixture_for_case


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    public = public_payload()
    hidden = hidden_gold_payload()
    if instrument["instrument_id"] != INSTRUMENT_ID:
        raise ValueError("confirmation 024 identity drifted")
    if instrument["dataset"]["dataset_id"] != predecessor.INSTRUMENT_ID:
        raise ValueError("confirmation 024 must reuse the unopened 023 package")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 024 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 024 hidden-gold hash drifted")
    if instrument["authority"]["maximum_cost_usd"] != 5.0:
        raise ValueError("confirmation 024 requires the USD 5 harness ceiling")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "case_count": len(build_contract()),
        "source_family_count": 50,
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
