from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_academic_factual_qa_api_retrieval_selection as selection
from src.digital_twin.evaluation.factual_qa_contract import (
    EvaluationCaseV1,
    EvaluationSplit,
)
from src.digital_twin.evaluation.retrieval_qualification import ProviderUsage
from src.digital_twin.repository_freeze import RepositoryFreezeError
from src.digital_twin.grounding import DocumentChunk


def test_api_retrieval_selection_validates_frozen_packages() -> None:
    result = selection.validate()

    assert result["status"] == "passed-terminal"
    assert result["source_cluster_count"] == 2_100
    assert result["selected_development_case_count"] == 300
    assert result["method_count"] == 7
    assert result["provider_calls"] == 0


def test_api_retrieval_selection_is_finite_across_simulations() -> None:
    passed = selection.simulate("pass")
    failed = selection.simulate("quality-failure")
    invalid = selection.simulate("identity-drift")

    assert passed["status"] == "completed-keep"
    assert passed["selected_method"] == "M5"
    assert failed["status"] == "completed-refine"
    assert failed["selected_method"] is None
    assert invalid["status"] == "invalid-execution"
    assert all(result["provider_calls"] == 0 for result in (passed, failed, invalid))


def test_api_retrieval_preflight_is_blocked_after_authority_revocation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-present")
    monkeypatch.setattr(selection, "_git_dirty", lambda: False)
    instrument = json.loads(json.dumps(selection._instrument()))
    instrument["metadata"]["verified_at"] = datetime.now(UTC).isoformat()
    monkeypatch.setattr(selection, "_instrument", lambda: instrument)

    result = selection.preflight(output_root=tmp_path / "unused")

    assert result["status"] == "blocked-not-authorized"
    assert result["technical_blockers"] == []
    assert result["authority_blockers"] == [
        "provider-execution-not-authorized",
        "paid-execution-not-authorized",
    ]
    assert result["model_or_provider_called"] is False


def test_api_retrieval_execution_authority_is_revoked() -> None:
    with pytest.raises(RepositoryFreezeError, match="not a bounded authorization"):
        selection.require_bounded_pilot_operation_allowed(
            selection.INSTRUMENT_ID,
            "external_model_evaluation",
        )


def test_optional_reranker_semantic_failure_is_isolated_without_retry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    cases = [
        EvaluationCaseV1(
            case_id=f"case-{index}",
            cluster_id=f"cluster-{index}",
            source_family_id=f"source-{index}",
            course_id="course-a",
            question=f"Which evidence supports concept {index}?",
            split=EvaluationSplit.DEVELOPMENT,
            slice="paraphrase",
            author_family="synthetic-test",
        )
        for index in range(3)
    ]
    chunks = {
        identifier: DocumentChunk(
            id=identifier,
            document_id=identifier,
            text=f"Evidence from {identifier}.",
            ordinal=index,
            source_artifact_id=identifier,
            source_version=1,
            retrieval_allowed=True,
            metadata={"course_id": "course-a"},
        )
        for index, identifier in enumerate(("chunk-0", "chunk-1"))
    }

    class FakeTransport:
        calls = 0

        def __init__(self, _binding) -> None:
            pass

        async def call_with_ledger(self, **kwargs):
            self.calls += 1
            case_id = json.loads(kwargs["prompt"])[0]["case_id"]
            return SimpleNamespace(
                content={
                    "items": [
                        {
                            "case_id": case_id,
                            "ranked_chunk_ids": ["chunk-0"],
                        }
                    ]
                }
            )

    monkeypatch.setattr(selection, "DirectProviderJsonTransport", FakeTransport)
    monkeypatch.setattr(selection, "should_use_semantic_reranking", lambda *_args, **_kwargs: True)

    output, usage = asyncio.run(
        selection._nano_rerank(
            cases=cases,
            rankings={
                "M5": {
                    case.case_id: ["chunk-0", "chunk-1"] for case in cases
                }
            },
            score_margins={case.case_id: 0.0 for case in cases},
            chunks_by_id=chunks,
            output_root=tmp_path,
            resume=False,
        )
    )

    assert output == {
        case.case_id: ["chunk-0", "chunk-1"] for case in cases
    }
    assert usage["method_status"] == "failed-semantic-output"
    assert usage["semantic_failure"]["reason"] == "chunk-id-set-drift"


def test_query_vector_cache_is_hash_bound_and_resume_safe(tmp_path: Path) -> None:
    cases = [
        EvaluationCaseV1(
            case_id=f"case-{index}",
            cluster_id=f"cluster-{index}",
            source_family_id=f"source-{index}",
            course_id="course-a",
            question=f"Question {index}?",
            split=EvaluationSplit.DEVELOPMENT,
            slice="direct-factual",
            author_family="synthetic-test",
        )
        for index in range(3)
    ]

    class FakeEmbedder:
        def __init__(self, *, fail: bool = False) -> None:
            self.calls = 0
            self.fail = fail
            self.usage = ProviderUsage()

        def usage_snapshot(self):
            return self.usage

        def embed_documents(self, texts):
            self.calls += 1
            if self.fail:
                raise AssertionError("completed cache attempted a provider call")
            self.usage = self.usage.model_copy(
                update={
                    "request_count": self.usage.request_count + 1,
                    "input_tokens": self.usage.input_tokens + len(texts),
                    "approximate_cost_usd": self.usage.approximate_cost_usd
                    + len(texts) * 0.02 / 1_000_000,
                }
            )
            return [[1.0, float(index + 1)] for index, _ in enumerate(texts)]

    path = tmp_path / "queries.sqlite3"
    first = FakeEmbedder()
    vectors, usage = selection._query_vectors(
        path=path,
        cases=cases,
        embedder=first,
        model="text-embedding-3-small",
        dimensions=2,
        instrument_sha256="a" * 64,
        resume=False,
    )
    resumed = FakeEmbedder(fail=True)
    replayed, replay_usage = selection._query_vectors(
        path=path,
        cases=cases,
        embedder=resumed,
        model="text-embedding-3-small",
        dimensions=2,
        instrument_sha256="a" * 64,
        resume=True,
    )

    assert set(vectors) == {row.question for row in cases}
    assert replayed == vectors
    assert usage == replay_usage
    assert first.calls == 1
    assert resumed.calls == 0
