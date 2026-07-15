"""Calibrate and evaluate evidence-sufficiency gates over BM25 retrieval."""

import argparse
import json
import subprocess
from pathlib import Path

from services.embeddings import FastEmbedTextEmbedder
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    BM25Retriever,
    DenseRetriever,
    EvidenceSufficiencyEvaluationSummary,
    LexicalCoverageEvidenceGate,
    MinimumRawScoreEvidenceGate,
    SecondaryRetrieverAgreementGate,
    evaluate_evidence_sufficiency,
    load_retrieval_benchmark_corpus,
    load_retrieval_evaluation_set,
)


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_ROOT = ROOT / "research" / "05_evaluation"
DEFAULT_CORPUS = EVALUATION_ROOT / "retrieval_corpus_v2.json"
DEFAULT_CALIBRATION = EVALUATION_ROOT / "evidence_sufficiency_v1_calibration.json"
DEFAULT_TEST = EVALUATION_ROOT / "evidence_sufficiency_v1_test.json"
DEFAULT_RAW_THRESHOLDS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0)
DEFAULT_COVERAGE_THRESHOLDS = (0.15, 0.2, 0.25, 0.3, 0.4, 0.5)
DEFAULT_MATCHING_TERMS = (1, 2, 3)
DEFAULT_SEMANTIC_THRESHOLDS = (0.7, 0.725, 0.75, 0.775, 0.8, 0.825, 0.85, 0.875)
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_CACHE = ROOT / "data" / "external" / "model_cache"
MINIMUM_ANSWERABLE_RECALL = 0.9
MAXIMUM_GATE_LATENCY_MS = 1.0
RANKING_NON_REGRESSION_RATIO = 0.95


def main() -> None:
    arguments = _arguments()
    corpus = load_retrieval_benchmark_corpus(arguments.corpus)
    calibration = load_retrieval_evaluation_set(arguments.calibration)
    test = load_retrieval_evaluation_set(arguments.dataset)
    _validate_versions(corpus.version, calibration.corpus_version, test.corpus_version)
    chunks = corpus.chunks
    embedder = FastEmbedTextEmbedder(
        model_name=arguments.model,
        cache_dir=arguments.cache_dir,
        local_files_only=arguments.local_files_only,
    )
    dense = DenseRetriever(chunks, embedder)

    raw_selection, raw_rows = _calibrate_raw_score(
        chunks,
        calibration,
        arguments.raw_thresholds,
    )
    coverage_selection, coverage_rows = _calibrate_lexical_coverage(
        chunks,
        calibration,
        arguments.coverage_thresholds,
        arguments.matching_terms,
    )
    semantic_selection, semantic_rows = _calibrate_semantic_agreement(
        chunks,
        calibration,
        dense,
        arguments.semantic_thresholds,
    )
    payload = {
        "benchmark_version": "evidence-sufficiency-v1",
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "corpus": {
            "path": _relative(arguments.corpus),
            "version": corpus.version,
            "chunk_count": len(chunks),
            "synthetic_only": corpus.synthetic_only,
        },
        "calibration": {
            "path": _relative(arguments.calibration),
            "dataset_version": calibration.version,
            "case_count": len(calibration.cases),
            "minimum_answerable_recall": MINIMUM_ANSWERABLE_RECALL,
            "raw_score": {"selected": raw_selection, "results": raw_rows},
            "lexical_coverage": {
                "selected": coverage_selection,
                "results": coverage_rows,
            },
            "semantic_agreement": {
                "selected": semantic_selection,
                "results": semantic_rows,
            },
            "selection_order": [
                "safety_violation_count == 0",
                "false_answer_count == 0",
                f"answerable_recall >= {MINIMUM_ANSWERABLE_RECALL}",
                "maximum balanced_accuracy",
                "maximum unconditional Recall@3",
                "maximum unconditional nDCG@3",
                "lowest mean gate latency",
            ],
        },
    }
    if not arguments.calibration_only:
        summaries = _evaluate_frozen_candidates(
            chunks,
            test,
            raw_selection,
            coverage_selection,
            dense,
            semantic_selection,
        )
        control = summaries[0]
        calibration_eligibility = [
            True,
            semantic_selection["calibration_eligible"],
            raw_selection["calibration_eligible"],
            coverage_selection["calibration_eligible"],
        ]
        decision = _decide(summaries, control, calibration_eligibility)
        payload["test"] = {
            "path": _relative(arguments.dataset),
            "dataset_version": test.version,
            "case_count": len(test.cases),
            "thresholds": {
                "answerable_recall": MINIMUM_ANSWERABLE_RECALL,
                "no_evidence_accuracy": 1.0,
                "false_answer_count": 0,
                "ranking_non_regression_ratio": RANKING_NON_REGRESSION_RATIO,
                "maximum_gate_latency_ms": MAXIMUM_GATE_LATENCY_MS,
            },
            "results": [summary.model_dump(mode="json") for summary in summaries],
            "candidate_assessments": [
                _assessment(summary, control, calibration_eligible)
                for summary, calibration_eligible in zip(
                    summaries,
                    calibration_eligibility,
                    strict=True,
                )
            ],
        }
        payload["decision"] = decision
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is None:
        print(json.dumps(_compact(payload), indent=2, sort_keys=True))
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")


