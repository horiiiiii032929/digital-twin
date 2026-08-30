from __future__ import annotations

import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

from scripts.run_cross_course_retrieval_qualification import (
    build_providers,
    preflight_provider,
)
from services.embeddings.jina_client import JinaTextEmbedder
from services.embeddings.openai_client import OpenAITextEmbedder
from services.embeddings.fastembed_client import FastEmbedTextEmbedder
from services.embeddings.qwen3_client import Qwen3TextEmbedder
from services.reranking.jina_client import JinaReranker
from services.reranking.qwen3_client import Qwen3Reranker
from services.retrieval_provider import (
    RetrievalBudgetExceeded,
    RetrievalProviderError,
    RetrievalUsageLedger,
    bearer_headers,
    post_json,
)
from src.digital_twin.evaluation import load_provider_qualification_config
from src.digital_twin.model_policy import ModelPolicyError


CONFIG_PATH = (
    Path(__file__).resolve().parents[2] / "research/05_evaluation/instruments/"
    "cross_course_provider_qualification_v1.json"
)


def test_usage_ledger_blocks_before_cost_cap_and_records_no_content() -> None:
    ledger = RetrievalUsageLedger(
        max_cost_usd=0.000001,
        price_per_million_input_tokens_usd=1,
    )

    with pytest.raises(RetrievalBudgetExceeded, match="before exceeding"):
        ledger.require_capacity(2)

    snapshot = ledger.usage_snapshot()
    assert snapshot.request_count == 0
    assert snapshot.input_tokens == 0
    assert snapshot.approximate_cost_usd == 0


@pytest.mark.parametrize(
    "arguments",
    (
        {"max_cost_usd": True, "price_per_million_input_tokens_usd": 0},
        {"max_cost_usd": 1, "price_per_million_input_tokens_usd": False},
        {
            "max_cost_usd": 1,
            "price_per_million_input_tokens_usd": 0,
            "request_count": -1,
        },
    ),
)
def test_usage_ledger_rejects_invalid_numeric_state(arguments) -> None:
    with pytest.raises(ValueError):
        RetrievalUsageLedger(**arguments)


def test_usage_ledger_does_not_treat_boolean_usage_as_token_count() -> None:
    ledger = RetrievalUsageLedger(
        max_cost_usd=1,
        price_per_million_input_tokens_usd=1,
    )

    ledger.record(
        values=["synthetic"],
        estimated_input_tokens=4,
        response={"usage": {"input_tokens": True}},
    )

    assert ledger.input_tokens == 4


def test_fastembed_adapter_rejects_non_finite_and_dimension_drift(monkeypatch) -> None:
    class Vector:
        def __init__(self, values):
            self.values = values

        def tolist(self):
            return self.values

    class FakeModel:
        def __init__(self, **options):
            del options

        def passage_embed(self, texts):
            return [Vector([1.0, float("nan")]) for _ in texts]

        def query_embed(self, text):
            del text
            return [Vector([1.0])]

    monkeypatch.setitem(
        sys.modules,
        "fastembed",
        SimpleNamespace(TextEmbedding=FakeModel),
    )
    embedder = FastEmbedTextEmbedder()

    with pytest.raises(ValueError, match="non-finite"):
        embedder.embed_documents(["document"])

    embedder._model.passage_embed = lambda texts: [Vector([1.0, 0.0]) for _ in texts]
    assert embedder.embed_documents(["document"]) == [[1.0, 0.0]]
    with pytest.raises(ValueError, match="dimensions differ"):
        embedder.embed_query("query")


def test_bearer_headers_require_key_without_exposing_it_in_errors() -> None:
    with pytest.raises(ValueError, match="API key"):
        bearer_headers("")

    headers = bearer_headers("secret-token")
    assert headers["Authorization"] == "Bearer secret-token"


@pytest.mark.parametrize(
    "endpoint",
    (
        "http://api.example.test/v1",
        "https://user:secret@api.example.test/v1",
        "https://api.example.test/v1#fragment",
    ),
)
def test_hosted_retrieval_endpoints_require_plain_https(endpoint: str) -> None:
    ledger = RetrievalUsageLedger(
        max_cost_usd=1,
        price_per_million_input_tokens_usd=1,
    )
    with pytest.raises(ValueError, match="plain HTTPS"):
        JinaTextEmbedder("secret", ledger=ledger, endpoint=endpoint)
    with pytest.raises(ValueError, match="plain HTTPS"):
        JinaReranker("secret", ledger=ledger, endpoint=endpoint)
    with pytest.raises(ValueError, match="plain HTTPS"):
        post_json(endpoint, {}, {}, 1)


