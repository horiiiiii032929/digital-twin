#!/usr/bin/env python3
"""Reproduce the non-sealed grounding-floor measurements from source inputs.

The historical audit notes were produced ad hoc. This command rebuilds their
shared measurements from the committed 500-case development package, the
registered region corpus, and the immutable selection-003 response ledgers.
It never reads the sealed 10,000-case package and makes no provider calls.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import academic_factual_qa_open_10000_winner_adapter as winner  # noqa: E402
from scripts import run_product_evidence_gate_selection_004 as selection  # noqa: E402
from scripts.score_academic_factual_qa_open_10000 import score_packages  # noqa: E402
from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
)
from src.digital_twin.grounding.hierarchical_retrieval import (  # noqa: E402
    concept_tokens,
)
from src.digital_twin.grounding.models import DocumentChunk  # noqa: E402
from src.digital_twin.grounding.reference_uniqueness import (  # noqa: E402
    _claim,
    _coverage,
    _scope,
    normalize_claim_class,
    prefer_specific_source_regions,
)
from src.digital_twin.grounding.semantic_evidence_atoms import (  # noqa: E402
    SourceSemanticEvidenceAtomRetrieverV1,
)
from src.digital_twin.grounding.source_range_evidence import (  # noqa: E402
    plan_public_source_ranges,
)


RUN_ID = "grounding-floor-audit-reproduction-001"
OUTPUT_PATH = ROOT / "reports/generated" / RUN_ID / "result.json"
HISTORICAL_RECORDS = {
    audit_id: ROOT / "research/05_evaluation/records" / f"{audit_id}.json"
    for audit_id in (
        "tie-resolution-hypothesis-audit-001",
        "wrong-region-selection-audit-001",
        "coverage-measure-hypothesis-audit-001",
        "tie-set-citation-hypothesis-audit-001",
    )
}


class GroundingFloorAuditError(RuntimeError):
    """Raised when the development evidence cannot be reproduced safely."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_state() -> tuple[str, bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return revision, bool(status.strip())


def _load_inputs() -> tuple[
    list[EvaluationCaseV1],
    dict[str, EvaluationGoldV1],
    dict[str, list[DocumentChunk]],
]:
    cases_payload = json.loads(selection.CASES_PATH.read_text(encoding="utf-8"))
    gold_payload = json.loads(selection.GOLD_PATH.read_text(encoding="utf-8"))
    cases = [EvaluationCaseV1.model_validate(row) for row in cases_payload["cases"]]
    gold = {
        row.case_id: row
        for row in (
            EvaluationGoldV1.model_validate(value) for value in gold_payload["gold"]
        )
    }
    if {row.case_id for row in cases} != set(gold):
        raise GroundingFloorAuditError("development case/gold identity set drifted")
    chunks_by_course, _ = winner.load_corpus_with_atom_lineage(selection.CORPUS_PATH)
    return cases, gold, chunks_by_course


def _read_responses(path: Path) -> dict[str, EvaluationResponseV1]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT case_id, payload_json, payload_sha256 FROM responses"
        ).fetchall()
    finally:
        connection.close()
    output: dict[str, EvaluationResponseV1] = {}
    for case_id, payload_json, payload_sha256 in rows:
        if hashlib.sha256(payload_json.encode("utf-8")).hexdigest() != payload_sha256:
            raise GroundingFloorAuditError(f"response hash drifted: {case_id}")
        response = EvaluationResponseV1.model_validate_json(payload_json)
        if response.case_id != case_id or case_id in output:
            raise GroundingFloorAuditError(f"response identity drifted: {case_id}")
        output[case_id] = response
    return output


def _chunk_key(chunk: DocumentChunk) -> tuple[str, int, str, int, int]:
    return (
        chunk.source_artifact_id or chunk.document_id,
        chunk.source_version,
        chunk.source_checksum,
        int(chunk.metadata["char_start"]),
        int(chunk.metadata["char_end"]),
    )


def _gold_keys(gold: EvaluationGoldV1) -> set[tuple[str, int, str, int, int]]:
    return {
        (
            ref.source_artifact_id,
            ref.source_version,
            ref.source_sha256,
            ref.char_start,
            ref.char_end,
        )
        for claim in gold.claims
        for ref in claim.evidence_refs
    }


def _provenance_text(chunk: DocumentChunk) -> str:
    return " ".join(
        (
            str(chunk.metadata.get("title", "")),
            chunk.locator,
            str(chunk.metadata.get("source_path", "")),
            str(chunk.metadata.get("course_id", "")),
            chunk.document_id,
            chunk.source_artifact_id or "",
        )
    )


def _locator_credited_coverage(target: str, chunk: DocumentChunk) -> float:
    required = concept_tokens(target)
    if not required:
        return 0.0
    observed = concept_tokens(_claim(chunk)) | concept_tokens(_provenance_text(chunk))
    return len(required & observed) / len(required)


