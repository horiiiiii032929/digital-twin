#!/usr/bin/env python3
"""Bind the unchanged confirmation-026 package to harness-only attempt 027.

The 027 attempt persisted 282 of 670 responses and then failed with "direct
transport canary binding drifted". That check is correct and valuable:
``_transport_canary_totals`` recomputes the run binding on every case, the
binding includes the git revision, and the operator committed while the run was
in flight. The harness detected the code changing underneath a running
evaluation, exactly as designed.

There is no code defect to fix. The correction is operational: no git operation
may run while an evaluation is executing.

Hidden gold has never been opened for this package across 026 and 027, so the
package itself remains untouched evidence. This follows the same route
confirmation 024 took after 023: a new attempt identity binding the identical
unopened public and gold payloads.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts import (
    build_governed_full_autonomy_v2_1_corpus_confirmation_027 as predecessor,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "governed-full-autonomy-v2-1-corpus-confirmation-028"
INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/"
    "governed_full_autonomy_v2_1_corpus_confirmation_028.json"
)
CONDITIONS = predecessor.CONDITIONS
SELECTED_CONDITIONS = predecessor.SELECTED_CONDITIONS
DAY = predecessor.DAY
DISTRACTOR_COUNT = predecessor.DISTRACTOR_COUNT
SOURCE_FAMILY_START = predecessor.SOURCE_FAMILY_START
SOURCE_FAMILY_COUNT = predecessor.SOURCE_FAMILY_COUNT
canonical_hash = predecessor.canonical_hash
build_contract = predecessor.build_contract
public_payload = predecessor.public_payload
hidden_gold_payload = predecessor.hidden_gold_payload
source_fixture_for_case = predecessor.source_fixture_for_case
distractor_fixtures_for_case = predecessor.distractor_fixtures_for_case


def validate() -> dict[str, Any]:
    instrument = json.loads(INSTRUMENT.read_text(encoding="utf-8"))
    public = public_payload()
    hidden = hidden_gold_payload()
    if instrument["instrument_id"] != INSTRUMENT_ID:
        raise ValueError("confirmation 028 identity drifted")
    if instrument["dataset"]["dataset_id"] != "governed-full-autonomy-v2-1-corpus-confirmation-026":
        raise ValueError("confirmation 028 must reuse the unopened 026 package")
    if public["content_sha256"] != instrument["dataset"]["public_sha256"]:
        raise ValueError("confirmation 028 public hash drifted")
    if hidden["content_sha256"] != instrument["dataset"]["hidden_gold_sha256"]:
        raise ValueError("confirmation 028 hidden-gold hash drifted")
    if instrument["authority"]["maximum_cost_usd"] != 5.0:
        raise ValueError("confirmation 028 requires the USD 5 ceiling")
    rows = build_contract()
    if len(rows) != 670:
        raise ValueError("confirmation 028 requires 670 cases")
    authority = instrument["authority"]
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": instrument["status"],
        "case_count": len(rows),
        "source_family_count": SOURCE_FAMILY_COUNT,
        "published_sources_per_release": DISTRACTOR_COUNT + 1,
        "reused_unopened_predecessor_package": predecessor.INSTRUMENT_ID,
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
