import copy

import pytest

from scripts.analyze_professor_fidelity import analyze
from scripts.build_course_tutor_splits import build_case
from scripts.execute_professor_fidelity import _parse_output, _score
from scripts.finalize_professor_fidelity_blinded_review import finalize_review
from scripts.judge_professor_fidelity import (
    _judgment_schema,
    _model_digest,
    _pair_mapping,
    _validate_judgment,
)
from scripts.professor_fidelity_scoring import score_response
from scripts.run_professor_fidelity_experiment import (
    ProfessorFidelityPlanError,
    build_preflight_manifest,
    load_instrument,
)


def _case(case_id: str, *, scenario: str = "direct") -> dict:
    answerable = scenario == "direct"
    claims = (
        [
            {
                "claim_id": "clm-01",
                "claim_text": "The register has a fixed width",
                "severity": "high",
                "evidence_unit_ids": ["ev-01"],
                "must_be_cited": True,
            }
        ]
        if answerable
        else []
    )
    evidence = (
        [
            {
                "evidence_unit_id": "ev-01",
                "source_artifact_id": "lecture-01",
                "source_version": "1.0.0",
                "passage_id": "lecture-01-page-001",
                "locator": "Lecture 1, page 1",
                "content_sha256": "0" * 64,
                "role": "essential",
                "permission_status": "approved",
                "supports_claim_ids": ["clm-01"],
                "replacement_passage_id": None,
            }
        ]
        if answerable
        else []
    )
    action = "answer" if answerable else "clarify"
    return {
        "case_id": case_id,
        "scenario_type": scenario,
        "student_input": {
            "question": "Explain the register.",
            "dialogue_history": [],
            "student_state": {"assessment_context": "unassessed"},
        },
        "ground_truth": {
            "corpus_answerability": "answerable" if answerable else "partially_answerable",
            "expected_behavior": {
                "primary_action": action,
                "acceptable_alternatives": [],
                "citation_requirement": "required" if answerable else "not_required",
                "required_tutoring_moves": ["direct_explanation"],
                "forbidden_actions": ["abstain"],
                "allowed_support_level": "full_explanation",
            },
            "required_claims": claims,
            "evidence_units": evidence,
        },
        "rubric": {
            "required_pedagogy_dimensions": ["clarity_and_coherence"],
        },
    }


def _hit(*, correct: bool = True) -> dict:
    return {
        "chunk_id": "chunk-1",
        "source_id": "lecture-01" if correct else "lecture-99",
        "locator": "Lecture 1, page 1" if correct else "Lecture 99, page 9",
        "page": 1 if correct else 9,
        "source_version": 1,
        "score": 1.0,
    }


def test_professor_fidelity_instrument_is_frozen_with_four_conditions():
    instrument = load_instrument()

    assert instrument["status"] == "frozen-preflight"
    assert [condition["condition_id"] for condition in instrument["conditions"]] == [
        "C0",
        "C1",
        "C2",
        "C3",
    ]
    assert instrument["generator_binding"]["status"] == "qualified-selected"
    assert instrument["analysis"]["human_outcome_claims_allowed"] is False


def test_professor_fidelity_preflight_manifest_excludes_private_text():
    instrument = load_instrument()

    manifest = build_preflight_manifest(instrument)

    assert manifest["execution_enabled"] is False
    assert manifest["private_text_emitted"] is False
    assert manifest["dataset"] is None
    assert manifest["blocked_reasons"]
    assert not any("course-tutor-v1" in reason for reason in manifest["blocked_reasons"])
    assert manifest["generator_qualification"]["status"] == "qualified-selected"
    assert manifest["generator_qualification"]["candidate_binding"] == (
        "litellm-deepseek-v4-flash-nonthinking-v1"
    )
    assert manifest["prompt_binding"]["implementation_id"] == (
        "strict-evidence-grounded-prompt-v3"
    )
    assert manifest["generator_qualification"]["credential_value_emitted"] is False


def test_professor_fidelity_instrument_rejects_condition_drift():
    instrument = load_instrument()
    instrument["conditions"][0]["condition_id"] = "C9"

    with pytest.raises(ProfessorFidelityPlanError, match="ordered"):
        from scripts.run_professor_fidelity_experiment import _validate_instrument

        _validate_instrument(instrument)


