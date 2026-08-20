from __future__ import annotations

import asyncio
from collections import Counter

from scripts.run_factual_qa_v3_scale_rehearsal import (
    EXPECTED_SLICES,
    MUTATION_TYPES,
    OpenRouterJsonTransport,
    _analyze,
    _deterministic_record,
    _mutation_probes,
    _parallel_ordered,
    _percentile,
    build_preflight,
    validate_assets,
)


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
    ][:20]
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

    _, mutations = _mutation_probes(
        blueprints, results, source_map=source_map, count=20
    )

    assert len(mutations) == 20
    assert Counter(item["mutation_type"] for item in mutations) == Counter(
        MUTATION_TYPES
    )
    assert all(item["deterministic"]["passed"] is False for item in mutations)


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
