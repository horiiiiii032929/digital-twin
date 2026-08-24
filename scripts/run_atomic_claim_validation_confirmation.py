#!/usr/bin/env python3
"""Validate, simulate, preflight, or execute atomic-claim confirmation 001."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from pydantic import ValidationError

from src.digital_twin.grounding import (
    AtomicAnswerClaim,
    AtomicClaimEvidenceValidator,
    DocumentChunk,
    ExactQuoteAtomicClaimVerifier,
    LocalNliCrossEncoderBackend,
    NliAtomicClaimVerifier,
    NliProbabilities,
    RetrievalHit,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "evidence-sufficiency-v3-atomic-claim-confirmation-001"
DEFAULT_INSTRUMENT = (
    ROOT
    / "research/05_evaluation/instruments/"
    "evidence_sufficiency_v3_atomic_claim_confirmation_001.json"
)


class AtomicClaimConfirmationError(RuntimeError):
    """Raised when the prospective confirmation cannot proceed validly."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AtomicClaimConfirmationError("model verification time needs a timezone")
    return parsed


def validate_instrument(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    instrument = json.loads(path.read_text(encoding="utf-8"))
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise AtomicClaimConfirmationError("instrument ID drifted")
    if instrument.get("status") not in {
        "reviewed-not-authorized",
        "frozen-pending-execution",
        "authorization-revoked",
    }:
        raise AtomicClaimConfirmationError("instrument status is invalid")
    dataset = instrument["dataset"]
    dataset_path = ROOT / dataset["path"]
    if (
        dataset.get("dataset_id")
        != "evidence-sufficiency-v3-atomic-claim-confirmation-001"
        or dataset.get("status") != "frozen-unopened"
        or dataset.get("case_count") != 120
        or dataset.get("releasable_case_count") != 40
        or dataset.get("reject_case_count") != 80
        or dataset.get("historical_120_case_split_reused") is not False
        or _sha256(dataset_path) != dataset.get("file_sha256")
    ):
        raise AtomicClaimConfirmationError("confirmation dataset binding drifted")
    candidate = instrument["candidates"][1]
    model = candidate["model"]
    if (
        instrument["candidates"][0].get("selectable") is not False
        or candidate.get("selectable") is not True
        or model.get("model_id") != "cross-encoder/nli-deberta-v3-base"
        or model.get("revision")
        != "6c749ce3425cd33b46d187e45b92bbf96ee12ec7"
        or model.get("license") != "apache-2.0"
        or model.get("label_order") != ["contradiction", "entailment", "neutral"]
    ):
        raise AtomicClaimConfirmationError("candidate model binding drifted")
    _parse_timestamp(model["verified_at"])
    if instrument["thresholds"] != {
        "minimum_entailment": 0.8,
        "maximum_contradiction": 0.2,
        "maximum_claims": 8,
        "evidence_limit": 5,
    }:
        raise AtomicClaimConfirmationError("claim thresholds drifted")
    if instrument["hard_gates"] != {
        "false_release_count_max": 0,
        "supported_draft_retention_min": 0.9,
        "mutation_detection_rate_min": 1.0,
        "lineage_rejection_rate_min": 1.0,
        "malformed_rejection_rate_min": 1.0,
        "multi_claim_retention_min": 0.9,
        "verifier_p95_ms_max": 500,
        "added_peak_memory_bytes_max": 2147483648,
    }:
        raise AtomicClaimConfirmationError("hard gates drifted")
    safety = instrument["execution_safety"]
    forbidden = {
        "provider_execution_authorized",
        "paid_execution_authorized",
        "private_source_execution_authorized",
        "heldout_execution_authorized",
        "product_binding_authorized",
        "automatic_selection",
        "automatic_release_promotion",
        "gemma_allowed",
        "claude_allowed",
    }
    if any(safety.get(name) is not False for name in forbidden):
        raise AtomicClaimConfirmationError("execution-safety boundary drifted")
    authorities = {
        safety.get("candidate_execution_authorized"),
        safety.get("local_model_execution_authorized"),
        safety.get("confirmation_split_execution_authorized"),
    }
    if len(authorities) != 1:
        raise AtomicClaimConfirmationError("local execution authorities disagree")
    authorized = authorities == {True}
    if authorized != (instrument["status"] == "frozen-pending-execution"):
        raise AtomicClaimConfirmationError("status and local authority disagree")
    return instrument


def preflight(instrument: dict[str, Any]) -> dict[str, Any]:
    safety = instrument["execution_safety"]
    blockers = [
        name.replace("_", "-") + "-false"
        for name in (
            "candidate_execution_authorized",
            "local_model_execution_authorized",
            "confirmation_split_execution_authorized",
        )
        if not safety[name]
    ]
    model = instrument["candidates"][1]["model"]
    age_hours = (
        datetime.now(timezone.utc)
        - _parse_timestamp(model["verified_at"]).astimezone(timezone.utc)
    ).total_seconds() / 3600
    if age_hours > instrument["freshness_policy"]["metadata_max_age_hours"]:
        blockers.append("stale-model-metadata")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "confirmation_split_opened": False,
        "model_loaded": False,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
    }


