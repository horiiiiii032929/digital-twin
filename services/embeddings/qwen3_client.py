"""Local Qwen3 embedding adapter for reproducible retrieval experiments."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any


class Qwen3EmbeddingDependencyError(RuntimeError):
    pass


class Qwen3TextEmbedder:
    """Expose a revision-pinned local Qwen3 embedding model as a TextEmbedder."""

    def __init__(
        self,
        model_path: Path,
        *,
        instruction: str,
        device: str = "mps",
        dtype: str = "float16",
        batch_size: int = 8,
        max_length: int = 2048,
    ) -> None:
        if not model_path.is_dir():
            raise ValueError(f"Qwen3 embedding model path is missing: {model_path}")
        if not instruction.strip():
            raise ValueError("Qwen3 embedding instruction is required")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if max_length < 32:
            raise ValueError("max_length must be at least 32")

        try:
            import torch
            import torch.nn.functional as functional
            from transformers import AutoModel, AutoTokenizer
        except ImportError as error:
            raise Qwen3EmbeddingDependencyError(
                "install the retrieval-benchmark extra before using Qwen3"
            ) from error

        if device == "mps" and not torch.backends.mps.is_available():
            raise ValueError("MPS was requested but is unavailable")
        try:
            torch_dtype = getattr(torch, dtype)
        except AttributeError as error:
            raise ValueError(f"unsupported torch dtype: {dtype}") from error

        started = time.perf_counter()
        self._torch = torch
        self._functional = functional
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            padding_side="left",
        )
        self._model = AutoModel.from_pretrained(
            model_path,
            local_files_only=True,
            dtype=torch_dtype,
        ).to(device)
        self._model.eval()
        if device == "mps":
            torch.mps.synchronize()
        self.model_load_seconds = time.perf_counter() - started
        self.model_path = model_path
        self.instruction = instruction.strip()
        self.device = device
        self.dtype = dtype
        self.batch_size = batch_size
        self.max_length = max_length

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed(list(texts))

    def embed_query(self, text: str) -> list[float]:
        detailed = f"Instruct: {self.instruction}\nQuery: {text}"
        vectors = self._embed([detailed])
        if len(vectors) != 1:
            raise ValueError("Qwen3 returned an unexpected query vector count")
        return vectors[0]

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)
            with self._torch.inference_mode():
                hidden = self._model(**encoded).last_hidden_state
                pooled = self._last_token_pool(
                    hidden,
                    encoded["attention_mask"],
                )
                normalized = self._functional.normalize(pooled, p=2, dim=1)
            vectors.extend(normalized.float().cpu().tolist())
        return vectors

    def _last_token_pool(self, hidden: Any, attention_mask: Any) -> Any:
        left_padding = attention_mask[:, -1].sum() == attention_mask.shape[0]
        if bool(left_padding):
            return hidden[:, -1]
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = hidden.shape[0]
        rows = self._torch.arange(batch_size, device=hidden.device)
        return hidden[rows, sequence_lengths]
