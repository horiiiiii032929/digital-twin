"""Provider-neutral contracts for cross-course retrieval qualification."""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.protocols import Retriever


class ProviderExecution(StrEnum):
    LOCAL = "local"
    HOSTED = "hosted"


class ProviderRole(StrEnum):
    EMBEDDING = "embedding"
    RERANKING = "reranking"


class RetrievalMethod(StrEnum):
    M0 = "M0"
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"


class ProviderDescriptor(BaseModel):
    provider_id: str = Field(min_length=1)
    role: ProviderRole
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    execution: ProviderExecution
    endpoint: str | None = None
    dimensions: int | None = Field(default=None, ge=1)
    max_cost_usd: float = Field(default=0, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def hosted_provider_requires_endpoint_and_budget(self) -> "ProviderDescriptor":
        if self.execution == ProviderExecution.HOSTED:
            if not self.endpoint:
                raise ValueError("hosted provider requires an endpoint")
            if self.max_cost_usd <= 0:
                raise ValueError("hosted provider requires a positive cost cap")
        elif self.endpoint is not None or self.max_cost_usd != 0:
            raise ValueError("local provider cannot declare endpoint or billed cost")
        return self


class ProviderPair(BaseModel):
    pair_id: str = Field(min_length=1)
    role: Literal["control", "candidate"]
    embedding: ProviderDescriptor
    reranking: ProviderDescriptor

    @model_validator(mode="after")
    def provider_roles_must_match(self) -> "ProviderPair":
        if self.embedding.role != ProviderRole.EMBEDDING:
            raise ValueError("embedding descriptor has the wrong role")
        if self.reranking.role != ProviderRole.RERANKING:
            raise ValueError("reranking descriptor has the wrong role")
        if self.embedding.execution != self.reranking.execution:
            raise ValueError("provider pair must use one execution boundary")
        return self


class RetrievalLadderConfig(BaseModel):
    bm25_k1: float = Field(gt=0)
    bm25_b: float = Field(ge=0, le=1)
    fusion_rank_constant: int = Field(ge=1)
    fusion_candidate_limit: int = Field(ge=1)
    rerank_candidate_limit: int = Field(ge=1)
    result_limit: int = Field(ge=5)


class ProviderQualificationConfig(BaseModel):
    schema_version: Literal[1]
    qualification_id: str = Field(min_length=1)
    dataset_seal_id: str = Field(min_length=1)
    development_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    heldout_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    heldout_access_allowed: Literal[False]
    spend_cap_usd: float = Field(gt=0, allow_inf_nan=False)
    budget_rate_usd_per_million_input_tokens: float = Field(
        gt=0,
        allow_inf_nan=False,
    )
    query_instruction: str = Field(min_length=1)
    ladder: RetrievalLadderConfig
    providers: list[ProviderPair] = Field(min_length=2)

    @model_validator(mode="after")
    def provider_set_must_have_one_control(self) -> "ProviderQualificationConfig":
        ids = [provider.pair_id for provider in self.providers]
        if len(ids) != len(set(ids)):
            raise ValueError("provider pair IDs must be unique")
        if sum(provider.role == "control" for provider in self.providers) != 1:
            raise ValueError("qualification requires exactly one control")
        if any(
            descriptor.max_cost_usd > self.spend_cap_usd
            for provider in self.providers
            for descriptor in (provider.embedding, provider.reranking)
        ):
            raise ValueError("provider cost cap exceeds qualification spend cap")
        return self


class ProviderUsage(BaseModel):
    request_count: int = Field(default=0, ge=0)
    input_items: int = Field(default=0, ge=0)
    input_characters: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    cache_hits: int = Field(default=0, ge=0)
    approximate_cost_usd: float = Field(default=0, ge=0, allow_inf_nan=False)


class UsageReporter(Protocol):
    def usage_snapshot(self) -> ProviderUsage:
        """Return a sanitized cumulative provider-usage snapshot."""


class SealedDevelopmentError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_provider_qualification_config(
    path: Path,
) -> ProviderQualificationConfig:
    return ProviderQualificationConfig.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def load_sealed_development(
    *,
    root: Path,
    seal_path: Path,
    ledger_path: Path,
    config: ProviderQualificationConfig,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load only the sealed development split and unopened-ledger metadata."""

    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    if seal["seal_id"] != config.dataset_seal_id:
        raise SealedDevelopmentError("qualification seal ID mismatch")
    if seal["development_sha256"] != config.development_sha256:
        raise SealedDevelopmentError("qualification development hash mismatch")
    if seal["heldout_sha256"] != config.heldout_sha256:
        raise SealedDevelopmentError("qualification held-out hash mismatch")
    if seal["heldout_access_allowed"] or config.heldout_access_allowed:
        raise SealedDevelopmentError("held-out access must remain disabled")
    if seal["heldout_status"] != "unopened":
        raise SealedDevelopmentError("seal does not report unopened held-out data")
    if ledger["seal_id"] != seal["seal_id"]:
        raise SealedDevelopmentError("held-out ledger seal mismatch")
    if ledger["heldout_sha256"] != config.heldout_sha256:
        raise SealedDevelopmentError("held-out ledger hash mismatch")
    if ledger["status"] != "unopened" or ledger["attempts"]:
        raise SealedDevelopmentError("held-out ledger is not pristine")

    development_path = root / seal["development_path"]
    if sha256_file(development_path) != config.development_sha256:
        raise SealedDevelopmentError("sealed development file hash mismatch")
    dataset = json.loads(development_path.read_text(encoding="utf-8"))
    if dataset["dataset_status"] != "sealed":
        raise SealedDevelopmentError("development dataset is not sealed")
    if len(dataset["cases"]) != 40:
        raise SealedDevelopmentError("development dataset must contain 40 cases")
    if any(case["split"] != "development" for case in dataset["cases"]):
        raise SealedDevelopmentError("development dataset contains another split")
    return dataset, seal


class CourseIsolationViolation(RuntimeError):
    pass


class CourseScopedRetriever:
    """Fail closed if an injected retriever returns a chunk outside its index."""

    def __init__(
        self,
        course_id: str,
        retriever: Retriever,
        allowed_chunks: list[DocumentChunk],
    ) -> None:
        if not course_id.strip():
            raise ValueError("course ID is required")
        identifiers = [chunk.id for chunk in allowed_chunks if chunk.retrieval_allowed]
        if not identifiers:
            raise ValueError("course scope has no approved chunks")
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("course scope contains duplicate chunk IDs")
        self.course_id = course_id
        self.retriever = retriever
        self.allowed_chunk_ids = frozenset(identifiers)

    def retrieve(self, query: str, *, limit: int = 5):
        hits = self.retriever.retrieve(query, limit=limit)
        unauthorized = [
            hit.chunk.id for hit in hits if hit.chunk.id not in self.allowed_chunk_ids
        ]
        if unauthorized:
            raise CourseIsolationViolation(
                f"{self.course_id} retriever returned unauthorized chunks"
            )
        return hits


def score_ranking(
    gold_ids: list[str],
    ranked_ids: list[str],
) -> dict[str, float | bool | int]:
    gold = set(gold_ids)
    if not gold:
        raise ValueError("positive case must contain gold evidence")
    gains = [1 if identifier in gold else 0 for identifier in ranked_ids[:10]]
    ideal = [1] * min(len(gold), 10)

    def dcg(values: list[int]) -> float:
        return sum(value / math.log2(rank + 2) for rank, value in enumerate(values))

    first_rank = next(
        (
            rank
            for rank, identifier in enumerate(ranked_ids, start=1)
            if identifier in gold
        ),
        None,
    )
    result: dict[str, float | bool | int] = {
        "complete_evidence_at_3": gold.issubset(ranked_ids[:3]),
        "ndcg_at_10": dcg(gains) / dcg(ideal) if ideal else 0.0,
        "mrr": 1 / first_rank if first_rank else 0.0,
        "gold_units": len(gold),
    }
    for limit in (1, 3, 5):
        covered = len(gold.intersection(ranked_ids[:limit]))
        result[f"covered_at_{limit}"] = covered
        result[f"recall_at_{limit}"] = covered / len(gold)
    return result


POSITIVE_SLICES = {"answerable", "cross_course_confusion"}


def assign_boundary_courses(
    cases: list[dict[str, Any]],
    course_ids: list[str],
) -> dict[str, str]:
    if not course_ids:
        raise ValueError("at least one course is required")
    boundary_cases = sorted(
        (case for case in cases if case["slice"] not in POSITIVE_SLICES),
        key=lambda case: case["case_id"],
    )
    return {
        case["case_id"]: course_ids[index % len(course_ids)]
        for index, case in enumerate(boundary_cases)
    }


def aggregate_rows(
    rows: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_method: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(row)
    overall: dict[str, Any] = {}
    slices: dict[str, Any] = {}
    for method in RetrievalMethod:
        members = by_method[method.value]
        positives = [row for row in members if row["is_positive"]]
        negatives = [row for row in members if not row["is_positive"]]
        threshold = thresholds[method.value]
        overall[method.value] = {
            "cases": len(members),
            "positive_cases": len(positives),
            "boundary_cases": len(negatives),
            "complete_evidence_success_at_3": _mean(
                [float(row["ranking"]["complete_evidence_at_3"]) for row in positives]
            ),
            "evidence_recall_at_1": _weighted_recall(positives, 1),
            "evidence_recall_at_3": _weighted_recall(positives, 3),
            "evidence_recall_at_5": _weighted_recall(positives, 5),
            "ndcg_at_10": _mean(
                [float(row["ranking"]["ndcg_at_10"]) for row in positives]
            ),
            "mrr": _mean([float(row["ranking"]["mrr"]) for row in positives]),
            "development_threshold": threshold,
            "no_evidence_accuracy_calibration": _mean(
                [float(row["decision_score"] < threshold) for row in negatives]
            ),
            "positive_answer_rate_calibration": _mean(
                [float(row["decision_score"] >= threshold) for row in positives]
            ),
            "action_accuracy_calibration": _mean(
                [
                    float((row["decision_score"] >= threshold) == row["is_positive"])
                    for row in members
                ]
            ),
            "course_isolation_violations": sum(
                row["course_isolation_violations"] for row in members
            ),
            "latency_p50_ms": _percentile(
                [row["latency_ms"] for row in members],
                0.5,
            ),
            "latency_p95_ms": _percentile(
                [row["latency_ms"] for row in members],
                0.95,
            ),
        }
        method_slices: dict[str, Any] = {}
        for slice_name in sorted({row["slice"] for row in members}):
            slice_members = [row for row in members if row["slice"] == slice_name]
            slice_positives = [row for row in slice_members if row["is_positive"]]
            method_slices[slice_name] = {
                "cases": len(slice_members),
                "complete_evidence_success_at_3": (
                    _mean(
                        [
                            float(row["ranking"]["complete_evidence_at_3"])
                            for row in slice_positives
                        ]
                    )
                    if slice_positives
                    else None
                ),
                "evidence_recall_at_5": (
                    _weighted_recall(slice_positives, 5) if slice_positives else None
                ),
                "action_accuracy_calibration": _mean(
                    [
                        float(
                            (row["decision_score"] >= threshold) == row["is_positive"]
                        )
                        for row in slice_members
                    ]
                ),
            }
        slices[method.value] = method_slices
    return overall, slices


def development_thresholds(
    rows: list[dict[str, Any]],
) -> dict[str, float]:
    return {
        method.value: math.nextafter(
            max(
                row["decision_score"]
                for row in rows
                if row["method"] == method.value and not row["is_positive"]
            ),
            math.inf,
        )
        for method in RetrievalMethod
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _weighted_recall(rows: list[dict[str, Any]], limit: int) -> float:
    numerator = sum(row["ranking"][f"covered_at_{limit}"] for row in rows)
    denominator = sum(row["ranking"]["gold_units"] for row in rows)
    return numerator / denominator if denominator else 0.0


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)