@pytest.mark.parametrize(
    ("adapter", "arguments"),
    (
        (Qwen3TextEmbedder, {"device": "remote"}),
        (Qwen3TextEmbedder, {"dtype": "int8"}),
        (Qwen3Reranker, {"device": "remote"}),
        (Qwen3Reranker, {"dtype": "int8"}),
    ),
)
def test_local_qwen_adapters_reject_unsupported_runtime_modes(
    tmp_path: Path,
    adapter,
    arguments,
) -> None:
    model_path = tmp_path / "model"
    model_path.mkdir()

    with pytest.raises(ValueError):
        adapter(model_path, instruction="Synthetic instruction", **arguments)


def test_hosted_preflight_requires_external_credential_without_calling_provider(
    monkeypatch,
) -> None:
    config = load_provider_qualification_config(CONFIG_PATH)
    pair = next(
        provider for provider in config.providers if provider.role == "candidate"
    )
    monkeypatch.delenv("JINA_API_KEY", raising=False)

    with pytest.raises(ValueError, match="JINA_API_KEY"):
        preflight_provider(pair)

    monkeypatch.setenv("JINA_API_KEY", "external-secret")
    assert preflight_provider(pair) == {
        "execution": "hosted",
        "credential_present": True,
        "provider_calls": 0,
    }


def test_local_provider_runtime_overrides_are_independent(
    monkeypatch, tmp_path
) -> None:
    config = load_provider_qualification_config(CONFIG_PATH)
    pair = next(provider for provider in config.providers if provider.role == "control")
    embedding_path = tmp_path / "embedding"
    reranking_path = tmp_path / "reranking"
    embedding_path.mkdir()
    reranking_path.mkdir()

    monkeypatch.setattr(
        "scripts.run_cross_course_retrieval_qualification.model_path",
        lambda model, revision: (
            embedding_path if "Embedding" in model else reranking_path
        ),
    )

    class FakeEmbedder:
        model_load_seconds = 0.1

        def __init__(self, model_path, **kwargs):
            del model_path
            self.batch_size = kwargs["batch_size"]
            self.max_length = kwargs["max_length"]

    class FakeReranker:
        model_load_seconds = 0.2

        def __init__(self, model_path, **kwargs):
            del model_path
            self.batch_size = kwargs["batch_size"]
            self.max_length = kwargs["max_length"]

    monkeypatch.setattr(
        "scripts.run_cross_course_retrieval_qualification.Qwen3TextEmbedder",
        FakeEmbedder,
    )
    monkeypatch.setattr(
        "scripts.run_cross_course_retrieval_qualification.Qwen3Reranker",
        FakeReranker,
    )

    embedder, reranker, load, ledger = build_providers(
        pair,
        config,
        batch_size=8,
        embedding_batch_size=16,
        reranking_batch_size=6,
        embedding_max_length=1536,
        reranking_max_length=768,
        device="cpu",
        dtype="float32",
    )

    assert embedder.batch_size == 16
    assert embedder.max_length == 1536
    assert reranker.batch_size == 6
    assert reranker.max_length == 768
    assert load == {"embedding_model_load": 0.1, "reranking_model_load": 0.2}
    assert ledger is None


def test_jina_embedding_contract_records_provider_usage() -> None:
    requests = []

    def transport(url, headers, body, timeout):
        requests.append((url, headers, body, timeout))
        return {
            "usage": {"total_tokens": 6},
            "data": [
                {"index": index, "embedding": [float(index + 1), 1.0]}
                for index, _ in enumerate(body["input"])
            ],
        }

    ledger = RetrievalUsageLedger(
        max_cost_usd=1,
        price_per_million_input_tokens_usd=1,
    )
    embedder = JinaTextEmbedder(
        "secret-token",
        ledger=ledger,
        dimensions=2,
        batch_size=2,
        transport=transport,
    )

    vectors = embedder.embed_documents(["first", "second"])
    query = embedder.embed_query("question")

    assert vectors == [[1.0, 1.0], [2.0, 1.0]]
    assert query == [1.0, 1.0]
    assert requests[0][2]["task"] == "retrieval.passage"
    assert requests[1][2]["task"] == "retrieval.query"
    assert requests[0][2]["model"] == "jina-embeddings-v5-text-small"
    usage = embedder.usage_snapshot()
    assert usage.request_count == 2
    assert usage.input_tokens == 12
    assert usage.approximate_cost_usd == pytest.approx(0.000012)


def test_openai_embedding_contract_requires_exact_identity_and_indexes() -> None:
    requests = []

    def transport(url, headers, body, timeout):
        requests.append((url, headers, body, timeout))
        return {
            "object": "list",
            "model": body["model"],
            "usage": {"prompt_tokens": 7, "total_tokens": 7},
            "data": [
                {"index": 1, "embedding": [0.0, 2.0]},
                {"index": 0, "embedding": [1.0, 0.0]},
            ],
        }

    ledger = RetrievalUsageLedger(
        max_cost_usd=1,
        price_per_million_input_tokens_usd=0.02,
    )
    embedder = OpenAITextEmbedder(
        "secret-token",
        ledger=ledger,
        dimensions=2,
        batch_size=2,
        transport=transport,
    )

    assert embedder.embed_documents(["first", "second"]) == [
        [1.0, 0.0],
        [0.0, 2.0],
    ]
    assert requests[0][0] == "https://api.openai.com/v1/embeddings"
    assert requests[0][2] == {
        "model": "text-embedding-3-small",
        "input": ["first", "second"],
        "encoding_format": "float",
        "dimensions": 2,
    }
    assert ledger.usage_snapshot().input_tokens == 7