def _narrowed_coverage(
    target: str,
    chunk: DocumentChunk,
    scoped: Sequence[DocumentChunk],
) -> float:
    required = concept_tokens(target)
    if not required:
        return 0.0
    shared = set.intersection(
        *(concept_tokens(_provenance_text(row)) for row in scoped)
    ) if scoped else set()
    discriminating = required - shared
    if not discriminating:
        return 0.0
    return len(discriminating & concept_tokens(_claim(chunk))) / len(discriminating)


def _leaders(
    target: str,
    scoped: Sequence[DocumentChunk],
    coverage: Callable[[str, DocumentChunk], float],
) -> list[DocumentChunk]:
    matching = [row for row in scoped if target and coverage(target, row) >= 0.5]
    if not matching:
        return []
    values = {row.id: round(coverage(target, row), 9) for row in matching}
    maximum = max(values.values())
    return [row for row in matching if values[row.id] == maximum]


def _summarize_measure(rows: list[dict[str, Any]], label: str) -> dict[str, int]:
    selected = [row for row in rows if row["measure"] == label]
    return {
        "targets": len(selected),
        "single_leader": sum(len(row["leaders"]) == 1 for row in selected),
        "single_leader_is_gold": sum(
            len(row["leaders"]) == 1 and row["leader_has_gold"] for row in selected
        ),
        "single_leader_is_wrong": sum(
            len(row["leaders"]) == 1
            and row["answerable"]
            and not row["leader_has_gold"]
            for row in selected
        ),
        "single_leader_on_boundary_case": sum(
            len(row["leaders"]) == 1 and not row["answerable"] for row in selected
        ),
        "tied": sum(len(row["leaders"]) > 1 for row in selected),
        "gold_inside_tie": sum(
            len(row["leaders"]) > 1 and row["leader_has_gold"] for row in selected
        ),
        "unresolved": sum(not row["leaders"] for row in selected),
    }


def _measure_reference_surface(
    cases: list[EvaluationCaseV1],
    gold: dict[str, EvaluationGoldV1],
    chunks_by_course: dict[str, list[DocumentChunk]],
) -> dict[str, Any]:
    retrievers = {
        course_id: SourceSemanticEvidenceAtomRetrieverV1(chunks, candidate_limit=30)
        for course_id, chunks in chunks_by_course.items()
    }
    target_rows: list[dict[str, Any]] = []
    ties_by_case: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        hits = retrievers[case.course_id].retrieve(case.question, limit=5)
        scoped, _, _ = _scope(
            case.question,
            prefer_specific_source_regions([hit.chunk for hit in hits]),
        )
        keys = _gold_keys(gold[case.case_id])
        targets = plan_public_source_ranges(case.question).evidence.targets
        measures: dict[str, Callable[[str, DocumentChunk], float]] = {
            "A_shipped": lambda target, chunk: _coverage(target, _claim(chunk)),
            "B_locator_credited": _locator_credited_coverage,
            "C_requirement_narrowed": lambda target, chunk: _narrowed_coverage(
                target, chunk, scoped
            ),
        }
        for target_index, target in enumerate(targets):
            for measure, coverage in measures.items():
                leaders = _leaders(target, scoped, coverage)
                row = {
                    "case_id": case.case_id,
                    "target_index": target_index,
                    "target": target,
                    "measure": measure,
                    "answerable": bool(keys),
                    "leaders": leaders,
                    "leader_has_gold": any(_chunk_key(value) in keys for value in leaders),
                }
                target_rows.append(row)
                if measure == "A_shipped" and len(leaders) > 1:
                    ties_by_case.setdefault(case.case_id, []).append(row)

    shipped = [row for row in target_rows if row["measure"] == "A_shipped"]
    ambiguous = [
        row
        for row in shipped
        if len(row["leaders"]) > 1
        and len({normalize_claim_class(_claim(value)) for value in row["leaders"]}) > 1
    ]
    gold_ties = [row for row in ambiguous if row["leader_has_gold"]]
    shortest = Counter()
    for row in gold_ties:
        lengths = {
            value.id: len(concept_tokens(_claim(value))) for value in row["leaders"]
        }
        minimum = min(lengths.values())
        selected = [value for value in row["leaders"] if lengths[value.id] == minimum]
        if len(selected) != 1:
            shortest["still_tied"] += 1
        elif _chunk_key(selected[0]) in _gold_keys(gold[row["case_id"]]):
            shortest["isolates_gold"] += 1
        else:
            shortest["picks_wrong_region"] += 1

    all_ties = [row for row in shipped if len(row["leaders"]) > 1]
    answerable_tie_cases = {
        case_id: rows
        for case_id, rows in ties_by_case.items()
        if gold[case_id].claims
    }
    boundary_tie_cases = {
        case_id: rows
        for case_id, rows in ties_by_case.items()
        if not gold[case_id].claims
    }
    tie_sizes = [len(row["leaders"]) for row in all_ties]
    all_ties_cover_gold = sum(
        all(row["leader_has_gold"] for row in rows)
        for rows in answerable_tie_cases.values()
    )
    return {
        "coverage_measures": {
            label: _summarize_measure(target_rows, label)
            for label in (
                "A_shipped",
                "B_locator_credited",
                "C_requirement_narrowed",
            )
        },
        "tie_resolution": {
            "ambiguous_tied_targets": len(ambiguous),
            "gold_inside_ambiguous_tied_leader_set": len(gold_ties),
            "shortest_claim_tiebreak": dict(shortest),
        },
        "tie_set_citation": {
            "cases_with_a_tie": len(ties_by_case),
            "answerable_cases_with_a_tie": len(answerable_tie_cases),
            "answerable_cases_where_every_tie_covers_gold": all_ties_cover_gold,
            "boundary_cases_with_a_tie": len(boundary_tie_cases),
            "tied_leader_sets": len(all_ties),
            "tie_size_mean": sum(tie_sizes) / len(tie_sizes),
            "tie_size_max": max(tie_sizes),
            "ties_whose_leaders_all_agree": sum(
                len({normalize_claim_class(_claim(value)) for value in row["leaders"]})
                == 1
                for row in all_ties
            ),
            "ties_whose_leaders_disagree": sum(
                len({normalize_claim_class(_claim(value)) for value in row["leaders"]})
                > 1
                for row in all_ties
            ),
        },
    }


