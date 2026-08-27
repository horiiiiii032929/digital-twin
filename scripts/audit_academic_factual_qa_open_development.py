#!/usr/bin/env python3
"""Audit the deterministic open-QA development package before product spend.

The existing builder proves identity, separation, and exact source lineage. This
audit adds a distinct fitness-for-use check: canonical answers must be usable as
reference answers, and structured slices must point to evidence of the claimed
modality. The quality flags are deliberately conservative diagnostics; they do
not mutate the immutable package or replace semantic review.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_10000 import SOURCE_PLAN_PATH  # noqa: E402
from scripts.construct_academic_factual_qa_open_10000 import (  # noqa: E402
    DEVELOPMENT_CASES_PATH,
    DEVELOPMENT_GOLD_PATH,
)
from src.digital_twin.evaluation.factual_qa_dataset import (  # noqa: E402
    normalize_question,
)


AUDIT_ID = "academic-factual-qa-open-10000-development-pre-spend-audit-001"
TEXT_SLICES = {
    "direct-factual",
    "paraphrased",
    "definition-explanation",
    "multi-evidence",
}
GOLD_ONLY_FIELDS = {
    "expected_action",
    "canonical_answer",
    "claims",
    "citations",
    "boundary_reason",
    "required_source_ids",
    "required_evidence",
}
PRIORITY_REVIEW_CASE_IDS = (
    "academic-open-dev-0001-q1",
    "academic-open-dev-0034-q1",
    "academic-open-dev-0100-q1",
    "academic-open-dev-0019-q4",
    "academic-open-dev-0038-q4",
    "academic-open-dev-0068-q4",
    "academic-open-dev-0092-q4",
    "academic-open-dev-0098-q4",
    "academic-open-dev-0001-q5",
    "academic-open-dev-0002-q5",
    "academic-open-dev-0003-q5",
    "academic-open-dev-0004-q5",
)

_LEADING_MARKUP = re.compile(r"^[`#%\\{}\[\]$*\s]+")
_MARKUP_ARTIFACT = re.compile(
    r"(?:```|%%expect|%xmode|student@|\\(?:seclabel|figref|codeimport)|"
    r"#\w+#|\$#)"
)
_CODE_SIGNAL = re.compile(
    r"(?:```|`[^`]+`|\b(?:def|for|while|print|import|return|class|console)\b|"
    r"student@|\./|\w+\([^)]*\)|[+*/-]\s*\d)"
)
_EQUATION_SIGNAL = re.compile(
    r"(?:=|\\(?:frac|sum|sqrt|lfloor|lceil)|≤|≥|<|>|\^)"
)
_TABLE_SIGNAL = re.compile(r"(?:\\begin\{tabular\}|\|.+\||\s&\s|\\\\)")


class DevelopmentPackageAuditError(RuntimeError):
    """Raised when the package cannot be audited deterministically."""


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _quality_flags(case: dict[str, Any], gold: dict[str, Any]) -> list[str]:
    if gold["expected_action"] != "answer":
        return []
    answer = gold["canonical_answer"].strip()
    slice_name = case["slice"]
    flags: list[str] = []
    plain_start = _LEADING_MARKUP.sub("", answer)
    if (
        slice_name in TEXT_SLICES
        and plain_start
        and not (plain_start[0].isupper() or plain_start[0].isdigit())
    ):
        flags.append("possible-fragment-start")
    if slice_name in TEXT_SLICES and answer[-1:] not in ".?!`$}]":
        flags.append("possible-fragment-end")
    if _MARKUP_ARTIFACT.search(answer):
        flags.append("raw-markup-or-runtime-artifact")
    if slice_name == "structured-code" and not _CODE_SIGNAL.search(answer):
        flags.append("structured-code-signal-missing")
    if slice_name == "structured-equation" and not _EQUATION_SIGNAL.search(answer):
        flags.append("structured-equation-signal-missing")
    if slice_name == "structured-table" and not _TABLE_SIGNAL.search(answer):
        flags.append("structured-table-signal-missing")
    return flags


def audit_development_package() -> dict[str, Any]:
    cases_package = _load(DEVELOPMENT_CASES_PATH)
    gold_package = _load(DEVELOPMENT_GOLD_PATH)
    source_package = _load(SOURCE_PLAN_PATH)
    cases = cases_package.get("cases", [])
    gold_rows = gold_package.get("gold", [])
    gold_by_id = {row["case_id"]: row for row in gold_rows}
    source_by_cluster = {
        row["cluster_id"]: row
        for row in source_package.get("clusters", [])
        if row.get("split") == "development"
    }
    if len(cases) != 500 or len(gold_rows) != 500:
        raise DevelopmentPackageAuditError("development package is not 500 by 500")
    if len(gold_by_id) != len(gold_rows):
        raise DevelopmentPackageAuditError("hidden-gold case IDs are duplicated")
    if {row["case_id"] for row in cases} != set(gold_by_id):
        raise DevelopmentPackageAuditError("public and hidden-gold IDs differ")

    public_gold_field_count = sum(
        len(GOLD_ONLY_FIELDS.intersection(row)) for row in cases
    )
    normalized = [normalize_question(row["question"]) for row in cases]
    normalized_duplicate_count = len(normalized) - len(set(normalized))
    canonical_answer_leak_count = 0
    lineage_defects: list[str] = []
    quality_by_case: dict[str, list[str]] = {}

    for case in cases:
        case_id = case["case_id"]
        gold = gold_by_id[case_id]
        cluster = source_by_cluster.get(case["cluster_id"])
        if cluster is None:
            lineage_defects.append(f"{case_id}:source-cluster-missing")
            continue
        normalized_answer = normalize_question(gold["canonical_answer"])
        if (
            gold["expected_action"] == "answer"
            and normalized_answer
            and normalized_answer in normalize_question(case["question"])
        ):
            canonical_answer_leak_count += 1
        if gold["expected_action"] == "answer":
            claim_text: list[str] = []
            if not gold["claims"]:
                lineage_defects.append(f"{case_id}:answer-claims-empty")
            for claim in gold["claims"]:
                claim_text.append(claim["answer_span"])
                if not claim["evidence_refs"]:
                    lineage_defects.append(
                        f"{case_id}:{claim['claim_id']}:evidence-empty"
                    )
                for ref in claim["evidence_refs"]:
                    if (
                        ref["source_artifact_id"] != cluster["source_artifact_id"]
                        or ref["source_version"] != cluster["source_version"]
                        or ref["source_sha256"] != cluster["source_sha256"]
                    ):
                        lineage_defects.append(
                            f"{case_id}:{claim['claim_id']}:source-identity-drift"
                        )
                        continue
                    relative_start = ref["char_start"] - cluster["char_start"]
                    relative_end = ref["char_end"] - cluster["char_start"]
                    if relative_start < 0 or relative_end > len(cluster["text"]):
                        lineage_defects.append(
                            f"{case_id}:{claim['claim_id']}:source-range-outside-cluster"
                        )
                    elif (
                        cluster["text"][relative_start:relative_end]
                        != claim["answer_span"]
                    ):
                        lineage_defects.append(
                            f"{case_id}:{claim['claim_id']}:source-quote-mismatch"
                        )
            if " ".join(claim_text) != gold["canonical_answer"]:
                lineage_defects.append(f"{case_id}:canonical-answer-claim-drift")
        elif gold["claims"]:
            lineage_defects.append(f"{case_id}:boundary-has-claims")

        flags = _quality_flags(case, gold)
        if flags:
            quality_by_case[case_id] = flags

    quality_counter = Counter(
        flag for flags in quality_by_case.values() for flag in flags
    )
    flagged_cases = [row for row in cases if row["case_id"] in quality_by_case]
    case_by_id = {row["case_id"]: row for row in cases}
    priority_rows = [
        {
            "case_id": case_id,
            "course_id": case_by_id[case_id]["course_id"],
            "slice": case_by_id[case_id]["slice"],
            "quality_flags": quality_by_case.get(case_id, []),
        }
        for case_id in PRIORITY_REVIEW_CASE_IDS
    ]
    structural_passed = not (
        public_gold_field_count
        or normalized_duplicate_count
        or canonical_answer_leak_count
        or lineage_defects
    )
    return {
        "schema_version": 1,
        "audit_id": AUDIT_ID,
        "status": "completed-refine" if quality_by_case else "completed-keep",
        "dataset_id": cases_package["dataset_id"],
        "case_count": len(cases),
        "answerable_case_count": sum(
            row["expected_action"] == "answer" for row in gold_rows
        ),
        "boundary_case_count": sum(
            row["expected_action"] != "answer" for row in gold_rows
        ),
        "structural_gate_passed": structural_passed,
        "public_gold_field_count": public_gold_field_count,
        "normalized_duplicate_count": normalized_duplicate_count,
        "canonical_answer_leak_count": canonical_answer_leak_count,
        "lineage_defect_count": len(lineage_defects),
        "lineage_defects": lineage_defects,
        "canonical_template_case_count": len(cases),
        "high_risk_answerable_case_count": len(flagged_cases),
        "high_risk_answerable_case_rate": len(flagged_cases) / 400,
        "high_risk_cluster_count": len(
            {row["cluster_id"] for row in flagged_cases}
        ),
        "quality_flags": dict(sorted(quality_counter.items())),
        "quality_flags_by_slice": dict(
            sorted(Counter(row["slice"] for row in flagged_cases).items())
        ),
        "quality_flags_by_course": dict(
            sorted(Counter(row["course_id"] for row in flagged_cases).items())
        ),
        "priority_review": priority_rows,
        "provider_calls": 0,
        "private_data_used": False,
        "final_split_opened": False,
        "interpretation": (
            "The package remains valid deterministic truth scaffolding, but it is "
            "not fit for product evaluation until reference-answer extraction, "
            "structured-modality targeting, and question wording are corrected."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.parse_args()
    print(json.dumps(audit_development_package(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