def test_professor_fidelity_output_requires_string_citation_ids():
    parsed = _parse_output(
        '{"answer":"Use the approved source.","citation_ids":["S1"],"action":"answer"}'
    )
    assert parsed["action"] == "answer"

    with pytest.raises(ValueError, match="keys drifted"):
        _parse_output('{"answer":"x","citation_ids":[],"action":"answer","extra":1}')
    with pytest.raises(ValueError, match="must be strings"):
        _parse_output('{"answer":"x","citation_ids":[1],"action":"answer"}')


def test_scoring_separates_id_source_completeness_and_semantics():
    case = _case("case-01")
    paraphrased = {
        "answer": "Every register uses the same number of bits.",
        "citation_ids": ["S1"],
        "action": "answer",
    }

    score = score_response(case, paraphrased, [_hit(correct=True)])

    assert score["citation_identity_validity"] is True
    assert score["citation_source_correctness"] is True
    assert score["citation_completeness"] is True
    assert score["exact_phrase_claim_recall_diagnostic"] == 0.0
    assert score["semantic_support_resolved"] is False
    assert score["safe_grounded_success"] is None

    wrong_source = score_response(case, paraphrased, [_hit(correct=False)])
    assert wrong_source["citation_identity_validity"] is True
    assert wrong_source["citation_source_correctness"] is False
    assert wrong_source["citation_completeness"] is False


def test_complete_evidence_excludes_cases_without_essential_evidence():
    case = _case("case-02", scenario="ambiguity")
    score = score_response(
        case,
        {"answer": "Which topic do you mean?", "citation_ids": [], "action": "clarify"},
        [],
    )

    assert score["complete_evidence_eligible"] is False
    assert score["complete_evidence_at_3"] is None


def test_legacy_score_wrapper_uses_corrected_structural_scoring():
    case = _case("case-03")
    score = _score(
        case,
        "C1",
        {"answer": "Unsupported.", "citation_ids": [], "action": "answer"},
        [],
    )

    assert score["deterministic_structural_success"] is False
    assert score["citation_identity_validity"] is False
    assert score["safe_grounded_success"] is None


def test_professor_fidelity_judge_records_ollama_digest(monkeypatch):
    monkeypatch.setattr(
        "scripts.judge_professor_fidelity.subprocess_run",
        lambda command: "NAME ID SIZE MODIFIED\ngemma3:4b a2af6cc3eb7f 3.3 GB now\n",
    )

    assert _model_digest("gemma3:4b") == "a2af6cc3eb7f"


def test_judge_contract_requires_per_dimension_pairwise_output():
    task_id = "judge-case-01-pair"
    dimensions = ["clarity_and_coherence", "tone_and_respect"]
    schema = _judgment_schema(task_id=task_id, mode="pairwise", dimensions=dimensions)
    value = {
        "schema_version": "1.0.0",
        "instrument_id": "llm-judge-v1",
        "task_id": task_id,
        "mode": "pairwise",
        "single_judgments": None,
        "pairwise_judgments": [
            {
                "dimension": dimension,
                "preference": "A",
                "evidence_quote_a": "clear",
                "evidence_quote_b": "less clear",
                "reason": "A is more actionable.",
            }
            for dimension in dimensions
        ],
    }

    assert schema["properties"]["pairwise_judgments"]["minItems"] == 2
    _validate_judgment(value, task_id=task_id, mode="pairwise", dimensions=dimensions)
    assert _pair_mapping(False) == {"A": "C1", "B": "C2"}
    assert _pair_mapping(True) == {"A": "C2", "B": "C1"}


