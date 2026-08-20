from __future__ import annotations

import asyncio
from collections import Counter
import pytest

from scripts.run_factual_qa_v3_scale_rehearsal import (
    EXPECTED_SLICES,
    MUTATION_TYPES,
    OpenRouterJsonTransport,
    _analyze,
    _deterministic_record,
    _enforce_cost_reservation,
    _maximum_batch_cost,
    _mutation_probes,
    _parallel_ordered,
    _percentile,
    build_preflight,
    validate_assets,
)
from scripts.run_factual_qa_quality_pilot import FactualQaPilotError, REVIEW_SCHEMA


def _accept_review() -> dict[str, object]:
    return {
        "verdict": "accept",
        "question_matches_blueprint": True,
        "answer_or_action_correct": True,
        "fully_supported": True,
        "citation_lineage_correct": True,
        "no_external_knowledge": True,
        "course_boundary_respected": True,
        "failure_categories": [],
        "rationale": "Synthetic accepted control.",
    }


def test_assets_expand_to_frozen_120_case_slice_design() -> None:
    assets = validate_assets()
    corpus = assets["corpus"]

    assert assets["instrument"]["status"] == "frozen-pending-execution"
    assert len(corpus["case_blueprints"]) == 120
    assert Counter(case["slice"] for case in corpus["case_blueprints"]) == (
        EXPECTED_SLICES
    )
    assert (
        sum(case["expected_action"] == "answer" for case in corpus["case_blueprints"])
        == 96
    )
    covered = {
        claim_id
        for case in corpus["case_blueprints"]
        for claim_id in case.get("target_claim_ids", [])
    }
    expected = {
        claim["claim_id"]
        for source in corpus["source_units"]
        for claim in source["claims"]
    }
    assert covered == expected


def test_source_design_has_exact_claim_anchors_and_distinct_visual_facts() -> None:
    corpus = validate_assets()["corpus"]
    claims = [
        (source, claim)
        for source in corpus["source_units"]
        for claim in source["claims"]
    ]

    assert len(claims) == 48
    assert len({claim["claim_id"] for _, claim in claims}) == 48
    assert all(
        " ".join(claim["evidence_quote"].split())
        in " ".join(source["evidence_text"].split())
        for source, claim in claims
    )
    visual_claims = [
        case["target_claim_ids"][0]
        for case in corpus["case_blueprints"]
        if case["slice"] == "multimodal"
    ]
    assert len(visual_claims) == len(set(visual_claims)) == 18


def test_multi_evidence_and_cross_course_cases_cover_distinct_sources_and_courses() -> None:
    corpus = validate_assets()["corpus"]
    source_map = {source["source_unit_id"]: source for source in corpus["source_units"]}
    claim_sources = {
        claim["claim_id"]: source["source_unit_id"]
        for source in corpus["source_units"]
        for claim in source["claims"]
    }
    multi = [
        case
        for case in corpus["case_blueprints"]
        if case["slice"] == "multi-evidence-text"
    ]
    assert len(multi) == 18
    assert all(len(set(case["evidence_unit_ids"])) == 2 for case in multi)
    assert all(
        {claim_sources[claim_id] for claim_id in case["target_claim_ids"]}
        == set(case["evidence_unit_ids"])
        for case in multi
    )

    cross_course = [
        case
        for case in corpus["case_blueprints"]
        if case["slice"] == "cross-course-confusion"
    ]
    all_courses = {source["course_id"] for source in corpus["source_units"]}
    assert {case["course_id"] for case in cross_course} == all_courses
    assert {
        source_map[case["distractor_unit_ids"][0]]["course_id"]
        for case in cross_course
    } == all_courses
    course_counts = Counter(case["course_id"] for case in corpus["case_blueprints"])
    assert max(course_counts.values()) - min(course_counts.values()) <= 2


def test_boundary_topics_are_assigned_to_the_relevant_course_context() -> None:
    cases = {
        case["blueprint_id"]: case
        for case in validate_assets()["corpus"]["case_blueprints"]
    }

    assert cases["fqa-r099"]["course_id"] == "course-machine-learning"
    assert cases["fqa-r100"]["course_id"] == "course-human-ai"
    assert cases["fqa-r103"]["course_id"] == "course-machine-learning"
    assert cases["fqa-r105"]["course_id"] == "course-browser-security"
    assert cases["fqa-r107"]["course_id"] == "course-human-ai"


def test_preflight_requires_both_provider_credentials(monkeypatch) -> None:
    assets = validate_assets()
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = build_preflight(assets)

    assert result["status"] == "blocked"
    assert result["deepseek_credential_present"] is True
    assert result["openrouter_credential_present"] is False
    assert result["credential_value_emitted"] is False
    assert result["external_call_enabled"] is False


def test_preflight_is_ready_only_with_both_keys_and_clean_revision(
    monkeypatch,
    tmp_path,
) -> None:
    assets = validate_assets()
    assets["instrument"]["status"] = "frozen-pending-execution"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured")
    monkeypatch.setenv("OPENROUTER_API_KEY", "configured")
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_oracle_pilot.EMBEDDING_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_scale_rehearsal._working_tree_dirty",
        lambda: False,
    )

    result = build_preflight(assets)

    assert result["status"] == "ready"
    assert result["working_tree_dirty"] is False
    assert result["external_call_enabled"] is False


