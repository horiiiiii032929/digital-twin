"""Finite, hash-bound orchestration for the autonomous evaluation program.

The program ledger is intentionally separate from provider and product-response
ledgers.  It records stage transitions and aggregate accounting only; public
questions, hidden gold, provider output, and product responses retain their
own physically separate stores.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PROGRAM_ID = "course-digital-twin-evaluation-program-001"
PROGRAM_ID_PATTERN = r"^course-digital-twin-evaluation-program-[0-9]{3}$"


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


class ProgramError(RuntimeError):
    """Raised when the finite program cannot preserve its frozen contract."""


class ProgramStageName(StrEnum):
    RETRIEVAL_DECISION = "retrieval-decision"
    PRODUCT_DEVELOPMENT = "product-development-500-plus-100"
    FINAL_CONSTRUCTION = "final-construction-10000"
    FINAL_PRODUCT = "final-product-10000-plus-1000"
    TRUE_VISUAL = "true-visual-30-plus-60"
    SYNTHETIC_PROFILE = "synthetic-profile-c0-c3"
    PROVIDER_T0_T1 = "provider-t0-t1-50-trajectories"
    RELEASE_REGRESSION = "local-release-regression"
    REPORTING = "professor-reporting"


class ProgramStageStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED_KEEP = "completed-keep"
    COMPLETED_REFINE = "completed-refine"
    COMPLETED_GO_DEEPER = "completed-go-deeper"
    INVALID_EXECUTION = "invalid-execution"
    INTERRUPTED = "interrupted"
    SKIPPED_DEPENDENCY = "skipped-dependency"


TERMINAL_STAGE_STATUSES = frozenset(
    {
        ProgramStageStatus.COMPLETED_KEEP,
        ProgramStageStatus.COMPLETED_REFINE,
        ProgramStageStatus.COMPLETED_GO_DEEPER,
        ProgramStageStatus.SKIPPED_DEPENDENCY,
    }
)


class ProgramModelBindingV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str = Field(min_length=1)
    provider: Literal["openai"] = "openai"
    model: str = Field(min_length=1)
    documented_revision: str = Field(min_length=1)
    exact_identity_required: bool = True
    request_store: Literal[False] = False
    structured_output: bool = True
    input_price_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    output_price_usd_per_million: float = Field(ge=0, allow_inf_nan=False)


class ProgramEmbeddingBindingV1(BaseModel):
    """Exact hosted embedding contract used by an API-first program."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    provider: Literal["openai"] = "openai"
    model: str = Field(min_length=1)
    documented_revision: str = Field(min_length=1)
    dimensions: int = Field(ge=1)
    batch_size: int = Field(ge=1, le=64)
    request_token_limit: int = Field(ge=1, le=300_000)
    input_price_usd_per_million: float = Field(ge=0, allow_inf_nan=False)
    exact_identity_required: Literal[True] = True
    artifact_instrument_id: str | None = Field(
        default=None, pattern=PROGRAM_ID_PATTERN
    )
    artifact_root_path: str | None = None

    @model_validator(mode="after")
    def validate_artifact_reuse(self) -> "ProgramEmbeddingBindingV1":
        if (self.artifact_instrument_id is None) != (self.artifact_root_path is None):
            raise ValueError(
                "embedding artifact instrument and root must be supplied together"
            )
        if self.artifact_root_path is not None:
            path = Path(self.artifact_root_path)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("embedding artifact root must be repository relative")
        return self


class ProgramStageV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: ProgramStageName
    order: int = Field(ge=1)
    budget_usd: float = Field(ge=0, allow_inf_nan=False)
    projected_p99_cost_usd: float = Field(ge=0, allow_inf_nan=False)
    dependencies: list[ProgramStageName] = Field(default_factory=list)
    independent_after_factual_failure: bool = False
    valid_keep_statuses: list[ProgramStageStatus] = Field(
        default_factory=lambda: [ProgramStageStatus.COMPLETED_KEEP]
    )
    maximum_invalid_corrections: Literal[1] = 1

    @field_validator("dependencies")
    @classmethod
    def dependencies_must_be_unique(
        cls, values: list[ProgramStageName]
    ) -> list[ProgramStageName]:
        if len(values) != len(set(values)):
            raise ValueError("program-stage dependencies must be unique")
        return values


