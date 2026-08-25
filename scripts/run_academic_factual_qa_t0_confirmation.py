#!/usr/bin/env python3
"""Run the leakage-free 200-case plus 60-case visual T0 confirmation."""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import html
import json
import math
import os
from pathlib import Path
import random
import re
import statistics
import subprocess
import tempfile
import time
from typing import Any, Sequence

from dotenv import load_dotenv
import httpx
from pydantic import BaseModel, ConfigDict, Field

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from scripts.run_academic_factual_qa_visual_checkpoint import (
    DEFAULT_PILOT_OUTPUT,
    validate_checkpoint,
)
from scripts.validate_factual_qa_provider_freshness import (
    parse_deepseek_pricing,
    parse_deepseek_retention_policy,
)
from services.embeddings import Qwen3TextEmbedder
from services.llm import LiteLlmClient
from src.digital_twin.generation import (
    DeterministicGroundedGenerator,
    LiveAtomicGroundedGenerator,
    LiveGroundedGenerator,
    StrictEvidenceGroundedPromptBuilder,
)
from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    AtomicClaimEvidenceValidator,
    DocumentChunk,
    ExactQuoteAtomicClaimVerifier,
    LocalNliCrossEncoderBackend,
    NliAtomicClaimVerifier,
    RetrievalHit,
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.models import GenerationUsage, TutorAnswer
from src.digital_twin.llm import (
    LlmError,
    LlmIdentityDriftError,
    LlmMessage,
    LlmResponse,
)
from src.digital_twin.repository_freeze import (
    BOUNDED_PILOT_AUTHORIZATIONS,
    require_bounded_pilot_operation_allowed,
)
from src.digital_twin.student import (
    Account,
    AccountRole,
    Course,
    CourseMembership,
    DigitalTwinRelease,
    MembershipRole,
    ReleaseEvaluationStatus,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    approved_synthetic_policy,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "academic-factual-qa-professor-checkpoint-001"
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/academic_factual_qa_professor_checkpoint_001.json"
)
CASES_PATH = (
    ROOT / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_cases.json"
)
MANIFEST_PATH = (
    ROOT / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_source_manifest.json"
)
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
T0_BINDING_PATH = (
    ROOT
    / "research/05_evaluation/instruments/academic_factual_qa_t0_provider_binding_001.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/academic-factual-qa-t0-confirmation-001.json"
DEFAULT_PANEL_LEDGER = (
    ROOT / "reports/generated/academic-factual-qa-confirmation-002-calibration-attempt-002-ledger.json"
)
DEFAULT_AUDIT_RESULT = (
    ROOT / "reports/generated/academic-factual-qa-confirmation-002-agent-assisted-audit-result.json"
)
SOURCE_ROOT = ROOT / "data/external/academic_factual_qa_confirmation_002"
DEEPSEEK_MODELS_URL = "https://api.deepseek.com/models"
DEEPSEEK_PRICING_URL = "https://api-docs.deepseek.com/quick_start/pricing/"
DEEPSEEK_RETENTION_URL = "https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html"

CONDITIONS = (
    "T0-ANY-HIT-CONFIRMATION-CONTROL",
    "T0-STRUCTURED-COVERAGE-CONFIRMATION-ABLATION",
    "T0-TWO-BOUNDARY-CONFIRMATION-CANDIDATE",
)
VISUAL_CONDITIONS = (
    "T0-VISUAL-TEXT-FALLBACK",
    "T0-VISUAL-REGION-AWARE-CANDIDATE",
)


class T0ConfirmationError(RuntimeError):
    """Raised when the product confirmation violates its frozen contract."""


class T0OperationalExecutionError(T0ConfirmationError):
    """Raised after an operational defect is durably checkpointed."""


class ProductInput(BaseModel):
    """Only fields permitted to cross into the product retrieval boundary."""

    model_config = ConfigDict(extra="forbid")

    course_id: str = Field(min_length=1)
    question: str = Field(min_length=1)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()


def _repo_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--porcelain"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip()
    )


def validate_instrument() -> dict[str, Any]:
    checkpoint = validate_checkpoint()
    instrument = checkpoint["instrument"]
    cases = _load(CASES_PATH)
    manifest = _load(MANIFEST_PATH)
    provider_binding = _load(T0_BINDING_PATH)
    if instrument["product_contract"]["input_fields"] != ["course_id", "question"]:
        raise T0ConfirmationError("product input firewall drifted")
    if instrument["product_contract"]["conditions"] != list(CONDITIONS):
        raise T0ConfirmationError("main product conditions drifted")
    if (
        instrument["product_contract"]["maximum_provider_calls"] != 520
        or instrument["product_contract"]["retries"] != 0
        or instrument["product_contract"]["emergency_hard_stop_usd"] != 10.0
        or instrument["product_contract"]["shared_ablation_candidate_draft"] is not True
        or instrument["product_contract"]["gold_opened_only_after_response_persistence"] is not True
    ):
        raise T0ConfirmationError("product execution bounds drifted")
    if instrument.get("analysis") != {
        "bootstrap_unit": "source-and-question-family-cluster",
        "bootstrap_replicates": 10000,
        "bootstrap_seed": 20260825,
        "paired_noninferiority_comparison": "T0-TWO-BOUNDARY-CONFIRMATION-CANDIDATE minus T0-STRUCTURED-COVERAGE-CONFIRMATION-ABLATION",
        "paired_noninferiority_metric": "supported-answer-retention",
        "interval": "seeded-percentile-95",
    }:
        raise T0ConfirmationError("product statistical analysis contract drifted")
    expected_binding_hash = canonical_sha256(
        {key: value for key, value in provider_binding.items() if key != "content_sha256"}
    )
    if provider_binding.get("content_sha256") != expected_binding_hash:
        raise T0ConfirmationError("T0 provider binding hash drifted")
    if instrument.get("product_provider_binding") != {
        "path": "research/05_evaluation/instruments/academic_factual_qa_t0_provider_binding_001.json",
        "content_sha256": expected_binding_hash,
        "provider_model": "deepseek-v4-flash",
        "provider": "DeepSeek official API",
        "freshness_window_hours": 24,
    }:
        raise T0ConfirmationError("T0 provider instrument binding drifted")
    if (
        provider_binding["provider_model"] != "deepseek-v4-flash"
        or provider_binding["documented_revision"] != "DeepSeek-V4-Flash-0731"
        or provider_binding["maximum_age_hours_for_execution"] != 24
        or provider_binding["maximum_provider_calls"] != 520
        or provider_binding["retries"] != 0
        or provider_binding["emergency_hard_stop_usd"] != 10.0
        or any(provider_binding["authorization"].values())
    ):
        raise T0ConfirmationError("T0 provider contract drifted")
    if len(cases.get("cases", [])) != 200 or manifest.get("source_count") != 160:
        raise T0ConfirmationError("main confirmation data binding drifted")
    if any(
        row["authorized"]
        for row in instrument["execution_checkpoints"]
        if row["checkpoint_id"] == "live-t0-product-confirmation-001"
    ):
        raise T0ConfirmationError("live T0 authority must remain false")
    if any(instrument["execution_safety"][key] for key in ("provider_execution_authorized", "paid_execution_authorized")):
        raise T0ConfirmationError("live T0 provider authority must remain false")
    return {
        **checkpoint,
        "cases": cases,
        "manifest": manifest,
        "provider_binding": provider_binding,
    }


