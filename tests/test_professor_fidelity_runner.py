import copy
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from openai import APITimeoutError

from scripts.analyze_professor_fidelity import analyze
from scripts.build_course_tutor_splits import (
    build_case,
    curate_source_case,
    question_for,
    validate_split_isolation,
)
from scripts.execute_professor_fidelity import (
    V4_PRO_EXPECTED_FINGERPRINT,
    _generator_runtime,
    _messages,
    _parse_output,
    _score,
    _v4_pro_cost,
)
from scripts.finalize_professor_fidelity_blinded_review import finalize_review
from scripts.judge_professor_fidelity import (
    DEEPSEEK_EXPECTED_FINGERPRINT,
    JUDGE_MODELS,
    SAMPLE_SELECTION_SALT,
    JudgeTransport,
    _selected,
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
from scripts.run_course_tutor_hybrid_review import (
    DEEPSEEK_PUBLIC_PROBE_COUNT,
    ENSEMBLE_ID,
    HUMAN_AUDIT_ID,
    MAX_HUMAN_CASES,
    MODEL_BINDINGS,
    PLAN_ID,
    SAMPLE_SEED,
    _summary,
    call_deepseek,
    required_human_case_ids,
    review_prompt,
    selection_commitment_sha256,
    select_baseline_case_ids,
    validate_model_decision,
)
from scripts.seal_course_tutor_splits import (
    REQUIRED_REVIEW_CHECKS,
    seal_splits,
    validate_hybrid_reviews,
)
from scripts.validate_professor_fidelity_post_audit import (
    validate as validate_post_audit_pipeline,
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
            "corpus_answerability": "answerable"
            if answerable
            else "partially_answerable",
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
        "chunk_id": "lecture-01-page-001" if correct else "chunk-wrong",
        "passage_id": "lecture-01-page-001" if correct else "lecture-99-page-009",
        "content_sha256": "0" * 64 if correct else "9" * 64,
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
    assert manifest["selection_blockers"]
    assert not any(
        "course-tutor-v1" in reason for reason in manifest["selection_blockers"]
    )
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


def test_professor_policy_prompt_never_receives_case_gold_labels():
    case = _case("case-policy")
    case["ground_truth"]["expected_behavior"].update(
        {
            "primary_action": "gold-action-must-stay-hidden",
            "required_tutoring_moves": ["gold-move-must-stay-hidden"],
            "forbidden_actions": ["gold-forbidden-must-stay-hidden"],
        }
    )
    bindings = {
        "generic_tutoring_policy": {"policy_id": "generic"},
        "structured_professor_policy": {"policy_id": "professor"},
    }

    serialized = "\n".join(
        message.content for message in _messages(case, "C2", [], bindings)
    )

    assert "gold-action-must-stay-hidden" not in serialized
    assert "gold-move-must-stay-hidden" not in serialized
    assert "gold-forbidden-must-stay-hidden" not in serialized
    assert '"policy_id": "professor"' in serialized


def test_p3_prompt_requires_clarification_before_explanation_and_hides_gold():
    case = _case("case-p3", scenario="ambiguity")
    case["ground_truth"]["expected_behavior"]["primary_action"] = (
        "gold-action-must-stay-hidden"
    )
    bindings = {
        "generic_tutoring_policy": {"policy_id": "generic"},
        "structured_professor_policy": {"policy_id": "professor"},
    }

    serialized = "\n".join(
        message.content
        for message in _messages(
            case,
            "C2",
            [],
            bindings,
            prompt_binding_id="professor-fidelity-integration-prompt-v3-p3",
        )
    )

    assert "do not explain either meaning yet" in serialized
    assert "Which meaning" in serialized
    assert "gold-action-must-stay-hidden" not in serialized


def test_v4_pro_anchor_runtime_is_exact_and_uses_manual_cost():
    runtime = _generator_runtime(
        {
            "generator": {
                "provider_model": "deepseek-v4-pro",
                "provider_revision": V4_PRO_EXPECTED_FINGERPRINT,
                "thinking": "disabled",
                "temperature": 0,
                "max_output_tokens": 1200,
                "timeout_seconds": 60,
            }
        }
    )

    assert runtime["provider_model"] == "deepseek-v4-pro"
    assert runtime["litellm_model"] == "deepseek/deepseek-v4-pro"
    assert runtime["expected_fingerprint"] == V4_PRO_EXPECTED_FINGERPRINT
    assert runtime["thinking"] is False
    assert runtime["cost_calculator"] is _v4_pro_cost
    assert _v4_pro_cost(
        completion_response={
            "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
        }
    ) == pytest.approx(1.305)


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
    assert score["citation_claim_source_coverage"] is True
    assert score["citation_completeness"] is None
    assert score["exact_phrase_claim_recall_diagnostic"] == 0.0
    assert score["semantic_support_resolved"] is False
    assert score["safe_grounded_success"] is None

    wrong_source = score_response(case, paraphrased, [_hit(correct=False)])
    assert wrong_source["citation_identity_validity"] is True
    assert wrong_source["citation_source_correctness"] is False
    assert wrong_source["citation_claim_source_coverage"] is False
    assert wrong_source["citation_completeness"] is None


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


def test_professor_fidelity_judge_records_qwen_digest(monkeypatch):
    monkeypatch.setattr(
        "scripts.judge_professor_fidelity.subprocess_run",
        lambda command: "NAME ID SIZE MODIFIED\nqwen3:4b 359d7dd4bcda 2.5 GB now\n",
    )

    assert _model_digest("qwen3:4b") == "359d7dd4bcda"
    assert JUDGE_MODELS == ("deepseek-v4-pro", "qwen3:4b")


def test_professor_fidelity_judge_uses_deepseek_v4_pro_json_thinking():
    captured = {}
    task_id = "judge-case-01-single"
    dimensions = ["clarity_and_coherence"]

    class Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                model="deepseek-v4-pro",
                system_fingerprint=DEEPSEEK_EXPECTED_FINGERPRINT,
                usage=SimpleNamespace(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    completion_tokens_details=SimpleNamespace(reasoning_tokens=40),
                ),
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content=(
                                '{"schema_version":"1.0.0",'
                                '"instrument_id":"llm-judge-v1",'
                                f'"task_id":"{task_id}",'
                                '"mode":"single",'
                                '"single_judgments":[{'
                                '"dimension":"clarity_and_coherence",'
                                '"label":"pass",'
                                '"evidence_quote":"clear",'
                                '"reason":"The response is clear."}],'
                                '"pairwise_judgments":null}'
                            )
                        ),
                    )
                ],
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    transport = JudgeTransport(
        "deepseek-v4-pro",
        split="development",
        call_limit=2,
        cost_stop_usd=1,
        deepseek_client=client,
    )
    schema = _judgment_schema(
        task_id=task_id,
        mode="single",
        dimensions=dimensions,
    )
    value = transport.call(
        prompt="Return JSON.",
        schema=schema,
        seed=5002,
        task_id=task_id,
    )

    _validate_judgment(
        value,
        task_id=task_id,
        mode="single",
        dimensions=dimensions,
    )
    assert captured["model"] == "deepseek-v4-pro"
    assert captured["max_tokens"] == 8192
    assert captured["reasoning_effort"] == "high"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["extra_body"]["thinking"] == {"type": "enabled"}
    assert transport.summary()["reasoning_tokens"] == 40