def _calibrate_raw_score(chunks, evaluation_set, thresholds):
    rows = []
    for threshold in thresholds:
        summary = evaluate_evidence_sufficiency(
            f"minimum-raw-score-{threshold:.3f}",
            BM25Retriever(chunks, k1=1.2, b=0.75),
            MinimumRawScoreEvidenceGate(threshold),
            chunks,
            evaluation_set,
        )
        rows.append(
            {
                "configuration": {"minimum_raw_score": threshold},
                **_calibration_metrics(summary),
            }
        )
    return _select(rows), rows


def _calibrate_lexical_coverage(
    chunks,
    evaluation_set,
    coverage_thresholds,
    matching_terms,
):
    rows = []
    for coverage in coverage_thresholds:
        for minimum_terms in matching_terms:
            summary = evaluate_evidence_sufficiency(
                f"lexical-coverage-{coverage:.3f}-terms-{minimum_terms}",
                BM25Retriever(chunks, k1=1.2, b=0.75),
                LexicalCoverageEvidenceGate(
                    minimum_query_coverage=coverage,
                    minimum_matching_terms=minimum_terms,
                    evidence_limit=3,
                ),
                chunks,
                evaluation_set,
            )
            rows.append(
                {
                    "configuration": {
                        "minimum_query_coverage": coverage,
                        "minimum_matching_terms": minimum_terms,
                        "evidence_limit": 3,
                    },
                    **_calibration_metrics(summary),
                }
            )
    return _select(rows), rows


def _calibrate_semantic_agreement(
    chunks,
    evaluation_set,
    dense,
    thresholds,
):
    rows = []
    for threshold in thresholds:
        for require_overlap in (False, True):
            summary = evaluate_evidence_sufficiency(
                "semantic-agreement-"
                f"{threshold:.3f}-overlap-{str(require_overlap).lower()}",
                BM25Retriever(chunks, k1=1.2, b=0.75),
                SecondaryRetrieverAgreementGate(
                    dense,
                    minimum_relevance_score=threshold,
                    secondary_limit=5,
                    require_source_overlap=require_overlap,
                ),
                chunks,
                evaluation_set,
            )
            rows.append(
                {
                    "configuration": {
                        "minimum_relevance_score": threshold,
                        "secondary_limit": 5,
                        "require_source_overlap": require_overlap,
                    },
                    **_calibration_metrics(summary),
                }
            )
    return _select(rows), rows


