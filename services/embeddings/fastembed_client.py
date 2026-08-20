"""Optional FastEmbed adapter; model files stay in the local cache."""

import math
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
        if not model_name.strip():
            raise ValueError("FastEmbed model_name is required")
        if not isinstance(local_files_only, bool):
            raise ValueError("local_files_only must be a boolean")
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
        self.model_name = model_name.strip()
        self._model = TextEmbedding(**options)
        self._dimensions: int | None = None

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        values = list(texts)
        vectors = self._validated_vectors(
            self._model.passage_embed(values),
            expected_count=len(values),
        )
        self._remember_dimensions(vectors)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        vectors = self._validated_vectors(
            self._model.query_embed(text),
            expected_count=1,
        )
        self._remember_dimensions(vectors)
        return vectors[0]

    @staticmethod
    def _validated_vectors(vectors, *, expected_count: int) -> list[list[float]]:
        materialized = list(vectors)
        if len(materialized) != expected_count:
            raise ValueError("FastEmbed returned an unexpected vector count")
        converted: list[list[float]] = []
        for vector in materialized:
            try:
                values = [float(value) for value in vector.tolist()]
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError("FastEmbed returned a non-numeric vector") from error
            if not values:
                raise ValueError("FastEmbed returned an empty vector")
            if any(not math.isfinite(value) for value in values):
                raise ValueError("FastEmbed returned a non-finite vector")
            converted.append(values)
        if len({len(vector) for vector in converted}) > 1:
            raise ValueError("FastEmbed returned inconsistent vector dimensions")
        return converted

    def _remember_dimensions(self, vectors: Sequence[Sequence[float]]) -> None:
        if not vectors:
            return
        dimensions = len(vectors[0])
        if self._dimensions is not None and dimensions != self._dimensions:
            raise ValueError("FastEmbed query and document dimensions differ")
        self._dimensions = dimensions
