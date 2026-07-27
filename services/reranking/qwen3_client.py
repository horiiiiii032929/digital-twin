"""Local Qwen3 reranking adapter for reproducible retrieval experiments."""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path


class Qwen3RerankingDependencyError(RuntimeError):
    pass


class Qwen3Reranker:
    """Score query-document pairs with a revision-pinned local Qwen3 model."""

    _PREFIX = (
        "<|im_start|>system\nJudge whether the Document meets the requirements "
        "based on the Query and the Instruct provided. Note that the answer can "
        'only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
    )
    _SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

    def __init__(
        self,
        model_path: Path,
        *,
        instruction: str,
        device: str = "mps",
        dtype: str = "float16",
        batch_size: int = 4,
        max_length: int = 2048,
    ) -> None:
        if not model_path.is_dir():
            raise ValueError(f"Qwen3 reranker model path is missing: {model_path}")
        if not instruction.strip():
            raise ValueError("Qwen3 reranker instruction is required")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        if max_length < 64:
            raise ValueError("max_length must be at least 64")

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as error:
            raise Qwen3RerankingDependencyError(
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
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            local_files_only=True,
            padding_side="left",
        )
        self._model = AutoModelForCausalLM.from_pretrained(
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
        self._false_token_id = self._tokenizer.convert_tokens_to_ids("no")
        self._true_token_id = self._tokenizer.convert_tokens_to_ids("yes")
        self._prefix_tokens = self._tokenizer.encode(
            self._PREFIX,
            add_special_tokens=False,
        )
        self._suffix_tokens = self._tokenizer.encode(
            self._SUFFIX,
            add_special_tokens=False,
        )

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        if not documents:
            return []
        pairs = [
            (
                f"<Instruct>: {self.instruction}\n"
                f"<Query>: {query}\n"
                f"<Document>: {document}"
            )
            for document in documents
        ]
        scores: list[float] = []
        available_length = (
            self.max_length - len(self._prefix_tokens) - len(self._suffix_tokens)
        )
        for start in range(0, len(pairs), self.batch_size):
            batch = pairs[start : start + self.batch_size]
            encoded = self._tokenizer(
                batch,
                padding=False,
                truncation=True,
                max_length=available_length,
                add_special_tokens=False,
            )
            wrapped = [
                [*self._prefix_tokens, *input_ids, *self._suffix_tokens]
                for input_ids in encoded["input_ids"]
            ]
            inputs = self._tokenizer.pad(
                {"input_ids": wrapped},
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            with self._torch.inference_mode():
                logits = self._model(**inputs).logits[:, -1, :]
                binary = self._torch.stack(
                    [
                        logits[:, self._false_token_id],
                        logits[:, self._true_token_id],
                    ],
                    dim=1,
                )
                probabilities = self._torch.softmax(binary, dim=1)[:, 1]
            scores.extend(probabilities.float().cpu().tolist())
        return scores
