"""Finite, flow-independent comparison of product LLM engine allocations."""

from __future__ import annotations

from collections import defaultdict
import random
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProductEngineBindingV1(_Contract):
    engine_id: str = Field(min_length=1, max_length=64)
    provider: Literal["deterministic", "openai-direct", "deepseek-direct"]
    planner_model: str = Field(min_length=1, max_length=128)
    generator_model: str = Field(min_length=1, max_length=128)
    planner_reasoning_effort: Literal["none", "low"] = "low"
    generator_reasoning_effort: Literal["none", "low"] = "none"
    maximum_output_tokens: int = Field(default=600, ge=1, le=2_000)
    input_price_usd_per_million: float = Field(ge=0)
    output_price_usd_per_million: float = Field(ge=0)
    credential_environment_variable: str | None = Field(default=None, max_length=64)
    returned_identity_must_equal: str | None = Field(default=None, max_length=128)
    dated_snapshot: bool

    @model_validator(mode="after")
    def direct_and_low_cost_boundary(self) -> "ProductEngineBindingV1":
        serialized = self.model_dump_json().casefold()
        if "gpt-5.6-sol" in serialized or "openrouter" in serialized:
            raise ValueError("cross-engine program excludes Sol and OpenRouter")
        if self.provider == "deterministic":
            if self.credential_environment_variable is not None:
                raise ValueError("deterministic engine cannot require credentials")
        elif self.credential_environment_variable is None:
            raise ValueError("provider-backed engine requires a credential boundary")
        if (
            self.provider != "deterministic"
            and self.returned_identity_must_equal != self.generator_model
        ):
            raise ValueError(
                "returned identity binds the factual/product generator model"
            )
        return self


class CrossEngineEvaluationProgramV1(_Contract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    program_id: str = Field(min_length=1, max_length=128)
    status: Literal[
        "build-only",
        "frozen-pending-authorization",
        "running",
        "completed-keep",
        "completed-refine",
        "invalid-execution",
    ]
    factual_public_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    factual_gold_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    factual_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    factual_control_selection_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_public_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_gold_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sealed_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_public_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_gold_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_control_public_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_control_gold_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_candidate_rankings_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    known_control_rankings_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    autonomy_public_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    autonomy_gold_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shared_prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shared_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    shared_scorer: Literal["independent-autonomy-scorer-v2"]
    engines: list[ProductEngineBindingV1] = Field(min_length=6, max_length=6)
    conditions: list[
        Literal[
            "t0-grounded-control",
            "t1-v1-reactive-control",
            "t1-v2-reactive",
            "t1-v2-autonomous",
        ]
    ] = Field(min_length=4, max_length=4)
    development_factual_cases: int = Field(ge=500)
    development_control_cases: int = Field(ge=100)
    autonomy_cases: int = Field(ge=820)
    sealed_confirmation_cases: int = Field(ge=1_000)
    known_regression_candidate_cases: int = Field(ge=10_000)
    known_regression_control_cases: int = Field(ge=1_000)
    total_budget_usd: float = Field(gt=0, le=100)
    paid_execution_authorized: bool = False
    protocol: dict[str, str | bool | int | float] = Field(default_factory=dict)
    supplementary_proxy_tracks: dict[str, str | bool] = Field(default_factory=dict)
    freshness: dict[str, str | int | float] = Field(default_factory=dict)
    boundaries: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def comparison_is_complete_and_finite(self) -> "CrossEngineEvaluationProgramV1":
        expected = {"e0", "e1", "e2", "e3", "e4", "e5"}
        ids = {item.engine_id for item in self.engines}
        if ids != expected:
            raise ValueError("cross-engine program must bind E0 through E5 exactly once")
        if len(self.conditions) != len(set(self.conditions)):
            raise ValueError("cross-engine conditions must be unique")
        if set(self.conditions) != {
            "t0-grounded-control",
            "t1-v1-reactive-control",
            "t1-v2-reactive",
            "t1-v2-autonomous",
        }:
            raise ValueError("cross-engine autonomy conditions drifted")
        return self


class EngineOutcomeV1(_Contract):
    engine_id: str
    condition: str
    case_id: str
    cluster_id: str
    safe_grounded_autonomous_success: bool
    cost_usd: float = Field(ge=0)
    latency_ms: float = Field(ge=0)


def hierarchical_engine_interval(
    rows: list[EngineOutcomeV1],
    *,
    seed: int = 20260901,
    replicates: int = 2_000,
) -> dict[str, float | int]:
    """Cluster bootstrap for one engine/condition cell."""

    if not rows:
        raise ValueError("engine interval requires rows")
    if replicates < 1_000:
        raise ValueError("engine interval requires at least 1,000 replicates")
    grouped: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        grouped[row.cluster_id].append(row.safe_grounded_autonomous_success)
    clusters = sorted(grouped)
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(replicates):
        selected = [rng.choice(clusters) for _ in clusters]
        values = [value for cluster in selected for value in grouped[cluster]]
        estimates.append(sum(values) / len(values))
    estimates.sort()
    observed = sum(row.safe_grounded_autonomous_success for row in rows) / len(rows)
    return {
        "value": observed,
        "lower_95": estimates[int(0.025 * replicates)],
        "upper_95": estimates[min(replicates - 1, int(0.975 * replicates))],
        "case_count": len(rows),
        "cluster_count": len(clusters),
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }


def paired_engine_difference_interval(
    left: list[EngineOutcomeV1],
    right: list[EngineOutcomeV1],
    *,
    seed: int = 20260901,
    replicates: int = 2_000,
) -> dict[str, float | int]:
    """Paired cluster bootstrap, preserving the case-level pairing."""

    left_by_id = {row.case_id: row for row in left}
    right_by_id = {row.case_id: row for row in right}
    if set(left_by_id) != set(right_by_id) or not left_by_id:
        raise ValueError("paired engine rows must contain the same non-empty case IDs")
    pairs_by_cluster: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for case_id in sorted(left_by_id):
        left_row = left_by_id[case_id]
        right_row = right_by_id[case_id]
        if left_row.cluster_id != right_row.cluster_id:
            raise ValueError("paired engine cluster identities differ")
        pairs_by_cluster[left_row.cluster_id].append(
            (
                int(left_row.safe_grounded_autonomous_success),
                int(right_row.safe_grounded_autonomous_success),
            )
        )
    clusters = sorted(pairs_by_cluster)
    rng = random.Random(seed)
    estimates: list[float] = []
    for _ in range(replicates):
        selected = [rng.choice(clusters) for _ in clusters]
        pairs = [pair for cluster in selected for pair in pairs_by_cluster[cluster]]
        estimates.append(sum(a - b for a, b in pairs) / len(pairs))
    estimates.sort()
    all_pairs = [pair for cluster in clusters for pair in pairs_by_cluster[cluster]]
    return {
        "difference": sum(a - b for a, b in all_pairs) / len(all_pairs),
        "lower_95": estimates[int(0.025 * replicates)],
        "upper_95": estimates[min(replicates - 1, int(0.975 * replicates))],
        "case_count": len(all_pairs),
        "cluster_count": len(clusters),
        "bootstrap_replicates": replicates,
        "bootstrap_seed": seed,
    }