def test_active_professor_fidelity_commands_exclude_gemma():
    root = Path(__file__).resolve().parents[1]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    commands = {
        name: command
        for name, command in package["scripts"].items()
        if name.startswith("judge:professor-fidelity")
    }

    assert commands
    assert all("gemma" not in command.casefold() for command in commands.values())
    assert "--model deepseek-v4-pro" in commands["judge:professor-fidelity-development"]
    assert "--model deepseek-v4-pro" in commands["judge:professor-fidelity-heldout"]


def test_active_anchor_commands_use_new_run_and_never_invalid_run():
    root = Path(__file__).resolve().parents[1]
    package = json.loads((root / "package.json").read_text(encoding="utf-8"))
    commands = {
        name: command
        for name, command in package["scripts"].items()
        if "professor-fidelity-anchor" in name
    }

    assert commands
    assert all("anchor-002" in command for command in commands.values())
    assert all("anchor-001" not in command for command in commands.values())


def test_professor_fidelity_judge_sensitivity_uses_one_shared_sample():
    case_ids = [f"case-{index:03d}" for index in range(104)]
    selected = [
        case_id
        for case_id in case_ids
        if _selected(case_id, 0.25, SAMPLE_SELECTION_SALT)
    ]

    assert 15 <= len(selected) <= 35
    assert selected == [
        case_id
        for case_id in case_ids
        if _selected(case_id, 0.25, SAMPLE_SELECTION_SALT)
    ]