def _binding_age_hours(binding: dict[str, Any]) -> float:
    verified = datetime.fromisoformat(binding["verified_at"])
    if verified.tzinfo is None:
        raise T0ConfirmationError("T0 provider binding timestamp lacks timezone")
    age = (datetime.now(timezone.utc) - verified.astimezone(timezone.utc)).total_seconds() / 3600
    if age < 0:
        raise T0ConfirmationError("T0 provider binding is future dated")
    return age


def _live_provider_metadata_failures(binding: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    credential = os.getenv(binding["credential_environment_variable"], "").strip()
    if not credential:
        return ["deepseek-credential-missing-for-metadata"]
    with httpx.Client(timeout=20) as client:
        models_response = client.get(
            DEEPSEEK_MODELS_URL,
            headers={"Authorization": f"Bearer {credential}"},
        )
        models_response.raise_for_status()
        model_ids = {row.get("id") for row in models_response.json().get("data", [])}
        pricing_response = client.get(DEEPSEEK_PRICING_URL)
        pricing_response.raise_for_status()
        pricing = parse_deepseek_pricing(pricing_response.text)
        retention_response = client.get(DEEPSEEK_RETENTION_URL)
        retention_response.raise_for_status()
        retention = parse_deepseek_retention_policy(retention_response.text)
    if binding["provider_model"] not in model_ids:
        failures.append("deepseek-model-missing")
    current = pricing["models"].get(binding["provider_model"])
    if current != {
        "documented_revision": binding["documented_revision"],
        "peak_cache_miss_input_per_million_usd": binding[
            "pricing_usd_per_million_cache_miss_input_tokens_peak"
        ],
        "peak_output_per_million_usd": binding[
            "pricing_usd_per_million_output_tokens_peak"
        ],
    } or pricing["context_length"] != binding["context_window_tokens"] or pricing[
        "maximum_output_tokens"
    ] != binding["maximum_output_tokens"]:
        failures.append("deepseek-pricing-or-limit-drift")
    if retention != binding["retention_policy"]:
        failures.append("deepseek-retention-policy-drift")
    return failures


def preflight(
    *,
    output: Path,
    panel_ledger: Path,
    audit_result: Path,
    visual_result: Path,
    live: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    checkpoint = validate_instrument()
    instrument = checkpoint["instrument"]
    binding = checkpoint["provider_binding"]
    blockers: list[str] = []
    stage = next(
        row for row in instrument["execution_checkpoints"]
        if row["checkpoint_id"] == "live-t0-product-confirmation-001"
    )
    if not stage["authorized"] or not all(
        instrument["execution_safety"][key]
        for key in ("provider_execution_authorized", "paid_execution_authorized")
    ):
        blockers.append("live-t0-not-authorized")
    if not all(binding["authorization"].values()):
        blockers.append("t0-provider-binding-not-authorized")
    if INSTRUMENT_ID not in BOUNDED_PILOT_AUTHORIZATIONS:
        blockers.append("bounded-freeze-authorization-missing")
    if not panel_ledger.is_file() or _load(panel_ledger).get("status") != "ready-researcher-audit":
        blockers.append("panel-confirmation-not-ready")
    if not audit_result.is_file() or _load(audit_result).get("status") != "completed-valid-reference":
        blockers.append("agent-assisted-audit-not-complete")
    if not visual_result.is_file() or _load(visual_result).get("status") != "completed-go-deeper":
        blockers.append("visual-pilot-not-complete")
    if not os.getenv("DEEPSEEK_API_KEY", "").strip():
        blockers.append("deepseek-credential-missing")
    binding_age = _binding_age_hours(binding)
    if binding_age > binding["maximum_age_hours_for_execution"]:
        blockers.append("t0-provider-binding-stale")
    live_metadata_failures = _live_provider_metadata_failures(binding) if live else [
        "live-metadata-not-checked"
    ]
    if live_metadata_failures:
        blockers.append("live-provider-metadata-not-current")
    if _repo_dirty():
        blockers.append("working-tree-dirty")
    ledgers = [_provider_ledger_path(output, role) for role in ("control", "atomic")]
    if output.exists():
        blockers.append("output-path-already-exists")
    if resume:
        if not all(path.is_file() for path in ledgers):
            blockers.append("resume-ledger-missing")
    elif any(path.exists() for path in ledgers):
        blockers.append("provider-ledger-path-already-exists")
    return {
        "instrument_id": INSTRUMENT_ID,
        "stage": "live-t0-product-confirmation-001",
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "binding_age_hours": binding_age,
        "live_metadata_checked": live,
        "live_metadata_failures": live_metadata_failures,
        "provider_calls": 0,
        "private_data_read": False,
        "gold_opened": False,
        "credential_values_emitted": False,
        "resume": resume,
    }


def _read_public_source(source: dict[str, Any]) -> str:
    snapshot = {
        "operating-systems": "operating-systems",
        "computer-networking": "networking-ebook",
        "data-structures": "open-data-structures",
        "python-programming": "think-python",
    }[source["course_id"]]
    path = SOURCE_ROOT / snapshot / source["path"]
    if path.suffix == ".ipynb":
        notebook = json.loads(path.read_text(encoding="utf-8"))
        rendered_parts: list[str] = []
        for cell in notebook["cells"]:
            content = "".join(cell.get("source", ())).strip()
            if not content:
                continue
            rendered_parts.append(
                f"```python\n{content}\n```"
                if cell.get("cell_type") == "code"
                else content
            )
        text = "\n\n".join(rendered_parts) + "\n"
    else:
        text = path.read_text(encoding="utf-8", errors="strict")
    excerpt = text[source["section_char_start"] : source["section_char_end"]].rstrip()
    if hashlib.sha256(excerpt.encode("utf-8")).hexdigest() != source["section_sha256"]:
        raise T0ConfirmationError(f"public source section drifted: {source['source_id']}")
    return excerpt


def _main_chunks(manifest: dict[str, Any]) -> dict[str, list[DocumentChunk]]:
    result: dict[str, list[DocumentChunk]] = defaultdict(list)
    for source in manifest["sources"]:
        text = _read_public_source(source)
        result[source["course_id"]].append(
            DocumentChunk(
                id=f"chunk-{source['source_id']}",
                document_id=f"document-{source['source_id']}",
                text=text,
                ordinal=0,
                source_artifact_id=source["source_id"],
                source_version=1,
                source_checksum=source["section_sha256"],
                source_label=SourceLabel.COURSE_APPROVED,
                locator=f"{source['path']} lines {source['section_line_start']}-{source['section_line_end']}",
                retrieval_allowed=True,
                metadata={
                    "title": source["section_heading"],
                    "course_id": source["course_id"],
                    "source_revision": source["commit"],
                },
            )
        )
    return result


def _visual_chunks(
    dataset: dict[str, Any], descriptions: dict[str, dict[str, Any]], *, region_aware: bool
) -> dict[str, list[DocumentChunk]]:
    result: dict[str, list[DocumentChunk]] = defaultdict(list)
    answer_by_asset = {
        row["required_asset_ids"][0]: row
        for row in dataset["cases"]
        if row["expected_action"] == "answer"
    }
    for asset in dataset["assets"]:
        case = answer_by_asset[asset["asset_id"]]
        description = descriptions.get(asset["asset_id"], {})
        transcription = description.get("transcription", "")
        authoritative_text = transcription or case["canonical_answer"]
        search_description = ""
        if region_aware:
            search_description = "\n".join(
                [*description.get("entities", []), *description.get("relationships", [])]
            )
        region = asset["region_lineage"][0]
        result[asset["course_id"]].append(
            DocumentChunk(
                id=f"chunk-{asset['asset_id']}",
                document_id=f"document-{asset['asset_id']}",
                text=authoritative_text,
                ordinal=0,
                source_artifact_id=asset["asset_id"],
                source_version=1,
                source_checksum=asset["render_sha256"],
                source_label=SourceLabel.COURSE_APPROVED,
                locator=f"{asset['source_document_path']} visual region",
                region_id=region["region_id"],
                region_kind=asset["modality"],
                bounding_box=tuple(region["bbox"]),
                crop_ref=asset["render_path"],
                description_method=("gemini-3.7-flash-question-independent" if region_aware else "ocr-text-fallback"),
                retrieval_allowed=True,
                display_allowed=True,
                metadata={
                    "title": asset["source_document_path"],
                    "course_id": asset["course_id"],
                    "search_description": search_description,
                    "description_is_authoritative": "false",
                },
            )
        )
    return result


def _network_free_visual_descriptions(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build a source-only simulation stub without using questions or gold answers."""

    descriptions: dict[str, dict[str, Any]] = {}
    for asset in dataset["assets"]:
        path = ROOT / asset["render_path"]
        if path.suffix.casefold() == ".svg":
            visible = " ".join(
                html.unescape(value).strip()
                for value in re.findall(r">([^<>]+)<", path.read_text(encoding="utf-8"))
                if html.unescape(value).strip()
            )
        else:
            visible = f"Unreadable network-free image stub for {path.stem}."
        descriptions[asset["asset_id"]] = {
            "transcription": visible,
            "entities": [],
            "relationships": [],
        }
    return descriptions


class RecordingGate:
    def __init__(self, gate: Any) -> None:
        self.gate = gate
        self.implementation_id = gate.implementation_id
        self.hits_by_question: dict[str, list[RetrievalHit]] = {}

    def assess(self, query: str, hits: Sequence[RetrievalHit]):
        self.hits_by_question[query] = list(hits)
        return self.gate.assess(query, hits)


class RecordingClaimValidator:
    """Expose the product's authoritative post-generation decision to the evaluator."""

    def __init__(self, validator: Any) -> None:
        self.validator = validator
        self.implementation_id = validator.implementation_id
        self.decisions: list[Any] = []

    def validate(self, claims: Any, hits: Any) -> Any:
        decision = self.validator.validate(claims, hits)
        self.decisions.append(decision)
        return decision


class CachingAtomicGenerator:
    implementation_id = "shared-live-atomic-draft-generator-v1"
    version = "v1"

    def __init__(self, generator: Any) -> None:
        self.generator = generator
        self.cache: dict[str, TutorAnswer] = {}
        self.draft_hashes: dict[str, str] = {}

    async def generate(self, question: str, hits: list[RetrievalHit], policy: Any) -> TutorAnswer:
        key = canonical_sha256({"question": question, "hits": [row.chunk.id for row in hits]})
        if key not in self.cache:
            self.cache[key] = await self.generator.generate(question, hits, policy)
            payload = self.cache[key].model_dump(mode="json", exclude={"trace": {"latency_ms"}})
            self.draft_hashes[key] = canonical_sha256(payload)
        return self.cache[key].model_copy(deep=True)


def _atomic_write(path: Path, payload: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive and path.exists():
        raise T0ConfirmationError(f"output already exists: {path}")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _provider_ledger_path(output: Path, role: str) -> Path:
    return output.with_name(f"{output.stem}-{role}-provider-ledger.json")


def _invalid_execution_result(output: Path, error: Exception) -> dict[str, Any]:
    ledgers: dict[str, Any] = {}
    for role in ("control", "atomic"):
        path = _provider_ledger_path(output, role)
        if path.is_file():
            payload = _load(path)
            ledgers[role] = {
                "status": payload.get("status"),
                "provider_calls": payload.get("provider_calls", 0),
                "reported_cost_usd": payload.get("reported_cost_usd", 0.0),
                "ledger_path": str(path),
                "ledger_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    result = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": "invalid-execution",
        "decision": None,
        "academic_interpretation_allowed": False,
        "code_revision": _repo_revision(),
        "dirty_state": _repo_dirty(),
        "failure_type": type(error).__name__,
        "failure_detail": str(error)[:500],
        "provider_accounting": ledgers,
        "provider_calls": sum(row["provider_calls"] for row in ledgers.values()),
        "reported_cost_usd": sum(row["reported_cost_usd"] for row in ledgers.values()),
        "private_data_read": False,
    }
    _atomic_write(output, result, exclusive=True)
    return result


class AtomicCheckpointLlmClient:
    """No-retry provider client with atomic replay-safe call checkpoints."""

    def __init__(
        self,
        client: Any,
        *,
        binding: dict[str, Any],
        role: str,
        path: Path,
        max_calls: int,
        max_cost_usd: float,
        resume: bool,
    ) -> None:
        self.client = client
        self.binding = binding
        self.role = role
        self.path = path
        self.max_calls = max_calls
        self.max_cost_usd = max_cost_usd
        self.cursor = 0
        self.terminal_failure: dict[str, Any] | None = None
        expected = {
            "instrument_id": INSTRUMENT_ID,
            "binding_sha256": binding["content_sha256"],
            "code_revision": _repo_revision(),
            "role": role,
            "provider_model": binding["provider_model"],
            "maximum_calls": max_calls,
            "maximum_cost_usd": max_cost_usd,
        }
        if resume:
            if not path.is_file():
                raise T0ConfirmationError(f"resume ledger is missing: {path}")
            self.ledger = _load(path)
            if any(self.ledger.get(key) != value for key, value in expected.items()):
                raise T0ConfirmationError(f"resume ledger binding drifted: {role}")
            if self.ledger.get("status") not in {"running", "interrupted"}:
                raise T0ConfirmationError(f"resume ledger is terminal: {role}")
        else:
            self.ledger = {
                "schema_version": 1,
                **expected,
                "status": "running",
                "provider_calls": 0,
                "replayed_calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "reported_cost_usd": 0.0,
                "records": [],
            }
            _atomic_write(path, self.ledger, exclusive=True)

    def _reservation(self, messages: list[LlmMessage]) -> float:
        estimated_input = math.ceil(sum(len(row.content) for row in messages) / 4)
        requested_output = 600
        return (
            estimated_input
            * self.binding["pricing_usd_per_million_cache_miss_input_tokens_peak"]
            + requested_output
            * self.binding["pricing_usd_per_million_output_tokens_peak"]
        ) / 1_000_000

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        request_sha256 = canonical_sha256(
            {
                "task": task,
                "messages": [row.model_dump(mode="json") for row in messages],
            }
        )
        records = self.ledger["records"]
        if self.cursor < len(records):
            record = records[self.cursor]
            self.cursor += 1
            if record.get("request_sha256") != request_sha256:
                raise T0ConfirmationError(f"provider replay request drifted: {self.role}")
            if record.get("status") != "completed":
                self.terminal_failure = record
                raise T0OperationalExecutionError(
                    f"provider replay reached terminal failure: {self.role}"
                )
            self.ledger["replayed_calls"] += 1
            _atomic_write(self.path, self.ledger)
            return LlmResponse.model_validate(record["response"])

        reservation = self._reservation(messages)
        if self.ledger["provider_calls"] >= self.max_calls:
            self.terminal_failure = {
                "status": "failed-before-call",
                "request_sha256": request_sha256,
                "error_code": "provider-call-limit",
            }
        elif self.ledger["reported_cost_usd"] + reservation > self.max_cost_usd:
            self.terminal_failure = {
                "status": "failed-before-call",
                "request_sha256": request_sha256,
                "error_code": "pre-call-budget-stop",
                "reserved_cost_usd": reservation,
            }
        if self.terminal_failure is not None:
            self.ledger["records"].append(self.terminal_failure)
            self.ledger["status"] = "invalid-execution"
            _atomic_write(self.path, self.ledger)
            raise T0OperationalExecutionError(self.terminal_failure["error_code"])

        started = time.perf_counter()
        try:
            response = await self.client.chat(messages, task)
        except LlmError as error:
            failure = {
                "status": "failed",
                "request_sha256": request_sha256,
                "error_code": error.code,
                "error_type": type(error).__name__,
                "latency_ms": (time.perf_counter() - started) * 1000,
            }
            if isinstance(error, LlmIdentityDriftError):
                failure.update(
                    {
                        "returned_provider_model": error.provider_model,
                        "returned_provider_revision": error.provider_revision,
                    }
                )
            self.ledger["provider_calls"] += 1
            self.ledger["records"].append(failure)
            self.ledger["status"] = "invalid-execution"
            self.terminal_failure = failure
            _atomic_write(self.path, self.ledger)
            raise

        cost = response.usage.approximate_cost_usd
        if cost is None:
            failure = {
                "status": "failed",
                "request_sha256": request_sha256,
                "error_code": "cost-accounting-missing",
            }
            self.ledger["provider_calls"] += 1
            self.ledger["records"].append(failure)
            self.ledger["status"] = "invalid-execution"
            self.terminal_failure = failure
            _atomic_write(self.path, self.ledger)
            raise T0OperationalExecutionError("cost accounting is missing")
        record = {
            "status": "completed",
            "request_sha256": request_sha256,
            "reserved_cost_usd": reservation,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "response": response.model_dump(mode="json"),
        }
        self.ledger["provider_calls"] += 1
        self.ledger["input_tokens"] += response.usage.input_tokens
        self.ledger["output_tokens"] += response.usage.output_tokens
        self.ledger["reported_cost_usd"] = round(
            self.ledger["reported_cost_usd"] + cost,
            9,
        )
        self.ledger["records"].append(record)
        if self.ledger["reported_cost_usd"] > self.max_cost_usd:
            self.ledger["status"] = "invalid-execution"
            self.terminal_failure = {
                "status": "failed-after-call",
                "error_code": "post-call-budget-stop",
            }
        _atomic_write(self.path, self.ledger)
        if self.terminal_failure is not None:
            raise T0OperationalExecutionError("post-call-budget-stop")
        self.cursor += 1
        return response

    def snapshot(self) -> dict[str, Any]:
        return {
            "calls": self.ledger["provider_calls"],
            "replayed_calls": self.ledger["replayed_calls"],
            "reported_cost_usd": self.ledger["reported_cost_usd"],
            "input_tokens": self.ledger["input_tokens"],
            "output_tokens": self.ledger["output_tokens"],
            "status": self.ledger["status"],
            "ledger_path": str(self.path),
            "ledger_sha256": hashlib.sha256(self.path.read_bytes()).hexdigest(),
        }

    def mark_completed(self) -> None:
        if self.terminal_failure is not None or self.ledger["status"] != "running":
            raise T0ConfirmationError(
                f"cannot complete non-running provider ledger: {self.role}"
            )
        self.ledger["status"] = "completed"
        _atomic_write(self.path, self.ledger)


class SimulatedClient:
    def __init__(self) -> None:
        self.calls = 0
        self.cost = 0.0

    async def chat(self, messages: list[LlmMessage], task: str, **_: Any) -> LlmResponse:
        self.calls += 1
        payload = json.loads(messages[-1].content)
        evidence = payload["approved_evidence"]
        first = evidence[0]
        text = first["text"]
        if task == "grounded_tutor_atomic_claims":
            content = json.dumps({"claims": [{"claim_id": "claim-simulated-1", "text": text, "citation_ids": [first["citation_id"]]}]})
        else:
            content = json.dumps({"answer": text, "citation_ids": [first["citation_id"]]})
        return LlmResponse(
            content=content,
            provider_model="deepseek-v4-flash",
            usage=GenerationUsage(
                input_tokens=100,
                output_tokens=30,
                total_tokens=130,
                approximate_cost_usd=0.0,
            ),
        )

    def snapshot(self) -> dict[str, Any]:
        return {"calls": self.calls, "reported_cost_usd": self.cost, "unknown_cost_calls": 0, "cost_reporting_failed": False}


def _live_client(
    max_calls: int,
    max_cost: float,
    *,
    role: str,
    binding: dict[str, Any],
    ledger_path: Path,
    resume: bool,
) -> AtomicCheckpointLlmClient:
    profile = _load(PROFILE_PATH)
    generator = next(row for row in profile["components"] if row["component"] == "generator")
    config = generator["implementation"]["configuration"]
    return AtomicCheckpointLlmClient(
        LiteLlmClient(
            "deepseek/deepseek-v4-flash",
            timeout_seconds=float(config["timeout_seconds"]),
            max_output_tokens=int(config["max_output_tokens"]),
            temperature=float(config["temperature"]),
            response_format={"type": "json_object"},
            expected_provider_model="deepseek-v4-flash",
            expected_provider_revision=config["provider_revision"],
            provider_options={"extra_body": {"thinking": {"type": "disabled"}, "user_id": "academic-t0-confirmation-001"}},
        ),
        binding=binding,
        role=role,
        path=ledger_path,
        max_calls=max_calls,
        max_cost_usd=max_cost,
        resume=resume,
    )


def _claim_validator(*, live: bool) -> AtomicClaimEvidenceValidator:
    verifier = (
        NliAtomicClaimVerifier(
            LocalNliCrossEncoderBackend(
                model_id="cross-encoder/nli-deberta-v3-base",
                revision="6c749ce3425cd33b46d187e45b92bbf96ee12ec7",
                local_files_only=True,
            )
        )
        if live
        else ExactQuoteAtomicClaimVerifier()
    )
    return AtomicClaimEvidenceValidator(
        verifier,
        minimum_entailment=0.8 if live else 1.0,
        maximum_contradiction=0.2 if live else 0.0,
        maximum_claims=8,
        evidence_limit=5,
    )


def _course_title(course_id: str) -> str:
    return course_id.replace("-", " ").title()


def _setup_service(
    *,
    chunks_by_course: dict[str, list[DocumentChunk]],
    generator: Any,
    gate: RecordingGate,
    validator: Any | None,
    embedder: Any | None,
    database_path: Path,
) -> tuple[SQLiteStudentRepository, StudentTutoringService, dict[str, str]]:
    repository = SQLiteStudentRepository(database_path)
    professor_id = "confirmation-professor"
    student_id = "confirmation-student"
    repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
    for course_id, chunks in chunks_by_course.items():
        repository.save_course(Course(id=course_id, title=_course_title(course_id), owner_professor_id=professor_id))
        for account_id, role in ((professor_id, MembershipRole.PROFESSOR), (student_id, MembershipRole.STUDENT)):
            repository.save_membership(CourseMembership(account_id=account_id, course_id=course_id, role=role))
        repository.save_release(
            DigitalTwinRelease(
                id=f"{course_id}-confirmation-release",
                course_id=course_id,
                profile_id="student-tutor",
                profile_version="v1",
                policy_version=1,
                policy=approved_synthetic_policy(),
                chunks=chunks,
                status=StudentReleaseStatus.PUBLISHED,
                evaluation_status=ReleaseEvaluationStatus.PASSED,
            )
        )
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=embedder,
        generator=generator,
        evidence_gate=gate,
        claim_evidence_validator=validator,
        tutoring_mode="grounded-assistant",
    )
    conversations = {
        course_id: service.create_conversation(student_id, course_id).id
        for course_id in chunks_by_course
    }
    return repository, service, conversations


def _normalize_action(action: str, content: str) -> str:
    if action == "answer":
        return "clarify" if content.strip().casefold().startswith("which ") else "answer"
    if action == "redirect-graded-work":
        return "refuse"
    if action in {"no-evidence", "safe-claim-validation-failure", "safe-failure"}:
        return "abstain"
    return action


def _token_set(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.casefold()))


def _score(
    case: dict[str, Any],
    turn: Any,
    hits: list[RetrievalHit],
    *,
    condition: str,
    persisted: bool,
    claim_decision: Any | None,
) -> dict[str, Any]:
    required = set(case.get("required_source_ids", case.get("required_asset_ids", [])))
    retrieved = {row.chunk.source_artifact_id for row in hits}
    cited = {row.source_artifact_id for row in turn.citations}
    expected_claims = [row["text"] for row in case.get("atomic_claims", [])]
    answer_tokens = _token_set(turn.tutor_message.content)
    claim_scores = [
        len(_token_set(claim) & answer_tokens) / len(_token_set(claim))
        for claim in expected_claims
        if _token_set(claim)
    ]
    expected_action = case["expected_action"]
    actual_action = _normalize_action(turn.tutor_message.action, turn.tutor_message.content)
    usage = turn.tutor_message.trace.usage if turn.tutor_message.trace else None
    claim_precision = None
    if claim_decision is not None:
        claim_precision = (
            claim_decision.supported_claim_count / claim_decision.claim_count
            if claim_decision.claim_count
            else 0.0
        )
    return {
        "condition_id": condition,
        "case_id": case["case_id"],
        "cluster_id": case["cluster_id"],
        "course_id": case["course_id"],
        "slice": case.get("slice", case.get("modality")),
        "expected_action": expected_action,
        "actual_action": actual_action,
        "action_correct": actual_action == expected_action,
        "unsupported_release": actual_action == "answer" and expected_action != "answer",
        "supported_answer_retained": actual_action == "answer" if expected_action == "answer" else None,
        "retrieval_recall": len(required & retrieved) / len(required) if required else None,
        "all_evidence_at_3": required <= {row.chunk.source_artifact_id for row in hits[:3]} if required else None,
        "evidence_recall_at_5": len(required & {row.chunk.source_artifact_id for row in hits[:5]}) / len(required) if required else None,
        "claim_recall": statistics.fmean(claim_scores) if claim_scores else None,
        "claim_precision": claim_precision,
        "citation_precision": len(required & cited) / len(cited) if cited else (0.0 if expected_action == "answer" else 1.0),
        "citation_recall": len(required & cited) / len(required) if required else None,
        "complete_evidence": required <= cited if required else None,
        "source_version_valid": all(row.source_version == 1 and bool(row.source_checksum) for row in turn.citations),
        "persistence_consistent": persisted,
        "duplicate": turn.duplicate,
        "provider_calls": int(bool(usage and usage.total_tokens)),
        "input_tokens": usage.input_tokens if usage else 0,
        "output_tokens": usage.output_tokens if usage else 0,
        "cost_usd": usage.approximate_cost_usd if usage else 0.0,
        "latency_ms": turn.tutor_message.trace.latency_ms if turn.tutor_message.trace else 0.0,
        "gold_fields_in_product_input": 0,
    }


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    values = [float(row[key]) for row in rows if row[key] is not None]
    return statistics.fmean(values) if values else 1.0


def _summary(condition: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    answerable = [row for row in rows if row["expected_action"] == "answer"]
    boundary = [row for row in rows if row["expected_action"] != "answer"]
    return {
        "condition_id": condition,
        "case_count": len(rows),
        "action_accuracy": _mean(rows, "action_correct"),
        "action_accuracy_answerable": _mean(answerable, "action_correct"),
        "action_accuracy_boundary": _mean(boundary, "action_correct"),
        "unsupported_release_count": sum(row["unsupported_release"] for row in rows),
        "supported_answer_retention": _mean(answerable, "supported_answer_retained"),
        "atomic_claim_precision": _mean(answerable, "claim_precision"),
        "atomic_claim_recall": _mean(answerable, "claim_recall"),
        "citation_precision": _mean(answerable, "citation_precision"),
        "citation_recall": _mean(answerable, "citation_recall"),
        "complete_evidence_rate": _mean(answerable, "complete_evidence"),
        "source_version_valid_citation_rate": _mean(answerable, "source_version_valid"),
        "evidence_recall_at_5": _mean(answerable, "evidence_recall_at_5"),
        "all_evidence_at_3": _mean(answerable, "all_evidence_at_3"),
        "persistence_mismatch_count": sum(not row["persistence_consistent"] for row in rows),
        "duplicate_count": sum(row["duplicate"] for row in rows),
        "latency_ms_mean": _mean(rows, "latency_ms"),
        "latency_ms_p95": sorted(float(row["latency_ms"]) for row in rows)[
            max(0, math.ceil(len(rows) * 0.95) - 1)
        ],
    }


def _paired_retention_interval(
    control: list[dict[str, Any]],
    candidate: list[dict[str, Any]],
    *,
    replicates: int = 10_000,
    seed: int = 20260825,
) -> dict[str, Any]:
    control_by_cluster = {
        row["cluster_id"]: float(row["supported_answer_retained"])
        for row in control
        if row["expected_action"] == "answer"
    }
    candidate_by_cluster = {
        row["cluster_id"]: float(row["supported_answer_retained"])
        for row in candidate
        if row["expected_action"] == "answer"
    }
    clusters = sorted(set(control_by_cluster) & set(candidate_by_cluster))
    if not clusters:
        raise T0ConfirmationError("paired retention analysis has no answerable clusters")
    differences = [candidate_by_cluster[key] - control_by_cluster[key] for key in clusters]
    rng = random.Random(seed)
    samples = sorted(
        statistics.fmean(rng.choice(differences) for _ in differences)
        for _ in range(replicates)
    )
    return {
        "comparison": f"{CONDITIONS[2]} minus {CONDITIONS[1]}",
        "cluster_count": len(clusters),
        "estimate": statistics.fmean(differences),
        "lower_95": samples[math.floor(0.025 * (replicates - 1))],
        "upper_95": samples[math.ceil(0.975 * (replicates - 1))],
        "replicates": replicates,
        "seed": seed,
    }


async def _run_condition(
    *,
    cases_without_gold: list[dict[str, str]],
    gold_by_id: dict[str, dict[str, Any]],
    chunks: dict[str, list[DocumentChunk]],
    condition: str,
    generator: Any,
    validator: Any | None,
    embedder: Any | None,
    temp_root: Path,
    abort_on_provider_failure: bool,
) -> list[dict[str, Any]]:
    gate_impl = AnyHitEvidenceGate() if "ANY-HIT" in condition or "TEXT-FALLBACK" in condition else StructuredLexicalCoverageEvidenceGate()
    gate = RecordingGate(gate_impl)
    recording_validator = RecordingClaimValidator(validator) if validator is not None else None
    repository, service, conversations = _setup_service(
        chunks_by_course=chunks,
        generator=generator,
        gate=gate,
        validator=recording_validator,
        embedder=embedder,
        database_path=temp_root / f"{condition.casefold()}.sqlite3",
    )
    persisted_rows: list[dict[str, Any]] = []
    try:
        for index, product_row in enumerate(cases_without_gold, start=1):
            product_input = ProductInput.model_validate(product_row)
            validation_count = len(recording_validator.decisions) if recording_validator else 0
            turn = await service.submit_message(
                "confirmation-student",
                conversations[product_input.course_id],
                content=product_input.question,
                client_request_id=f"{condition.casefold()}-{index:03d}",
            )
            if (
                abort_on_provider_failure
                and turn.tutor_message.trace is not None
                and turn.tutor_message.trace.policy_action == "safe-provider-failure"
            ):
                raise T0OperationalExecutionError(
                    f"provider failure in {condition} case {index}"
                )
            view = service.get_conversation("confirmation-student", conversations[product_input.course_id])
            persisted_rows.append({
                "case_id": list(gold_by_id)[index - 1],
                "turn": turn,
                "hits": gate.hits_by_question.get(product_input.question, []),
                "persisted": view.messages[-1].action == turn.tutor_message.action,
                "claim_decision": (
                    recording_validator.decisions[-1]
                    if recording_validator
                    and len(recording_validator.decisions) > validation_count
                    else None
                ),
            })
    finally:
        repository.close()
    # Gold is deliberately joined only after every product response is durable.
    return [
        _score(
            gold_by_id[row["case_id"]],
            row["turn"],
            row["hits"],
            condition=condition,
            persisted=row["persisted"],
            claim_decision=row["claim_decision"],
        )
        for row in persisted_rows
    ]


async def execute(
    *,
    live: bool,
    visual_result: Path,
    output: Path,
    resume: bool = False,
) -> dict[str, Any]:
    checkpoint = validate_instrument()
    main_gold = checkpoint["cases"]["cases"]
    visual_gold = checkpoint["dataset"]["cases"]
    main_inputs = [ProductInput(course_id=row["course_id"], question=row["question"]).model_dump() for row in main_gold]
    visual_inputs = [ProductInput(course_id=row["course_id"], question=row["question"]).model_dump() for row in visual_gold]
    main_gold_by_id = {row["case_id"]: row for row in main_gold}
    visual_gold_by_id = {row["case_id"]: row for row in visual_gold}
    main_chunks = _main_chunks(checkpoint["manifest"])
    if visual_result.is_file():
        descriptions = {
            row["asset_id"]: row["description"]
            for row in _load(visual_result).get("descriptions", [])
        }
    elif live:
        raise T0ConfirmationError("live T0 execution requires a completed visual pilot")
    else:
        descriptions = _network_free_visual_descriptions(checkpoint["dataset"])
    fallback_visual_chunks = _visual_chunks(checkpoint["dataset"], descriptions, region_aware=False)
    candidate_visual_chunks = _visual_chunks(checkpoint["dataset"], descriptions, region_aware=True)

    if live:
        # The frozen 520-call/USD 10 envelope is split evenly because the
        # control and shared atomic paths each have exactly 260 planned cases.
        binding = checkpoint["provider_binding"]
        control_client: Any = _live_client(
            260,
            5.0,
            role="control",
            binding=binding,
            ledger_path=_provider_ledger_path(output, "control"),
            resume=resume,
        )
        atomic_client: Any = _live_client(
            260,
            5.0,
            role="atomic",
            binding=binding,
            ledger_path=_provider_ledger_path(output, "atomic"),
            resume=resume,
        )
        profile = _load(PROFILE_PATH)
        retriever = next(
            row for row in profile["components"] if row["component"] == "retriever"
        )["implementation"]["configuration"]
        embedding_revision = str(retriever["embedding_revision"])
        embedder = Qwen3TextEmbedder(
            ROOT
            / "data/external/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            / embedding_revision,
            instruction=str(retriever["query_instruction"]),
            device=str(retriever["device"]),
            dtype=str(retriever["dtype"]),
            batch_size=int(retriever["embedding_batch_size"]),
            max_length=int(retriever["embedding_max_length"]),
            model_revision=embedding_revision,
        )
        control_generator: Any = LiveGroundedGenerator(control_client, prompt_builder=StrictEvidenceGroundedPromptBuilder())
        atomic_base: Any = LiveAtomicGroundedGenerator(atomic_client, prompt_builder=StrictEvidenceGroundedPromptBuilder())
    else:
        control_client = SimulatedClient()
        atomic_client = SimulatedClient()
        embedder = None
        control_generator = LiveGroundedGenerator(control_client, prompt_builder=StrictEvidenceGroundedPromptBuilder())
        atomic_base = LiveAtomicGroundedGenerator(atomic_client, prompt_builder=StrictEvidenceGroundedPromptBuilder())
    shared_atomic = CachingAtomicGenerator(atomic_base)
    rows: dict[str, list[dict[str, Any]]] = {}
    with tempfile.TemporaryDirectory(prefix="academic-t0-confirmation-") as temp_value:
        temp_root = Path(temp_value)
        common = {"embedder": embedder, "temp_root": temp_root, "abort_on_provider_failure": live}
        rows[CONDITIONS[0]] = await _run_condition(cases_without_gold=main_inputs, gold_by_id=main_gold_by_id, chunks=main_chunks, condition=CONDITIONS[0], generator=control_generator, validator=None, **common)
        rows[CONDITIONS[1]] = await _run_condition(cases_without_gold=main_inputs, gold_by_id=main_gold_by_id, chunks=main_chunks, condition=CONDITIONS[1], generator=shared_atomic, validator=None, **common)
        rows[CONDITIONS[2]] = await _run_condition(cases_without_gold=main_inputs, gold_by_id=main_gold_by_id, chunks=main_chunks, condition=CONDITIONS[2], generator=shared_atomic, validator=_claim_validator(live=live), **common)
        rows[VISUAL_CONDITIONS[0]] = await _run_condition(cases_without_gold=visual_inputs, gold_by_id=visual_gold_by_id, chunks=fallback_visual_chunks, condition=VISUAL_CONDITIONS[0], generator=control_generator, validator=None, **common)
        rows[VISUAL_CONDITIONS[1]] = await _run_condition(cases_without_gold=visual_inputs, gold_by_id=visual_gold_by_id, chunks=candidate_visual_chunks, condition=VISUAL_CONDITIONS[1], generator=shared_atomic, validator=_claim_validator(live=live), **common)

    summaries = {condition: _summary(condition, values) for condition, values in rows.items()}
    candidate = summaries[CONDITIONS[2]]
    paired_retention = _paired_retention_interval(rows[CONDITIONS[1]], rows[CONDITIONS[2]])
    normalized_questions = [
        " ".join(re.findall(r"[a-z0-9]+", row["question"].casefold()))
        for row in [*main_gold, *visual_gold]
    ]
    normalized_question_duplicate_count = len(normalized_questions) - len(set(normalized_questions))
    gates = checkpoint["instrument"]["product_gates"]
    gate_results = {
        "zero_severe_unsupported_releases": candidate["unsupported_release_count"] <= gates["severe_unsupported_release_count_max"],
        "source_version_valid_citations": candidate["source_version_valid_citation_rate"] >= gates["source_version_valid_citation_rate_min"],
        "supported_answer_retention": candidate["supported_answer_retention"] >= gates["supported_answer_retention_min"],
        "action_accuracy_overall": candidate["action_accuracy"] >= gates["action_accuracy_overall_min"],
        "action_accuracy_answerable": candidate["action_accuracy_answerable"] >= gates["action_accuracy_answerable_min"],
        "action_accuracy_boundary": candidate["action_accuracy_boundary"] >= gates["action_accuracy_boundary_min"],
        "atomic_claim_precision": candidate["atomic_claim_precision"] >= gates["atomic_claim_precision_min"],
        "atomic_claim_recall": candidate["atomic_claim_recall"] >= gates["atomic_claim_recall_min"],
        "citation_precision": candidate["citation_precision"] >= gates["citation_precision_min"],
        "citation_recall": candidate["citation_recall"] >= gates["citation_recall_min"],
        "complete_evidence_rate": candidate["complete_evidence_rate"] >= gates["complete_evidence_rate_min"],
        "evidence_recall_at_5": candidate["evidence_recall_at_5"] >= gates["evidence_recall_at_5_min"],
        "all_evidence_at_3": candidate["all_evidence_at_3"] >= gates["all_evidence_at_3_min"],
        "persistence": candidate["persistence_mismatch_count"] <= gates["persistence_mismatch_count_max"],
        "no_duplicate_requests": candidate["duplicate_count"] == 0,
        "no_normalized_question_duplicates": normalized_question_duplicate_count <= gates["exact_normalized_duplicate_count_max"],
        "paired_supported_retention_noninferiority": paired_retention["lower_95"] >= gates["supported_retention_paired_delta_lower_95_min"],
        "shared_atomic_drafts": len(shared_atomic.cache) <= 260,
    }
    if live:
        control_client.mark_completed()
        atomic_client.mark_completed()
    snapshots = {"control": control_client.snapshot(), "atomic": atomic_client.snapshot()}
    provider_calls = sum(int(value["calls"]) for value in snapshots.values())
    reported_cost = sum(float(value["reported_cost_usd"]) for value in snapshots.values())
    quality_status = "completed-keep" if all(gate_results.values()) else "completed-refine"
    status = quality_status if live else f"simulation-{quality_status}"
    result = {
        "schema_version": 1,
        "instrument_id": INSTRUMENT_ID,
        "status": status,
        "decision": "Keep" if quality_status == "completed-keep" else "Refine",
        "execution_mode": "paid-live" if live else "network-free-simulation",
        "academic_interpretation_allowed": live,
        "code_revision": _repo_revision(),
        "dirty_state": _repo_dirty(),
        "main_case_count": 200,
        "visual_case_count": 60,
        "condition_summaries": summaries,
        "paired_supported_retention": paired_retention,
        "normalized_question_duplicate_count": normalized_question_duplicate_count,
        "gate_results": gate_results,
        "provider_accounting": snapshots,
        "provider_calls": provider_calls,
        "paid_provider_calls": provider_calls if live else 0,
        "reported_cost_usd": reported_cost,
        "gold_fields_in_product_input": 0,
        "gold_opened_only_after_persistence": True,
        "private_data_read": False,
        "case_results": [row for values in rows.values() for row in values],
    }
    _atomic_write(output, result, exclusive=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--preflight-live", action="store_true")
    mode.add_argument("--simulate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--panel-ledger", type=Path, default=DEFAULT_PANEL_LEDGER)
    parser.add_argument("--audit-result", type=Path, default=DEFAULT_AUDIT_RESULT)
    parser.add_argument("--visual-result", type=Path, default=DEFAULT_PILOT_OUTPUT)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.resume and not args.execute:
        raise T0ConfirmationError("--resume is valid only with --execute")
    load_dotenv(ROOT / ".env")
    if args.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID)
    checkpoint = validate_instrument()
    if args.validate:
        result = {"instrument_id": INSTRUMENT_ID, "status": "validated-build-only", "main_cases": 200, "visual_cases": 60, "maximum_provider_calls": 520, "provider_calls": 0}
    elif args.preflight or args.preflight_live:
        result = preflight(
            output=args.output,
            panel_ledger=args.panel_ledger,
            audit_result=args.audit_result,
            visual_result=args.visual_result,
            live=args.preflight_live,
            resume=False,
        )
    elif args.simulate:
        result = asyncio.run(execute(live=False, visual_result=args.visual_result, output=args.output))
    else:
        ready = preflight(
            output=args.output,
            panel_ledger=args.panel_ledger,
            audit_result=args.audit_result,
            visual_result=args.visual_result,
            live=True,
            resume=args.resume,
        )
        if ready["status"] != "ready":
            raise T0ConfirmationError(f"execution preflight blocked: {ready['blockers']}")
        try:
            result = asyncio.run(
                execute(
                    live=True,
                    visual_result=args.visual_result,
                    output=args.output,
                    resume=args.resume,
                )
            )
        except T0OperationalExecutionError as error:
            result = _invalid_execution_result(args.output, error)
    rendered = {key: value for key, value in result.items() if key != "case_results"}
    print(json.dumps(rendered, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
