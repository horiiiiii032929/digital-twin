#!/usr/bin/env python3
"""Bind the sole canary-role correction to the unopened confirmation-018 gold."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts import (
    build_governed_full_autonomy_v2_1_actual_product_confirmation_018 as predecessor,
)
from src.digital_twin.student.autonomy_eligibility import (
    ACTION_ELIGIBILITY_VERSION,
    event_action_contract,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-actual-product-confirmation-019"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_actual_product_confirmation_019.json"
)
CONDITIONS = predecessor.CONDITIONS
DAY = predecessor.DAY
INVARIANTS = predecessor.INVARIANTS


def build_contract():
    return predecessor.build_contract()


def public_payload():
    return predecessor.public_payload()


def hidden_gold_payload():
    return predecessor.hidden_gold_payload()


def source_fixture_for_case(case_id: str):
    return predecessor.source_fixture_for_case(case_id)


def validate() -> dict[str, object]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    public = public_payload()
    hidden = hidden_gold_payload()
    if instrument["instrument_id"] != INSTRUMENT_ID:
        raise ValueError("confirmation 019 identity drifted")
    if instrument["method"]["action_eligibility_version"] != ACTION_ELIGIBILITY_VERSION:
        raise ValueError("confirmation 019 eligibility version drifted")
    if instrument["method"]["event_action_contract"] != event_action_contract():
        raise ValueError("confirmation 019 event-action contract drifted")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 019 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 019 hidden-gold hash drifted")
    if instrument["execution"]["harness_correction_only"] is not True:
        raise ValueError("confirmation 019 must remain a harness-only correction")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "provider_execution_authorized": authority["provider_execution_authorized"],
        "paid_execution_authorized": authority["paid_execution_authorized"],
        "case_count": len(build_contract()),
        "source_family_count": 50,
        "reuses_unopened_confirmation_018_hidden_gold": True,
        "prior_public_canary_count": 2,
        "public_sha256": public["content_sha256"],
        "hidden_gold_sha256": hidden["content_sha256"],
        "provider_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
