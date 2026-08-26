#!/usr/bin/env python3
"""Join persisted responses with hidden gold and score the open benchmark."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sqlite3
import statistics
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_contract import (  # noqa: E402
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationAtomicClaimV1,
    EvaluationCaseV1,
    EvaluationCitationV1,
    EvaluationClaimV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    EvaluationSplit,
)
from src.digital_twin.evaluation.factual_qa_dataset import normalize_question  # noqa: E402
from src.digital_twin.evaluation.factual_qa_execution import (  # noqa: E402
    canonical_json_sha256,
)
from src.digital_twin.evaluation.factual_qa_scoring import (  # noqa: E402
    FactualQaCaseScoreV1,
    score_case,
    summarize_scores,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-open-10000-v1"
INSTRUMENT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_open_10000_v1.json"
)
DATASET_ROOT = ROOT / "research/05_evaluation/datasets"
DEFAULT_CASES = DATASET_ROOT / "academic_factual_qa_open_10000_v1_cases.json"
DEFAULT_GOLD = DATASET_ROOT / "academic_factual_qa_open_10000_v1_gold.json"
DEFAULT_RESPONSES = (
    ROOT / "reports/generated/academic-factual-qa-open-10000-v1-responses.sqlite3"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/academic-factual-qa-open-10000-v1-result.json"
)
DEFAULT_CONTROL_CASES = (
    DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_control_cases.json"
)
DEFAULT_CONTROL_GOLD = (
    DATASET_ROOT / "academic_factual_qa_open_10000_v1_development_control_gold.json"
)
DEFAULT_CONTROL_RESPONSES = (
    ROOT
    / "reports/generated/academic-factual-qa-open-10000-v1-development-control-responses.sqlite3"
)


class OpenBenchmarkScoringError(RuntimeError):
    """Raised when scoring evidence is incomplete, mixed, or invalid."""


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validated_package(path: Path, *, rows_key: str) -> dict[str, Any]:
    payload = _load_json(path)
    expected = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != expected:
        raise OpenBenchmarkScoringError(f"package hash drifted: {path.name}")
    if payload.get("case_count") != len(payload.get(rows_key, [])):
        raise OpenBenchmarkScoringError(f"package row count drifted: {path.name}")
    return payload


def _load_completed_responses(path: Path) -> tuple[dict[str, str], list[EvaluationResponseV1]]:
    if not path.is_file():
        raise OpenBenchmarkScoringError("response ledger is missing")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        if metadata.get("status") != "completed":
            raise OpenBenchmarkScoringError("hidden gold cannot open before responses complete")
        records = list(
            connection.execute(
                "SELECT case_id, payload_json, payload_sha256 FROM responses ORDER BY sequence"
            )
        )
    finally:
        connection.close()
    responses: list[EvaluationResponseV1] = []
    for case_id, serialized, expected_hash in records:
        if hashlib.sha256(serialized.encode("utf-8")).hexdigest() != expected_hash:
            raise OpenBenchmarkScoringError(f"response hash drifted: {case_id}")
        response = EvaluationResponseV1.model_validate_json(serialized)
        if response.case_id != case_id:
            raise OpenBenchmarkScoringError(f"response identity drifted: {case_id}")
        responses.append(response)
    if int(metadata.get("response_count", "-1")) != len(responses):
        raise OpenBenchmarkScoringError("response completion count drifted")
    return metadata, responses


def _gate_results(
    summary: dict[str, Any],
    scores: list[FactualQaCaseScoreV1],
    instrument: dict[str, Any],
    *,
    duplicate_count: int,
) -> dict[str, bool]:
    metrics = summary["metrics"]
    gates = instrument["hard_gates"]
    malformed = sum(row.actual_action == EvaluationAction.OPERATIONAL_FAILURE for row in scores)
    return {
        "fully_grounded_factual_success": metrics["fully_grounded_factual_success"]
        >= gates["fully_grounded_factual_success_min"],
        "source_family_lower_95": summary["fully_grounded_source_family_interval"][
            "lower_95"
        ]
        >= gates["fully_grounded_source_family_lower_95_min"],
        "action_accuracy_overall": metrics["action_accuracy_overall"]
        >= gates["action_accuracy_overall_min"],
        "action_accuracy_answerable": metrics["action_accuracy_answerable"]
        >= gates["action_accuracy_answerable_min"],
        "boundary_action_accuracy": metrics["boundary_action_accuracy"]
        >= gates["boundary_action_accuracy_min"],
        "zero_severe_unsupported_releases": summary["severe_unsupported_release_count"]
        <= gates["severe_unsupported_release_count_max"],
        "atomic_claim_precision": metrics["atomic_claim_precision"]
        >= gates["atomic_claim_precision_min"],
        "atomic_claim_recall": metrics["atomic_claim_recall"]
        >= gates["atomic_claim_recall_min"],
        "citation_precision": metrics["citation_precision"]
        >= gates["citation_precision_min"],
        "citation_recall": metrics["citation_recall"]
        >= gates["citation_recall_min"],
        "source_version_validity": metrics["source_version_validity"]
        >= gates["source_version_validity_min"],
        "canonical_all_evidence_at_3": metrics["canonical_all_evidence_at_3"]
        >= gates["canonical_all_evidence_at_3_min"],
        "evidence_recall_at_5": metrics["evidence_recall_at_5"]
        >= gates["evidence_recall_at_5_min"],
        "provider_completion": metrics["provider_completion"]
        >= gates["provider_completion_min"],
        "malformed_output": malformed / len(scores) <= gates["malformed_output_max"],
        "zero_exact_duplicates": duplicate_count <= gates["exact_duplicate_count_max"],
    }


def score_packages(
    *,
    cases_path: Path,
    gold_path: Path,
    responses_path: Path,
) -> dict[str, Any]:
    # The completed response ledger is opened first. Hidden gold is loaded only
    # after this durable completion check succeeds.
    ledger_metadata, responses = _load_completed_responses(responses_path)
    cases_package = _validated_package(cases_path, rows_key="cases")
    gold_package = _validated_package(gold_path, rows_key="gold")
    if (
        cases_package.get("dataset_id") != gold_package.get("dataset_id")
        or cases_package.get("split") != gold_package.get("split")
        or cases_package.get("case_count") != gold_package.get("case_count")
    ):
        raise OpenBenchmarkScoringError("public and hidden packages are not paired")
    if ledger_metadata.get("cases_sha256") != cases_package["content_sha256"]:
        raise OpenBenchmarkScoringError("response ledger is bound to different public inputs")
    cases = [EvaluationCaseV1.model_validate(row) for row in cases_package["cases"]]
    gold = [EvaluationGoldV1.model_validate(row) for row in gold_package["gold"]]
    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    response_by_id = {row.case_id: row for row in responses}
    if not (
        case_by_id.keys() == gold_by_id.keys() == response_by_id.keys()
        and len(case_by_id) == len(cases)
        and len(gold_by_id) == len(gold)
        and len(response_by_id) == len(responses)
    ):
        raise OpenBenchmarkScoringError("case/gold/response identities are incomplete or duplicated")
    scores = [
        score_case(case_by_id[case_id], gold_by_id[case_id], response_by_id[case_id])
        for case_id in sorted(case_by_id)
    ]
    normalized_questions = [normalize_question(row.question) for row in cases]
    duplicate_count = sum(
        count - 1 for count in Counter(normalized_questions).values() if count > 1
    )
    summary = summarize_scores(scores)
    summary["overall_grounded_task_success"] = sum(
        row.fully_grounded_success if row.answerable else row.boundary_safe
        for row in scores
    ) / len(scores)
    instrument = _load_json(INSTRUMENT_PATH)
    gate_results = _gate_results(
        summary, scores, instrument, duplicate_count=duplicate_count
    )
    return {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "dataset_id": cases_package["dataset_id"],
        "split": cases_package["split"],
        "status": "completed-keep" if all(gate_results.values()) else "completed-refine",
        "decision": "Keep" if all(gate_results.values()) else "Refine",
        "summary": summary,
        "gate_results": gate_results,
        "failed_gates": sorted(key for key, passed in gate_results.items() if not passed),
        "exact_duplicate_count": duplicate_count,
        "case_scores": [row.model_dump(mode="json") for row in scores],
        "response_ledger_sha256": hashlib.sha256(responses_path.read_bytes()).hexdigest(),
        "public_cases_sha256": cases_package["content_sha256"],
        "hidden_gold_sha256": gold_package["content_sha256"],
        "model_assisted_evaluation": True,
        "independent_external_human_annotation": False,
    }


def paired_comparison(
    candidate: dict[str, Any],
    control: dict[str, Any],
    *,
    lower_delta_gate: float,
    boundary_not_worse: bool,
    replicates: int = 10_000,
    seed: int = 20260826,
) -> dict[str, Any]:
    """Compare the candidate with a frozen control subset by source family."""

    candidate_scores = {
        row["case_id"]: FactualQaCaseScoreV1.model_validate(row)
        for row in candidate["case_scores"]
    }
    control_scores = {
        row["case_id"]: FactualQaCaseScoreV1.model_validate(row)
        for row in control["case_scores"]
    }
    if not control_scores or not set(control_scores).issubset(candidate_scores):
        raise OpenBenchmarkScoringError(
            "control identities must be a non-empty subset of candidate identities"
        )
    pairs = [
        (candidate_scores[case_id], control_scores[case_id])
        for case_id in sorted(control_scores)
    ]
    for candidate_row, control_row in pairs:
        if (
            candidate_row.source_family_id != control_row.source_family_id
            or candidate_row.expected_action != control_row.expected_action
        ):
            raise OpenBenchmarkScoringError("paired control metadata drifted")

    answerable = [pair for pair in pairs if pair[0].answerable]
    boundary = [pair for pair in pairs if not pair[0].answerable]
    if not answerable or not boundary:
        raise OpenBenchmarkScoringError(
            "paired comparison requires answerable and boundary cases"
        )

    family_deltas: dict[str, list[float]] = {}
    for candidate_row, control_row in answerable:
        family_deltas.setdefault(candidate_row.source_family_id, []).append(
            float(candidate_row.fully_grounded_success)
            - float(control_row.fully_grounded_success)
        )
    family_means = [
        statistics.fmean(values) for _, values in sorted(family_deltas.items())
    ]
    rng = random.Random(seed)
    samples = sorted(
        statistics.fmean(rng.choice(family_means) for _ in family_means)
        for _ in range(replicates)
    )
    candidate_boundary = statistics.fmean(
        float(candidate_row.boundary_safe) for candidate_row, _ in boundary
    )
    control_boundary = statistics.fmean(
        float(control_row.boundary_safe) for _, control_row in boundary
    )
    lower_95 = samples[math.floor(0.025 * (replicates - 1))]
    paired_gates = {
        "supported_answer_retention_lower_95": lower_95 >= lower_delta_gate,
        "boundary_safety_not_worse": (
            candidate_boundary >= control_boundary if boundary_not_worse else True
        ),
    }
    candidate_gates = candidate["gate_results"]
    return {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "completed-keep"
            if all(candidate_gates.values()) and all(paired_gates.values())
            else "completed-refine"
        ),
        "decision": (
            "Keep"
            if all(candidate_gates.values()) and all(paired_gates.values())
            else "Refine"
        ),
        "candidate_status": candidate["status"],
        "control_status": control["status"],
        "paired_case_count": len(pairs),
        "paired_answerable_count": len(answerable),
        "paired_boundary_count": len(boundary),
        "supported_answer_retention": {
            "estimate": statistics.fmean(family_means),
            "lower_95": lower_95,
            "upper_95": samples[math.ceil(0.975 * (replicates - 1))],
            "source_family_count": len(family_means),
            "replicates": replicates,
            "seed": seed,
        },
        "boundary_safety": {
            "candidate": candidate_boundary,
            "control": control_boundary,
            "delta": candidate_boundary - control_boundary,
        },
        "candidate_gate_results": candidate_gates,
        "paired_gate_results": paired_gates,
        "failed_gates": sorted(
            [key for key, passed in candidate_gates.items() if not passed]
            + [key for key, passed in paired_gates.items() if not passed]
        ),
    }


def _synthetic_packages(directory: Path) -> tuple[Path, Path, Path]:
    reference = CanonicalEvidenceRefV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256="a" * 64,
        char_start=0,
        char_end=20,
    )
    case = EvaluationCaseV1(
        case_id="case-001",
        cluster_id="cluster-001",
        source_family_id="family-001",
        course_id="course-001",
        question="What is the source fact?",
        split=EvaluationSplit.DEVELOPMENT,
        slice="direct-factual",
        author_family="fixture",
    )
    gold = EvaluationGoldV1(
        case_id="case-001",
        expected_action=EvaluationAction.ANSWER,
        canonical_answer="the source fact",
        claims=[
            EvaluationClaimV1(
                claim_id="claim-001",
                answer_span="the source fact",
                evidence_refs=[reference],
            )
        ],
    )
    citation = EvaluationCitationV1(
        source_artifact_id="source-001",
        source_version=1,
        source_sha256="a" * 64,
        char_start=0,
        char_end=20,
    )
    response = EvaluationResponseV1(
        case_id="case-001",
        flow_id="fixture",
        action=EvaluationAction.ANSWER,
        answer="The source fact.",
        atomic_claims=[EvaluationAtomicClaimV1(text="the source fact", citations=[citation])],
        citations=[citation],
        retrieved_evidence=[citation],
        operational_status="completed",
        provider_model="not-called",
    )
    cases_payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": "fixture",
        "split": "development",
        "case_count": 1,
        "cases": [case.model_dump(mode="json")],
    }
    cases_payload["content_sha256"] = canonical_json_sha256(cases_payload)
    gold_payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": "fixture",
        "split": "development",
        "case_count": 1,
        "gold": [gold.model_dump(mode="json")],
    }
    gold_payload["content_sha256"] = canonical_json_sha256(gold_payload)
    cases_path = directory / "cases.json"
    gold_path = directory / "gold.json"
    response_path = directory / "responses.sqlite3"
    cases_path.write_text(json.dumps(cases_payload), encoding="utf-8")
    gold_path.write_text(json.dumps(gold_payload), encoding="utf-8")
    connection = sqlite3.connect(response_path)
    serialized = response.model_dump_json()
    with connection:
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute(
            "CREATE TABLE responses (sequence INTEGER PRIMARY KEY, case_id TEXT UNIQUE, payload_json TEXT, payload_sha256 TEXT)"
        )
        for key, value in {
            "status": "completed",
            "response_count": "1",
            "cases_sha256": cases_payload["content_sha256"],
        }.items():
            connection.execute("INSERT INTO metadata VALUES (?, ?)", (key, value))
        connection.execute(
            "INSERT INTO responses VALUES (?, ?, ?, ?)",
            (1, "case-001", serialized, hashlib.sha256(serialized.encode()).hexdigest()),
        )
    connection.close()
    return cases_path, gold_path, response_path


def simulate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="academic-open-scoring-") as directory:
        paths = _synthetic_packages(Path(directory))
        result = score_packages(
            cases_path=paths[0], gold_path=paths[1], responses_path=paths[2]
        )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "simulated-network-free",
        "simulated_result_status": result["status"],
        "simulated_gate_results": result["gate_results"],
        "provider_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--score", action="store_true")
    mode.add_argument("--compare", action="store_true")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    parser.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    parser.add_argument("--control-cases", type=Path, default=DEFAULT_CONTROL_CASES)
    parser.add_argument("--control-gold", type=Path, default=DEFAULT_CONTROL_GOLD)
    parser.add_argument(
        "--control-responses", type=Path, default=DEFAULT_CONTROL_RESPONSES
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stage", choices=("development", "final"), default="final")
    arguments = parser.parse_args()
    if arguments.score or arguments.compare:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
        instrument = _load_json(INSTRUMENT_PATH)
        if arguments.stage == "development":
            require_bounded_pilot_operation_allowed(
                INSTRUMENT_ID, "method_evaluation_execution"
            )
            if not instrument["execution"]["development_execution_authorized"]:
                raise OpenBenchmarkScoringError(
                    "development scoring is not authorized"
                )
        else:
            require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "heldout_execution")
            if not instrument["execution"]["final_execution_authorized"]:
                raise OpenBenchmarkScoringError("final scoring is not authorized")
        if arguments.output.exists():
            raise OpenBenchmarkScoringError("result output already exists")
        candidate = score_packages(
            cases_path=arguments.cases,
            gold_path=arguments.gold,
            responses_path=arguments.responses,
        )
        if arguments.compare:
            control = score_packages(
                cases_path=arguments.control_cases,
                gold_path=arguments.control_gold,
                responses_path=arguments.control_responses,
            )
            gates = _load_json(INSTRUMENT_PATH)["hard_gates"]
            result = paired_comparison(
                candidate,
                control,
                lower_delta_gate=gates[
                    "paired_supported_retention_delta_lower_95_min"
                ],
                boundary_not_worse=gates["paired_boundary_safety_not_worse"],
            )
        else:
            result = candidate
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            arguments.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.write("\n")
    elif arguments.simulate:
        result = simulate()
    else:
        instrument = _load_json(INSTRUMENT_PATH)
        result = {
            "instrument_id": INSTRUMENT_ID,
            "status": "passed",
            "hard_gate_count": len(instrument["hard_gates"]),
            "provider_calls": 0,
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
