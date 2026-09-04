import json
import sqlite3

import pytest

from scripts import run_product_evidence_gate_selection_004 as selection
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationResponseV1,
    EvaluationSplit,
    SystemUnderTestManifestV1,
)
from src.digital_twin.evaluation.factual_qa_execution import (
    ResponseLedgerV1,
    canonical_json_sha256,
)


def _case() -> EvaluationCaseV1:
    return EvaluationCaseV1(
        case_id="case-001",
        cluster_id="cluster-001",
        source_family_id="source-family-001",
        course_id="course-001",
        question="What is the documented fact?",
        split=EvaluationSplit.DEVELOPMENT,
        slice="direct-factual",
        author_family="deterministic",
    )


def _manifest() -> SystemUnderTestManifestV1:
    return SystemUnderTestManifestV1(
        flow_id="test-flow",
        adapter_version="v1",
        code_revision="abcdef0",
        profile_sha256="a" * 64,
        retriever="test-retriever",
        generator="test-generator",
        policy="test-policy",
        evidence_gate="test-gate",
    )


def _completed_ledger(tmp_path, monkeypatch):
    case = _case()
    manifest = _manifest()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps({"content_sha256": "b" * 64, "cases": [case.model_dump(mode="json")]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(selection, "CASES_PATH", cases_path)
    ledger_path = tmp_path / "responses.sqlite3"
    metadata = selection._expected_ledger_metadata(
        "candidate",
        [case],
        manifest,
        source_instrument_id=selection.LEDGER_SOURCE_INSTRUMENT_ID,
    )
    ledger = ResponseLedgerV1(
        ledger_path,
        cases_sha256=metadata["cases_sha256"],
        system_manifest_sha256=metadata["system_manifest_sha256"],
        run_configuration_sha256=metadata["run_configuration_sha256"],
        resume=False,
    )
    ledger.record(
        EvaluationResponseV1(
            case_id=case.case_id,
            flow_id=manifest.flow_id,
            action=EvaluationAction.CLARIFY,
            answer="Please clarify the requested fact.",
            operational_status="completed",
        )
    )
    ledger.mark_complete(expected_count=1)
    ledger.close()
    return ledger_path, case, manifest


def test_completed_selection_ledger_requires_full_binding(tmp_path, monkeypatch):
    ledger_path, case, manifest = _completed_ledger(tmp_path, monkeypatch)

    verification = selection._validate_completed_ledger(
        arm_id="candidate",
        path=ledger_path,
        cases=[case],
        manifest=manifest,
    )

    assert verification["verified_response_count"] == 1
    assert len(verification["ledger_sha256"]) == 64

    connection = sqlite3.connect(ledger_path)
    with connection:
        connection.execute(
            "UPDATE metadata SET value = ? WHERE key = 'system_manifest_sha256'",
            (canonical_json_sha256({"drifted": True}),),
        )
    connection.close()

    with pytest.raises(selection.GateSelectionError, match="binding drifted"):
        selection._validate_completed_ledger(
            arm_id="candidate",
            path=ledger_path,
            cases=[case],
            manifest=manifest,
        )


def test_completed_selection_ledger_rejects_payload_hash_drift(tmp_path, monkeypatch):
    ledger_path, case, manifest = _completed_ledger(tmp_path, monkeypatch)
    connection = sqlite3.connect(ledger_path)
    with connection:
        connection.execute(
            "UPDATE responses SET payload_json = ? WHERE case_id = ?",
            (json.dumps({"case_id": case.case_id}), case.case_id),
        )
    connection.close()

    with pytest.raises(selection.GateSelectionError, match="payload hash drifted"):
        selection._validate_completed_ledger(
            arm_id="candidate",
            path=ledger_path,
            cases=[case],
            manifest=manifest,
        )


def test_score_arm_uses_answerable_factual_metric(monkeypatch):
    monkeypatch.setattr(
        selection,
        "score_packages",
        lambda **_kwargs: {
            "summary": {
                "metrics": {"fully_grounded_factual_success": 0.425},
                "overall_grounded_task_success": 0.5,
                "severe_unsupported_release_count": 0,
                "operational_failure_count": 0,
                "case_count": 500,
            },
            "gate_results": {},
            "status": "completed-refine",
        },
    )
    monkeypatch.setattr(selection, "_pairing_manifest", lambda path: path)

    score = selection._score_arm("candidate")

    assert score["fully_grounded_factual_success"] == 0.425
    assert score["overall_grounded_task_success"] == 0.5
