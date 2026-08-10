import pytest

from scripts.analyze_professor_fidelity import analyze
from scripts.run_professor_fidelity_experiment import (
    ProfessorFidelityPlanError,
    build_preflight_manifest,
    load_instrument,
)
from scripts.execute_professor_fidelity import _parse_output, _score
from scripts.judge_professor_fidelity import _model_digest


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
    assert not any("generator" in reason for reason in manifest["blocked_reasons"])
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


def test_professor_fidelity_output_requires_exact_action_contract():
    parsed = _parse_output(
        '{"answer":"Use the approved source.","citation_ids":["S1"],"action":"answer"}'
    )
    assert parsed["action"] == "answer"

    with pytest.raises(ValueError, match="keys drifted"):
        _parse_output('{"answer":"x","citation_ids":[],"action":"answer","extra":1}')


def test_professor_fidelity_scoring_fails_unsupported_answer():
    case = {
        "scenario_type": "direct",
        "ground_truth": {
            "expected_behavior": {
                "primary_action": "answer",
                "acceptable_alternatives": [],
                "citation_requirement": "required",
            },
            "required_claims": [{"claim_text": "fixed length of 32 bits"}],
            "evidence_units": [],
        },
    }
    score = _score(
        case,
        "C1",
        {"answer": "MIPS uses a regular format.", "citation_ids": [], "action": "answer"},
        [],
    )
    assert score["safe_grounded_success"] is False
    assert score["unsupported_high_severity_claim"] is True


def test_professor_fidelity_judge_records_ollama_digest(monkeypatch):
    monkeypatch.setattr(
        "scripts.judge_professor_fidelity.subprocess_run",
        lambda command: "NAME ID SIZE MODIFIED\ngemma3:4b a2af6cc3eb7f 3.3 GB now\n",
    )

    assert _model_digest("gemma3:4b") == "a2af6cc3eb7f"


def test_professor_fidelity_analysis_applies_gates_and_keeps_failures_sanitized():
    results = []
    judgments = []
    for case_index in range(10):
        case_id = f"case-{case_index:02d}"
        responses = []
        mapping = {"A": "C0", "B": "C1", "C": "C2", "D": "C3"}
        for label, condition in mapping.items():
            passed = condition == "C3" or (condition == "C2" and case_index < 9)
            results.append(
                {
                    "case_id": case_id,
                    "scenario_type": "direct",
                    "condition": condition,
                    "latency_ms": 100,
                    "score": {
                        "safe_grounded_success": passed,
                        "hard_gate_passed": passed,
                        "citation_validity": passed,
                        "citation_completeness": passed,
                        "complete_evidence_at_3": passed,
                        "action_passed": passed,
                    },
                }
            )
            responses.append(
                {
                    "label": label,
                    "dimensions": [{"dimension": "clarity", "label": "pass" if passed else "fail"}],
                }
            )
        judgments.append(
            {
                "case_id": case_id,
                "mapping": mapping,
                "repeat": False,
                "judgment": {"responses": responses, "c1_c2_preference": "C2"},
            }
        )
    run = {
        "run_id": "synthetic-run",
        "case_count": 10,
        "condition_attempts": 40,
        "cost_usd": 0.01,
        "input_tokens": 100,
        "output_tokens": 100,
        "latency_p50_ms": 100,
        "latency_p95_ms": 100,
        "provider_model": "synthetic",
        "provider_revision": "synthetic",
        "retrieval": "synthetic",
        "results": results,
    }
    judge = {
        "model": "synthetic-judge",
        "model_digest": "digest",
        "case_judgments": judgments,
    }

    result = analyze(run, judge, None)

    assert result["decision"] == "keep"
    assert result["condition_summaries"]["C3"]["safe_grounded_success"] == 1.0
    assert result["representative_failures"] == []