def _score_arm(arm_id: str, output_root: Path) -> dict[str, Any]:
    pairing = selection._pairing_manifest(output_root / arm_id / "pairing-manifest.json")
    result = score_packages(
        cases_path=selection.CASES_PATH,
        gold_path=selection.GOLD_PATH,
        responses_path=output_root / arm_id / "responses.sqlite3",
        pairing_path=pairing,
    )
    summary = result["summary"]
    return {
        "fully_grounded_factual_success": summary["metrics"][
            "fully_grounded_factual_success"
        ],
        "overall_grounded_task_success": summary["overall_grounded_task_success"],
        "boundary_action_accuracy": summary["metrics"]["boundary_action_accuracy"],
        "severe_unsupported_release_count": summary[
            "severe_unsupported_release_count"
        ],
        "operational_failure_count": summary["operational_failure_count"],
        "failed_gate_count": len(result["failed_gates"]),
    }


def build_result() -> dict[str, Any]:
    code_revision, working_tree_dirty = _git_state()
    cases, gold, chunks_by_course = _load_inputs()
    ledgers: dict[str, dict[str, Any]] = {}
    for arm_id in selection.ARMS:
        manifest = selection._manifest(arm_id)
        path = selection.OUTPUT_ROOT / arm_id / "responses.sqlite3"
        ledgers[arm_id] = selection._validate_completed_ledger(
            arm_id=arm_id,
            path=path,
            cases=cases,
            manifest=manifest,
        )
        responses = _read_responses(path)
        if set(responses) != {row.case_id for row in cases}:
            raise GroundingFloorAuditError(f"{arm_id} response set is incomplete")
    metrics = {
        arm_id: _score_arm(arm_id, selection.OUTPUT_ROOT)
        for arm_id in selection.ARMS
    }
    reference_surface = _measure_reference_surface(cases, gold, chunks_by_course)
    candidate = metrics["candidate"]
    incumbent = metrics["incumbent"]
    historical_hashes = {
        audit_id: _sha256_file(path)
        for audit_id, path in HISTORICAL_RECORDS.items()
    }
    return {
        "schema_version": 1,
        "run_id": RUN_ID,
        "code_revision": code_revision,
        "working_tree_dirty": working_tree_dirty,
        "status": "completed-corrected",
        "decision": (
            "Keep the relative selection of dominance-scoped-ambiguity-safe-v3; "
            "correct the reported factual metric and treat the historical floor "
            "narrative as development-only mechanism evidence, not a proven task floor."
        ),
        "evidence_class": "development-split-reproduction-and-correction",
        "sealed_package_touched": False,
        "provider_calls": 0,
        "cost_usd": 0.0,
        "inputs": {
            "case_count": len(cases),
            "cases_sha256": _sha256_file(selection.CASES_PATH),
            "gold_sha256": _sha256_file(selection.GOLD_PATH),
            "corpus_sha256": _sha256_file(selection.CORPUS_PATH),
            "historical_record_sha256": historical_hashes,
        },
        "verified_ledgers": ledgers,
        "corrected_selection_metrics": metrics,
        "corrected_factual_improvement_points": 100
        * (
            candidate["fully_grounded_factual_success"]
            - incumbent["fully_grounded_factual_success"]
        ),
        "relative_promotion_rule_still_passes": bool(
            candidate["fully_grounded_factual_success"]
            > incumbent["fully_grounded_factual_success"]
            and candidate["severe_unsupported_release_count"]
            <= incumbent["severe_unsupported_release_count"]
            and candidate["operational_failure_count"]
            <= incumbent["operational_failure_count"]
        ),
        "reference_surface": reference_surface,
        "limitations": [
            "Development-split evidence only; the sealed package was not accessed.",
            "This reproduces the current code and immutable ledgers, not an uncommitted ad hoc historical script.",
            "The audits compare bounded deterministic mechanisms and do not prove a universal task ceiling.",
            "Public synthetic sources only; no professor fidelity, usability, or learning claim.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    result = build_result()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