def test_openai_embedding_contract_rejects_identity_and_token_drift() -> None:
    ledger = RetrievalUsageLedger(
        max_cost_usd=1,
        price_per_million_input_tokens_usd=0.02,
    )

    def wrong_identity(url, headers, body, timeout):
        del url, headers, timeout
        return {
            "model": "text-embedding-3-large",
            "data": [{"index": 0, "embedding": [1.0, 0.0]}],
        }

    embedder = OpenAITextEmbedder(
        "secret-token",
        ledger=ledger,
        dimensions=2,
        transport=wrong_identity,
    )
    with pytest.raises(RetrievalProviderError, match="identity drifted"):
        embedder.embed_query("question")

    bounded = OpenAITextEmbedder(
        "secret-token",
        ledger=RetrievalUsageLedger(
            max_cost_usd=1,
            price_per_million_input_tokens_usd=0.02,
        ),
        dimensions=2,
        request_token_limit=1,
        transport=wrong_identity,
    )
    with pytest.raises(RetrievalProviderError, match="request token"):
        bounded.embed_documents(["more than three characters"])


def test_jina_reranker_restores_original_document_order() -> None:
    def transport(url, headers, body, timeout):
        del url, headers, timeout
        assert body["return_documents"] is False
        return {
            "usage": {"total_tokens": 4},
            "results": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.2},
            ],
        }

    ledger = RetrievalUsageLedger(
        max_cost_usd=1,
        price_per_million_input_tokens_usd=1,
    )
    reranker = JinaReranker(
        "secret-token",
        ledger=ledger,
        transport=transport,
    )

    assert reranker.score("query", ["first", "second"]) == [0.2, 0.9]
    assert reranker.usage_snapshot().request_count == 1


def test_jina_adapters_reject_malformed_shapes_without_response_content() -> None:
    def malformed(url, headers, body, timeout):
        del url, headers, body, timeout
        return {"data": [{"index": 0, "embedding": "secret bad shape"}]}

    embedder = JinaTextEmbedder(
        "secret-token",
        ledger=RetrievalUsageLedger(
            max_cost_usd=1,
            price_per_million_input_tokens_usd=1,
        ),
        transport=malformed,
    )

    with pytest.raises(RetrievalProviderError) as raised:
        embedder.embed_query("private query")

    assert "secret" not in str(raised.value)
    assert "private query" not in str(raised.value)


@pytest.mark.parametrize(
    "embedding",
    ([1.0], [1.0, float("nan")]),
)
def test_jina_embedder_rejects_wrong_or_non_finite_vectors(embedding) -> None:
    def malformed(url, headers, body, timeout):
        del url, headers, body, timeout
        return {"data": [{"index": 0, "embedding": embedding}]}

    embedder = JinaTextEmbedder(
        "secret-token",
        dimensions=2,
        ledger=RetrievalUsageLedger(
            max_cost_usd=1,
            price_per_million_input_tokens_usd=1,
        ),
        transport=malformed,
    )

    with pytest.raises(RetrievalProviderError):
        embedder.embed_query("private query")
    assert embedder.usage_snapshot().failure_count == 1


@pytest.mark.parametrize("score", [float("nan"), -0.1, 1.1])
def test_jina_reranker_rejects_invalid_scores(score) -> None:
    def malformed(url, headers, body, timeout):
        del url, headers, body, timeout
        return {"results": [{"index": 0, "relevance_score": score}]}

    reranker = JinaReranker(
        "secret-token",
        ledger=RetrievalUsageLedger(
            max_cost_usd=1,
            price_per_million_input_tokens_usd=1,
        ),
        transport=malformed,
    )

    with pytest.raises(RetrievalProviderError):
        reranker.score("private query", ["private document"])
    assert reranker.usage_snapshot().failure_count == 1


@pytest.mark.parametrize(
    ("adapter", "model"),
    (
        (JinaTextEmbedder, "jina-embeddings-v4"),
        (JinaReranker, "jina-reranker-v2-base-multilingual"),
        (JinaTextEmbedder, "gemma3:4b"),
    ),
)
def test_jina_adapters_reject_unregistered_or_prohibited_models(adapter, model) -> None:
    with pytest.raises(ModelPolicyError):
        adapter(
            "secret-token",
            ledger=RetrievalUsageLedger(
                max_cost_usd=1,
                price_per_million_input_tokens_usd=1,
            ),
            model=model,
        )