class _StaticNliBackend:
    implementation_id = "network-free-static-nli"
    version = "simulation-v1"

    def __init__(self, rows: list[NliProbabilities]) -> None:
        self.rows = rows

    def score_pairs(
        self,
        pairs: Sequence[tuple[str, str]],
    ) -> list[NliProbabilities]:
        if len(pairs) != len(self.rows):
            raise AtomicClaimConfirmationError("simulation pair count drifted")
        return self.rows


def _hit(identifier: str, text: str, *, allowed: bool = True) -> RetrievalHit:
    return RetrievalHit(
        chunk=DocumentChunk(
            id=identifier,
            document_id=f"document-{identifier}",
            text=text,
            ordinal=0,
            retrieval_allowed=allowed,
        ),
        relevance_score=1,
        raw_score=1,
    )


def _validator(instrument: dict[str, Any], verifier) -> AtomicClaimEvidenceValidator:
    thresholds = instrument["thresholds"]
    return AtomicClaimEvidenceValidator(
        verifier,
        minimum_entailment=thresholds["minimum_entailment"],
        maximum_contradiction=thresholds["maximum_contradiction"],
        maximum_claims=thresholds["maximum_claims"],
        evidence_limit=thresholds["evidence_limit"],
    )


def simulate(instrument: dict[str, Any]) -> dict[str, Any]:
    evidence = [_hit("hit-a", "A password reset revokes every active session.")]
    supported = AtomicAnswerClaim(
        claim_id="claim-supported",
        text="Existing sessions stop working after a password reset.",
        evidence_hit_ids=["hit-a"],
    )
    unsupported = AtomicAnswerClaim(
        claim_id="claim-unsupported",
        text="A password reset deletes the user account.",
        evidence_hit_ids=["hit-a"],
    )
    candidate = _validator(
        instrument,
        NliAtomicClaimVerifier(
            _StaticNliBackend(
                [
                    NliProbabilities(
                        contradiction=0.02,
                        entailment=0.94,
                        neutral=0.04,
                    )
                ]
            )
        ),
    )
    accepted = candidate.validate([supported], evidence)
    rejected = _validator(
        instrument,
        NliAtomicClaimVerifier(
            _StaticNliBackend(
                [
                    NliProbabilities(
                        contradiction=0.93,
                        entailment=0.02,
                        neutral=0.05,
                    )
                ]
            )
        ),
    ).validate([unsupported], evidence)
    unknown = candidate.validate(
        [
            AtomicAnswerClaim(
                claim_id="claim-lineage",
                text="Existing sessions stop working after a password reset.",
                evidence_hit_ids=["missing"],
            )
        ],
        evidence,
    )
    if not accepted.releasable or rejected.releasable or unknown.releasable:
        raise AtomicClaimConfirmationError("network-free simulation failed")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-network-free-simulation",
        "supported_claim_released": True,
        "unsupported_claim_rejected": True,
        "unknown_lineage_rejected": True,
        "confirmation_split_opened": False,
        "model_loaded": False,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_read": False,
    }


def _dataset(instrument: dict[str, Any]) -> dict[str, Any]:
    path = ROOT / instrument["dataset"]["path"]
    dataset = json.loads(path.read_text(encoding="utf-8"))
    content_hash = dataset.pop("content_sha256")
    if (
        _canonical_sha256(dataset) != content_hash
        or content_hash != instrument["dataset"]["content_sha256"]
    ):
        raise AtomicClaimConfirmationError("confirmation content hash drifted")
    dataset["content_sha256"] = content_hash
    return dataset


def _case_hits(case: dict[str, Any]) -> list[RetrievalHit]:
    return [
        _hit(
            row["hit_id"],
            row["text"],
            allowed=row["retrieval_allowed"],
        )
        for row in case["hits"]
    ]


def _peak_rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if sys.platform == "darwin" else value * 1024)


def _p95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]