def test_analysis_uses_eligible_denominators_and_complete_evidence_gate():
    cases = [_case(f"case-{index:02d}") for index in range(10)]
    results = []
    judgments = []
    for case_index, case in enumerate(cases):
        for condition in ("C0", "C1", "C2", "C3"):
            has_evidence = condition in {"C1", "C2"} or (
                condition == "C3" and case_index < 7
            )
            results.append(
                {
                    "case_id": case["case_id"],
                    "scenario_type": "direct",
                    "condition": condition,
                    "status": "completed",
                    "latency_ms": 100,
                    "answer": "Every register uses the same number of bits.",
                    "citation_ids": ["S1"] if has_evidence else [],
                    "retrieved": [_hit(correct=True)] if has_evidence else [],
                    "score": {"actual_action": "answer"},
                }
            )
            judgments.append(
                {
                    "case_id": case["case_id"],
                    "condition": condition,
                    "required_claim_expression": True,
                    "supported_claim_precision": True,
                    "citation_semantic_alignment": True,
                    "pedagogy_dimensions": [
                        {"dimension": "clarity_and_coherence", "label": "pass"}
                    ],
                }
            )
    run = {
        "run_id": "synthetic-run",
        "dataset_sha256": "a" * 64,
        "case_count": 10,
        "condition_attempts": 40,
        "completed_attempts": 40,
        "requested_attempts": 40,
        "cost_usd": 0.01,
        "input_tokens": 100,
        "output_tokens": 100,
        "latency_p50_ms": 100,
        "latency_p95_ms": 100,
        "provider_model": "synthetic",
        "provider_revision": "synthetic",
        "retrieval": "synthetic",
        "code_revision": "synthetic",
        "results": results,
    }
    review = {
        "schema_version": "1.0.0",
        "review_id": "review-1",
        "source_run_id": "synthetic-run",
        "dataset_sha256": "a" * 64,
        "status": "complete",
        "reviewed_at": "2026-08-10T12:00:00+00:00",
        "reviewer": {
            "reviewer_id": "researcher-1",
            "role": "researcher",
            "blinded_to_conditions": True,
            "independent_human_review": False,
        },
        "judgments": judgments,
    }

    result = analyze(run, {"cases": cases}, review=review)

    c3 = result["condition_summaries"]["C3"]
    assert c3["complete_evidence_at_3"]["passed"] == 7
    assert c3["complete_evidence_at_3"]["applicable"] == 10
    assert c3["complete_evidence_at_3"]["value"] == 0.7
    assert c3["citation_source_correctness"]["value"] == 0.7
    assert result["decision_gates"]["c3_complete_evidence_at_3_at_least_0_80"] is False
    assert result["decision"] == "refine"
    assert result["representative_failures"]
    assert "answer" not in result["representative_failures"][0]


def test_blinded_review_finalizer_resolves_hidden_conditions():
    mapping = {
        "source_run_id": "run-1",
        "dataset_sha256": "a" * 64,
        "assignments": [
            {
                "task_id": "review-case-a",
                "case_id": "case-a",
                "response_label": "A",
                "condition": "C2",
            }
        ],
    }
    template = {
        "review_id": "review-1",
        "source_run_id": "run-1",
        "dataset_sha256": "a" * 64,
        "status": "complete",
        "reviewed_at": "2026-08-10T12:00:00+00:00",
        "reviewer": {
            "reviewer_id": "researcher-1",
            "role": "researcher",
            "blinded_to_conditions": True,
            "independent_human_review": False,
        },
        "judgments": [
            {
                "task_id": "review-case-a",
                "case_id": "case-a",
                "response_label": "A",
                "required_claim_expression": True,
                "supported_claim_precision": True,
                "citation_semantic_alignment": True,
                "pedagogy_dimensions": [
                    {"dimension": "clarity_and_coherence", "label": "pass"}
                ],
            }
        ],
    }

    result = finalize_review(template, mapping)

    assert result["judgments"][0]["condition"] == "C2"
    assert "task_id" not in result["judgments"][0]


def test_course_tutor_builder_does_not_claim_human_double_review(monkeypatch):
    monkeypatch.setattr(
        "scripts.build_course_tutor_splits.source_rows",
        lambda base, manifest: [
            {
                "evidence_unit_id": "ev-01",
                "source_artifact_id": "lecture-01",
                "source_version": "1.0.0",
                "passage_id": "passage-01",
                "locator": "Lecture 1, page 1",
                "content_sha256": "0" * 64,
                "role": "essential",
                "permission_status": "approved",
                "supports_claim_ids": [],
                "replacement_passage_id": None,
            }
        ],
    )
    manifest = {
        "topic_strata": [{"id": "topic-1", "documents": ["lecture-01"]}],
    }
    base = {
        "case_id": "source-1",
        "lecture_id": "lecture-01",
        "query": "What is the register width?",
        "claims": ["The register has a fixed width"],
        "required_evidence": [{"document_id": "lecture-01", "page": 1}],
    }

    case, _ = build_case(
        split="development",
        ordinal=1,
        scenario="direct",
        base=copy.deepcopy(base),
        manifest=manifest,
    )

    assert case["annotation"]["status"] == "draft"
    assert case["annotation"]["professor_decision"] == "pending"
