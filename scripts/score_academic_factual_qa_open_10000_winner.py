#!/usr/bin/env python3
"""Score the winner regression with the registered, unchanged gate logic.

``score_academic_factual_qa_open_10000`` owns the factual grounding, action,
claim, citation, retrieval, completion, severe-release, and paired
non-inferiority gates. This module reuses those functions verbatim and selects
no threshold of its own; it only supplies the sealed package and this
instrument's own bounded authorization.

``score_packages`` opens the response ledger and refuses anything that is not a
durable, complete run before it touches gold, so hidden gold cannot be read
early through this path.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import academic_factual_qa_open_10000_sealed_package as sealed  # noqa: E402
from scripts.run_academic_factual_qa_open_10000_winner import (  # noqa: E402
    ARMS,
    INSTRUMENT_ID,
    _arm_root,
)
from scripts.score_academic_factual_qa_open_10000 import (  # noqa: E402
    paired_comparison,
    score_packages,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


PACKAGE_FILES = {
    "public_cases": "final-public-cases.json",
    "hidden_gold": "final-hidden-gold.json",
    "control_cases": "control-public-cases.json",
    "control_gold": "control-hidden-gold.json",
}
# Registered in the Program 011 comparison and carried forward unchanged.
LOWER_DELTA_GATE = 0.0
BOUNDARY_NOT_WORSE = True


class WinnerScoringError(RuntimeError):
    """Raised when the evidence is not in a scorable state."""


def _ledger(arm_id: str) -> Path:
    path = _arm_root(arm_id) / "responses.sqlite3"
    if not path.is_file():
        raise WinnerScoringError(f"{arm_id} has no response ledger at {path}")
    return path


def _receipts(arm_ids: list[str]) -> list[sealed.CompletionReceiptV1]:
    import sqlite3

    receipts = []
    for arm_id in arm_ids:
        connection = sqlite3.connect(f"file:{_ledger(arm_id)}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            count = connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        finally:
            connection.close()
        receipts.append(
            sealed.CompletionReceiptV1(
                ledger_id=arm_id,
                status=str(metadata.get("status", "")),
                response_count=int(count),
                expected_count=int(ARMS[arm_id]["expected_case_count"]),
            )
        )
    return receipts


def _pairing_manifest(
    *,
    package: sealed.SealedPackageV1,
    cases_file: str,
    gold_file: str,
    destination: Path,
) -> Path:
    """Declare which public package pairs with which gold package.

    The sealed packages carry different ``split`` labels ("final" against
    "final-hidden"), so the scorer's implicit pairing check does not apply and
    it requires an explicit manifest instead. This is built only after the
    completion receipts pass, so it is written with gold already legitimately
    open and never earlier.
    """

    cases_package = json.loads((package.root / cases_file).read_text(encoding="utf-8"))
    gold_package = json.loads((package.root / gold_file).read_text(encoding="utf-8"))
    case_ids = sorted(row["case_id"] for row in cases_package["cases"])
    gold_ids = sorted(row["case_id"] for row in gold_package["gold"])
    if case_ids != gold_ids:
        raise WinnerScoringError(
            f"{cases_file} and {gold_file} do not cover the same case identities"
        )
    payload: dict[str, Any] = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "public_package": {
            "dataset_id": cases_package.get("dataset_id"),
            "split": cases_package.get("split"),
            "content_sha256": cases_package.get("content_sha256"),
        },
        "hidden_gold_package": {
            "dataset_id": gold_package.get("dataset_id"),
            "split": gold_package.get("split"),
            "content_sha256": gold_package.get("content_sha256"),
        },
        "case_count": len(case_ids),
        "case_ids_sha256": canonical_json_sha256(case_ids),
    }
    payload["content_sha256"] = canonical_json_sha256(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return destination


def score(*, candidate_arm: str, control_arm: str) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
    package = sealed.resolve_sealed_package()

    # Refuse before any gold path is even constructed unless both arms are
    # durable and complete.
    receipts = _receipts([candidate_arm, control_arm])
    package.hidden_gold(receipts=receipts)

    candidate = score_packages(
        cases_path=package.root / PACKAGE_FILES["public_cases"],
        gold_path=package.root / PACKAGE_FILES["hidden_gold"],
        responses_path=_ledger(candidate_arm),
        pairing_path=_pairing_manifest(
            package=package,
            cases_file=PACKAGE_FILES["public_cases"],
            gold_file=PACKAGE_FILES["hidden_gold"],
            destination=_arm_root(candidate_arm) / "pairing-manifest.json",
        ),
    )
    control = score_packages(
        cases_path=package.root / PACKAGE_FILES["control_cases"],
        gold_path=package.root / PACKAGE_FILES["control_gold"],
        responses_path=_ledger(control_arm),
        pairing_path=_pairing_manifest(
            package=package,
            cases_file=PACKAGE_FILES["control_cases"],
            gold_file=PACKAGE_FILES["control_gold"],
            destination=_arm_root(control_arm) / "pairing-manifest.json",
        ),
    )
    comparison = paired_comparison(
        candidate,
        control,
        lower_delta_gate=LOWER_DELTA_GATE,
        boundary_not_worse=BOUNDARY_NOT_WORSE,
    )
    gates = candidate.get("gate_results", {})
    failed = sorted(name for name, passed in gates.items() if not passed)
    return {
        "instrument_id": INSTRUMENT_ID,
        "evidence_class": "known-benchmark-regression",
        "candidate_arm": candidate_arm,
        "control_arm": control_arm,
        "candidate_status": candidate.get("status"),
        "gate_results": gates,
        "failed_gates": failed,
        "decision": "keep" if not failed else "no-release",
        "candidate_metrics": {
            key: value
            for key, value in candidate.items()
            if key not in {"case_scores", "gate_results"}
        },
        "control_metrics": {
            key: value
            for key, value in control.items()
            if key not in {"case_scores", "gate_results"}
        },
        "paired_comparison": comparison,
        "hidden_gold_opened_after_response_completion": True,
        "completion_receipts": [
            {
                "ledger_id": row.ledger_id,
                "status": row.status,
                "response_count": row.response_count,
                "expected_count": row.expected_count,
            }
            for row in receipts
        ],
        **package.provenance(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-arm", default="candidate-deterministic")
    parser.add_argument("--control-arm", default="control")
    parser.add_argument("--output", type=Path, default=None)
    arguments = parser.parse_args()
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
    result = score(
        candidate_arm=arguments.candidate_arm,
        control_arm=arguments.control_arm,
    )
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized, encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
