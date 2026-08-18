#!/usr/bin/env python3
"""Write the corrected aggregate-only interpretation of anchor machine review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.judge_professor_fidelity import write_json_exclusive
from scripts.summarize_professor_fidelity_anchor_machine_review import summarize


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "reports/generated/"
    "professor-fidelity-v2-anchor-002-machine-review-summary-001-"
    "analysis-correction-001.json"
)
CORRECTION_ID = (
    "professor-fidelity-v2-anchor-002-machine-review-summary-001-"
    "analysis-correction-001"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def correct() -> dict[str, Any]:
    result = summarize()
    result["summary_id"] = CORRECTION_ID
    result["correction_of"] = (
        "professor-fidelity-v2-anchor-002-machine-review-summary-001"
    )
    result["correction_scope"] = [
        "reclassify pedagogy-versus-hidden-hard-gate disagreement as diagnostic",
        "compute pairwise repeat agreement from source labels",
        "state repeat denominators as two cases, eight responses, and 48 labels",
        "separate all-response citation compliance from claim-applicable correctness",
    ]
    result["decision_impact"] = (
        "No decision change: repeat consistency, completed sensitivity, and blinded "
        "reference gates still keep automated pedagogy ineligible."
    )
    return result


def main() -> None:
    arguments = parse_args()
    result = correct()
    write_json_exclusive(arguments.output, result)
    print(
        json.dumps(
            {
                "summary_id": result["summary_id"],
                "status": result["status"],
                "decision": result["decision"],
                "decision_impact": result["decision_impact"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
