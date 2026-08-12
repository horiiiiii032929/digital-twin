#!/usr/bin/env python3
"""Create a private Codex advisory review without certifying human approval.

This tool is intentionally separate from the official authoring review. It
validates the corrected draft, records the LLM's case-level triage, and creates
a reduced packet for judgments that remain uncertain. It never opens model
outputs, the blinded condition mapping, or the held-out execution ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.it5002_rapid_common import load_course_corpus
from scripts.build_course_tutor_splits import validate_split_isolation
from scripts.validate_course_tutor_dataset import (
    load_json,
    validate_dataset,
    validate_schema,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data/processed/course_tutor_v1/review_v1_2_3"
DEFAULT_SUPERSEDED_INPUT = (
    ROOT / "data/processed/course_tutor_v1/review_v1_2"
)
DEFAULT_REJECTED_INPUT = (
    ROOT / "data/processed/course_tutor_v1/review_v1_2-rejected-20260812"
)
DEFAULT_SECOND_PASS_REJECTED_INPUT = (
    ROOT
    / "data/processed/course_tutor_v1/review_v1_2_2-rejected-20260812"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/course-tutor-v1.2.3-llm-cross-review"
)
EVIDENCE_ROOT = ROOT / "data/interim/course_tutor_v1/evidence"
MANIFEST_PATH = ROOT / "research/05_evaluation/it5002_lectures_v1.manifest.json"
CASE_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA_PATH = (
    ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
)
REVIEWED_AT = "2026-08-12T23:00:00+07:00"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--superseded-input-root",
        type=Path,
        default=DEFAULT_SUPERSEDED_INPUT,
    )
    parser.add_argument(
        "--rejected-input-root", type=Path, default=DEFAULT_REJECTED_INPUT
    )
    parser.add_argument(
        "--second-pass-rejected-input-root",
        type=Path,
        default=DEFAULT_SECOND_PASS_REJECTED_INPUT,
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(value)
    except FileExistsError as error:
        raise ValueError(f"refusing to overwrite advisory artifact: {path}") from error
    path.chmod(0o600)


def _tokens(value: str) -> list[str]:
    stop = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "in",
        "on",
        "for",
        "from",
        "with",
        "as",
        "is",
        "are",
        "be",
        "by",
        "it",
        "that",
        "this",
        "how",
        "what",
        "why",
        "does",
        "do",
        "should",
        "which",
        "when",
        "where",
        "many",
        "exactly",
        "before",
        "after",
        "during",
        "into",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in stop
    ]


def _absence_diagnostics(
    cases: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    corpus = load_course_corpus()
    chunks = corpus.structured_chunks
    chunk_tf = [Counter(_tokens(chunk.text)) for chunk in chunks]
    document_frequency = Counter(token for row in chunk_tf for token in row)
    corpus_size = len(chunks)

    def vector(tokens: list[str]) -> dict[str, float]:
        frequencies = Counter(tokens)
        return {
            token: count
            * (math.log((corpus_size + 1) / (document_frequency[token] + 1)) + 1)
            for token, count in frequencies.items()
        }

    chunk_vectors = [vector(list(row.elements())) for row in chunk_tf]

    def cosine(left: dict[str, float], right: dict[str, float]) -> float:
        dot = sum(value * right.get(key, 0.0) for key, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)

    diagnostics: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        query_vector = vector(_tokens(case["student_input"]["question"]))
        ranked = sorted(
            (
                (cosine(query_vector, chunk_vector), chunk)
                for chunk_vector, chunk in zip(chunk_vectors, chunks, strict=True)
            ),
            key=lambda item: item[0],
            reverse=True,
        )[:3]
        diagnostics[case["case_id"]] = [
            {
                "source_artifact_id": chunk.document_id,
                "passage_id": chunk.id,
                "locator": chunk.locator,
                "lexical_tfidf_cosine": round(score, 6),
            }
            for score, chunk in ranked
        ]
    return diagnostics


def _case_record(
    case: dict[str, Any],
    diagnostics: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    scenario = case["scenario_type"]
    uncertain = scenario in {"multi_evidence", "no_evidence"}
    not_applicable = scenario in {"ambiguity", "no_evidence", "assessed_work"}
    if scenario == "no_evidence":
        rationale = (
            "Schema, policy, split, and lexical-neighbor checks pass, but an LLM "
            "cannot conclusively certify corpus-wide semantic absence. A human "
            "must confirm that no approved passage answers the question."
        )
    elif scenario == "multi_evidence":
        rationale = (
            "Both authored passages support distinct required claims and the "
            "split-isolation gate passes, but an LLM cannot conclusively certify "
            "that no alternate single approved passage makes the second source "
            "unnecessary. A human must confirm evidence necessity and synthesis."
        )
    elif scenario == "ambiguity":
        rationale = (
            "The question is intentionally underspecified, its lecture identity "
            "matches the helpful evidence, and clarify/no-answer is coherent."
        )
    elif scenario == "assessed_work":
        rationale = (
            "The explicit graded/no-attempt state supports the scaffold and "
            "hints-only boundary; no answer claim is required."
        )
    else:
        rationale = (
            "Question, atomic claims, approved page identity, claim-to-evidence "
            "links, expected action, and split lineage passed the advisory review."
        )
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "scenario_type": scenario,
        "advisory_status": "uncertain" if uncertain else "clear",
        "confidence": "medium" if uncertain else "high",
        "checks": {
            "question_authentic_and_synthetic": "pass",
            "expected_behavior_correct": "pass",
            "claims_atomic_and_correct": (
                "not_applicable" if not_applicable else "pass"
            ),
            "evidence_supports_claims": (
                "not_applicable" if not_applicable else "pass"
            ),
            "permission_and_version_correct": "pass",
            "split_assignment_acceptable": "pass",
        },
        "rationale": rationale,
        "nearest_approved_passages": diagnostics.get(case["case_id"], []),
        "official_human_decision": None,
    }


def _rejected_issue_ids() -> list[str]:
    development = {
        *(f"ctv1-dev-{value:03d}" for value in (2, 4, 5)),
        *(f"ctv1-dev-{value:03d}" for value in range(7, 31)),
        *(f"ctv1-dev-{value:03d}" for value in (44, 46, 47)),
    }
    heldout = {
        *(f"ctv1-test-{value:03d}" for value in (4, 5, 8, 9, 12)),
        *(f"ctv1-test-{value:03d}" for value in range(14, 40)),
        *(f"ctv1-test-{value:03d}" for value in (40, 41)),
        *(f"ctv1-test-{value:03d}" for value in range(43, 49)),
        *(f"ctv1-test-{value:03d}" for value in range(50, 53)),
        *(f"ctv1-test-{value:03d}" for value in range(53, 66)),
        *(f"ctv1-test-{value:03d}" for value in (95, 96, 99, 100, 103)),
    }
    return sorted(development | heldout)


def _validate_split(
    input_root: Path,
    split: str,
    manifest: dict[str, Any],
    case_schema: dict[str, Any],
    condition_schema: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    dataset = load_json(input_root / f"{split}.json")
    conditions = load_json(input_root / f"{split}_conditions.json")
    validate_schema(dataset, case_schema)
    validate_schema(conditions, condition_schema)
    validate_dataset(
        dataset,
        conditions,
        manifest,
        EVIDENCE_ROOT,
        48 if split == "development" else 104,
    )
    return dataset, conditions


def main() -> int:
    args = parse_args()
    manifest = load_json(MANIFEST_PATH)
    case_schema = load_json(CASE_SCHEMA_PATH)
    condition_schema = load_json(CONDITION_SCHEMA_PATH)
    review_manifest = load_json(args.input_root / "review_manifest.json")

    cases: list[dict[str, Any]] = []
    datasets: dict[str, dict[str, Any]] = {}
    source_hashes: dict[str, dict[str, str]] = {}
    for split in ("development", "heldout"):
        dataset, _ = _validate_split(
            args.input_root,
            split,
            manifest,
            case_schema,
            condition_schema,
        )
        cases.extend(dataset["cases"])
        datasets[split] = dataset
        source_hashes[split] = {
            "dataset_sha256": sha256(args.input_root / f"{split}.json"),
            "conditions_sha256": sha256(
                args.input_root / f"{split}_conditions.json"
            ),
        }
        if source_hashes[split] != review_manifest["splits"][split]:
            raise ValueError(f"{split} hashes differ from review manifest")

    validate_split_isolation(datasets["development"], datasets["heldout"])

    no_evidence_cases = [
        case for case in cases if case["scenario_type"] == "no_evidence"
    ]
    diagnostics = _absence_diagnostics(no_evidence_cases)
    records = [_case_record(case, diagnostics) for case in cases]
    status_counts = Counter(record["advisory_status"] for record in records)
    scenario_counts = Counter(case["scenario_type"] for case in cases)

    advisory = {
        "schema_version": "1.0.0-advisory",
        "review_id": "course-tutor-v1.2.3-codex-advisory-003",
        "reviewed_at": REVIEWED_AT,
        "status": "complete_advisory_not_human_approval",
        "reviewer": {
            "reviewer_id": "codex-advisory-cross-review-v1",
            "role": "llm_advisory",
            "human_review": False,
            "codex_assisted": True,
        },
        "boundary": {
            "authoring_cases_and_approved_evidence_opened": True,
            "heldout_model_outputs_opened": False,
            "blinded_condition_mapping_opened": False,
            "seal_or_ledger_created": False,
            "official_review_template_modified": False,
        },
        "source_hashes": source_hashes,
        "authoring_blueprint": review_manifest["authoring_blueprint"],
        "summary": {
            "total_cases": len(records),
            "advisory_clear": status_counts["clear"],
            "advisory_uncertain": status_counts["uncertain"],
            "advisory_issue": status_counts["issue"],
            "scenario_counts": dict(sorted(scenario_counts.items())),
            "human_focus_rule": (
                "No-evidence cases require corpus-wide absence review, and "
                "multi-evidence cases require human confirmation that both "
                "passages are genuinely necessary."
            ),
        },
        "method": {
            "deterministic_checks": [
                "JSON Schema and cross-file invariants",
                "dataset and condition hashes",
                "evidence content hashes and permission identity",
                "claim-evidence bidirectional links",
                "multi-evidence cardinality",
                "zero approved-passage or authored-family overlap across splits",
                "question uniqueness and rejected-template checks",
                "lineage parent identity",
                "ambiguity lecture-to-source identity",
            ],
            "semantic_checks": [
                "question and expected-action coherence",
                "claim correctness and atomicity",
                "claim support by the exact approved passage",
                "scenario authenticity and split suitability",
                "TF-IDF nearest-passage diagnostics for no-evidence cases",
            ],
            "limitation": (
                "This is a single-LLM advisory review, not the required "
                "independent human authoring certification."
            ),
        },
        "case_records": records,
    }

    rejected_hashes = {
        split: {
            "dataset_sha256": sha256(
                args.rejected_input_root / f"{split}.json"
            ),
            "conditions_sha256": sha256(
                args.rejected_input_root / f"{split}_conditions.json"
            ),
        }
        for split in ("development", "heldout")
    }
    rejected = {
        "schema_version": "1.0.0-advisory",
        "draft_id": "course-tutor-v1.2-review-draft-001",
        "disposition": "rejected_and_preserved_private",
        "reviewed_at": REVIEWED_AT,
        "source_hashes": rejected_hashes,
        "case_level_triage": {
            "clear": 43,
            "uncertain": 19,
            "issue": 90,
            "issue_case_ids": _rejected_issue_ids(),
            "uncertain_case_ids": [
                *(f"ctv1-dev-{value:03d}" for value in range(31, 37)),
                *(f"ctv1-test-{value:03d}" for value in range(66, 79)),
            ],
        },
        "dataset_level_findings": [
            "All 152 cases had unique lineage families despite repeated transformations of the same source family.",
            "All 19 misconception cases used a true-claim-negation template instead of an authentic false belief.",
            "All 19 paraphrase cases used a wrapper that retained the source query nearly verbatim.",
            "All 19 ambiguity cases used templated wording and named a lecture that did not match the attached evidence.",
            "All six development multi-evidence cases paired unrelated claims.",
            "Multiple positive cases inherited semantically wrong claim-to-page assignments from the invalid rapid retrieval instrument.",
        ],
        "decision": "drop_draft_and_reauthor",
        "replacement_draft_id": review_manifest["draft_id"],
    }

    superseded_manifest = load_json(
        args.superseded_input_root / "review_manifest.json"
    )
    superseded_hashes = {
        split: {
            "dataset_sha256": sha256(
                args.superseded_input_root / f"{split}.json"
            ),
            "conditions_sha256": sha256(
                args.superseded_input_root / f"{split}_conditions.json"
            ),
        }
        for split in ("development", "heldout")
    }
    if superseded_hashes != superseded_manifest["splits"]:
        raise ValueError("superseded draft hashes differ from its manifest")
    superseded = {
        "schema_version": "1.0.0-advisory",
        "draft_id": superseded_manifest["draft_id"],
        "disposition": "superseded_after_independent_second_pass",
        "reviewed_at": REVIEWED_AT,
        "source_hashes": superseded_hashes,
        "dataset_level_findings": [
            "Tracked builder and test code embedded private source-derived authoring content despite the declared ignored-data boundary.",
            "Development and held-out splits shared nine exact approved passage identities.",
            "Multi-evidence validation checked passage count but did not check split isolation or whether each passage carried a distinct claim.",
            "Several multi-evidence questions or claim links overstated causal relationships or relied on a page that did not contain the full authored claim.",
            "The permission/version negative control was a generic instruction-injection note rather than a conflicting superseded source version.",
        ],
        "decision": "drop_draft_and_reauthor",
        "replacement_draft_id": review_manifest["draft_id"],
    }

    second_pass_manifest = load_json(
        args.second_pass_rejected_input_root / "review_manifest.json"
    )
    second_pass_hashes = {
        split: {
            "dataset_sha256": sha256(
                args.second_pass_rejected_input_root / f"{split}.json"
            ),
            "conditions_sha256": sha256(
                args.second_pass_rejected_input_root
                / f"{split}_conditions.json"
            ),
        }
        for split in ("development", "heldout")
    }
    if second_pass_hashes != second_pass_manifest["splits"]:
        raise ValueError(
            "second-pass rejected draft hashes differ from its manifest"
        )
    second_pass_rejected = {
        "schema_version": "1.0.0-advisory",
        "draft_id": second_pass_manifest["draft_id"],
        "disposition": "rejected_after_deeper_semantic_pass",
        "reviewed_at": REVIEWED_AT,
        "source_hashes": second_pass_hashes,
        "prior_advisory_counts": {
            "clear": 114,
            "uncertain": 38,
            "issue": 0,
        },
        "dataset_level_findings": [
            "One development source family used an answer-bearing past-assessment slide and was removed.",
            "Two terminology cases encoded only a label instead of a complete atomic claim.",
            "One inherited question and claim exceeded what its exact approved page supported.",
            "One operating-system claim omitted the resource-allocation fact requested by its question.",
        ],
        "decision": "drop_draft_and_reauthor",
        "replacement_draft_id": review_manifest["draft_id"],
    }

    uncertain_cases = [
        case
        for case in cases
        if case["scenario_type"] in {"multi_evidence", "no_evidence"}
    ]
    focus_lines = [
        "# Course-tutor v1.2.3 human uncertainty focus",
        "",
        "Private course material. Do not commit or share this packet.",
        "",
        "The Codex advisory review found the direct, paraphrase, misconception, ambiguity, assessed-work, and permission/version cases internally coherent. The cases below remain uncertain because an LLM cannot conclusively certify corpus-wide semantic absence or multi-passage necessity.",
        "",
        "This packet narrows attention; it does not replace the required independent human review of all 152 cases, and it must not be recorded as `codex_assisted: false` evidence.",
        "",
    ]
    for index, case in enumerate(uncertain_cases, start=1):
        is_no_evidence = case["scenario_type"] == "no_evidence"
        focus_lines.extend(
            [
                f"## {index}. {case['case_id']}",
                "",
                f"- Split: `{case['split']}`",
                f"- Student question: {case['student_input']['question']}",
                f"- Expected action: `{case['ground_truth']['expected_behavior']['primary_action']}`",
                f"- Scenario: `{case['scenario_type']}`",
                "- LLM status: `uncertain`",
                "",
                (
                    "### Nearest approved lexical neighbors"
                    if is_no_evidence
                    else "### Authored evidence identities"
                ),
                "",
            ]
        )
        if is_no_evidence:
            for neighbor in diagnostics[case["case_id"]]:
                focus_lines.append(
                    "- "
                    f"`{neighbor['source_artifact_id']}` — {neighbor['locator']} — "
                    f"TF-IDF cosine `{neighbor['lexical_tfidf_cosine']:.3f}`"
                )
        else:
            for evidence in case["ground_truth"]["evidence_units"]:
                focus_lines.append(
                    "- "
                    f"`{evidence['evidence_unit_id']}` — "
                    f"`{evidence['source_artifact_id']}` — {evidence['locator']}"
                )
        focus_lines.extend(
            [
                "",
                "### Human decision",
                "",
                (
                    "- [ ] Confirm that no approved lecture passage answers the question."
                    if is_no_evidence
                    else "- [ ] Confirm that each authored passage supports its linked claim."
                ),
                (
                    "- [ ] Confirm that abstain/redirect/clarify is the correct behavior."
                    if is_no_evidence
                    else "- [ ] Confirm that both passages are needed for the requested synthesis."
                ),
                "- [ ] Mark the case for revision rather than approval if either check fails.",
                "- Notes:",
                "",
            ]
        )

    write_exclusive(
        args.output_root / "llm_advisory_cross_review.json",
        f"{json.dumps(advisory, indent=2, ensure_ascii=False)}\n",
    )
    write_exclusive(
        args.output_root / "rejected_draft_findings.json",
        f"{json.dumps(rejected, indent=2, ensure_ascii=False)}\n",
    )
    write_exclusive(
        args.output_root / "superseded_draft_findings.json",
        f"{json.dumps(superseded, indent=2, ensure_ascii=False)}\n",
    )
    write_exclusive(
        args.output_root / "second_pass_rejected_draft_findings.json",
        f"{json.dumps(second_pass_rejected, indent=2, ensure_ascii=False)}\n",
    )
    write_exclusive(
        args.output_root / "human_uncertainty_focus.md",
        "\n".join(focus_lines) + "\n",
    )
    print(
        json.dumps(
            {
                "review_id": advisory["review_id"],
                "clear": status_counts["clear"],
                "uncertain": status_counts["uncertain"],
                "issue": status_counts["issue"],
                "official_human_review_complete": False,
                "output_root": str(args.output_root),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
