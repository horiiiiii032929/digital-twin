"""Build the corrected evidence-sufficiency v2 decision draft.

The historical 001 draft remains immutable. This successor corrects only the
defects confirmed by the bounded deterministic and Codex semantic audit:

* multi-evidence cases must bind two distinct active source units;
* permission/version cases must expose the paired stale source as a distractor;
* modality-tagged cases must state that candidate input is derived text, not a
  raw-visual quality benchmark; and
* the priority packet must cover every high-risk decision boundary.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from scripts.build_evidence_sufficiency_v2_decision_draft import (
    DecisionDraftError,
    _sha256,
    build_draft,
    validate_draft,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ID = "evidence-sufficiency-v2-deterministic-audit-001"
DATASET_ID = "evidence-sufficiency-v2-decision-draft-002"
BASE_DATASET_ID = "evidence-sufficiency-v2-decision-draft-001"
BASE_CONTENT_SHA256 = "7c43a9195ad95c660ec113e7499904439e5853ecf2653bf1025c32f233bcf023"
DEFAULT_OUTPUT = (
    ROOT
    / "research/05_evaluation/drafts/evidence_sufficiency_v2_decision_draft_002.json"
)


MULTI_EVIDENCE_SPECS = (
    (
        "esv2-multi-01",
        "database",
        "database-transactions-claim-1",
        "What atomicity rule applies to transaction changes",
        "database-recovery-claim-1",
        "what ordering does write-ahead logging require?",
    ),
    (
        "esv2-multi-02",
        "distributed-systems",
        "distributed-systems-consistency-claim-1",
        "What ordering does linearizability require",
        "distributed-systems-failure-claim-1",
        "what does a timeout establish?",
    ),
    (
        "esv2-multi-03",
        "human-computer-interaction",
        "human-computer-interaction-usability-claim-1",
        "What does a usability test observe",
        "human-computer-interaction-feedback-claim-1",
        "when must a system acknowledge a user action?",
    ),
    (
        "esv2-multi-04",
        "machine-learning",
        "machine-learning-splits-claim-1",
        "When may the test split be used",
        "machine-learning-metrics-claim-1",
        "what does precision measure?",
    ),
    (
        "esv2-multi-05",
        "secure-web",
        "secure-web-sessions-claim-1",
        "When must a session identifier be rotated",
        "secure-web-authorization-claim-1",
        "where must object authorization be checked?",
    ),
    (
        "esv2-multi-06",
        "software-testing",
        "software-testing-unit-claim-1",
        "What does a unit test isolate",
        "software-testing-integration-claim-1",
        "what does an integration test verify?",
    ),
    (
        "esv2-multi-07",
        "database",
        "database-indexes-claim-1",
        "What query pattern does a B-tree index support",
        "database-isolation-claim-2",
        "which anomaly can remain under snapshot isolation?",
    ),
    (
        "esv2-multi-08",
        "distributed-systems",
        "distributed-systems-replication-claim-1",
        "What overlap must quorum reads and writes provide",
        "distributed-systems-consensus-claim-2",
        "what must happen to a committed log entry across leader changes?",
    ),
    (
        "esv2-multi-09",
        "human-computer-interaction",
        "human-computer-interaction-accessibility-claim-1",
        "What requirements apply to keyboard focus",
        "human-computer-interaction-cognitive-load-claim-1",
        "what does progressive disclosure do?",
    ),
    (
        "esv2-multi-10",
        "machine-learning",
        "machine-learning-regularization-claim-1",
        "What penalty does L2 regularization add",
        "machine-learning-calibration-claim-1",
        "what does a calibrated probability of 0.8 mean?",
    ),
    (
        "esv2-multi-11",
        "secure-web",
        "secure-web-cookies-claim-1",
        "What transport restriction does the Secure cookie flag impose",
        "secure-web-oauth-claim-1",
        "what does the OAuth state value bind?",
    ),
    (
        "esv2-multi-12",
        "software-testing",
        "software-testing-property-claim-1",
        "What does a property test check",
        "software-testing-mutation-claim-1",
        "what does mutation testing check?",
    ),
    (
        "esv2-multi-13",
        "database",
        "database-replication-claim-1",
        "When does synchronous replication confirm a write",
        "database-recovery-claim-2",
        "what is the purpose of a recovery checkpoint?",
    ),
    (
        "esv2-multi-14",
        "distributed-systems",
        "distributed-systems-time-claim-1",
        "What property makes a monotonic clock suitable for elapsed time",
        "distributed-systems-failure-claim-2",
        "why must retried operations be idempotent or deduplicated?",
    ),
    (
        "esv2-multi-15",
        "human-computer-interaction",
        "human-computer-interaction-research-claim-1",
        "How must interview notes separate evidence and interpretation",
        "human-computer-interaction-feedback-claim-2",
        "what information must an error message provide?",
    ),
)

PRIORITY_REVIEW_CASE_IDS = (
    "esv2-multi-01",
    "esv2-multi-08",
    "esv2-multimodal-01",
    "esv2-multimodal-08",
    "esv2-permission-01",
    "esv2-permission-06",
    "esv2-ambiguous-01",
    "esv2-ambiguous-04",
    "esv2-near-abstain-01",
    "esv2-near-abstain-03",
    "esv2-cross-01",
    "esv2-none-01",
)

HUMAN_CONFIRMATION_CASE_IDS = (
    "esv2-multi-01",
    "esv2-multimodal-01",
    "esv2-permission-01",
    "esv2-ambiguous-01",
)


def _claim_map(
    payload: dict[str, Any],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        claim["claim_id"]: (source, claim)
        for source in payload["sources"]
        for claim in source["claims"]
    }


def _replace_multi_evidence_cases(payload: dict[str, Any]) -> None:
    cases = {case["case_id"]: case for case in payload["cases"]}
    claims = _claim_map(payload)
    for (
        case_id,
        course_id,
        first_id,
        first_question,
        second_id,
        second_question,
    ) in MULTI_EVIDENCE_SPECS:
        case = cases[case_id]
        selected = [claims[first_id], claims[second_id]]
        if any(source["course_id"] != course_id for source, _ in selected):
            raise DecisionDraftError(f"{case_id} correction crosses course boundary")
        case["course_id"] = course_id
        case["question"] = (
            f"Answer both parts from distinct approved {course_id} sources: "
            f"{first_question}; and {second_question}"
        )
        case["required_claims"] = [
            {"claim_id": claim["claim_id"], "statement": claim["statement"]}
            for _, claim in selected
        ]
        case["evidence"] = [
            {
                "claim_id": claim["claim_id"],
                "source_unit_id": source["source_unit_id"],
                "quote": claim["evidence_quote"],
            }
            for source, claim in selected
        ]


def _add_stale_version_distractors(payload: dict[str, Any]) -> None:
    source_map = {source["source_unit_id"]: source for source in payload["sources"]}
    stale_by_logical = {
        source["logical_source_id"]: source
        for source in payload["sources"]
        if not source["active"]
    }
    for case in payload["cases"]:
        if case["slice"] != "permission-version":
            continue
        active = source_map[case["evidence"][0]["source_unit_id"]]
        stale = stale_by_logical[active["logical_source_id"]]
        case["tempting_source_ids"] = [stale["source_unit_id"]]


def _declare_representation_scope(payload: dict[str, Any]) -> None:
    payload["evidence_representation_scope"] = {
        "candidate_input": "retrieved-text-representation",
        "modality_tagged_source_count": sum(
            source["modality"] != "text" and source["active"]
            for source in payload["sources"]
        ),
        "raw_visual_assets_present": False,
        "raw_visual_quality_evaluated": False,
        "interpretation": (
            "The multimodal slice tests evidence sufficiency after deterministic "
            "text representation of non-text sources; raw visual ingestion and "
            "region-grounding quality remain owned by issue 86."
        ),
    }
    for source in payload["sources"]:
        source["evidence_representation"] = {
            "kind": (
                "source-text"
                if source["modality"] == "text"
                else "deterministic-text-surrogate"
            ),
            "origin_modality": source["modality"],
            "raw_asset_present": False,
        }
    for case in payload["cases"]:
        case["evidence_representation_scope"] = (
            "derived-text-from-modality-tagged-source"
            if case["slice"] == "multimodal"
            else "retrieved-source-text"
        )


def _validate_corrected(payload: dict[str, Any]) -> dict[str, Any]:
    base_compatible = copy.deepcopy(payload)
    base_compatible.pop("content_sha256", None)
    for case in base_compatible["cases"]:
        case["review_status"] = "pending-independent-review"
    validate_draft(base_compatible)

    if payload.get("dataset_id") != DATASET_ID:
        raise DecisionDraftError("corrected dataset ID drifted")
    if payload.get("predecessor") != {
        "dataset_id": BASE_DATASET_ID,
        "content_sha256": BASE_CONTENT_SHA256,
    }:
        raise DecisionDraftError("corrected predecessor binding drifted")
    source_map = {source["source_unit_id"]: source for source in payload["sources"]}
    for case in payload["cases"]:
        if case["slice"] == "multi-evidence":
            source_ids = {item["source_unit_id"] for item in case["evidence"]}
            if len(case["evidence"]) != 2 or len(source_ids) != 2:
                raise DecisionDraftError("multi-evidence case lacks distinct sources")
        if case["slice"] == "permission-version":
            active = source_map[case["evidence"][0]["source_unit_id"]]
            tempting = [source_map[item] for item in case["tempting_source_ids"]]
            if len(tempting) != 1 or tempting[0]["active"]:
                raise DecisionDraftError("permission case lacks one stale distractor")
            if tempting[0]["logical_source_id"] != active["logical_source_id"]:
                raise DecisionDraftError("permission stale distractor is unrelated")
        if case["slice"] == "multimodal":
            source = source_map[case["evidence"][0]["source_unit_id"]]
            if source["modality"] == "text":
                raise DecisionDraftError("multimodal case uses a text source")
            if case.get("evidence_representation_scope") != (
                "derived-text-from-modality-tagged-source"
            ):
                raise DecisionDraftError("multimodal proxy scope is missing")

    scope = payload.get("evidence_representation_scope", {})
    if scope.get("raw_visual_assets_present") is not False:
        raise DecisionDraftError("raw-visual presence must remain false")
    if scope.get("raw_visual_quality_evaluated") is not False:
        raise DecisionDraftError("raw-visual quality must remain out of scope")
    priority = payload.get("priority_review_case_ids", [])
    if tuple(priority) != PRIORITY_REVIEW_CASE_IDS:
        raise DecisionDraftError("corrected priority packet drifted")
    confirmations = payload.get("human_confirmation_case_ids", [])
    if tuple(confirmations) != HUMAN_CONFIRMATION_CASE_IDS:
        raise DecisionDraftError("human confirmation packet drifted")
    if not set(confirmations).issubset(priority):
        raise DecisionDraftError("human confirmations must be priority cases")
    expected_hash = _sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != expected_hash:
        raise DecisionDraftError("corrected content hash drifted")
    return {
        "dataset_id": DATASET_ID,
        "status": payload["status"],
        "case_count": len(payload["cases"]),
        "source_count": len(payload["sources"]),
        "multi_evidence_case_count": sum(
            case["slice"] == "multi-evidence" for case in payload["cases"]
        ),
        "permission_case_count": sum(
            case["slice"] == "permission-version" for case in payload["cases"]
        ),
        "multimodal_proxy_case_count": sum(
            case["slice"] == "multimodal" for case in payload["cases"]
        ),
        "human_confirmation_case_count": len(confirmations),
        "content_sha256": payload["content_sha256"],
        "provider_or_model_calls": payload["provider_or_model_calls"],
        "private_data_read": payload["private_data_read"],
        "opened_for_candidate_evaluation": payload["opened_for_candidate_evaluation"],
        "freeze_eligible": payload["review"]["freeze_eligible"],
    }


def build_corrected_draft() -> dict[str, Any]:
    base = build_draft()
    if (
        base["dataset_id"] != BASE_DATASET_ID
        or base["content_sha256"] != BASE_CONTENT_SHA256
    ):
        raise DecisionDraftError("historical draft binding drifted")
    payload = copy.deepcopy(base)
    payload.pop("content_sha256")
    payload["dataset_id"] = DATASET_ID
    payload["status"] = "corrected-draft-pending-human-confirmation"
    payload["predecessor"] = {
        "dataset_id": BASE_DATASET_ID,
        "content_sha256": BASE_CONTENT_SHA256,
    }
    payload["audit_id"] = AUDIT_ID
    payload["corrections"] = [
        "multi-evidence-cases-bind-two-distinct-active-source-units",
        "permission-version-cases-expose-the-paired-stale-source",
        "multimodal-cases-declare-derived-text-only-evaluation-scope",
        "priority-packet-covers-all-high-risk-boundaries",
    ]
    _replace_multi_evidence_cases(payload)
    _add_stale_version_distractors(payload)
    _declare_representation_scope(payload)
    payload["priority_review_case_ids"] = list(PRIORITY_REVIEW_CASE_IDS)
    payload["human_confirmation_case_ids"] = list(HUMAN_CONFIRMATION_CASE_IDS)
    for case in payload["cases"]:
        case["review_status"] = (
            "codex-reviewed-pending-human-confirmation"
            if case["case_id"] in HUMAN_CONFIRMATION_CASE_IDS
            else "codex-reviewed"
        )
    payload["review"] = {
        "structural_review": "passed",
        "codex_full_semantic_review": "passed-with-four-deterministic-corrections",
        "independent_advisory_review": "review-008-unreliable-no-dataset-conclusion",
        "human_priority_review": "pending-four-case-confirmation",
        "freeze_eligible": False,
    }
    corrected = {**payload, "content_sha256": _sha256(payload)}
    _validate_corrected(corrected)
    return corrected


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    expected = build_corrected_draft()
    if args.write:
        require_bounded_pilot_operation_allowed(AUDIT_ID)
        if args.output.exists():
            raise DecisionDraftError("corrected output path already exists")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(expected, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        result = _validate_corrected(expected)
        result["status"] = "corrected-draft-written"
    else:
        observed = json.loads(args.output.read_text(encoding="utf-8"))
        if observed != expected:
            raise DecisionDraftError("committed corrected draft is not byte-stable")
        result = _validate_corrected(observed)
        result["status"] = "corrected-draft-current"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
