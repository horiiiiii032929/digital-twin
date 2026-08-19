import json

import pytest

from scripts.run_local_reviewer_sensitivity import (
    ReviewCall,
    ReviewerSensitivityError,
    analyze_results,
    execute,
    review_schema,
    validate_assets,
    validate_review,
)


def _accepted_review():
    return {
        "verdict": "accept",
        "primary_failure": "none",
        "response_action_correct": True,
        "response_content_correct": True,
        "fully_supported": True,
        "citation_lineage_correct": True,
        "course_boundary_respected": True,
        "evidence_observation": "The supplied evidence supports the candidate.",
        "rationale": "Every review dimension passes.",
    }


def _rejected_review(primary_failure):
    return {
        "verdict": "reject",
        "primary_failure": primary_failure,
        "response_action_correct": primary_failure
        not in {
            "unsupported_no_evidence_answer",
            "wrong_boundary_action",
            "cross_course_leakage",
        },
        "response_content_correct": False,
        "fully_supported": False,
        "citation_lineage_correct": primary_failure
        not in {"incomplete_answer", "cross_course_leakage"},
        "course_boundary_respected": primary_failure != "cross_course_leakage",
        "evidence_observation": "The candidate contains the seeded defect.",
        "rationale": "The response must be rejected.",
    }


class _PerfectTransport:
    def __init__(self, assets):
        candidate = assets["instrument"]["candidate"]
        self.identity = {
            "model": candidate["model"],
            "digest": candidate["model_digest"],
            "capabilities": candidate["required_capabilities"],
        }
        self.failures = [
            pair["defect"]["primary_failure"]
            for pair in assets["dataset"]["pairs"]
        ]
        self.calls = 0

    async def review(self, *, prompt, schema, image_bytes):
        del schema, image_bytes
        json.loads(prompt)
        pair_index, condition_index = divmod(self.calls, 2)
        self.calls += 1
        value = (
            _accepted_review()
            if condition_index == 0
            else _rejected_review(self.failures[pair_index])
        )
        return ReviewCall(
            value=value,
            provider_model=self.identity["model"],
            provider_digest=self.identity["digest"],
            input_tokens=100,
            output_tokens=20,
            latency_ms=10.0,
        )


def test_assets_freeze_22_paired_public_probes_with_six_visual_pairs():
    assets = validate_assets()

    assert len(assets["dataset"]["pairs"]) == 11
    assert sum(
        pair["source_mode"] == "approved-image"
        for pair in assets["dataset"]["pairs"]
    ) == 6
    assert assets["source_integrity_rate"] == 1.0
    assert assets["instrument"]["candidate"]["model"] == "qwen3.5:9b-q4_K_M"


def test_review_schema_is_closed_and_uses_frozen_failure_labels():
    assets = validate_assets()
    schema = review_schema(assets["instrument"]["failure_labels"])

    assert schema["additionalProperties"] is False
    assert schema["properties"]["primary_failure"]["enum"] == assets[
        "instrument"
    ]["failure_labels"]


def test_review_contract_mismatch_is_preserved_and_fails_closed():
    assets = validate_assets()
    contradictory = _accepted_review()
    contradictory["fully_supported"] = False

    normalized = validate_review(
        contradictory, assets["instrument"]["failure_labels"]
    )

    assert normalized["reported_verdict"] == "accept"
    assert normalized["verdict"] == "reject"
    assert normalized["contract_mismatch"] is True


def test_review_rejects_unknown_failure_label():
    assets = validate_assets()
    review = _rejected_review("wrong_factual_answer")
    review["primary_failure"] = "invented-label"

    with pytest.raises(ReviewerSensitivityError, match="failure label"):
        validate_review(review, assets["instrument"]["failure_labels"])


@pytest.mark.asyncio
async def test_perfect_transport_passes_all_prospective_gates():
    assets = validate_assets()
    transport = _PerfectTransport(assets)

    payload = await execute(assets, transport)

    assert transport.calls == 22
    assert payload["metrics"]["structured_completion_rate"] == 1.0
    assert payload["metrics"]["critical_defect_recall"] == 1.0
    assert payload["metrics"]["clean_control_acceptance_rate"] == 1.0
    assert payload["metrics"]["visual_defect_recall"] == 1.0
    assert payload["metrics"]["visual_clean_accept_count"] == 6
    assert payload["metrics"]["primary_failure_accuracy"] == 1.0
    assert payload["all_gates_passed"] is True
    assert payload["decision"] == "go-deeper-diagnostic-only"


def test_analysis_fails_when_one_critical_defect_is_accepted():
    assets = validate_assets()
    identity = {
        "model": assets["instrument"]["candidate"]["model"],
        "digest": assets["instrument"]["candidate"]["model_digest"],
        "capabilities": ["completion", "vision"],
    }
    results = []
    for pair in assets["dataset"]["pairs"]:
        for condition in ("clean", "defect"):
            expected_failure = (
                "none" if condition == "clean" else pair["defect"]["primary_failure"]
            )
            review = (
                _accepted_review()
                if condition == "clean"
                else _rejected_review(expected_failure)
            )
            results.append(
                {
                    "condition": condition,
                    "source_mode": pair["source_mode"],
                    "expected_primary_failure": expected_failure,
                    "review": review,
                    "call": {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "latency_ms": 1.0,
                    },
                }
            )
    results[1]["review"] = _accepted_review()

    analysis = analyze_results(assets["instrument"], results, identity)

    assert analysis["metrics"]["critical_defect_recall"] < 1.0
    assert analysis["gates"]["critical_defect_recall"] is False
    assert analysis["all_gates_passed"] is False
