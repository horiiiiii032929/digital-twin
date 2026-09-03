#!/usr/bin/env python3
"""Select the product's evidence gate on development evidence.

Registered by `research/05_evaluation/instruments/product_evidence_gate_selection_002.json`,
whose decision rule was committed before this ran.

One development corpus, gold already committed, everything held fixed except
the evidence gate. Three arms: the gate the product ships today, the v4
candidate confirmation 028 recorded Keep for, and the v3 predecessor the sealed
regression recorded No Release for.

Scoring reuses `score_academic_factual_qa_open_10000.score_packages` unchanged.
This module selects no threshold. Nothing here reads, opens, or rescores a
sealed package.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import academic_factual_qa_open_10000_winner_adapter as winner  # noqa: E402
from scripts.score_academic_factual_qa_open_10000 import score_packages  # noqa: E402
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "product-evidence-gate-selection-002"
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/product_evidence_gate_selection_002.json"
)
OUTPUT_ROOT = ROOT / "reports/generated" / INSTRUMENT_ID
CASES_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_cases_002.json"
)
GOLD_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_gold_002.json"
)
# The development source package is ignored output and lives beside the
# repository that produced it.
# Selection 002 runs on the region-granularity corpus whose spans match gold.
CORPUS_PATH = ROOT / (
    "reports/generated/academic-factual-qa-development-region-corpus-001/"
    "development-region-corpus.json"
)

ARMS: dict[str, dict[str, Any]] = {
    "incumbent": {
        "evidence_gate": winner.PRODUCT_SHIPPED_GATE,
        "role": "what .env.local-r1 actually selects and the 2026-09-02 qualification ran",
    },
    "template-default": {
        "evidence_gate": winner.PRODUCT_STRUCTURED_LEXICAL_GATE,
        "role": "the deploy/local-r1.env.example default, first mistaken for the incumbent",
    },
    "candidate": {
        "evidence_gate": winner.SUCCESSOR_EVIDENCE_GATE,
        "role": "confirmed Keep by corpus confirmation 028",
    },
    "reference": {
        "evidence_gate": winner.CANDIDATE_EVIDENCE_GATE,
        "role": "the v3 predecessor the sealed regression recorded No Release for",
    },
}


class GateSelectionError(RuntimeError):
    """Raised when the comparison cannot produce comparable evidence."""


def _sources_path() -> Path:
    if not CORPUS_PATH.is_file():
        raise GateSelectionError(
            "build the region corpus first: "
            "scripts/build_academic_factual_qa_development_region_corpus.py"
        )
    return CORPUS_PATH


def _cases() -> list[EvaluationCaseV1]:
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return [EvaluationCaseV1.model_validate(row) for row in payload["cases"]]


def _manifest(arm_id: str) -> SystemUnderTestManifestV1:
    return SystemUnderTestManifestV1(
        flow_id=winner.WINNER_FLOW_ID,
        adapter_version="v1",
        code_revision="8966e47",
        profile_sha256=winner.winner_profile_sha256(),
        retriever=winner.WINNER_RETRIEVER_ID,
        generator=winner.WINNER_GENERATOR_ID,
        policy=winner.WINNER_POLICY_ID,
        evidence_gate=ARMS[arm_id]["evidence_gate"],
        model_bindings={"factual_generator": "deterministic/evidence-set-v2"},
        known_benchmark=False,
    )


def _run_arm(arm_id: str) -> dict[str, Any]:
    import sqlite3

    cases = _cases()
    existing = OUTPUT_ROOT / arm_id / "responses.sqlite3"
    if existing.is_file():
        connection = sqlite3.connect(f"file:{existing}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            rows = connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        finally:
            connection.close()
        if metadata.get("status") == "completed" and rows == len(cases):
            return {
                "arm_id": arm_id,
                "evidence_gate": ARMS[arm_id]["evidence_gate"],
                "case_count": rows,
                "provider_calls": 0,
                "ledger_status": "completed",
                "ledger_path": str(existing),
                "reused_completed_ledger": True,
            }
        raise GateSelectionError(
            f"{arm_id} has an incomplete ledger at {existing}; remove it to re-run"
        )

    manifest = _manifest(arm_id)
    root = OUTPUT_ROOT / arm_id
    root.mkdir(parents=True, exist_ok=True)
    adapter = winner.build_winner_adapter(
        manifest=manifest,
        cases=cases,
        runtime={
            "state_path": root / "state.sqlite3",
            "source_package_path": _sources_path(),
            "conversation_scope": "case",
        },
    )
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    ledger = ResponseLedgerV1(
        root / "responses.sqlite3",
        cases_sha256=payload["content_sha256"],
        system_manifest_sha256=canonical_json_sha256(manifest.model_dump(mode="json")),
        run_configuration_sha256=canonical_json_sha256(
            {"instrument_id": INSTRUMENT_ID, "arm_id": arm_id, "case_count": len(cases)}
        ),
        resume=False,
    )
    started = time.monotonic()
    snapshot = asyncio.run(
        execute_cases(cases=cases, adapter=adapter, manifest=manifest, ledger=ledger)
    )
    elapsed = time.monotonic() - started
    if adapter.provider_call_count != 0:
        raise GateSelectionError(
            f"{arm_id} made {adapter.provider_call_count} provider calls; this "
            "comparison is registered as provider-free"
        )
    ledger.close()
    return {
        "arm_id": arm_id,
        "evidence_gate": ARMS[arm_id]["evidence_gate"],
        "evidence_gate_implementation_id": adapter.evidence_gate_id,
        "case_count": len(cases),
        "elapsed_seconds": elapsed,
        "provider_calls": 0,
        "ledger_status": snapshot["status"],
        "ledger_path": str(root / "responses.sqlite3"),
    }


def _pairing_manifest(destination: Path) -> Path:
    """Declare which public package pairs with which gold package.

    The development cases and gold carry different `split` labels, so the
    scorer's implicit pairing check does not apply and it requires an explicit
    manifest. The gold is the committed development answer key; nothing here is
    held out.
    """

    cases_package = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    gold_package = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    case_ids = sorted(row["case_id"] for row in cases_package["cases"])
    gold_ids = sorted(row["case_id"] for row in gold_package["gold"])
    if case_ids != gold_ids:
        raise GateSelectionError("development cases and gold cover different identities")
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
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return destination


def _score_arm(arm_id: str) -> dict[str, Any]:
    scored = score_packages(
        cases_path=CASES_PATH,
        gold_path=GOLD_PATH,
        responses_path=OUTPUT_ROOT / arm_id / "responses.sqlite3",
        pairing_path=_pairing_manifest(OUTPUT_ROOT / arm_id / "pairing-manifest.json"),
    )
    summary = scored["summary"]
    return {
        "arm_id": arm_id,
        "evidence_gate": ARMS[arm_id]["evidence_gate"],
        "fully_grounded_factual_success": summary["overall_grounded_task_success"],
        "severe_unsupported_release_count": summary["severe_unsupported_release_count"],
        "operational_failure_count": summary["operational_failure_count"],
        "case_count": summary["case_count"],
        "gate_results": scored.get("gate_results", {}),
        "status": scored.get("status"),
    }


def _decide(scores: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Apply the rule that was committed before any arm ran."""

    incumbent = scores["incumbent"]
    candidate = scores["candidate"]
    checks = {
        "severe_unsupported_not_worse": (
            candidate["severe_unsupported_release_count"]
            <= incumbent["severe_unsupported_release_count"]
        ),
        "grounded_success_strictly_better": (
            candidate["fully_grounded_factual_success"]
            > incumbent["fully_grounded_factual_success"]
        ),
        "operational_failures_not_worse": (
            candidate["operational_failure_count"]
            <= incumbent["operational_failure_count"]
        ),
    }
    promote = all(checks.values())
    return {
        "promote_candidate": promote,
        "checks": checks,
        "selected_gate": (
            candidate["evidence_gate"] if promote else incumbent["evidence_gate"]
        ),
        "disposition": (
            "promote v4 into the product"
            if promote
            else "keep structured-lexical-v1; record v4 as implemented but unpromoted"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.parse_args()
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    instrument = json.loads(INSTRUMENT_PATH.read_text(encoding="utf-8"))
    if not instrument["decision_rule"]["fixed_before_execution"]:
        raise GateSelectionError("the decision rule must be fixed before execution")

    runs = {arm_id: _run_arm(arm_id) for arm_id in ARMS}
    scores = {arm_id: _score_arm(arm_id) for arm_id in ARMS}
    decision = _decide(scores)
    result = {
        "instrument_id": INSTRUMENT_ID,
        "evidence_class": "development-split-method-selection",
        "dataset_id": "academic-factual-qa-open-10000-v1-development-002",
        "runs": runs,
        "scores": scores,
        "decision": decision,
        "decision_rule_source": str(INSTRUMENT_PATH.relative_to(ROOT)),
        "provider_calls": 0,
        "cost_usd": 0.0,
        "sealed_package_touched": False,
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