def _calibration_metrics(summary: EvidenceSufficiencyEvaluationSummary) -> dict:
    eligible = (
        summary.safety_violation_count == 0
        and summary.false_answer_count == 0
        and summary.answerable_recall >= MINIMUM_ANSWERABLE_RECALL
    )
    return {
        "eligible": eligible,
        "answerable_recall": summary.answerable_recall,
        "no_evidence_accuracy": summary.no_evidence_accuracy,
        "balanced_accuracy": summary.balanced_accuracy,
        "false_answer_count": summary.false_answer_count,
        "false_abstention_count": summary.false_abstention_count,
        "unconditional_recall_at_3": summary.unconditional_recall_at_3,
        "unconditional_ndcg_at_3": summary.unconditional_ndcg_at_3,
        "mean_gate_latency_ms": summary.mean_gate_latency_ms,
        "safety_violation_count": summary.safety_violation_count,
    }


def _select(rows: list[dict]) -> dict:
    eligible = [row for row in rows if row["eligible"]]
    pool = eligible or rows
    selected = max(
        pool,
        key=lambda row: (
            row["balanced_accuracy"],
            row["unconditional_recall_at_3"],
            row["unconditional_ndcg_at_3"],
            -row["mean_gate_latency_ms"],
        ),
    )
    return {**selected["configuration"], "calibration_eligible": bool(eligible)}


def _evaluate_frozen_candidates(
    chunks,
    evaluation_set,
    raw,
    coverage,
    dense,
    semantic,
):
    return [
        evaluate_evidence_sufficiency(
            "any-hit-control",
            BM25Retriever(chunks, k1=1.2, b=0.75),
            AnyHitEvidenceGate(),
            chunks,
            evaluation_set,
        ),
        evaluate_evidence_sufficiency(
            "semantic-agreement-"
            f"{semantic['minimum_relevance_score']:.3f}-"
            f"overlap-{str(semantic['require_source_overlap']).lower()}",
            BM25Retriever(chunks, k1=1.2, b=0.75),
            SecondaryRetrieverAgreementGate(
                dense,
                minimum_relevance_score=semantic["minimum_relevance_score"],
                secondary_limit=semantic["secondary_limit"],
                require_source_overlap=semantic["require_source_overlap"],
            ),
            chunks,
            evaluation_set,
        ),
        evaluate_evidence_sufficiency(
            f"minimum-raw-score-{raw['minimum_raw_score']:.3f}",
            BM25Retriever(chunks, k1=1.2, b=0.75),
            MinimumRawScoreEvidenceGate(raw["minimum_raw_score"]),
            chunks,
            evaluation_set,
        ),
        evaluate_evidence_sufficiency(
            "lexical-coverage-"
            f"{coverage['minimum_query_coverage']:.3f}-"
            f"terms-{coverage['minimum_matching_terms']}",
            BM25Retriever(chunks, k1=1.2, b=0.75),
            LexicalCoverageEvidenceGate(
                minimum_query_coverage=coverage["minimum_query_coverage"],
                minimum_matching_terms=coverage["minimum_matching_terms"],
                evidence_limit=coverage["evidence_limit"],
            ),
            chunks,
            evaluation_set,
        ),
    ]


def _assessment(summary, control, calibration_eligible: bool = True) -> dict:
    metrics = {
        "answerable_recall": {
            "value": summary.answerable_recall,
            "threshold": MINIMUM_ANSWERABLE_RECALL,
            "passed": summary.answerable_recall >= MINIMUM_ANSWERABLE_RECALL,
        },
        "balanced_accuracy": {
            "value": summary.balanced_accuracy,
            "threshold": 0.95,
            "passed": summary.balanced_accuracy >= 0.95,
        },
        "unconditional_recall_at_3": {
            "value": summary.unconditional_recall_at_3,
            "threshold": control.unconditional_recall_at_3
            * RANKING_NON_REGRESSION_RATIO,
            "passed": summary.unconditional_recall_at_3
            >= control.unconditional_recall_at_3 * RANKING_NON_REGRESSION_RATIO,
        },
        "unconditional_ndcg_at_3": {
            "value": summary.unconditional_ndcg_at_3,
            "threshold": control.unconditional_ndcg_at_3
            * RANKING_NON_REGRESSION_RATIO,
            "passed": summary.unconditional_ndcg_at_3
            >= control.unconditional_ndcg_at_3 * RANKING_NON_REGRESSION_RATIO,
        },
        "mean_gate_latency_ms": {
            "value": summary.mean_gate_latency_ms,
            "threshold": MAXIMUM_GATE_LATENCY_MS,
            "passed": summary.mean_gate_latency_ms <= MAXIMUM_GATE_LATENCY_MS,
        },
    }
    gates = {
        "calibration_requirements": calibration_eligible,
        "permission_and_version_filter": summary.safety_violation_count == 0,
        "no_held_out_false_answers": summary.false_answer_count == 0,
        "no_evidence_accuracy": summary.no_evidence_accuracy == 1.0,
    }
    return {
        "candidate": summary.candidate,
        "eligible": all(metric["passed"] for metric in metrics.values())
        and all(gates.values()),
        "metrics": metrics,
        "hard_gates": gates,
    }


