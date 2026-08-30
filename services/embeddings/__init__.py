"""Local embedding adapters used by retrieval experiments."""

from services.embeddings.fastembed_client import FastEmbedTextEmbedder
from services.embeddings.jina_client import JinaTextEmbedder
from services.embeddings.openai_client import OpenAITextEmbedder
from services.embeddings.qwen3_client import (
    Qwen3EmbeddingDependencyError,
    Qwen3TextEmbedder,
)


__all__ = [
    "FastEmbedTextEmbedder",
    "JinaTextEmbedder",
    "OpenAITextEmbedder",
    "Qwen3EmbeddingDependencyError",
    "Qwen3TextEmbedder",
]