class ProgramManifestV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"] = "1.0.0"
    program_id: str = Field(default=PROGRAM_ID, pattern=PROGRAM_ID_PATTERN)
    status: Literal[
        "reviewed-pending-authorization",
        "frozen-authorized",
        "completed",
        "terminated",
    ]
    owner_issue: Literal[127] = 127
    total_budget_usd: Literal[50.0] = 50.0
    credential_environment_variable: Literal["OPENAI_API_KEY"] = "OPENAI_API_KEY"
    provider_api: Literal["responses"] = "responses"
    provider_endpoint: Literal["https://api.openai.com/v1/responses"] = (
        "https://api.openai.com/v1/responses"
    )
    provider_execution_authorized: bool
    paid_execution_authorized: bool
    automatic_stage_progression: Literal[True] = True
    deterministic_truth_authoritative: Literal[True] = True
    llm_reviews_authoritative: Literal[False] = False
    private_data_authorized: Literal[False] = False
    retrieval_execution_device: Literal["cpu"] = "cpu"
    retrieval_execution_dtype: Literal["float16"] = "float16"
    retrieval_embedding: ProgramEmbeddingBindingV1 | None = None
    retrieval_nano_reranking_enabled: bool | None = None
    models: list[ProgramModelBindingV1] = Field(min_length=4, max_length=4)
    stages: list[ProgramStageV1] = Field(min_length=9, max_length=9)
    metadata_verified_at: datetime
    metadata_freshness_hours: Literal[24] = 24
    source_plan_path: str = Field(min_length=1)
    development_cases_path: str = Field(min_length=1)
    development_gold_path: str = Field(min_length=1)
    development_source_path: str | None = None
    development_control_cases_path: str | None = None
    development_control_gold_path: str | None = None
    visual_dataset_path: str = Field(min_length=1)
    global_hard_stops: list[str] = Field(min_length=6)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("metadata_verified_at")
    @classmethod
    def metadata_time_requires_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("program metadata timestamp must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_finite_program(self) -> "ProgramManifestV1":
        if self.status == "reviewed-pending-authorization" and (
            self.provider_execution_authorized or self.paid_execution_authorized
        ):
            raise ValueError("reviewed program cannot already carry paid authority")
        if self.status in {"completed", "terminated"} and (
            self.provider_execution_authorized or self.paid_execution_authorized
        ):
            raise ValueError("terminal program cannot retain paid authority")
        if self.provider_execution_authorized != self.paid_execution_authorized:
            raise ValueError("program provider and paid authorization must agree")
        roles = [row.role for row in self.models]
        if len(roles) != len(set(roles)):
            raise ValueError("program model roles must be unique")
        orders = [row.order for row in self.stages]
        names = [row.name for row in self.stages]
        if orders != list(range(1, len(self.stages) + 1)):
            raise ValueError("program stages must have contiguous frozen order")
        if len(names) != len(set(names)):
            raise ValueError("program stage names must be unique")
        if not math.isclose(
            sum(row.budget_usd for row in self.stages),
            self.total_budget_usd,
            rel_tol=0,
            abs_tol=1e-9,
        ):
            raise ValueError("program stage budgets must sum to the global ceiling")
        if any(row.projected_p99_cost_usd > row.budget_usd for row in self.stages):
            raise ValueError("program stage p99 projection exceeds its frozen reserve")
        if sum(row.projected_p99_cost_usd for row in self.stages) > self.total_budget_usd:
            raise ValueError("program p99 projection exceeds the global ceiling")
        seen: set[ProgramStageName] = set()
        for stage in self.stages:
            if any(dependency not in seen for dependency in stage.dependencies):
                raise ValueError("program stage dependency must precede the stage")
            seen.add(stage.name)
        expected_hash = canonical_sha256(
            self.model_dump(
                mode="json",
                exclude={"content_sha256"},
                exclude_none=True,
            )
        )
        if self.content_sha256 != expected_hash:
            raise ValueError("program manifest content hash drifted")
        return self

    def stage(self, name: ProgramStageName) -> ProgramStageV1:
        return next(row for row in self.stages if row.name == name)

    def metadata_age_hours(self, *, now: datetime | None = None) -> float:
        current = now or datetime.now(UTC)
        age = (
            current.astimezone(UTC) - self.metadata_verified_at.astimezone(UTC)
        ).total_seconds() / 3600
        if age < 0:
            raise ProgramError("program metadata is future dated")
        return age


class ProgramLedgerV1:
    """Exclusive SQLite state machine for one finite program execution."""

    def __init__(
        self,
        path: Path,
        *,
        manifest: ProgramManifestV1,
        code_revision: str,
        resume: bool,
    ) -> None:
        if not code_revision or not all(character in "0123456789abcdef" for character in code_revision):
            raise ValueError("program code revision must be a git hexadecimal revision")
        self.path = path
        self.manifest = manifest
        if resume and not path.is_file():
            raise ProgramError("program resume ledger does not exist")
        if not resume and path.exists():
            raise ProgramError("program ledger output already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        if not resume:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
        self.connection = sqlite3.connect(path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS stages (
                name TEXT PRIMARY KEY,
                stage_order INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL,
                execution_attempts INTEGER NOT NULL DEFAULT 0,
                invalid_corrections INTEGER NOT NULL DEFAULT 0,
                provider_calls INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0,
                result_sha256 TEXT,
                started_at TEXT,
                finished_at TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_name TEXT,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        expected = {
            "schema_version": "1",
            "program_id": manifest.program_id,
            "program_manifest_sha256": manifest.content_sha256,
            "code_revision": code_revision,
            "global_budget_usd": str(manifest.total_budget_usd),
        }
        if resume:
            actual = dict(self.connection.execute("SELECT key, value FROM metadata"))
            if any(actual.get(key) != value for key, value in expected.items()):
                self.close()
                raise ProgramError("program resume binding drifted")
            if actual.get("status") not in {"running", "interrupted"}:
                self.close()
                raise ProgramError("program resume ledger is terminal")
            self._set_metadata("status", "running")
        else:
            with self.connection:
                for key, value in {**expected, "status": "running"}.items():
                    self.connection.execute(
                        "INSERT INTO metadata(key, value) VALUES (?, ?)", (key, value)
                    )
                for stage in manifest.stages:
                    self.connection.execute(
                        "INSERT INTO stages(name, stage_order, status) VALUES (?, ?, ?)",
                        (stage.name.value, stage.order, ProgramStageStatus.PENDING.value),
                    )
            self._event(None, "program-started", {"program_id": manifest.program_id})

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    def _set_metadata(self, key: str, value: str) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO metadata(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def _event(
        self,
        stage: ProgramStageName | None,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        with self.connection:
            self.connection.execute(
                "INSERT INTO events(stage_name, event_type, payload_json, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    stage.value if stage is not None else None,
                    event_type,
                    json.dumps(payload, sort_keys=True, separators=(",", ":")),
                    self._now(),
                ),
            )

    def _stage_row(self, name: ProgramStageName) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM stages WHERE name = ?", (name.value,)
        ).fetchone()
        if row is None:
            raise ProgramError(f"program stage is unregistered: {name.value}")
        return row

    def total_cost_usd(self) -> float:
        return float(
            self.connection.execute(
                "SELECT COALESCE(SUM(cost_usd), 0) FROM stages"
            ).fetchone()[0]
        )

    def start_stage(self, name: ProgramStageName) -> None:
        stage = self.manifest.stage(name)
        row = self._stage_row(name)
        if row["status"] not in {
            ProgramStageStatus.PENDING.value,
            ProgramStageStatus.INVALID_EXECUTION.value,
            ProgramStageStatus.INTERRUPTED.value,
        }:
            raise ProgramError(f"stage cannot start from {row['status']}: {name.value}")
        for dependency in stage.dependencies:
            dependency_status = ProgramStageStatus(self._stage_row(dependency)["status"])
            if dependency_status not in self.manifest.stage(dependency).valid_keep_statuses:
                raise ProgramError(
                    f"stage dependency is not passing: {dependency.value}={dependency_status.value}"
                )
        if row["status"] == ProgramStageStatus.INVALID_EXECUTION.value:
            if int(row["invalid_corrections"]) >= stage.maximum_invalid_corrections:
                raise ProgramError("stage exhausted its one harness-only correction")
            correction = int(row["invalid_corrections"]) + 1
        else:
            correction = int(row["invalid_corrections"])
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET status = ?, execution_attempts = execution_attempts + 1, "
                "invalid_corrections = ?, started_at = ?, finished_at = NULL "
                "WHERE name = ?",
                (
                    ProgramStageStatus.RUNNING.value,
                    correction,
                    self._now(),
                    name.value,
                ),
            )
        self._event(name, "stage-started", {"invalid_corrections": correction})

    def record_usage(
        self,
        name: ProgramStageName,
        *,
        provider_calls: int,
        cost_usd: float,
    ) -> None:
        if provider_calls < 0 or not math.isfinite(cost_usd) or cost_usd < 0:
            raise ValueError("program usage must be finite and non-negative")
        row = self._stage_row(name)
        if row["status"] != ProgramStageStatus.RUNNING.value:
            raise ProgramError("program usage can only be recorded for a running stage")
        stage_limit = self.manifest.stage(name).budget_usd
        stage_cost = float(row["cost_usd"]) + cost_usd
        global_cost = self.total_cost_usd() + cost_usd
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET provider_calls = provider_calls + ?, "
                "cost_usd = cost_usd + ? WHERE name = ?",
                (provider_calls, cost_usd, name.value),
            )
        self._event(
            name,
            "usage-recorded",
            {"provider_calls": provider_calls, "cost_usd": cost_usd},
        )
        if stage_cost > stage_limit or global_cost > self.manifest.total_budget_usd:
            self.mark_invalid(
                name,
                reason="stage-budget-exceeded" if stage_cost > stage_limit else "global-budget-exceeded",
            )
            raise ProgramError("program emergency cost ceiling exceeded")

    def remaining_budget_usd(self, name: ProgramStageName) -> float:
        row = self._stage_row(name)
        return max(
            0.0,
            min(
                self.manifest.stage(name).budget_usd - float(row["cost_usd"]),
                self.manifest.total_budget_usd - self.total_cost_usd(),
            ),
        )

    def complete_stage(
        self,
        name: ProgramStageName,
        *,
        status: ProgramStageStatus,
        result: dict[str, Any],
    ) -> None:
        if status not in TERMINAL_STAGE_STATUSES:
            raise ValueError("stage completion requires a terminal quality status")
        if self._stage_row(name)["status"] != ProgramStageStatus.RUNNING.value:
            raise ProgramError("only a running stage can complete")
        result_hash = canonical_sha256(result)
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET status = ?, result_sha256 = ?, finished_at = ? "
                "WHERE name = ?",
                (status.value, result_hash, self._now(), name.value),
            )
        self._event(name, "stage-completed", {"status": status.value, "result_sha256": result_hash})

    def mark_invalid(self, name: ProgramStageName, *, reason: str) -> None:
        row = self._stage_row(name)
        if row["status"] != ProgramStageStatus.RUNNING.value:
            raise ProgramError("only a running stage can become invalid")
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET status = ?, finished_at = ? WHERE name = ?",
                (ProgramStageStatus.INVALID_EXECUTION.value, self._now(), name.value),
            )
        self._event(name, "stage-invalid", {"reason": reason[:500]})

    def mark_interrupted(self) -> None:
        running = self.connection.execute(
            "SELECT name FROM stages WHERE status = ?",
            (ProgramStageStatus.RUNNING.value,),
        ).fetchall()
        with self.connection:
            for row in running:
                self.connection.execute(
                    "UPDATE stages SET status = ? WHERE name = ?",
                    (ProgramStageStatus.INTERRUPTED.value, row["name"]),
                )
        self._set_metadata("status", "interrupted")
        self._event(None, "program-interrupted", {})

    def skip_stage(self, name: ProgramStageName, *, reason: str) -> None:
        row = self._stage_row(name)
        if row["status"] != ProgramStageStatus.PENDING.value:
            raise ProgramError("only a pending stage can be skipped")
        with self.connection:
            self.connection.execute(
                "UPDATE stages SET status = ?, finished_at = ? WHERE name = ?",
                (ProgramStageStatus.SKIPPED_DEPENDENCY.value, self._now(), name.value),
            )
        self._event(name, "stage-skipped", {"reason": reason[:500]})

    def terminate(self, *, reason: str) -> None:
        self._set_metadata("status", "terminated")
        self._event(None, "program-terminated", {"reason": reason[:500]})

    def mark_complete(self) -> None:
        if self.connection.execute(
            "SELECT COUNT(*) FROM stages WHERE status IN (?, ?, ?)",
            (
                ProgramStageStatus.PENDING.value,
                ProgramStageStatus.RUNNING.value,
                ProgramStageStatus.INTERRUPTED.value,
            ),
        ).fetchone()[0]:
            raise ProgramError("program cannot complete with unfinished stages")
        self._set_metadata("status", "completed")
        self._event(None, "program-completed", {"total_cost_usd": self.total_cost_usd()})

    def snapshot(self) -> dict[str, Any]:
        metadata = dict(self.connection.execute("SELECT key, value FROM metadata"))
        stages = [
            dict(row)
            for row in self.connection.execute(
                "SELECT * FROM stages ORDER BY stage_order"
            )
        ]
        return {
            "metadata": metadata,
            "stages": stages,
            "total_cost_usd": self.total_cost_usd(),
            "remaining_budget_usd": max(
                0.0, self.manifest.total_budget_usd - self.total_cost_usd()
            ),
        }

    def close(self) -> None:
        self.connection.close()


def load_program_manifest(path: Path) -> ProgramManifestV1:
    try:
        return ProgramManifestV1.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ProgramError("program manifest is unavailable or invalid") from error