def _decide(summaries, control, calibration_eligibility) -> dict:
    assessments = [
        _assessment(summary, control, calibration_eligible)
        for summary, calibration_eligible in zip(
            summaries,
            calibration_eligibility,
            strict=True,
        )
    ]
    eligible = [
        summary
        for summary, assessment in zip(summaries[1:], assessments[1:], strict=True)
        if assessment["eligible"]
    ]
    if not eligible:
        return {
            "outcome": "refine",
            "selected_candidate": None,
            "retained_fallback": "bm25-v1-with-any-hit-control",
            "rationale": "No candidate passed every held-out answerability, abstention, ranking, safety, and latency requirement.",
        }
    selected = max(
        eligible,
        key=lambda summary: (
            summary.balanced_accuracy,
            summary.answerable_recall,
            summary.unconditional_recall_at_3,
            summary.unconditional_ndcg_at_3,
            -summary.mean_gate_latency_ms,
        ),
    )
    return {
        "outcome": "refine",
        "selected_candidate": selected.candidate,
        "retained_fallback": "bm25-v1-with-any-hit-control",
        "rationale": "The selected evidence gate passed every held-out gate while preserving the predeclared ranking tolerance; BM25 ranking remains provisional and separately subject to refinement.",
    }


def _compact(payload: dict) -> dict:
    compact = dict(payload)
    if "test" in compact:
        test = dict(compact["test"])
        test["results"] = [
            {
                key: value
                for key, value in result.items()
                if key not in {"decisions", "retrieval"}
            }
            for result in test["results"]
        ]
        compact["test"] = test
    return compact


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--calibration", type=Path, default=DEFAULT_CALIBRATION)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--calibration-only", action="store_true")
    parser.add_argument(
        "--raw-thresholds",
        type=_float_tuple,
        default=DEFAULT_RAW_THRESHOLDS,
    )
    parser.add_argument(
        "--coverage-thresholds",
        type=_float_tuple,
        default=DEFAULT_COVERAGE_THRESHOLDS,
    )
    parser.add_argument(
        "--matching-terms",
        type=_int_tuple,
        default=DEFAULT_MATCHING_TERMS,
    )
    parser.add_argument(
        "--semantic-thresholds",
        type=_float_tuple,
        default=DEFAULT_SEMANTIC_THRESHOLDS,
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--local-files-only", action="store_true")
    return parser.parse_args()


def _float_tuple(value: str) -> tuple[float, ...]:
    values = tuple(float(item) for item in value.split(","))
    if not values or any(item < 0 for item in values):
        raise argparse.ArgumentTypeError("thresholds must be nonnegative")
    return values


def _int_tuple(value: str) -> tuple[int, ...]:
    values = tuple(int(item) for item in value.split(","))
    if not values or any(item < 1 for item in values):
        raise argparse.ArgumentTypeError("matching terms must be positive integers")
    return values


def _validate_versions(corpus: str, *datasets: str) -> None:
    if any(dataset != corpus for dataset in datasets):
        raise SystemExit("corpus version mismatch")


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


if __name__ == "__main__":
    main()
