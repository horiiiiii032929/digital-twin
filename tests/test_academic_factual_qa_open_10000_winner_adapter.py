"""The winner-only adapter must bind confirmation 024 and call no provider."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from scripts import academic_factual_qa_open_10000_winner_adapter as winner
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)


COURSES = (
    "computer-networking",
    "data-structures",
    "operating-systems",
    "python-programming",
)
SENTENCE = (
    "Distance vector routing exchanges reachability tables between neighbours "
    "so that each router converges on a shortest path."
)


def _chunk(course_id: str, ordinal: int) -> dict[str, object]:
    text = f"{SENTENCE} This paragraph belongs to {course_id} section {ordinal}."
    return {
        "id": f"source-region-{course_id}-{ordinal}",
        "document_id": f"{course_id}:principles/dv.rst",
        "text": text,
        "ordinal": ordinal,
        "source_artifact_id": f"{course_id}:principles/dv.rst",
        "source_version": 1,
        "source_label": "course-approved",
        "locator": f"principles/dv.rst characters {ordinal * 100}–{ordinal * 100 + len(text)}",
        "source_checksum": f"{ordinal:064x}",
        "region_id": f"source-region-{course_id}-{ordinal}",
        "retrieval_allowed": True,
        "display_allowed": True,
        "metadata": {
            "title": f"{course_id} section {ordinal}",
            "course_id": course_id,
            "char_start": str(ordinal * 100),
            "char_end": str(ordinal * 100 + len(text)),
            "source_path": "principles/dv.rst",
            "search_description": text,
            "source_family_id": f"family-{course_id}-{ordinal}",
            "parent_cluster_id": f"academic-open-final-{course_id}-{ordinal}",
        },
    }


@pytest.fixture()
def corpus_path(tmp_path: Path) -> Path:
    path = tmp_path / "final-source-corpus.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "split": "final-retrieval-corpus",
                "chunks": [
                    _chunk(course_id, ordinal)
                    for course_id in COURSES
                    for ordinal in range(1, 4)
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _cases() -> list[EvaluationCaseV1]:
    return [
        EvaluationCaseV1(
            case_id=f"academic-open-final-0000{index}-q1",
            cluster_id=f"academic-open-final-0000{index}",
            source_family_id="0123456789abcdef01234567",
            course_id=course_id,
            question="What does distance vector routing exchange between neighbours?",
            split="final",
            slice="direct-factual",
            author_family="deterministic-canonical-fallback-v1",
        )
        for index, course_id in enumerate(COURSES, start=1)
    ]


def _manifest(evidence_gate: str, generator: str) -> SystemUnderTestManifestV1:
    return SystemUnderTestManifestV1(
        flow_id=winner.WINNER_FLOW_ID,
        adapter_version="v1",
        code_revision="2bac95d",
        profile_sha256=winner.winner_profile_sha256(),
        retriever=winner.WINNER_RETRIEVER_ID,
        generator=generator,
        policy="deterministic-tutor-action-router-v3",
        evidence_gate=evidence_gate,
        known_benchmark=True,
    )


def _candidate_manifest() -> SystemUnderTestManifestV1:
    return _manifest(winner.CANDIDATE_EVIDENCE_GATE, winner.WINNER_GENERATOR_ID)


def _control_manifest() -> SystemUnderTestManifestV1:
    return _manifest(winner.CONTROL_EVIDENCE_GATE, winner.WINNER_GENERATOR_ID)


def _run(adapter, cases, manifest, tmp_path: Path) -> ResponseLedgerV1:
    ledger = ResponseLedgerV1(
        tmp_path / "responses.sqlite3",
        cases_sha256=canonical_json_sha256([row.model_dump(mode="json") for row in cases]),
        system_manifest_sha256=canonical_json_sha256(manifest.model_dump(mode="json")),
        run_configuration_sha256=canonical_json_sha256({"arm": "test"}),
        resume=False,
    )
    asyncio.run(
        execute_cases(cases=cases, adapter=adapter, manifest=manifest, ledger=ledger)
    )
    return ledger


def test_candidate_binds_the_confirmation_024_components(corpus_path: Path, tmp_path: Path) -> None:
    adapter = winner.build_winner_adapter(
        manifest=_candidate_manifest(),
        cases=_cases(),
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
        },
    )

    assert adapter.condition == "candidate"
    assert adapter.evidence_gate_id == "source-semantic-evidence-atom-gate-v3"
    assert adapter.retriever_id == "source-semantic-evidence-atom-retriever-v1"
    assert adapter.generator_id == "deterministic-evidence-set-grounded-generator-v2"
    assert adapter.tutoring_mode == "governed-autonomous-tutoring-graph-v2.1"


def test_control_binds_the_any_hit_rollback_gate(corpus_path: Path, tmp_path: Path) -> None:
    adapter = winner.build_winner_adapter(
        manifest=_control_manifest(),
        cases=_cases(),
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
        },
    )

    assert adapter.condition == "control"
    assert adapter.evidence_gate_id == "any-hit-evidence-gate"


def test_the_deterministic_arm_makes_no_provider_call(corpus_path: Path, tmp_path: Path) -> None:
    cases = _cases()
    manifest = _candidate_manifest()
    adapter = winner.build_winner_adapter(
        manifest=manifest,
        cases=cases,
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
        },
    )

    ledger = _run(adapter, cases, manifest, tmp_path)

    assert adapter.provider_call_count == 0
    assert ledger.snapshot()["status"] == "completed"
    assert ledger.snapshot()["response_count"] == len(cases)


def test_every_response_carries_a_resolvable_lineage(corpus_path: Path, tmp_path: Path) -> None:
    cases = _cases()
    manifest = _candidate_manifest()
    adapter = winner.build_winner_adapter(
        manifest=manifest,
        cases=cases,
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
        },
    )

    ledger = _run(adapter, cases, manifest, tmp_path)
    rows = [
        json.loads(row[0])
        for row in ledger.connection.execute("SELECT payload_json FROM responses")
    ]

    assert {row["case_id"] for row in rows} == {row.case_id for row in cases}
    for row in rows:
        assert row["flow_id"] == winner.WINNER_FLOW_ID
        assert row["operational_status"] == "completed"
        assert row["usage"]["cost_usd"] == 0.0
        for citation in row["citations"]:
            assert citation["char_start"] is not None
            assert citation["char_end"] > citation["char_start"]


def test_cases_are_independent_by_default(corpus_path: Path, tmp_path: Path) -> None:
    """T1-v2 accumulates belief state, so a shared conversation would couple cases."""

    cases = _cases()
    adapter = winner.build_winner_adapter(
        manifest=_candidate_manifest(),
        cases=cases,
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
        },
    )

    assert adapter.conversation_scope == "case"


def test_repeating_one_case_is_stable_under_case_scope(
    corpus_path: Path, tmp_path: Path
) -> None:
    """The same question asked twice must not drift with accumulated state."""

    case = _cases()[0]
    repeated = [
        case.model_copy(update={"case_id": f"{case.case_id}-repeat-{index}"})
        for index in range(4)
    ]
    manifest = _candidate_manifest()
    adapter = winner.build_winner_adapter(
        manifest=manifest,
        cases=repeated,
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
        },
    )

    ledger = _run(adapter, repeated, manifest, tmp_path)
    rows = [
        json.loads(row[0])
        for row in ledger.connection.execute("SELECT payload_json FROM responses")
    ]

    assert len({row["action"] for row in rows}) == 1
    assert len({row["answer"] for row in rows}) == 1


def test_course_scope_can_still_be_requested(corpus_path: Path, tmp_path: Path) -> None:
    """Program 011 shared one conversation per course; keep that reproducible."""

    adapter = winner.build_winner_adapter(
        manifest=_candidate_manifest(),
        cases=_cases(),
        runtime={
            "state_path": tmp_path / "state.sqlite3",
            "source_package_path": corpus_path,
            "conversation_scope": "course",
        },
    )

    assert adapter.conversation_scope == "course"


def test_an_unknown_conversation_scope_is_refused(
    corpus_path: Path, tmp_path: Path
) -> None:
    with pytest.raises(winner.WinnerAdapterError, match="conversation scope"):
        winner.build_winner_adapter(
            manifest=_candidate_manifest(),
            cases=_cases(),
            runtime={
                "state_path": tmp_path / "state.sqlite3",
                "source_package_path": corpus_path,
                "conversation_scope": "release",
            },
        )


def test_an_unbound_evidence_gate_is_refused(corpus_path: Path, tmp_path: Path) -> None:
    manifest = _manifest(
        "ambiguity-safe-source-semantic-evidence-atoms-v2", winner.WINNER_GENERATOR_ID
    )

    with pytest.raises(winner.WinnerAdapterError, match="evidence gate"):
        winner.build_winner_adapter(
            manifest=manifest,
            cases=_cases(),
            runtime={
                "state_path": tmp_path / "state.sqlite3",
                "source_package_path": corpus_path,
            },
        )


def test_a_non_winner_generator_is_refused(corpus_path: Path, tmp_path: Path) -> None:
    manifest = _manifest(
        winner.CANDIDATE_EVIDENCE_GATE, "openai-gpt-5.4-mini-live-atomic"
    )

    with pytest.raises(winner.WinnerAdapterError, match="generator"):
        winner.build_winner_adapter(
            manifest=manifest,
            cases=_cases(),
            runtime={
                "state_path": tmp_path / "state.sqlite3",
                "source_package_path": corpus_path,
            },
        )


def test_a_flow_identity_mismatch_is_refused(corpus_path: Path, tmp_path: Path) -> None:
    manifest = _candidate_manifest().model_copy(update={"flow_id": "some-other-flow"})

    with pytest.raises(winner.WinnerAdapterError, match="flow"):
        winner.build_winner_adapter(
            manifest=manifest,
            cases=_cases(),
            runtime={
                "state_path": tmp_path / "state.sqlite3",
                "source_package_path": corpus_path,
            },
        )
