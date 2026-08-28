from __future__ import annotations

import inspect

import pytest

from scripts.academic_factual_qa_open_10000_t0_adapter import _setup_service
import scripts.qualify_retrieval_index_lifecycle as qualification
from scripts.qualify_retrieval_index_lifecycle import (
    execute_local,
    preflight,
    simulate,
    validate,
)
from src.digital_twin.repository_freeze import RepositoryFreezeError


def test_build_only_instrument_keeps_every_execution_authority_false() -> None:
    result = validate()

    assert result == {
        "instrument_id": "retrieval-index-lifecycle-development-001",
        "status": "passed-build-only",
        "source_region_count": 2100,
        "provider_calls": 0,
        "local_model_loaded": False,
        "final_cases_opened": False,
    }


def test_network_free_simulation_proves_runtime_load_invariants() -> None:
    result = simulate()

    assert result["status"] == "simulated-network-free-keep"
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


def test_live_preflight_and_local_execution_fail_closed() -> None:
    readiness = preflight()

    assert readiness["status"] == "blocked-not-authorized"
    assert "instrument-local-model-execution-authorized-false" in readiness[
        "blockers"
    ]
    assert "instrument-method-evaluation-execution-authorized-false" in readiness[
        "blockers"
    ]
    assert readiness["provider_calls"] == 0
    assert readiness["final_cases_opened"] is False

    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        execute_local()


def test_resume_preflight_reuses_partial_index_root_without_authorizing_execution(
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
