import json

import pytest

from scripts.run_local_reviewer_sensitivity import (
    ReviewCall,
    ReviewerSensitivityError,
    analyze_results,
    derive_review,
    deterministic_citation_lineage,
    execute,
    review_schema,
    validate_assets,
    validate_semantic_review,
)


def _accepted_semantic_review():
    return {
        "response_action_correct": True,
        "response_content_correct": True,
        "evidence_complete": True,
        "course_boundary_respected": True,
        "evidence_observation": "The supplied evidence supports the candidate.",
        "rationale": "Every review dimension passes.",
    }


def _semantic_for_failure(primary_failure):
    semantic = {
        **_accepted_semantic_review(),
        "evidence_observation": "The candidate contains the seeded defect.",
        "rationale": "The response must be rejected.",
    }
    if primary_failure == "incomplete_answer":
        semantic["evidence_complete"] = False
    elif primary_failure in {
        "unsupported_no_evidence_answer",
        "wrong_boundary_action",
    }:
        semantic["response_action_correct"] = False
        semantic["response_content_correct"] = False
        semantic["evidence_complete"] = False
    elif primary_failure == "cross_course_leakage":
        semantic["response_action_correct"] = False
        semantic["response_content_correct"] = False
        semantic["evidence_complete"] = False
        semantic["course_boundary_respected"] = False
    else:
        semantic["response_content_correct"] = False
        semantic["evidence_complete"] = False
    return semantic


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
        self.visual_calls = 0

    async def review(self, *, prompt, schema, image_bytes):
        del schema
        json.loads(prompt)
        if image_bytes:
            self.visual_calls += 1
        pair_index, condition_index = divmod(self.calls, 2)
        self.calls += 1
        value = (
            _accepted_semantic_review()
            if condition_index == 0
            else _semantic_for_failure(self.failures[pair_index])
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


def test_review_schema_is_closed_and_excludes_deterministic_fields():
    schema = review_schema()

    assert schema["additionalProperties"] is False
    assert "primary_failure" not in schema["properties"]
    assert "verdict" not in schema["properties"]
    assert "citation_lineage_correct" not in schema["properties"]


def test_semantic_review_rejects_missing_boolean():
    incomplete = _accepted_semantic_review()
    del incomplete["evidence_complete"]

    with pytest.raises(ReviewerSensitivityError, match="boolean fields"):
        validate_semantic_review(incomplete)


def test_deterministic_citation_lineage_handles_approved_and_disallowed_sources():
    assets = validate_assets()
    approved = assets["dataset"]["pairs"][0]
    disallowed = next(
        pair
        for pair in assets["dataset"]["pairs"]
        if pair["source_mode"] == "disallowed-distractor"
    )

    assert deterministic_citation_lineage(approved, approved["clean"]) is True
    assert deterministic_citation_lineage(disallowed, disallowed["clean"]) is True
    assert deterministic_citation_lineage(disallowed, disallowed["defect"]) is False


def test_derived_triage_labels_match_every_seeded_defect():
    assets = validate_assets()

    for pair in assets["dataset"]["pairs"]:
        blueprint = assets["blueprint_map"][pair["blueprint_id"]]
        review = derive_review(
            _semantic_for_failure(pair["defect"]["primary_failure"]),
            pair=pair,
            candidate=pair["defect"],
            blueprint=blueprint,
        )
        assert review["verdict"] == "reject"
        assert review["primary_failure"] == pair["defect"]["primary_failure"]


@pytest.mark.asyncio
async def test_perfect_transport_passes_all_prospective_gates():
    assets = validate_assets()
    transport = _PerfectTransport(assets)

    def synthetic_image_loader(pair, source_map):
        del source_map
        if pair["source_mode"] == "approved-image":
            return [b"synthetic-png-bytes"]
        return []

    payload = await execute(
        assets,
        transport,
        image_loader=synthetic_image_loader,
    )

    assert transport.calls == 22
    assert transport.visual_calls == 12
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
            semantic = (
                _accepted_semantic_review()
                if condition == "clean"
                else _semantic_for_failure(expected_failure)
            )
            review = derive_review(
                semantic,
                pair=pair,
                candidate=pair[condition],
                blueprint=assets["blueprint_map"][pair["blueprint_id"]],
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
    results[1]["review"] = derive_review(
        _accepted_semantic_review(),
        pair=assets["dataset"]["pairs"][0],
        candidate=assets["dataset"]["pairs"][0]["clean"],
        blueprint=assets["blueprint_map"][
            assets["dataset"]["pairs"][0]["blueprint_id"]
        ],
    )

    analysis = analyze_results(assets["instrument"], results, identity)

    assert analysis["metrics"]["critical_defect_recall"] < 1.0
    assert analysis["gates"]["critical_defect_recall"] is False
    assert analysis["all_gates_passed"] is False