def test_draft_instrument_cannot_be_ready_for_execution(
    monkeypatch,
    tmp_path,
) -> None:
    assets = validate_assets()
    assets["instrument"]["status"] = "reviewed-pending-execution-authorization"
    monkeypatch.setenv("DEEPSEEK_API_KEY", "configured")
    monkeypatch.setenv("OPENROUTER_API_KEY", "configured")
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_oracle_pilot.EMBEDDING_ROOT",
        tmp_path,
    )
    monkeypatch.setattr(
        "scripts.run_factual_qa_v3_scale_rehearsal._working_tree_dirty",
        lambda: False,
    )

    result = build_preflight(assets)

    assert result["status"] == "blocked"
    assert result["instrument_frozen"] is False


def test_openrouter_reviewer_is_pinned_to_first_party_mistral() -> None:
    binding = validate_assets()["instrument"]["model_roles"]["independent_reviewer"]

    transport = OpenRouterJsonTransport(binding)

    assert transport.client.model == "openrouter/mistralai/mistral-small-2603"
    assert transport.client.expected_provider_model == ("mistralai/mistral-small-2603")
    assert transport.client.provider_options == {
        "extra_body": {
            "provider": {
                "order": ["Mistral"],
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": "deny",
                "zdr": True,
            }
        }
    }


def test_all_20_reviewer_mutations_are_deterministic_defects() -> None:
    corpus = validate_assets()["corpus"]
    source_map = {source["source_unit_id"]: source for source in corpus["source_units"]}
    blueprints = [
        case
        for case in corpus["case_blueprints"]
        if case["expected_action"] == "answer"
    ]
    results = []
    for blueprint in blueprints:
        claim_ids = blueprint["target_claim_ids"]
        citations = [
            {
                "source_unit_id": source_id,
                "quote": source_map[source_id]["evidence_text"],
            }
            for source_id in blueprint["evidence_unit_ids"]
        ]
        authored = {
            "question": f"Question for {blueprint['blueprint_id']}?",
            "answer": " ".join(
                claim["text"]
                for source_id in blueprint["evidence_unit_ids"]
                for claim in source_map[source_id]["claims"]
                if claim["claim_id"] in claim_ids
            ),
            "action": "answer",
            "selected_claim_ids": claim_ids,
            "citations": citations,
        }
        deterministic = _deterministic_record(
            blueprint, authored, source_map=source_map
        )
        assert deterministic["passed"] is True
        results.append(
            {
                "authored_case": authored,
                "deterministic": deterministic,
                "independent_review": _accept_review(),
            }
        )

    mutation_blueprints, mutations = _mutation_probes(
        blueprints, results, source_map=source_map, count=20
    )

    assert len(mutations) == 20
    assert Counter(item["mutation_type"] for item in mutations) == Counter(
        MUTATION_TYPES
    )
    assert all(item["deterministic"]["passed"] is False for item in mutations)
    assert Counter(item["slice"] for item in mutation_blueprints) == {
        "direct-text": 5,
        "paraphrase-text": 5,
        "multi-evidence-text": 5,
        "multimodal": 5,
    }
    assert {item["course_id"] for item in mutation_blueprints} == {
        "course-browser-security",
        "course-data-systems",
        "course-machine-learning",
        "course-human-ai",
    }


def test_deterministic_checks_require_a_citation_anchor_for_every_target_claim() -> None:
    corpus = validate_assets()["corpus"]
    source_map = {source["source_unit_id"]: source for source in corpus["source_units"]}
    blueprint = next(
        case
        for case in corpus["case_blueprints"]
        if case["slice"] == "multi-evidence-text"
    )
    first_id, second_id = blueprint["evidence_unit_ids"]
    second_target = next(
        claim_id
        for claim_id in blueprint["target_claim_ids"]
        if any(
            claim["claim_id"] == claim_id for claim in source_map[second_id]["claims"]
        )
    )
    unrelated_second_quote = next(
        claim["evidence_quote"]
        for claim in source_map[second_id]["claims"]
        if claim["claim_id"] != second_target
    )
    authored = {
        "question": "What are the two required facts?",
        "answer": "Synthetic answer.",
        "action": "answer",
        "selected_claim_ids": blueprint["target_claim_ids"],
        "citations": [
            {
                "source_unit_id": first_id,
                "quote": source_map[first_id]["evidence_text"],
            },
            {"source_unit_id": second_id, "quote": unrelated_second_quote},
        ],
    }

    result = _deterministic_record(blueprint, authored, source_map=source_map)

    assert result["checks"]["citation_sources_complete"] is True
    assert result["checks"]["target_claim_citations_complete"] is False
    assert result["passed"] is False


