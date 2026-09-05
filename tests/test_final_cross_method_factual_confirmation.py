"""Regression tests for the one-time final cross-method confirmation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import final_cross_method_factual_adapter as adapter
from scripts import run_final_cross_method_factual_confirmation as runner
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationResponseV1,
)


def test_validation_does_not_open_hidden_gold(monkeypatch: pytest.MonkeyPatch) -> None:
    original = runner._load_object

    def guarded(path: Path):
        if path == runner.GOLD_PATH:
            raise AssertionError("validation opened hidden gold")
        return original(path)

    monkeypatch.setattr(runner, "_load_object", guarded)

    result = runner.validate()

    assert result["hidden_gold_loaded"] is False
    assert result["case_count"] == 1_000
    assert result["arm_count"] == 5


def test_hidden_gold_is_refused_until_every_arm_is_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, _ = runner._public_cases()
    opened = False

    def forbidden(_path: Path):
        nonlocal opened
        opened = True
        raise AssertionError("gold package opened before response completeness")

    monkeypatch.setattr(runner, "_load_object", forbidden)

    with pytest.raises(runner.FinalCrossMethodRunError, match="response IDs"):
        runner._load_hidden_gold_after_responses(
            cases,
            {"incomplete": []},
        )
    assert opened is False


def test_manifest_records_exact_retriever_and_gate() -> None:
    manifest = runner._manifest(
        adapter.BM25_RETRIEVER_ID,
        adapter.DOMINANCE_GATE,
        "a" * 40,
    )

    assert manifest.retriever == "bm25-v1"
    assert manifest.evidence_gate == "dominance-scoped-ambiguity-safe-v3"
    assert manifest.known_benchmark is False
    assert manifest.profile_sha256 == adapter.profile_sha256()


def test_no_method_arm_is_duplicated() -> None:
    identities = [(retriever, gate) for _, retriever, gate in runner.ARMS]

    assert len(identities) == len(set(identities))
    assert (adapter.BM25_RETRIEVER_ID, adapter.ANY_HIT_GATE) in identities
    assert (adapter.QWEN_RETRIEVER_ID, adapter.DOMINANCE_GATE) in identities


def test_response_completeness_is_checked_by_identity() -> None:
    case = EvaluationCaseV1(
        case_id="case-1",
        cluster_id="cluster-1",
        source_family_id="family-1",
        course_id="course-1",
        question="Question?",
        split="final",
        slice="direct-factual",
        author_family="deterministic",
    )
    response = EvaluationResponseV1(
        case_id="wrong-case",
        flow_id=adapter.FLOW_ID,
        action="abstain",
        answer="I cannot answer from the available evidence.",
        operational_status="completed",
    )

    with pytest.raises(runner.FinalCrossMethodRunError, match="response IDs"):
        runner._load_hidden_gold_after_responses([case], {"arm": [response]})


def test_frozen_instrument_declares_no_provider_or_paid_calls() -> None:
    instrument = json.loads(
        (
            runner.ROOT
            / "research/05_evaluation/instruments/"
            "final_cross_method_factual_confirmation_001.json"
        ).read_text(encoding="utf-8")
    )

    assert instrument["execution"]["provider_calls"] == 0
    assert instrument["authorization"]["provider_execution_authorized"] is False
    assert instrument["authorization"]["paid_execution_authorized"] is False
