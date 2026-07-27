from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from services.embeddings import JinaTextEmbedder
from services.jina_api import JinaBudgetExceeded, JinaUsageLedger
from services.reranking import JinaReranker
from scripts.run_it5002_hosted_retrieval_preflight import load_api_key


def test_jina_embedder_uses_separate_passage_and_query_tasks() -> None:
    requests: list[dict[str, Any]] = []

    def transport(
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        del url, headers, timeout
        requests.append(body)
        return {
            "data": [
                {"index": index, "embedding": [float(index + 1), 0.5]}
                for index, _text in enumerate(body["input"])
            ],
            "usage": {"prompt_tokens": 7},
        }

    ledger = JinaUsageLedger(max_cost_usd=1)
    embedder = JinaTextEmbedder(
        "test-key",
        ledger=ledger,
        batch_size=2,
        transport=transport,
    )

    assert embedder.embed_documents(["first", "second"]) == [
        [1.0, 0.5],
        [2.0, 0.5],
    ]
    assert embedder.embed_query("question") == [1.0, 0.5]
    assert [request["task"] for request in requests] == [
        "retrieval.passage",
        "retrieval.query",
    ]
    assert ledger.request_count == 2
    assert ledger.input_tokens == 14


def test_jina_reranker_restores_original_document_order() -> None:
    def transport(
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        del url, headers, body, timeout
        return {
            "results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.2},
            ],
            "usage": {"total_tokens": 12},
        }

    ledger = JinaUsageLedger(max_cost_usd=1)
    reranker = JinaReranker("test-key", ledger=ledger, transport=transport)

    assert reranker.score("query", ["first", "second"]) == [0.2, 0.9]
    assert ledger.request_count == 1
    assert ledger.input_tokens == 12


def test_jina_budget_is_enforced_before_transport() -> None:
    called = False

    def transport(
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        del url, headers, body, timeout
        nonlocal called
        called = True
        return {}

    ledger = JinaUsageLedger(
        max_cost_usd=0.000001,
        price_per_million_input_tokens_usd=1,
    )
    embedder = JinaTextEmbedder("test-key", ledger=ledger, transport=transport)

    with pytest.raises(JinaBudgetExceeded):
        embedder.embed_query("a query that exceeds the declared budget")

    assert called is False


def test_hosted_runner_loads_key_from_ignored_env_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("JINA_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("JINA_API_KEY='local-secret'\n", encoding="utf-8")

    assert load_api_key(env_path) == "local-secret"
