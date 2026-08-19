import json
from copy import deepcopy

import pytest

from scripts.run_factual_qa_quality_pilot import (
    FactualQaPilotError,
    analyze_results,
    build_human_audit_packet,
    deterministic_case_checks,
    execute,
    JsonCall,
    validate_assets,
    validate_corpus,
    validate_review,
)


def _assets():
    return validate_assets()


def _source_map(corpus):
    return {source["source_unit_id"]: source for source in corpus["source_units"]}


def _valid_authored(blueprint, source_map):
    if blueprint["expected_action"] == "answer":
        claims = [
            source_map[source_id]["claims"][0]["claim_id"]
            for source_id in blueprint["evidence_unit_ids"]
        ]
        citations = [
            {
                "source_unit_id": source_id,
                "quote": source_map[source_id]["evidence_text"],
            }
            for source_id in blueprint["evidence_unit_ids"]
        ]
        answer = " ".join(
            source_map[source_id]["claims"][0]["text"]
            for source_id in blueprint["evidence_unit_ids"]
        )
    else:
        claims = []
        citations = []
        answer = {
            "abstain": "The approved target-course sources do not provide that information.",
            "clarify": "Could you clarify which interpretation you mean?",
            "refuse": "I cannot bypass permissions or reveal private notes.",
        }[blueprint["expected_action"]]
    return {
        "question": f"Synthetic question for {blueprint['blueprint_id']}?",
        "answer": answer,
        "action": blueprint["expected_action"],
        "selected_claim_ids": claims,
        "citations": citations,
    }


def _accepted_review():
    return {
        "verdict": "accept",
        "question_matches_blueprint": True,
        "answer_or_action_correct": True,
        "fully_supported": True,
        "citation_lineage_correct": True,
        "no_external_knowledge": True,
        "course_boundary_respected": True,
        "failure_categories": [],
        "rationale": "The synthetic case follows the frozen source and action.",
    }


def _call(provider_model, provider_revision):
    return {
        "provider_model": provider_model,
        "provider_revision": provider_revision,
        "input_tokens": 10,
        "output_tokens": 5,
        "approximate_cost_usd": 0.001,
        "latency_ms": 10.0,
    }


def _passing_results(assets):
    corpus = assets["corpus"]
    source_map = _source_map(corpus)
    results = []
    for blueprint in corpus["case_blueprints"]:
        authored = _valid_authored(blueprint, source_map)
        results.append(
            {
                "blueprint_id": blueprint["blueprint_id"],
                "slice": blueprint["slice"],
                "course_id": blueprint["course_id"],
                "expected_action": blueprint["expected_action"],
                "evidence_unit_ids": blueprint["evidence_unit_ids"],
                "authored_case": authored,
                "deterministic": deterministic_case_checks(
                    blueprint, authored, source_map=source_map
                ),
                "cross_review": _accepted_review(),
                "independent_review": _accepted_review(),
                "author_call": _call("deepseek-v4-pro", "fp-pro"),
                "cross_review_call": _call("deepseek-v4-flash", "fp-flash"),
                "independent_review_call": _call("qwen3:4b", "359d7dd4bcda"),
                "retained": True,
                "quarantine_reasons": [],
            }
        )
    return results


def test_factual_qa_assets_bind_24_synthetic_blueprints():
    assets = _assets()

    assert assets["source_summary"] == {
        "source_units": 21,
        "text_units": 15,
        "visual_units": 6,
        "courses": 4,
        "case_blueprints": 24,
        "slice_counts": {
            "adversarial-integrity": 1,
            "ambiguous": 2,
            "cross-course-confusion": 1,
            "direct-text": 4,
            "multi-evidence-text": 3,
            "multimodal": 6,
            "no-evidence": 3,
            "paraphrase-text": 4,
        },
        "source_integrity_rate": 1.0,
    }


def test_corpus_validation_rejects_private_data_boundary():
    corpus = deepcopy(_assets()["corpus"])
    corpus["data_boundary"]["private_course_text"] = True

    with pytest.raises(FactualQaPilotError, match="data boundary"):
        validate_corpus(corpus)


def test_deterministic_checks_require_exact_source_quotes():
    assets = _assets()
    corpus = assets["corpus"]
    blueprint = corpus["case_blueprints"][0]
    source_map = _source_map(corpus)
    authored = _valid_authored(blueprint, source_map)
    authored["citations"][0]["quote"] = "A plausible but unsupported quotation."

    result = deterministic_case_checks(blueprint, authored, source_map=source_map)

    assert result["passed"] is False
    assert result["checks"]["citation_quotes_exact"] is False