def test_post_audit_pipeline_preflight_is_non_executing_and_fail_closed():
    result = validate_post_audit_pipeline()

    assert result["status"] == "passed"
    assert result["execution_status"] == (
        "anchor-ready-development-blocked-by-independent-human-authoring-audit"
    )
    assert result["active_anchor"]["run_id"] == "professor-fidelity-v2-anchor-002"
    assert result["active_anchor"]["selection_status"] == "not-selected"
    assert result["active_primary_judge"]["model"] == "deepseek-v4-pro"
    assert result["active_gemma_calls"] == 0
    assert result["private_artifact_content_read"] is False
    assert result["heldout_content_read"] is False
    assert result["model_called"] is False


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
                    "citation_completeness": True,
                    "presented_evidence_completeness": True,
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
    assert result["decision_gates"]["selected_retrieval_and_chunker_identity"] is False
    assert result["decision_gates"]["condition_set_hash_bound"] is False
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
                "citation_completeness": True,
                "presented_evidence_completeness": True,
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
        chunks_by_id={},
    )

    assert case["annotation"]["status"] == "draft"
    assert case["annotation"]["professor_decision"] == "pending"


def test_course_tutor_builder_rebinds_invalid_source_evidence_and_claim():
    source = {
        "case_id": "private-source-case",
        "family_id": "private-source-family",
        "lecture_id": "private-document",
        "query": "Original private question?",
        "claims": ["Original private claim."],
        "required_evidence": [],
    }
    chunk = SimpleNamespace(
        id="chunk-page-8",
        document_id="private-document",
        page_start=8,
        content_hash="1" * 64,
    )

    private_blueprint = {
        "curated_source_rewrites": {
            source["case_id"]: {
                "query": "Re-authored private question?",
                "claims": ["Re-authored private claim."],
            }
        },
        "curated_evidence_pages": {source["case_id"]: [8]},
    }

    curated = curate_source_case(source, {chunk.id: chunk}, private_blueprint)

    assert curated["claims"] == ["Re-authored private claim."]
    assert curated["required_evidence"] == [
        {
            "document_id": "private-document",
            "page": 8,
            "chunk_id": "chunk-page-8",
            "content_hash": "1" * 64,
        }
    ]


def test_course_tutor_builder_uses_authentic_misconception_and_ambiguity():
    misconception_base = {
        "case_id": "private-misconception-source",
        "lecture_id": "private-document-a",
        "query": "What is the approved concept?",
    }
    ambiguity_base = {
        "case_id": "private-ambiguity-source",
        "lecture_id": "private-document-b",
        "query": "Which private concept applies?",
    }

    private_blueprint = {
        "misconception_questions": {
            misconception_base["case_id"]: (
                "I think the source says the opposite of the approved concept. "
                "Is that right?"
            )
        },
        "ambiguity_questions": {
            ambiguity_base["case_id"]: (
                "The concept slide in Lecture 8 is unclear. Which detail should "
                "I identify first?"
            )
        },
    }

    misconception = question_for(
        "misconception", misconception_base, 1, private_blueprint
    )
    ambiguity = question_for("ambiguity", ambiguity_base, 1, private_blueprint)

    assert "opposite" in misconception
    assert "cannot be the right idea here" not in misconception
    assert "Lecture 8" in ambiguity
    assert "concept slide" in ambiguity


def test_course_tutor_builder_rejects_cross_split_passage_overlap():
    def dataset(split, passage_id):
        return {
            "cases": [
                {
                    "lineage": {"case_family_id": f"family-{split}"},
                    "ground_truth": {
                        "evidence_units": [
                            {
                                "passage_id": passage_id,
                                "permission_status": "approved",
                            }
                        ]
                    },
                }
            ]
        }

    with pytest.raises(ValueError, match="share approved passages"):
        validate_split_isolation(
            dataset("development", "same-passage"),
            dataset("heldout", "same-passage"),
        )


def _hybrid_test_datasets() -> dict:
    datasets = {}
    for split in ("development", "heldout"):
        cases = []
        for scenario in (
            "ambiguity",
            "assessed_work",
            "direct",
            "misconception",
            "multi_evidence",
            "no_evidence",
            "paraphrase",
            "permission_version",
        ):
            for ordinal in range(3):
                cases.append(
                    {
                        "case_id": f"{split}-{scenario}-{ordinal}",
                        "split": split,
                        "scenario_type": scenario,
                    }
                )
        datasets[split] = {"cases": cases}
    return datasets


