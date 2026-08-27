#!/usr/bin/env python3
"""Audit the complete-region development package before product execution."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import re
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_academic_factual_qa_open_development_v3 import (  # noqa: E402
    build_packages,
)
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationAction,
)
from src.digital_twin.evaluation.factual_qa_references import (  # noqa: E402
    SourceClusterV2,
    extract_structured_regions,
)


AUDIT_ID = "academic-factual-qa-open-10000-development-pre-spend-audit-002"
GOLD_ONLY_FIELDS = {
    "expected_action",
    "canonical_answer",
    "claims",
    "citations",
    "boundary_reason",
    "required_source_ids",
    "required_evidence",
}
_HARD_ARTIFACT = re.compile(
    r"```|%%expect|%xmode|student@|\\(?:codeimport|javaimport|cppimport|"
    r"includegraphics|figref)|#\w+#\s+#\w+#|\$#"
)


class CorrectedDevelopmentAuditError(RuntimeError):
    """Raised when the corrected package cannot be audited."""


def audit_corrected_package() -> dict[str, Any]:
    built = build_packages()
    cases_package = built["packages"]["cases"]
    gold_package = built["packages"]["gold"]
    cases = cases_package["cases"]
    gold_rows = gold_package["gold"]
    gold_by_id = {row["case_id"]: row for row in gold_rows}
    clusters = {
        row.cluster_id: row
        for row in (
            SourceClusterV2.model_validate(value)
            for value in built["source_plan"]["clusters"]
        )
    }
    if len(cases) != 500 or len(gold_rows) != 500 or len(clusters) != 100:
        raise CorrectedDevelopmentAuditError("corrected audit cardinality drifted")

    defects: list[str] = []
    public_gold_field_count = sum(
        len(GOLD_ONLY_FIELDS.intersection(row)) for row in cases
    )
    if public_gold_field_count:
        defects.append("public-package-exposes-gold")

    text_target_count = 0
    structured_target_count = 0
    complete_text_target_count = 0
    complete_structured_target_count = 0
    original_region_lineage_count = 0
    modality_counts: Counter[str] = Counter()

    for case in cases:
        case_id = case["case_id"]
        gold = gold_by_id.get(case_id)
        cluster = clusters.get(case["cluster_id"])
        if gold is None or cluster is None:
            defects.append(f"{case_id}:identity-missing")
            continue
        question_index = int(case_id.rsplit("-q", 1)[1])
        if question_index == 5:
            if gold["expected_action"] == EvaluationAction.ANSWER or gold["claims"]:
                defects.append(f"{case_id}:boundary-lineage-invalid")
            continue
        target = cluster.reference_targets[question_index - 1]
        if target.slice != case["slice"]:
            defects.append(f"{case_id}:target-slice-drift")
        if gold["expected_action"] != EvaluationAction.ANSWER:
            defects.append(f"{case_id}:answerable-action-drift")
            continue
        if gold["canonical_answer"] != " ".join(target.canonical_claims):
            defects.append(f"{case_id}:canonical-claim-drift")
        if len(gold["claims"]) != len(target.evidence_spans):
            defects.append(f"{case_id}:claim-evidence-count-drift")
            continue

        modality_counts[target.modality] += 1
        if target.modality == "text":
            text_target_count += 1
            target_complete = True
            for claim, span, expected_claim in zip(
                gold["claims"],
                target.evidence_spans,
                target.canonical_claims,
                strict=True,
            ):
                if claim["answer_span"] != expected_claim:
                    target_complete = False
                if expected_claim[-1:] not in ".?!":
                    target_complete = False
                if not 4 <= len(re.findall(r"[A-Za-z0-9]+", expected_claim)) <= 30:
                    target_complete = False
                if _HARD_ARTIFACT.search(span.quote):
                    target_complete = False
                ref = claim["evidence_refs"][0]
                start = ref["char_start"] - cluster.char_start
                end = ref["char_end"] - cluster.char_start
                if cluster.text[start:end] != span.quote or ref["region_id"] is not None:
                    target_complete = False
            if target_complete:
                complete_text_target_count += 1
            else:
                defects.append(f"{case_id}:text-reference-incomplete")
            continue

        structured_target_count += 1
        structured_regions = {
            (row.start, row.end, row.modality): row
            for row in extract_structured_regions(cluster.text)
        }
        target_complete = True
        for claim, span, expected_claim in zip(
            gold["claims"],
            target.evidence_spans,
            target.canonical_claims,
            strict=True,
        ):
            if claim["answer_span"] != expected_claim:
                target_complete = False
            ref = claim["evidence_refs"][0]
            start = ref["char_start"] - cluster.char_start
            end = ref["char_end"] - cluster.char_start
            if cluster.text[start:end] != span.quote or not ref["region_id"]:
                target_complete = False
            else:
                original_region_lineage_count += 1
            if case["slice"].startswith("structured-") and (
                start,
                end,
                target.modality,
            ) not in structured_regions:
                target_complete = False
            if case["slice"] == "structured-code" and not re.search(
                r"(?:\$ |\w+\([^)]*\)|[=;{}]|\./|"
                r"\b(?:def|return|import|for|while|GET|POST|curl|cat|python)\b)",
                expected_claim,
            ):
                target_complete = False
            if case["slice"] == "structured-equation" and not re.search(
                r"(?:=|<|>|\\(?:frac|sum|sqrt)|\^|_)", expected_claim
            ):
                target_complete = False
            if case["slice"] == "structured-table" and not re.search(
                r"(?:&|\||:|\d)", expected_claim
            ):
                target_complete = False
        if target_complete:
            complete_structured_target_count += 1
        else:
            defects.append(f"{case_id}:structured-reference-incomplete")

    answerable_count = sum(
        row["expected_action"] == EvaluationAction.ANSWER for row in gold_rows
    )
    boundary_count = len(gold_rows) - answerable_count
    if answerable_count != 400 or boundary_count != 100:
        defects.append("action-distribution-drift")
    if built["normalized_duplicate_count"]:
        defects.append("normalized-duplicates")
    if built["canonical_answer_leak_count"]:
        defects.append("canonical-answer-leak")

    priority_ids = [
        "academic-open-dev2-0001-q1",
        "academic-open-dev2-0013-q4",
        "academic-open-dev2-0025-q5",
        "academic-open-dev2-0026-q1",
        "academic-open-dev2-0044-q4",
        "academic-open-dev2-0050-q5",
        "academic-open-dev2-0051-q1",
        "academic-open-dev2-0069-q4",
        "academic-open-dev2-0075-q5",
        "academic-open-dev2-0076-q1",
        "academic-open-dev2-0098-q4",
        "academic-open-dev2-0100-q5",
    ]
    case_by_id = {row["case_id"]: row for row in cases}
    priority_packet = [
        {
            "case_id": case_id,
            "course_id": case_by_id[case_id]["course_id"],
            "slice": case_by_id[case_id]["slice"],
            "question": case_by_id[case_id]["question"],
            "canonical_answer": gold_by_id[case_id]["canonical_answer"],
        }
        for case_id in priority_ids
    ]
    return {
        "schema_version": 1,
        "audit_id": AUDIT_ID,
        "status": "completed-keep" if not defects else "completed-refine",
        "instrument_id": built["instrument_id"],
        "source_plan_sha256": built["source_plan_sha256"],
        "case_count": len(cases),
        "answerable_case_count": answerable_count,
        "boundary_case_count": boundary_count,
        "public_gold_field_count": public_gold_field_count,
        "normalized_duplicate_count": built["normalized_duplicate_count"],
        "canonical_answer_leak_count": built["canonical_answer_leak_count"],
        "text_target_count": text_target_count,
        "complete_text_target_count": complete_text_target_count,
        "structured_target_count": structured_target_count,
        "complete_structured_target_count": complete_structured_target_count,
        "original_region_lineage_count": original_region_lineage_count,
        "target_modality_distribution": dict(sorted(modality_counts.items())),
        "defect_count": len(defects),
        "defects": defects,
        "priority_packet": priority_packet,
        "provider_calls": 0,
        "private_data_used": False,
        "final_split_opened": False,
        "interpretation": (
            "The prospective package is structurally and reference-fit for the "
            "next wording and product-development checkpoint. This no-call audit "
            "does not evaluate product answer quality or naturalness."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.parse_args()
    print(json.dumps(audit_corrected_package(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
