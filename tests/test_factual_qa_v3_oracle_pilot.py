from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.run_factual_qa_v3_oracle_pilot import (
    FactualQaPilotError,
    _analyze,
    _audit_packet,
    _retrieval_record,
    validate_assets,
)


def test_assets_freeze_40_cases_and_current_models() -> None:
    assets = validate_assets()

    assert len(assets["corpus"]["case_blueprints"]) == 40
    assert assets["instrument"]["model_leaderboard"] is False
    assert (
        assets["instrument"]["model_roles"]["author"]["provider_model"]
        == "deepseek-v4-flash"
    )
    assert (
        assets["instrument"]["model_roles"]["independent_reviewer"]["model"]
        == "qwen3.5:9b-q4_K_M"
    )


def test_assets_reject_cost_boundary_drift(tmp_path) -> None:
    assets = validate_assets()
    instrument = deepcopy(assets["instrument"])
    instrument["execution"]["cost_stop_usd"] = 2.0
    path = tmp_path / "instrument.json"
    path.write_text(__import__("json").dumps(instrument))

    with pytest.raises(FactualQaPilotError, match="execution boundary"):
        validate_assets(path)


class _Hit:
    def __init__(self, page: int) -> None:
        self.chunk = type("Chunk", (), {"page_start": page})()


class _Retriever:
    def retrieve(self, question: str, *, limit: int):
        assert question
        assert limit == 5
        return [_Hit(2), _Hit(1), _Hit(3)]


def test_retrieval_record_scores_all_required_sources_without_gold_injection() -> None:
    record = _retrieval_record(
        {
            "expected_action": "answer",
            "evidence_unit_ids": ["source-a", "source-b"],
        },
        question="What do both sources establish?",
        retriever=_Retriever(),
        page_sources={1: "source-a", 2: "source-b", 3: "source-c"},
    )

    assert record["all_evidence_at_3"] is True
    assert record["evidence_recall_at_5"] == 1.0


def test_passing_summary_still_requires_eight_case_human_audit() -> None:
    instrument = validate_assets()["instrument"]
    results = []
    for index in range(40):
        boundary = index >= 32
        slice_name = (
            "multimodal" if index < 6 else "no-evidence" if boundary else "direct-text"
        )
        results.append(
            {
                "blueprint_id": f"case-{index:02d}",
                "slice": slice_name,
                "expected_action": "abstain" if boundary else "answer",
                "authored_case": {
                    "question": "Question?",
                    "answer": "Answer.",
                    "action": "abstain" if boundary else "answer",
                    "citations": [],
                },
                "deterministic": {"passed": True, "checks": {"ok": True}},
                "retrieval": {
                    "applicable": not boundary,
                    "all_evidence_at_3": None if boundary else True,
                    "evidence_recall_at_5": None if boundary else 1.0,
                },
                "independent_review": {"verdict": "accept"},
                "author_call": {
                    "provider_model": "deepseek-v4-flash",
                    "provider_revision": "fp-current",
                },
                "independent_review_call": {
                    "provider_model": "qwen3.5:9b-q4_K_M",
                    "provider_revision": "6488c96fa5fa",
                },
                "human_audit_priority": index < 8,
            }
        )

    summary = _analyze(
        instrument,
        results,
        ingestion={"pdf_ingestion_rate": 1.0},
        external_cost=0.2,
    )
    packet = _audit_packet(results, sample_size=8)

    assert summary["machine_gates_passed"] is True
    assert summary["decision"] == "human-audit-required"
    assert summary["scale_authorized"] is False
    assert len(packet) == 8


def test_audit_packet_prioritizes_deterministic_failure_within_slice() -> None:
    accepted = {
        "blueprint_id": "accepted-first-lexically",
        "slice": "multimodal",
        "authored_case": {
            "question": "Q?",
            "answer": "A",
            "action": "answer",
            "citations": [],
        },
        "deterministic": {"passed": True, "checks": {"exact_quote": True}},
        "retrieval": {"applicable": True},
        "independent_review": {"verdict": "accept"},
        "human_audit_priority": True,
    }
    failed = {
        **accepted,
        "blueprint_id": "failed-second-lexically",
        "deterministic": {"passed": False, "checks": {"exact_quote": False}},
    }

    packet = _audit_packet([accepted, failed], sample_size=1)

    assert packet[0]["blueprint_id"] == "failed-second-lexically"
