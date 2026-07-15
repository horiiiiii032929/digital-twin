"""Optional FastEmbed adapter; model files stay in the local cache."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any


class FastEmbedDependencyError(RuntimeError):
    pass


class FastEmbedTextEmbedder:
    """Expose FastEmbed's passage/query encoders through the domain protocol."""

    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
        cache_dir: Path | None = None,
        local_files_only: bool = False,
    ) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as error:
            raise FastEmbedDependencyError(
                "install the retrieval-benchmark extra before using FastEmbed"
            ) from error

        options: dict[str, Any] = {
            "model_name": model_name,
            "local_files_only": local_files_only,
        }
        if cache_dir is not None:
            options["cache_dir"] = str(cache_dir)
        self.model_name = model_name
        self._model = TextEmbedding(**options)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [vector.tolist() for vector in self._model.passage_embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        vectors = list(self._model.query_embed(text))
        if len(vectors) != 1:
            raise ValueError("FastEmbed returned an unexpected query vector count")
        return vectors[0].tolist()
