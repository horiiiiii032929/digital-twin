from __future__ import annotations

import inspect

import pytest

from scripts.academic_factual_qa_open_10000_t0_adapter import _setup_service
import scripts.qualify_retrieval_index_lifecycle as qualification
from scripts.qualify_retrieval_index_lifecycle import (
    QueryOnlyEmbedder,
    preflight,
    runtime_preflight,
    simulate,
    validate,
)


def test_query_only_embedder_rejects_runtime_document_embedding() -> None:
    delegate = qualification.SyntheticEmbedder()
    runtime = QueryOnlyEmbedder(delegate)

    assert runtime.embed_query("bounded query")
    with pytest.raises(qualification.IndexQualificationError):
        runtime.embed_documents(["must not execute"])
    assert runtime.query_calls == 1
    assert runtime.document_calls == 1


def test_completed_instrument_has_all_execution_authority_revoked() -> None:
    result = validate()

    assert result == {
        "instrument_id": "retrieval-index-lifecycle-development-001",
        "status": "passed-terminal-authorization-revoked",
        "source_region_count": 2100,
        "provider_calls": 0,
        "local_model_loaded": False,
        "final_cases_opened": False,
    }


def test_network_free_simulation_proves_runtime_load_invariants() -> None:
    result = simulate()

    assert result["source_region_count"] == 2100
    assert result["query_count"] == 40
    assert result["artifact_count"] == 4
    assert result["provider_calls"] == 0
    assert result["local_model_loaded"] is False
    assert result["final_cases_opened"] is False
    assert result["metrics"]["runtime_document_embedding_calls"] == 0
    assert result["metrics"]["restart_retrieval_consistency"] == 1
    assert result["metrics"]["retrieval_equivalence"] == 1
    assert result["metrics"]["binding_rejection_accuracy"] == 1
    assert result["metrics"]["corruption_detection_accuracy"] == 1
    gates = qualification._load(qualification.INSTRUMENT_PATH)["hard_gates"]
    assert (
        result["metrics"]["simulated_peak_python_memory_mib"]
        <= gates["simulated_peak_python_memory_mib_max"]
    )
    assert (
        result["metrics"]["simulated_artifact_size_mib"]
        <= gates["simulated_artifact_size_mib_max"]
    )
    expected_status = (
        "simulated-network-free-keep"
        if result["metrics"]["simulated_cold_load_seconds"]
        <= gates["simulated_cold_load_seconds_max"]
        else "simulated-network-free-refine"
    )
    # Wall-clock load is retained as a measured qualification result, but an
    # arbitrary busy test host must not turn deterministic integrity checks
    # into a flaky repository regression.
    assert result["status"] == expected_status


def test_completed_result_blocks_every_reexecution(
    tmp_path,
    monkeypatch,
) -> None:
    output = tmp_path / "indexes"
    output.mkdir()
    result_path = tmp_path / "result.json"
    runtime_result_path = tmp_path / "runtime-result.json"
    result_path.write_text("{}", encoding="utf-8")
    runtime_result_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(qualification, "OUTPUT_ROOT", output)
    monkeypatch.setattr(qualification, "RESULT_PATH", result_path)
    monkeypatch.setattr(qualification, "RUNTIME_RESULT_PATH", runtime_result_path)
    readiness = preflight()

    assert readiness["status"] == "blocked-not-authorized"
    assert "instrument-local-model-execution-authorized-false" in readiness["blockers"]
    assert "instrument-method-evaluation-execution-authorized-false" in readiness[
        "blockers"
    ]
    assert "freeze-local_model_evaluation-authorization-missing" in readiness[
        "blockers"
    ]
    assert "exclusive-output-already-exists" in readiness["blockers"]
    assert readiness["provider_calls"] == 0
    assert readiness["final_cases_opened"] is False
    runtime_readiness = runtime_preflight()
    assert runtime_readiness["status"] == "blocked-not-authorized"
    assert "instrument-local-model-execution-authorized-false" in runtime_readiness[
        "blockers"
    ]
    assert "exclusive-runtime-result-already-exists" in runtime_readiness["blockers"]


def test_resume_preflight_reuses_partial_index_root(
    tmp_path,
    monkeypatch,
) -> None:
    output = tmp_path / "indexes"
    output.mkdir()
    monkeypatch.setattr(qualification, "OUTPUT_ROOT", output)
    monkeypatch.setattr(qualification, "RESULT_PATH", tmp_path / "result.json")

    readiness = qualification.preflight(resume=True)

    assert readiness["status"] == "blocked-not-authorized"
    assert "exclusive-output-already-exists" not in readiness["blockers"]


def test_product_adapter_can_only_verify_prebuilt_indexes() -> None:
    source = inspect.getsource(_setup_service)

    assert "index_store.verify_bound(index_binding)" in source
    assert "index_store.build(" not in source