def _evaluate(
    candidate_id: str,
    validator: AtomicClaimEvidenceValidator,
    dataset: dict[str, Any],
    gates: dict[str, Any],
    baseline_rss: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for case in dataset["cases"]:
        malformed = False
        started = time.perf_counter()
        try:
            claims = [AtomicAnswerClaim.model_validate(row) for row in case["claims"]]
            decision = validator.validate(claims, _case_hits(case))
        except (ValidationError, ValueError):
            malformed = True
            decision = None
        latencies.append((time.perf_counter() - started) * 1000)
        predicted = bool(decision and decision.releasable)
        rows.append(
            {
                "case_id": case["case_id"],
                "slice": case["slice"],
                "mutation_class": case["mutation_class"],
                "expected_releasable": case["expected_releasable"],
                "predicted_releasable": predicted,
                "correct": predicted == case["expected_releasable"],
                "malformed_contract": malformed,
                "reason": decision.reason if decision else "malformed claim contract",
                "score": decision.score if decision else 0.0,
                "unsupported_claim_ids": (
                    decision.unsupported_claim_ids if decision else []
                ),
            }
        )
    supported = [row for row in rows if row["expected_releasable"]]
    rejected = [row for row in rows if not row["expected_releasable"]]
    mutations = [row for row in rows if row["mutation_class"]]
    lineage = [
        row
        for row in rows
        if row["slice"] in {"wrong-lineage", "stale-source", "cross-course"}
    ]
    malformed = [
        row
        for row in rows
        if row["slice"] in {"missing-citation", "malformed-claim-contract"}
    ]
    multi = [
        row
        for row in rows
        if row["expected_releasable"] and row["slice"].endswith("multi")
    ]
    metrics = {
        "case_count": len(rows),
        "false_release_count": sum(row["predicted_releasable"] for row in rejected),
        "supported_draft_retention": sum(row["predicted_releasable"] for row in supported)
        / len(supported),
        "mutation_detection_rate": sum(not row["predicted_releasable"] for row in mutations)
        / len(mutations),
        "lineage_rejection_rate": sum(not row["predicted_releasable"] for row in lineage)
        / len(lineage),
        "malformed_rejection_rate": sum(not row["predicted_releasable"] for row in malformed)
        / len(malformed),
        "multi_claim_retention": sum(row["predicted_releasable"] for row in multi)
        / len(multi),
        "verifier_p95_ms": _p95(latencies),
        "added_peak_memory_bytes": max(0, _peak_rss_bytes() - baseline_rss),
        "failures_by_slice": dict(
            Counter(row["slice"] for row in rows if not row["correct"])
        ),
    }
    metrics["passed"] = all(
        (
            metrics["false_release_count"] <= gates["false_release_count_max"],
            metrics["supported_draft_retention"]
            >= gates["supported_draft_retention_min"],
            metrics["mutation_detection_rate"]
            >= gates["mutation_detection_rate_min"],
            metrics["lineage_rejection_rate"]
            >= gates["lineage_rejection_rate_min"],
            metrics["malformed_rejection_rate"]
            >= gates["malformed_rejection_rate_min"],
            metrics["multi_claim_retention"] >= gates["multi_claim_retention_min"],
            metrics["verifier_p95_ms"] <= gates["verifier_p95_ms_max"],
            metrics["added_peak_memory_bytes"]
            <= gates["added_peak_memory_bytes_max"],
        )
    )
    return {"candidate_id": candidate_id, "metrics": metrics, "cases": rows}


def execute(instrument: dict[str, Any]) -> dict[str, Any]:
    ready = preflight(instrument)
    if ready["status"] != "ready":
        raise AtomicClaimConfirmationError(
            "execution is blocked: " + ", ".join(ready["blockers"])
        )
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    output_path = ROOT / instrument["output"]["raw_ignored_path"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise AtomicClaimConfirmationError("exclusive result path already exists")
    dataset = _dataset(instrument)
    baseline_rss = _peak_rss_bytes()
    exact = _evaluate(
        "exact-quote-atomic-claim-control-v1",
        _validator(instrument, ExactQuoteAtomicClaimVerifier()),
        dataset,
        instrument["hard_gates"],
        baseline_rss,
    )
    model = instrument["candidates"][1]["model"]
    nli_backend = LocalNliCrossEncoderBackend(
        model_id=model["model_id"],
        revision=model["revision"],
        max_length=model["execution_max_length"],
        batch_size=8,
        local_files_only=False,
    )
    nli = _evaluate(
        "nli-atomic-claim-verifier-v1",
        _validator(instrument, NliAtomicClaimVerifier(nli_backend)),
        dataset,
        instrument["hard_gates"],
        baseline_rss,
    )
    failed = [row for row in nli["cases"] if not row["correct"]]
    controls = [row for row in nli["cases"] if row["correct"]]
    priority = (failed + controls[: max(0, 12 - len(failed))])[:12]
    status = "completed-keep" if nli["metrics"]["passed"] else "completed-refine"
    result = {
        "schema_version": 1,
        "run_id": INSTRUMENT_ID,
        "status": status,
        "decision": "Keep" if status == "completed-keep" else "Refine",
        "instrument_sha256": _sha256(DEFAULT_INSTRUMENT),
        "dataset_content_sha256": dataset["content_sha256"],
        "code_revision": _git_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "candidates": [exact, nli],
        "priority_audit_packet": priority,
        "provider_calls": 0,
        "paid_cost_usd": 0,
        "private_data_used": False,
        "automatic_product_binding": False,
    }
    result["canonical_result_sha256"] = _canonical_sha256(result)
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    return result


def _git_revision() -> str:
    import subprocess

    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    import subprocess

    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    args = parser.parse_args()
    instrument = validate_instrument(args.instrument)
    if args.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    if args.simulate:
        result = simulate(instrument)
    elif args.execute:
        result = execute(instrument)
    else:
        result = preflight(instrument)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