def test_deterministic_checks_require_every_source_for_multi_evidence():
    assets = _assets()
    corpus = assets["corpus"]
    blueprint = next(
        item for item in corpus["case_blueprints"] if item["blueprint_id"] == "fqa-p03"
    )
    source_map = _source_map(corpus)
    authored = _valid_authored(blueprint, source_map)
    authored["selected_claim_ids"] = authored["selected_claim_ids"][:1]
    authored["citations"] = authored["citations"][:1]

    result = deterministic_case_checks(blueprint, authored, source_map=source_map)

    assert result["passed"] is False
    assert result["checks"]["required_sources_covered"] is False
    assert result["checks"]["citation_sources_complete"] is False


def test_review_verdict_contradiction_is_preserved_and_rejected_fail_closed():
    review = _accepted_review()
    review["fully_supported"] = False

    normalized = validate_review(review)

    assert normalized["reported_verdict"] == "accept"
    assert normalized["verdict"] == "reject"
    assert normalized["contract_mismatch"] is True
    assert "review_contract_mismatch" in normalized["failure_categories"]


def test_passing_machine_result_stops_at_human_audit():
    assets = _assets()
    results = _passing_results(assets)

    summary = analyze_results(
        assets["instrument"],
        results,
        external_cost_usd=0.1,
        source_integrity_rate=1.0,
    )

    assert summary["machine_gates_passed"] is True
    assert summary["decision"] == "go-deeper"
    assert summary["scale_authorized"] is False
    assert summary["human_audit_required"] is True


def test_any_deterministic_failure_forces_refine():
    assets = _assets()
    results = _passing_results(assets)
    results[0]["deterministic"] = {
        "passed": False,
        "checks": {"citation_quotes_exact": False},
    }
    results[0]["retained"] = False
    results[0]["quarantine_reasons"] = ["deterministic:citation_quotes_exact"]

    summary = analyze_results(
        assets["instrument"],
        results,
        external_cost_usd=0.1,
        source_integrity_rate=1.0,
    )

    assert summary["machine_gates_passed"] is False
    assert summary["decision"] == "refine"
    assert "deterministic_provenance_rate" in summary["failed_gates"]


def test_human_audit_packet_is_six_case_stratified_and_pending():
    assets = _assets()
    packet = build_human_audit_packet(
        instrument_id=assets["instrument"]["instrument_id"],
        corpus_sha256=assets["corpus_sha256"],
        results=_passing_results(assets),
    )

    assert packet["status"] == "pending-human-review"
    assert len(packet["cases"]) == 6
    assert {case["slice"] for case in packet["cases"]} == {
        "direct-text",
        "paraphrase-text",
        "multi-evidence-text",
        "multimodal",
        "no-evidence",
        "ambiguous",
    }


class _FakeTransport:
    def __init__(self, provider_model, provider_revision):
        self.provider_model = provider_model
        self.provider_revision = provider_revision

    async def call_json(self, *, system, prompt, task, schema):
        del system, schema
        payload = json.loads(prompt)
        if task == "factual_qa_case_authoring":
            blueprint = payload["blueprint"]
            sources = payload["approved_target_course_sources"]
            if blueprint["expected_action"] == "answer":
                selected_claim_ids = [
                    source["allowed_claims"][0]["claim_id"] for source in sources
                ]
                citations = [
                    {
                        "source_unit_id": source["source_unit_id"],
                        "quote": source["source_truth"],
                    }
                    for source in sources
                ]
                answer = " ".join(
                    source["allowed_claims"][0]["text"] for source in sources
                )
            else:
                selected_claim_ids = []
                citations = []
                answer = "A safe boundary response."
            value = {
                "question": f"Question for {blueprint['blueprint_id']}?",
                "answer": answer,
                "action": blueprint["expected_action"],
                "selected_claim_ids": selected_claim_ids,
                "citations": citations,
            }
        else:
            value = _accepted_review()
        return JsonCall(
            value=value,
            provider_model=self.provider_model,
            provider_revision=self.provider_revision,
            input_tokens=10,
            output_tokens=5,
            approximate_cost_usd=0.001,
            latency_ms=10.0,
        )


@pytest.mark.asyncio
async def test_execute_runs_all_roles_and_requires_human_audit_before_scale():
    assets = _assets()

    result = await execute(
        assets,
        author_transport=_FakeTransport("deepseek-v4-pro", "fp-pro"),
        cross_reviewer_transport=_FakeTransport("deepseek-v4-flash", "fp-flash"),
        independent_reviewer_transport=_FakeTransport("qwen3:4b", "359d7dd4bcda"),
    )

    assert result["status"] == "machine-gates-passed-human-audit-required"
    assert result["call_counts"] == {"author": 24, "cross": 24, "independent": 24}
    assert result["summary"]["retained_cases"] == 24
    assert result["summary"]["scale_authorized"] is False
    assert len(result["human_audit_packet"]["cases"]) == 6
