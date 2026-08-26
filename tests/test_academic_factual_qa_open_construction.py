from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts.construct_academic_factual_qa_open_10000 import (
    AUTHOR_SCHEMA,
    VERIFIER_SCHEMA,
    simulate,
    preflight as construction_preflight,
    validate,
)
from src.digital_twin.evaluation import (
    AuthoredClusterVariantsV1,
    ClusterDraftV1,
    EvaluationAction,
    EvaluationSplit,
    SourceClusterV1,
    assemble_deterministic_verified_cluster,
    build_deterministic_cluster_truth,
)
from src.digital_twin.evaluation.provider_json import ProviderCallLedgerV1


def _cluster(*, boundary_slice: str = "cross-course") -> SourceClusterV1:
    text = (
        "A process is a program in execution. Each process has an address space. "
        "The scheduler selects a runnable process. A context switch preserves state."
    )
    return SourceClusterV1(
        cluster_id="cluster-001",
        source_family_id="family-001",
        course_id="operating-systems",
        source_artifact_id="operating-systems:processes.md",
        source_version=1,
        source_sha256="a" * 64,
        source_path="processes.md",
        section_heading="Processes",
        char_start=100,
        char_end=100 + len(text),
        text=text,
        source_modality="text",
        split=EvaluationSplit.DEVELOPMENT,
        answerable_slices=[
            "direct-factual",
            "paraphrased",
            "definition-explanation",
            "multi-evidence",
        ],
        boundary_slice=boundary_slice,
        author_family="deepseek-v4-flash",
        verifier_family="gemini-3.7-flash",
        license_spdx="CC-BY-4.0",
        repository_url="https://example.test/open-course",
        repository_commit="b" * 40,
    )


def _assembled_inputs(cluster: SourceClusterV1):
    truth = build_deterministic_cluster_truth(
        cluster,
        course_ids=("operating-systems", "computer-networking"),
    )
    authored = AuthoredClusterVariantsV1(
        cluster_id=cluster.cluster_id,
        questions=[
            {
                "case_id": row.case_id,
                "question": f"Which source statement correctly addresses item {index}?",
            }
            for index, row in enumerate(truth.questions, start=1)
        ],
    )
    verifier = ClusterDraftV1(
        cluster_id=cluster.cluster_id,
        questions=[
            {
                "case_id": row.case_id,
                "question": authored.questions[index].question,
                "action": row.action,
                "answer": row.canonical_answer,
                "evidence_spans": [span.model_dump() for span in row.evidence_spans],
                "boundary_reason": row.boundary_reason,
            }
            for index, row in enumerate(truth.questions)
        ],
    )
    return truth, authored, verifier


def test_deterministic_truth_precedes_and_controls_model_outputs() -> None:
    cluster = _cluster()
    truth, authored, verifier = _assembled_inputs(cluster)

    cases, gold = assemble_deterministic_verified_cluster(
        cluster, truth, authored, verifier
    )

    assert len(cases) == len(gold) == 5
    assert gold[0].canonical_answer == truth.questions[0].canonical_answer
    assert cases[-1].course_id == "computer-networking"
    assert gold[-1].expected_action == EvaluationAction.ABSTAIN
    assert gold[-1].claims == []


def test_verifier_cannot_mutate_authoritative_answer_or_action() -> None:
    cluster = _cluster()
    truth, authored, verifier = _assembled_inputs(cluster)
    verifier.questions[0].answer = "A different answer"

    with pytest.raises(ValueError, match="verifier answer or evidence disagreement"):
        assemble_deterministic_verified_cluster(cluster, truth, authored, verifier)

    _, authored, verifier = _assembled_inputs(cluster)
    verifier.questions[-1].action = EvaluationAction.ANSWER
    with pytest.raises(ValueError, match="verifier action disagreement"):
        assemble_deterministic_verified_cluster(cluster, truth, authored, verifier)


def test_provider_output_schemas_do_not_let_author_define_gold() -> None:
    rendered = str(AUTHOR_SCHEMA)
    assert "answer" not in AUTHOR_SCHEMA["properties"]["questions"]["items"]["properties"]
    assert "evidence_spans" not in rendered
    assert set(VERIFIER_SCHEMA["properties"]["questions"]["items"]["properties"]) >= {
        "action",
        "answer",
        "evidence_spans",
    }


def test_construction_validate_and_simulation_are_network_free() -> None:
    assert validate()["provider_calls"] == 0
    result = simulate()
    assert result["status"] == "simulated-network-free"
    assert result["case_count"] == 5
    assert result["provider_calls"] == 0


def test_successor_preflight_requires_instrument_and_binding_authorization() -> None:
    result = construction_preflight(
        stage="development",
        ledger_path=Path(
            "data/interim/academic_factual_qa_open_10000_v1_test-do-not-create.sqlite3"
        ),
        resume=False,
    )

    assert result["status"] == "blocked-not-authorized"
    assert "dataset-construction-authorized-false" in result["blockers"]
    assert (
        "provider-binding-dataset-construction-authorized-false"
        in result["blockers"]
    )


def test_provider_ledger_binds_resume_and_budget(tmp_path: Path) -> None:
    path = tmp_path / "provider.sqlite3"
    ledger = ProviderCallLedgerV1(
        path,
        run_binding={"run": "one"},
        maximum_calls=2,
        maximum_cost_usd=1,
        resume=False,
    )
    ledger.mark_interrupted()
    ledger.close()

    resumed = ProviderCallLedgerV1(
        path,
        run_binding={"run": "one"},
        maximum_calls=2,
        maximum_cost_usd=1,
        resume=True,
    )
    resumed.close()
    with pytest.raises(RuntimeError, match="binding drifted"):
        ProviderCallLedgerV1(
            path,
            run_binding={"run": "two"},
            maximum_calls=2,
            maximum_cost_usd=1,
            resume=True,
        )


def test_provider_ledger_preserves_sanitized_failure_detail(tmp_path: Path) -> None:
    path = tmp_path / "provider-failure.sqlite3"
    ledger = ProviderCallLedgerV1(
        path,
        run_binding={"run": "failure"},
        maximum_calls=1,
        maximum_cost_usd=1,
        resume=False,
    )
    ledger.record_failed(
        request_key="canary:deepseek",
        request_sha256="a" * 64,
        provider_role="canary",
        failure_type="ProviderJsonError",
        failure_detail="expected='old' observed='new'",
        latency_ms=12.5,
    )
    ledger.close()

    connection = sqlite3.connect(path)
    row = connection.execute(
        "SELECT failure_type, failure_detail FROM calls"
    ).fetchone()
    connection.close()

    assert row == (
        "ProviderJsonError",
        "expected='old' observed='new'",
    )