def test_parallel_ordered_preserves_input_order() -> None:
    active = 0
    maximum_active = 0

    async def operation(value: int) -> int:
        nonlocal active, maximum_active
        active += 1
        maximum_active = max(maximum_active, active)
        await asyncio.sleep(0)
        active -= 1
        return value * 2

    result = asyncio.run(
        _parallel_ordered(list(range(8)), concurrency=3, operation=operation)
    )

    assert result == [value * 2 for value in range(8)]
    assert maximum_active == 3


def test_cost_reservation_blocks_a_batch_before_the_hard_cap_can_be_exceeded() -> None:
    instrument = validate_assets()["instrument"]
    binding = instrument["model_roles"]["independent_reviewer"]
    reserved = _maximum_batch_cost(
        binding,
        system="Synthetic review system.",
        prompts=["Synthetic bounded prompt." for _ in range(120)],
        schema=REVIEW_SCHEMA,
    )

    assert 0 < reserved < instrument["execution"]["cost_stop_usd"]
    with pytest.raises(FactualQaPilotError, match="cost reservation exceeds stop"):
        _enforce_cost_reservation(
            instrument,
            incurred=instrument["execution"]["cost_stop_usd"],
            reserved=reserved,
        )


def test_percentile_uses_nearest_rank() -> None:
    assert _percentile(list(range(1, 21)), 0.95) == 19


def test_passing_summary_still_requires_human_audit_and_blocks_10000_scale() -> None:
    instrument = validate_assets()["instrument"]
    slices = [
        slice_name
        for slice_name, count in EXPECTED_SLICES.items()
        for _ in range(count)
    ]
    results = []
    boundary_slices = {
        "no-evidence": "abstain",
        "ambiguous": "clarify",
        "cross-course-confusion": "abstain",
        "adversarial-integrity": "refuse",
    }
    for index, slice_name in enumerate(slices):
        action = boundary_slices.get(slice_name, "answer")
        results.append(
            {
                "blueprint_id": f"fqa-summary-{index:03d}",
                "slice": slice_name,
                "expected_action": action,
                "authored_case": {
                    "question": f"Unique rehearsal question {index}?",
                    "action": action,
                    "citations": [],
                },
                "deterministic": {"passed": True},
                "retrieval": {
                    "all_evidence_at_3": True if action == "answer" else None,
                    "evidence_recall_at_5": 1.0 if action == "answer" else None,
                },
                "independent_review": _accept_review(),
                "author_call": {
                    "provider_model": "deepseek-v4-flash",
                    "provider_revision": "stable-author-revision",
                },
                "independent_review_call": {
                    "provider_model": "mistralai/mistral-small-2603",
                    "latency_ms": 1000.0,
                },
                "dispute_review": None,
                "dispute_review_call": None,
                "distractor_unit_ids": [],
            }
        )
    mutation_results = [
        {
            "review": {**_accept_review(), "verdict": "reject"},
            "paired_clean_review": _accept_review(),
            "review_call": {
                "provider_model": "mistralai/mistral-small-2603",
                "latency_ms": 1000.0,
            },
        }
        for _ in range(20)
    ]

    summary = _analyze(
        instrument,
        results,
        mutation_results=mutation_results,
        ingestion={"pdf_ingestion_rate": 1.0},
        external_cost=0.25,
        review_elapsed_seconds=60.0,
        elapsed_seconds=180.0,
        call_counts={
            "author": 120,
            "independent_case": 120,
            "independent_mutation": 20,
            "dispute": 0,
        },
    )

    assert summary["machine_gates_passed"] is True
    assert summary["decision"] == "human-audit-required"
    assert summary["scale_to_10000_authorized"] is False
    assert summary["failed_gates"] == []

    results[0]["independent_review"] = {**_accept_review(), "verdict": "reject"}
    failed = _analyze(
        instrument,
        results,
        mutation_results=mutation_results,
        ingestion={"pdf_ingestion_rate": 1.0},
        external_cost=0.25,
        review_elapsed_seconds=60.0,
        elapsed_seconds=180.0,
        call_counts={
            "author": 120,
            "independent_case": 120,
            "independent_mutation": 20,
            "dispute": 0,
        },
    )
    assert failed["machine_gates_passed"] is False
    assert failed["metrics"]["unreviewed_disagreement_count"] == 1
    assert "unreviewed_disagreement_count" in failed["failed_gates"]
    assert "dispute_review_completion_rate" in failed["failed_gates"]

    results[0]["dispute_review"] = _accept_review()
    results[0]["dispute_review_call"] = {
        "provider_model": "deepseek-v4-pro",
        "provider_revision": "stable-dispute-revision",
    }
    resolved = _analyze(
        instrument,
        results,
        mutation_results=mutation_results,
        ingestion={"pdf_ingestion_rate": 1.0},
        external_cost=0.25,
        review_elapsed_seconds=60.0,
        elapsed_seconds=180.0,
        call_counts={
            "author": 120,
            "independent_case": 120,
            "independent_mutation": 20,
            "dispute": 1,
        },
    )
    assert resolved["machine_gates_passed"] is True
    assert resolved["metrics"]["unresolved_disagreement_count"] == 0