def test_course_tutor_hybrid_baseline_is_one_case_per_stratum():
    datasets = _hybrid_test_datasets()
    selected = select_baseline_case_ids(datasets)

    assert len(selected) == 16
    selected_cases = {
        case["case_id"]: case
        for dataset in datasets.values()
        for case in dataset["cases"]
    }
    strata = {}
    for case_id in selected:
        case = selected_cases[case_id]
        key = (case["split"], case["scenario_type"])
        strata[key] = strata.get(key, 0) + 1
    assert set(strata.values()) == {1}


def test_course_tutor_v6_uses_deepseek_v4_pro_and_excludes_gemma():
    assert MODEL_BINDINGS[0]["model"] == "deepseek-v4-pro"
    assert MODEL_BINDINGS[0]["documented_revision"] == "DeepSeek-V4-Pro-0813"
    assert MODEL_BINDINGS[0]["thinking"] is True
    assert MODEL_BINDINGS[0]["reasoning_effort"] == "high"
    assert not any("gemma" in binding["model"].casefold() for binding in MODEL_BINDINGS)


def test_course_tutor_v6_calls_official_deepseek_json_thinking_transport():
    captured = {}

    class Completions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                model="deepseek-v4-pro",
                system_fingerprint="fp-v4-pro-synthetic",
                usage=SimpleNamespace(
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    completion_tokens_details=SimpleNamespace(reasoning_tokens=40),
                ),
                choices=[
                    SimpleNamespace(
                        finish_reason="stop",
                        message=SimpleNamespace(
                            content=(
                                '{"decision":"approve",'
                                '"question_authentic_and_synthetic":true,'
                                '"expected_behavior_correct":true,'
                                '"claims_atomic_and_correct":true,'
                                '"evidence_supports_claims":true,'
                                '"permission_and_version_correct":true,'
                                '"split_assignment_acceptable":true,'
                                '"reason":"All six checks pass."}'
                            )
                        ),
                    )
                ],
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    result = call_deepseek(
        client=client,
        prompt="Return JSON.",
        expected_revision="fp-v4-pro-synthetic",
    )

    assert result["status"] == "valid"
    assert captured["model"] == "deepseek-v4-pro"
    assert captured["max_tokens"] == 8192
    assert captured["reasoning_effort"] == "high"
    assert captured["response_format"] == {"type": "json_object"}
    assert captured["extra_body"]["thinking"] == {"type": "enabled"}
    assert result["finish_reason"] == "stop"
    assert result["usage"]["reasoning_tokens"] == 40


