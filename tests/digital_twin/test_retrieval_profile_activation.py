from pathlib import Path

import pytest

from src.digital_twin.evaluation import load_release_profile
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    FallbackRetriever,
    build_selected_retriever,
)


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"


def chunk(identifier: str, text: str, *, source: str = "lecture") -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id=f"document-{identifier}",
        text=text,
        ordinal=0,
        source_artifact_id=source,
        source_version=1,
        locator="page 1",
        retrieval_allowed=True,
    )


class KeywordEmbedder:
    provider_id = "local-huggingface"
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    model_revision = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    execution = "local"
    instruction = (
        "Given a student question within one authorized university course, "
        "retrieve passages that directly support a grounded answer."
    )
    device = "mps"
    dtype = "float16"
    max_length = 2048
    batch_size = 16

    def embed_documents(self, texts):
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    @staticmethod
    def _vector(text):
        lowered = text.lower()
        return [
            float("cache" in lowered),
            float("policy" in lowered),
            0.1,
        ]


class FailingEmbedder(KeywordEmbedder):
    def embed_documents(self, texts):
        del texts
        raise RuntimeError("provider unavailable")

    def embed_query(self, text):
        del text
        raise RuntimeError("provider unavailable")


class QueryFailingEmbedder(KeywordEmbedder):
    def embed_query(self, text):
        del text
        raise RuntimeError("provider unavailable")


def selected_entry():
    profile = load_release_profile(PROFILE_PATH)
    return next(
        entry for entry in profile.components if entry.component.value == "retriever"
    )


def test_selected_m2_profile_freezes_provider_and_ranking_binding():
    configuration = selected_entry().implementation.configuration

    assert configuration == {
        "method": "M2",
        "provider_pair": "local-qwen3-0-6b",
        "embedding_provider": "local-huggingface",
        "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
        "embedding_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
        "embedding_execution": "local",
        "query_instruction": (
            "Given a student question within one authorized university course, "
            "retrieve passages that directly support a grounded answer."
        ),
        "device": "mps",
        "dtype": "float16",
        "embedding_max_length": 2048,
        "embedding_batch_size": 16,
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
        "tokenizer": "lowercase-alphanumeric",
        "fusion_rank_constant": 60,
        "fusion_candidate_limit": 20,
        "result_limit": 10,
        "reranker": "none",
    }


def test_selected_m2_builds_with_an_injected_embedder():
    retriever = build_selected_retriever(
        selected_entry(),
        [
            chunk("cache", "cache coherence and memory"),
            chunk("policy", "course policy and release"),
        ],
        embedder=KeywordEmbedder(),
    )

    assert isinstance(retriever, FallbackRetriever)
    assert retriever.primary_available is True
    assert retriever.primary_implementation_id == "qwen3-hybrid-v1"
    assert [hit.chunk.id for hit in retriever.retrieve("cache", limit=5)]


def test_selected_m2_rejects_an_embedder_that_does_not_match_the_profile():
    embedder = KeywordEmbedder()
    embedder.model_revision = "different-revision"

    with pytest.raises(
        ValueError,
        match="injected embedder does not match selected profile: model_revision",
    ):
        build_selected_retriever(
            selected_entry(),
            [chunk("cache", "cache coherence and memory")],
            embedder=embedder,
            allow_control_fallback=False,
        )


def test_selected_m2_without_provider_uses_bm25_control():
    retriever = build_selected_retriever(
        selected_entry(),
        [chunk("cache", "cache coherence and memory")],
    )

    assert isinstance(retriever, FallbackRetriever)
    assert retriever.primary_available is False
    assert retriever.last_failure_type == "embedder-not-configured"
    assert retriever.retrieve("cache")[0].chunk.id == "cache"
    assert retriever.fallback_count == 1


def test_selected_m2_falls_back_after_provider_failure():
    retriever = build_selected_retriever(
        selected_entry(),
        [chunk("cache", "cache coherence and memory")],
        embedder=FailingEmbedder(),
    )

    assert retriever.primary_available is False
    assert retriever.last_failure_type == "RuntimeError"
    assert retriever.retrieve("cache")[0].chunk.id == "cache"


def test_selected_m2_falls_back_when_query_provider_fails():
    retriever = build_selected_retriever(
        selected_entry(),
        [chunk("cache", "cache coherence and memory")],
        embedder=QueryFailingEmbedder(),
    )

    assert retriever.primary_available is True
    assert retriever.retrieve("cache")[0].chunk.id == "cache"
    assert retriever.fallback_count == 1
    assert retriever.last_failure_type == "RuntimeError"


def test_fallback_retriever_does_not_hide_invalid_queries():
    retriever = FallbackRetriever(
        None,
        BM25Retriever([chunk("cache", "cache coherence")]),
        primary_implementation_id="primary",
        fallback_implementation_id="bm25-v1",
    )

    with pytest.raises(ValueError, match="lexical token"):
        retriever.retrieve("---")
