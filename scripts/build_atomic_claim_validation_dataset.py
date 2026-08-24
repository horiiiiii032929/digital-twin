#!/usr/bin/env python3
"""Build fresh synthetic-public atomic-claim validation datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "evidence-sufficiency-v3-atomic-claim-confirmation-001"
DEFAULT_OUTPUT = (
    ROOT
    / "research/05_evaluation/datasets/"
    "evidence_sufficiency_v3_atomic_claim_confirmation_001.json"
)


FACTS = [
    (
        "security",
        "A password reset revokes every active session.",
        "Existing sessions stop working after a password reset.",
        "A reset token expires after fifteen minutes.",
        "Reset links remain valid for only fifteen minutes.",
        "A password reset deletes the user account.",
    ),
    (
        "databases",
        "A composite index stores keys in its declared column order.",
        "The order of columns is preserved in a composite index.",
        "A transaction rollback discards its uncommitted writes.",
        "Uncommitted changes are removed when a transaction rolls back.",
        "A rollback permanently deletes the database schema.",
    ),
    (
        "networks",
        "TCP establishes a connection before carrying application data.",
        "Application data is sent by TCP only after connection establishment.",
        "A router forwards packets between distinct networks.",
        "Routers move packets from one network to another.",
        "TCP encrypts every application payload by default.",
    ),
    (
        "algorithms",
        "Binary search requires a sorted search space.",
        "The input must be ordered before binary search is applicable.",
        "Merge sort has logarithmic recursion depth.",
        "The recursive call stack of merge sort grows logarithmically.",
        "Binary search works correctly on any unsorted sequence.",
    ),
    (
        "operating-systems",
        "A context switch saves the running task state.",
        "The current task state is preserved during a context switch.",
        "Virtual memory maps process addresses to physical storage.",
        "Process addresses are translated through virtual-memory mappings.",
        "A context switch permanently terminates the running task.",
    ),
    (
        "software-testing",
        "A unit test isolates one bounded behavior.",
        "Unit tests focus on a single bounded behavior.",
        "A regression test preserves previously accepted behavior.",
        "Previously accepted behavior is protected by regression tests.",
        "A unit test proves the entire deployed system is correct.",
    ),
    (
        "distributed-systems",
        "An idempotency key prevents duplicate processing of one request.",
        "Repeated delivery of the same request is deduplicated by its idempotency key.",
        "A lease permits bounded temporary ownership of work.",
        "Work ownership is temporary and bounded when controlled by a lease.",
        "An idempotency key guarantees that a network request is delivered.",
    ),
    (
        "machine-learning",
        "A validation split guides model selection without opening the test split.",
        "Model choices use validation data while the test data stays unopened.",
        "Data leakage makes evaluation results overly optimistic.",
        "Evaluation can look better than reality when data leakage occurs.",
        "The validation split is the final unbiased test set.",
    ),
    (
        "web-security",
        "SameSite cookies reduce some cross-site request forgery exposure.",
        "Some CSRF risk is reduced by applying the SameSite cookie attribute.",
        "Content Security Policy restricts permitted content sources.",
        "A Content Security Policy limits where page content may be loaded from.",
        "SameSite cookies encrypt all stored cookie values.",
    ),
    (
        "data-engineering",
        "A schema migration changes the durable data structure explicitly.",
        "Durable data structures are changed through explicit schema migrations.",
        "A checkpoint records resumable processing progress.",
        "Processing can resume from progress captured in a checkpoint.",
        "A checkpoint automatically repairs every malformed record.",
    ),
]


def _sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hit(
    identifier: str,
    text: str,
    *,
    course_id: str,
    version: int = 2,
    retrieval_allowed: bool = True,
) -> dict[str, Any]:
    return {
        "hit_id": identifier,
        "text": text,
        "course_id": course_id,
        "source_id": identifier.rsplit("-v", 1)[0],
        "source_version": version,
        "retrieval_allowed": retrieval_allowed,
    }


def _claim(identifier: str, text: str, *hit_ids: str) -> dict[str, Any]:
    return {
        "claim_id": identifier,
        "text": text,
        "evidence_hit_ids": list(hit_ids),
    }


def _case(
    case_id: str,
    slice_name: str,
    expected_releasable: bool,
    hits: list[dict[str, Any]],
    claims: list[dict[str, Any]],
    *,
    mutation_class: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "slice": slice_name,
        "expected_releasable": expected_releasable,
        "mutation_class": mutation_class,
        "hits": hits,
        "claims": claims,
    }


def build_dataset() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for index, (topic, fact_a, para_a, fact_b, para_b, false_claim) in enumerate(
        FACTS,
        start=1,
    ):
        course_id = f"course-{(index - 1) % 4 + 1}"
        other_course = f"course-{index % 4 + 1}"
        prefix = f"acv-{index:02d}"
        hit_a = _hit(f"{prefix}-a-v2", fact_a, course_id=course_id)
        hit_b = _hit(f"{prefix}-b-v2", fact_b, course_id=course_id)
        noise = _hit(
            f"{prefix}-noise-v2",
            "The course calendar lists a review session on Friday.",
            course_id=course_id,
        )
        stale = _hit(
            f"{prefix}-a-v1",
            false_claim,
            course_id=course_id,
            version=1,
            retrieval_allowed=False,
        )
        cross_course = _hit(
            f"{prefix}-cross-v2",
            fact_a,
            course_id=other_course,
            retrieval_allowed=False,
        )
        cases.extend(
            [
                _case(
                    f"{prefix}-exact-single",
                    "supported-exact-single",
                    True,
                    [hit_a, noise],
                    [_claim(f"claim-{prefix}-a", fact_a, hit_a["hit_id"])],
                ),
                _case(
                    f"{prefix}-paraphrase-single",
                    "supported-paraphrase-single",
                    True,
                    [hit_a, noise],
                    [_claim(f"claim-{prefix}-a", para_a, hit_a["hit_id"])],
                ),
                _case(
                    f"{prefix}-exact-multi",
                    "supported-exact-multi",
                    True,
                    [hit_a, hit_b, noise],
                    [
                        _claim(f"claim-{prefix}-a", fact_a, hit_a["hit_id"]),
                        _claim(f"claim-{prefix}-b", fact_b, hit_b["hit_id"]),
                    ],
                ),
                _case(
                    f"{prefix}-paraphrase-multi",
                    "supported-paraphrase-multi",
                    True,
                    [hit_a, hit_b, noise],
                    [
                        _claim(f"claim-{prefix}-a", para_a, hit_a["hit_id"]),
                        _claim(f"claim-{prefix}-b", para_b, hit_b["hit_id"]),
                    ],
                ),
                _case(
                    f"{prefix}-contradiction",
                    "unsupported-contradiction",
                    False,
                    [hit_a, noise],
                    [_claim(f"claim-{prefix}-false", false_claim, hit_a["hit_id"])],
                    mutation_class="contradiction",
                ),
                _case(
                    f"{prefix}-unsupported-addition",
                    "unsupported-addition",
                    False,
                    [hit_a, noise],
                    [
                        _claim(f"claim-{prefix}-a", fact_a, hit_a["hit_id"]),
                        _claim(
                            f"claim-{prefix}-false",
                            false_claim,
                            hit_a["hit_id"],
                        ),
                    ],
                    mutation_class="unsupported-addition",
                ),
                _case(
                    f"{prefix}-wrong-lineage",
                    "wrong-lineage",
                    False,
                    [hit_a, hit_b],
                    [_claim(f"claim-{prefix}-a", fact_a, hit_b["hit_id"])],
                    mutation_class="wrong-lineage",
                ),
                _case(
                    f"{prefix}-stale-source",
                    "stale-source",
                    False,
                    [hit_a, stale],
                    [_claim(f"claim-{prefix}-false", false_claim, stale["hit_id"])],
                    mutation_class="stale-source",
                ),
                _case(
                    f"{prefix}-cross-course",
                    "cross-course",
                    False,
                    [hit_a, cross_course],
                    [_claim(f"claim-{prefix}-a", fact_a, cross_course["hit_id"])],
                    mutation_class="cross-course",
                ),
                _case(
                    f"{prefix}-partial-multi",
                    "partial-multi-claim",
                    False,
                    [hit_a, hit_b],
                    [
                        _claim(f"claim-{prefix}-a", fact_a, hit_a["hit_id"]),
                        _claim(
                            f"claim-{prefix}-false",
                            false_claim,
                            hit_b["hit_id"],
                        ),
                    ],
                    mutation_class="partial-multi-claim",
                ),
                _case(
                    f"{prefix}-missing-citation",
                    "missing-citation",
                    False,
                    [hit_a],
                    [
                        {
                            "claim_id": f"claim-{prefix}-a",
                            "text": fact_a,
                            "evidence_hit_ids": [],
                        }
                    ],
                    mutation_class="missing-citation",
                ),
                _case(
                    f"{prefix}-duplicate-claim-id",
                    "malformed-claim-contract",
                    False,
                    [hit_a],
                    [
                        _claim(f"claim-{prefix}-a", fact_a, hit_a["hit_id"]),
                        _claim(f"claim-{prefix}-a", fact_a, hit_a["hit_id"]),
                    ],
                    mutation_class="duplicate-claim-id",
                ),
            ]
        )
    if len(cases) != 120:
        raise RuntimeError("atomic-claim dataset must contain exactly 120 cases")
    slices: dict[str, int] = {}
    for case in cases:
        slices[case["slice"]] = slices.get(case["slice"], 0) + 1
    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": "evidence-sufficiency-v3-atomic-claim-confirmation-001",
        "status": "frozen-unopened",
        "data_boundary": "synthetic-public-only",
        "case_count": len(cases),
        "releasable_case_count": sum(case["expected_releasable"] for case in cases),
        "reject_case_count": sum(not case["expected_releasable"] for case in cases),
        "slices": slices,
        "cases": cases,
    }
    payload["content_sha256"] = _sha256(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    payload = build_dataset()
    encoded = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if args.check or not args.write:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != encoded:
            raise SystemExit("atomic-claim dataset is missing or drifted")
        print(json.dumps({"status": "passed", "case_count": 120, "path": str(args.output)}))
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8")
    print(json.dumps({"status": "built", "case_count": 120, "path": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