def test_course_tutor_v6_treats_deepseek_timeout_as_retryable():
    class Completions:
        def create(self, **kwargs):
            del kwargs
            raise APITimeoutError(
                request=httpx.Request(
                    "POST", "https://api.deepseek.com/chat/completions"
                )
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    result = call_deepseek(
        client=client,
        prompt="Return JSON.",
        expected_revision="fp-v4-pro-synthetic",
    )

    assert result["status"] == "invalid"
    assert result["failure_class"] == "transient_provider_error"
    assert result["retryable"] is True
    assert result["hard_stop"] is False
    assert result["elapsed_seconds"] >= 0


def test_course_tutor_v6_declares_frozen_split_aliases():
    prompt = review_prompt(
        {
            "scenario_type": "direct",
            "case_id": "synthetic",
        }
    )

    assert "development=dev and heldout=test" in prompt
    assert "development/test or heldout/dev mismatch fails" in prompt


def test_course_tutor_model_decision_requires_consistent_checks():
    decision = {
        "decision": "approve",
        **{check: True for check in REQUIRED_REVIEW_CHECKS},
        "reason": "All six checks pass.",
    }
    assert validate_model_decision(decision) == decision

    decision["evidence_supports_claims"] = False
    with pytest.raises(ValueError, match="inconsistent"):
        validate_model_decision(decision)


def test_course_tutor_summary_counts_invalid_null_decision():
    rows = []
    for index, binding in enumerate(MODEL_BINDINGS):
        valid = index != 0
        rows.append(
            {
                "reviewer_id": binding["reviewer_id"],
                "endpoint_class": binding["endpoint_class"],
                "case_id": "synthetic-case",
                "status": "valid" if valid else "invalid",
                "decision": ({"decision": "approve"} if valid else None),
                "attempts": ([{}] if binding["endpoint_class"] == "external" else []),
            }
        )

    summary = _summary(
        rows,
        [],
        ["synthetic-case"],
        {"synthetic-case": ["deepseek_not_approve"]},
    )

    assert summary["valid_model_decisions"] == 2
    assert summary["invalid_model_decisions"] == 1
    assert summary["by_reviewer"][MODEL_BINDINGS[0]["reviewer_id"]]["invalid"] == 1


def test_course_tutor_v6_escalates_by_two_family_quorum():
    rows = [
        {
            "case_id": "case-1",
            "scenario_type": "direct",
            "endpoint_class": "external",
            "status": "valid",
            "decision": {"decision": "approve"},
        },
        {
            "case_id": "case-1",
            "scenario_type": "direct",
            "endpoint_class": "local",
            "status": "valid",
            "decision": {"decision": "approve"},
        },
        {
            "case_id": "case-1",
            "scenario_type": "direct",
            "endpoint_class": "local",
            "status": "valid",
            "decision": {"decision": "revise"},
        },
    ]

    required, _ = required_human_case_ids(rows, [])
    assert required == []

    rows[1]["decision"]["decision"] = "revise"
    required, reasons = required_human_case_ids(rows, [])
    assert required == ["case-1"]
    assert reasons["case-1"] == ["no_local_family_approve"]

    rows[0]["decision"]["decision"] = "revise"
    rows[1]["decision"]["decision"] = "approve"
    required, reasons = required_human_case_ids(rows, [])
    assert required == ["case-1"]
    assert reasons["case-1"] == ["deepseek_not_approve"]


def test_course_tutor_seal_requires_github_purge_confirmation(tmp_path):
    with pytest.raises(ValueError, match="GitHub Support purge confirmation"):
        seal_splits(
            tmp_path / "draft",
            tmp_path / "sealed",
            tmp_path / "ensemble.json",
            tmp_path / "audit.json",
            github_purge_confirmed=False,
        )


def test_course_tutor_seal_validates_hybrid_ensemble_and_human_audit():
    datasets = _hybrid_test_datasets()
    draft_hashes = {
        "development": {
            "dataset_sha256": "a" * 64,
            "conditions_sha256": "b" * 64,
        },
        "heldout": {
            "dataset_sha256": "c" * 64,
            "conditions_sha256": "d" * 64,
        },
    }
    model_decisions = []
    for binding in MODEL_BINDINGS:
        for dataset in datasets.values():
            for case in dataset["cases"]:
                model_decisions.append(
                    {
                        "reviewer_id": binding["reviewer_id"],
                        "model": binding["model"],
                        "model_digest": binding["digest"],
                        "documented_revision": binding["documented_revision"],
                        "family": binding["family"],
                        "endpoint_class": binding["endpoint_class"],
                        "thinking": binding["thinking"],
                        "reasoning_effort": binding["reasoning_effort"],
                        "case_id": case["case_id"],
                        "split": case["split"],
                        "scenario_type": case["scenario_type"],
                        "status": "valid",
                        "decision": {
                            "decision": "approve",
                            **{check: True for check in REQUIRED_REVIEW_CHECKS},
                            "reason": "All six checks pass.",
                        },
                        **(
                            {
                                "provider_model": "deepseek-v4-pro",
                                "provider_revision": "fp-v4-pro-synthetic",
                                "provider_identity_source": "response",
                                "finish_reason": "stop",
                                "usage": {
                                    "approximate_cost_usd": 0.00001,
                                    "reasoning_tokens": 10,
                                },
                                "attempts": [
                                    {
                                        "status": "valid",
                                        "decision": {
                                            "decision": "approve",
                                            **{
                                                check: True
                                                for check in REQUIRED_REVIEW_CHECKS
                                            },
                                            "reason": "All six checks pass.",
                                        },
                                        "provider_model": "deepseek-v4-pro",
                                        "provider_revision": "fp-v4-pro-synthetic",
                                        "finish_reason": "stop",
                                        "usage": {
                                            "approximate_cost_usd": 0.00001,
                                            "reasoning_tokens": 10,
                                        },
                                        "hard_stop": False,
                                    }
                                ],
                            }
                            if binding["endpoint_class"] == "external"
                            else {}
                        ),
                    }
                )
    baseline = select_baseline_case_ids(datasets)
    required, reasons = required_human_case_ids(model_decisions, baseline)
    assert len(required) == 20
    assert (
        sum(
            "mandatory_no_evidence_census" in case_reasons
            for case_reasons in reasons.values()
        )
        == 6
    )
    transport_preflights = []
    for binding in MODEL_BINDINGS:
        probe_indexes = (
            range(1, DEEPSEEK_PUBLIC_PROBE_COUNT + 1)
            if binding["endpoint_class"] == "external"
            else (None,)
        )
        for probe_index in probe_indexes:
            transport_preflights.append(
                {
                    "reviewer_id": binding["reviewer_id"],
                    "model": binding["model"],
                    "model_digest": binding["digest"],
                    "documented_revision": binding["documented_revision"],
                    "family": binding["family"],
                    "endpoint_class": binding["endpoint_class"],
                    "thinking": binding["thinking"],
                    "reasoning_effort": binding["reasoning_effort"],
                    "probe_index": probe_index,
                    "private_data_used": False,
                    "status": "valid",
                    "decision": {
                        "decision": "approve",
                        **{check: True for check in REQUIRED_REVIEW_CHECKS},
                        "reason": "Synthetic transport preflight passes.",
                    },
                    **(
                        {
                            "provider_model": "deepseek-v4-pro",
                            "provider_revision": "fp-v4-pro-synthetic",
                            "finish_reason": "stop",
                            "usage": {
                                "approximate_cost_usd": 0.00001,
                                "reasoning_tokens": 10,
                            },
                            "retryable": False,
                            "hard_stop": False,
                        }
                        if binding["endpoint_class"] == "external"
                        else {}
                    ),
                }
            )
    ensemble = {
        "plan_id": PLAN_ID,
        "ensemble_id": ENSEMBLE_ID,
        "ensemble_status": "complete",
        "protocol_status": "awaiting_human_audit",
        "sample_seed": SAMPLE_SEED,
        "draft_hashes": draft_hashes,
        "models": list(MODEL_BINDINGS),
        "local_only": False,
        "external_provider_calls": 58,
        "external_provider_cost_usd": 0.00058,
        "external_provider_revision": "fp-v4-pro-synthetic",
        "created_at": "2026-08-14T09:00:00+07:00",
        "code": {"revision": "e" * 40, "dirty": False},
        "transport_preflights": transport_preflights,
        "selection": {
            "baseline_case_ids": baseline,
            "required_human_case_ids": required,
            "escalation_reasons": reasons,
            "maximum_human_cases": MAX_HUMAN_CASES,
        },
        "model_decisions": model_decisions,
    }
    decisions = [
        {
            "case_id": case_id,
            **{check: True for check in REQUIRED_REVIEW_CHECKS},
            "decision": "approve",
            "notes": "",
        }
        for case_id in required
    ]
    audit = {
        "review_id": HUMAN_AUDIT_ID,
        "plan_id": PLAN_ID,
        "ensemble_id": ENSEMBLE_ID,
        "ensemble_sha256": "f" * 64,
        "status": "complete",
        "reviewed_at": "2026-08-14T10:00:00+07:00",
        "reviewer": {
            "reviewer_id": "researcher-1",
            "role": "researcher",
            "human_review": True,
            "independent_human_audit": True,
            "codex_assisted": False,
            "blinded_to_model_decisions": True,
            "model_decisions_inspected": False,
        },
        "draft_hashes": draft_hashes,
        "selection_commitment_sha256": selection_commitment_sha256(baseline, required),
        "required_case_count": len(required),
        "case_decisions": decisions,
    }

    _, validated = validate_hybrid_reviews(
        ensemble=ensemble,
        human_audit=audit,
        ensemble_sha256="f" * 64,
        datasets=datasets,
        draft_hashes=draft_hashes,
    )
    assert set(validated) == set(required)

    decisions[0]["evidence_supports_claims"] = False
    with pytest.raises(ValueError, match="unapproved"):
        validate_hybrid_reviews(
            ensemble=ensemble,
            human_audit=audit,
            ensemble_sha256="f" * 64,
            datasets=datasets,
            draft_hashes=draft_hashes,
        )
