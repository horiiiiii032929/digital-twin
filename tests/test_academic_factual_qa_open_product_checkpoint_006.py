from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import academic_factual_qa_open_10000_t0_adapter as live_adapter
from scripts import run_academic_factual_qa_open_product_checkpoint_005 as historical
from scripts import run_academic_factual_qa_open_product_checkpoint_006 as checkpoint


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_successor_is_build_only_and_binds_qualified_indexes() -> None:
    result = checkpoint.validate()
    assert result["status"] == "passed-build-only"
    assert result["case_count"] == 500
    assert result["control_case_count"] == 100
    assert result["maximum_calls"] == 666
    assert result["maximum_cost_usd"] == 8.0
    assert result["retrieval_index_qualification"] == "completed-keep"
    assert result["retrieval_index_artifact_count"] == 4
    assert result["runtime_document_embedding_requests"] == 0

    instrument = _load(checkpoint.INSTRUMENT_PATH)
    lifecycle = instrument["retrieval_index_lifecycle"]
    assert lifecycle["qualification_decision_record"] == "AFQC-068"
    assert lifecycle["runtime_document_embedding_requests_max"] == 0
    assert lifecycle["startup_policy"] == (
        "verify-and-load-exact-artifacts-only-never-build"
    )
    assert len(lifecycle["artifact_ids"]) == 4
    assert not any(instrument["authorization"].values())
    assert instrument["execution"]["final_execution_authorized"] is False


def test_successor_does_not_mutate_historical_checkpoint() -> None:
    before = historical.validate()
    checkpoint.validate()
    after = historical.validate()
    assert before == after
    assert historical.INSTRUMENT_ID.endswith("checkpoint-005")
    assert historical.CHECKPOINT_STATE.name.endswith("checkpoint-005-state.json")


def test_candidate_and_control_share_exact_index_lifecycle() -> None:
    candidate = _load(checkpoint.CANDIDATE_MANIFEST)
    control = _load(checkpoint.CONTROL_MANIFEST)
    assert candidate["known_benchmark"] is True
    assert candidate["retriever"] == control["retriever"]
    assert candidate["model_bindings"] == control["model_bindings"]
    assert candidate["model_bindings"]["retrieval-index-lifecycle"] == (
        "retrieval-index-lifecycle-development-001@AFQC-068"
    )
    for key in set(candidate) - {"flow_id", "evidence_gate"}:
        assert candidate[key] == control[key]


def test_local_index_preflight_verifies_all_exact_artifacts() -> None:
    instrument = _load(checkpoint.INSTRUMENT_PATH)
    assert checkpoint._verify_local_indexes(instrument) == instrument[
        "retrieval_index_lifecycle"
    ]["artifact_ids"]
    adapter_source = Path(live_adapter.__file__).read_text(encoding="utf-8")
    setup_source = adapter_source[
        adapter_source.index("def _setup_service(") : adapter_source.index(
            "def build_live_t0_adapter("
        )
    ]
    assert "index_store.verify_bound(index_binding)" in setup_source
    assert "index_store.build(" not in setup_source


def test_missing_local_indexes_block_preflight(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(checkpoint, "INDEX_ROOT", tmp_path / "missing-indexes")
    monkeypatch.setattr(checkpoint, "_repo_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = checkpoint.preflight()
    assert result["status"] == "blocked-not-authorized"
    assert any(
        blocker.startswith("retrieval-index-verification-failed:")
        for blocker in result["blockers"]
    )
    assert result["provider_calls"] == 0


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("pass", "completed-keep"),
        ("product-failure", "completed-refine"),
        ("provider-failure", "invalid-execution"),
        ("advisory-malformed", "completed-keep"),
        ("truth-defect", "needs-human-review"),
    ],
)
def test_successor_simulations_are_finite(scenario: str, expected: str) -> None:
    result = checkpoint.simulate(scenario=scenario)
    assert result["status"] == expected
    assert result["retrieval_index_mode"] == "immutable-load-only"
    assert result["runtime_document_embedding_requests"] == 0
    assert result["provider_calls"] == 0
    assert result["hidden_gold_visible_to_product"] is False


def test_clean_preflight_is_blocked_by_authority_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(checkpoint, "_repo_dirty", lambda: False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = checkpoint.preflight()
    assert result["status"] == "blocked-not-authorized"
    assert result["runtime_document_embedding_requests"] == 0
    assert not any(
        blocker.startswith("retrieval-index-verification-failed:")
        for blocker in result["blockers"]
    )
    assert not any(
        blocker in {"repository-dirty", "openai-api-key-missing", "provider-metadata-stale"}
        for blocker in result["blockers"]
    )
    assert all(
        "authorization" in blocker or blocker.endswith("-false")
        for blocker in result["blockers"]
    )


def test_resume_binds_exact_retrieval_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_path = tmp_path / "checkpoint-state.json"
    monkeypatch.setattr(checkpoint, "CHECKPOINT_STATE", state_path)
    monkeypatch.setattr(checkpoint, "_repo_revision", lambda: "revision")
    instrument = _load(checkpoint.INSTRUMENT_PATH)
    binding = _load(checkpoint.BINDING_PATH)
    state = checkpoint._initial_state(instrument, binding)
    checkpoint._write_state(state, exclusive=True)
    assert checkpoint._resume_state(instrument, binding)["status"] == "running"

    changed = json.loads(json.dumps(instrument))
    changed["retrieval_index_lifecycle"]["artifact_ids"]["computer-networking"] = (
        "0" * 64
    )
    with pytest.raises(checkpoint.ProductCheckpointError, match="binding drifted"):
        checkpoint._resume_state(changed, binding)
