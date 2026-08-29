"""Finite, case-ID-bound contracts for the R1 model-selection cascade.

The v2 boundary deliberately treats provider formatting as data quality rather
than execution integrity.  Rows are joined by case ID, deterministically
ordered, and quarantined independently.  Only callers may classify corruption,
identity drift, leakage, or a broken ledger as an invalid execution.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ModelCandidateManifestV2(BaseModel):
    """Exact model and product configuration evaluated by one cascade arm."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0.0"] = "2.0.0"
    candidate_id: str = Field(min_length=1)
    provider: Literal["openai"] = "openai"
    provider_model: str = Field(min_length=1)
    expected_returned_model: str = Field(min_length=1)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"]
    max_output_tokens: int = Field(ge=1, le=128_000)
    request_store: Literal[False] = False
    prompt_id: str = Field(min_length=1)
    retriever_id: str = Field(min_length=1)
    evidence_gate_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    code_revision: str = Field(pattern=r"^[0-9a-f]{7,40}$")
    pricing_verified_at: str = Field(min_length=1)
    input_price_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    output_price_usd_per_million: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def returned_identity_must_be_exact(self) -> "ModelCandidateManifestV2":
        if self.expected_returned_model != self.provider_model:
            raise ValueError("candidate returned-model identity must be exact")
        return self


class QuarantinedCaseV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    reason: Literal[
        "missing-id",
        "duplicate-id",
        "malformed-row",
        "semantic-invalid",
    ]
    detail: str = Field(min_length=1, max_length=500)


class ReconciledCaseV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str = Field(min_length=1)
    payload: dict[str, Any] | None = None
    quarantine: QuarantinedCaseV2 | None = None

    @model_validator(mode="after")
    def exactly_one_outcome(self) -> "ReconciledCaseV2":
        if (self.payload is None) == (self.quarantine is None):
            raise ValueError("case must be accepted or quarantined")
        return self


class CaseBatchReconciliationV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["2.0.0"] = "2.0.0"
    expected_case_ids: list[str]
    rows: list[ReconciledCaseV2]
    unknown_case_ids: list[str]
    exact_id_set: bool

    @model_validator(mode="after")
    def rows_follow_expected_order(self) -> "CaseBatchReconciliationV2":
        if [row.case_id for row in self.rows] != self.expected_case_ids:
            raise ValueError("reconciled rows must follow deterministic input order")
        return self

    @property
    def quarantined_count(self) -> int:
        return sum(row.quarantine is not None for row in self.rows)


SemanticValidator = Callable[[dict[str, Any]], dict[str, Any]]


def reconcile_case_batch(
    *,
    expected_case_ids: Iterable[str],
    provider_rows: Iterable[Any],
    validate_semantics: SemanticValidator,
) -> CaseBatchReconciliationV2:
    """Join a provider batch by ID and quarantine bad rows independently.

    Provider order is intentionally ignored. Missing, duplicate, unknown, and
    malformed rows remain visible diagnostics; a single bad row never discards
    unrelated valid rows from the same paid response.
    """

    expected = list(expected_case_ids)
    supplied_rows = list(provider_rows)
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("expected case IDs must be non-empty and unique")
    expected_set = set(expected)
    grouped: dict[str, list[dict[str, Any]]] = {}
    malformed_without_known_id: list[str] = []
    unknown: list[str] = []
    for index, raw in enumerate(supplied_rows):
        if not isinstance(raw, dict):
            malformed_without_known_id.append(f"row-{index}")
            continue
        case_id = raw.get("case_id")
        if not isinstance(case_id, str) or not case_id.strip():
            malformed_without_known_id.append(f"row-{index}")
            continue
        normalized_id = case_id.strip()
        if normalized_id not in expected_set:
            unknown.append(normalized_id)
            continue
        grouped.setdefault(normalized_id, []).append(raw)

    rows: list[ReconciledCaseV2] = []
    for case_id in expected:
        candidates = grouped.get(case_id, [])
        if not candidates:
            rows.append(
                ReconciledCaseV2(
                    case_id=case_id,
                    quarantine=QuarantinedCaseV2(
                        case_id=case_id,
                        reason="missing-id",
                        detail="provider output omitted the expected case ID",
                    ),
                )
            )
            continue
        if len(candidates) != 1:
            rows.append(
                ReconciledCaseV2(
                    case_id=case_id,
                    quarantine=QuarantinedCaseV2(
                        case_id=case_id,
                        reason="duplicate-id",
                        detail=f"provider output contained {len(candidates)} rows",
                    ),
                )
            )
            continue
        try:
            payload = validate_semantics(candidates[0])
            if not isinstance(payload, dict):
                raise ValueError("semantic validator did not return an object")
        except (TypeError, ValueError) as error:
            rows.append(
                ReconciledCaseV2(
                    case_id=case_id,
                    quarantine=QuarantinedCaseV2(
                        case_id=case_id,
                        reason="semantic-invalid",
                        detail=str(error)[:500] or type(error).__name__,
                    ),
                )
            )
        else:
            rows.append(ReconciledCaseV2(case_id=case_id, payload=payload))

    counts = Counter(
        raw.get("case_id")
        for raw in supplied_rows
        if isinstance(raw, dict) and isinstance(raw.get("case_id"), str)
    )
    exact = (
        not malformed_without_known_id
        and not unknown
        and set(counts) == expected_set
        and all(counts[case_id] == 1 for case_id in expected)
    )
    return CaseBatchReconciliationV2(
        expected_case_ids=expected,
        rows=rows,
        unknown_case_ids=sorted(set([*unknown, *malformed_without_known_id])),
        exact_id_set=exact,
    )


class TransportRetryBudgetV2:
    """Global retry budget: one retry per failed request and at most 2%."""

    RETRYABLE_KINDS = frozenset({"timeout", "http-429", "http-5xx"})

    def __init__(self, *, planned_calls: int, maximum_fraction: float = 0.02) -> None:
        if planned_calls < 1:
            raise ValueError("planned calls must be positive")
        if not math.isfinite(maximum_fraction) or not 0 <= maximum_fraction <= 1:
            raise ValueError("retry fraction must be between zero and one")
        self.planned_calls = planned_calls
        self.maximum_retries = math.floor(planned_calls * maximum_fraction)
        self._retried_keys: set[str] = set()

    @property
    def used_retries(self) -> int:
        return len(self._retried_keys)

    def allow(self, *, request_key: str, failure_kind: str) -> bool:
        if failure_kind not in self.RETRYABLE_KINDS:
            return False
        if request_key in self._retried_keys:
            return False
        if self.used_retries >= self.maximum_retries:
            return False
        self._retried_keys.add(request_key)
        return True
