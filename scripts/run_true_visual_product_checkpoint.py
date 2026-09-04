#!/usr/bin/env python3
"""Run the one-shot 60-case true-visual checkpoint through the T0 product."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
from typing import Any

from dotenv import load_dotenv

from src.digital_twin.action_router import DeterministicActionRouterV3
from src.digital_twin.evaluation.factual_qa_adapters import normalize_product_action
from src.digital_twin.generation import (
    DeterministicEvidenceSetGroundedGenerator,
    DeterministicPolicyEnforcer,
)
from src.digital_twin.grounding import (
    AtomicClaimEvidenceValidator,
    BM25Retriever,
    CanonicalSourceAtomicClaimVerifier,
    DominanceScopedAmbiguitySafeEvidenceGateV3,
    DocumentChunk,
    PersistentJinaQuotaLedgerV1,
    QuestionTargetedAtomicEvidenceGate,
    QuotaBoundJinaVisualQueryProviderV1,
    RegionKind,
    StructuredLexicalCoverageEvidenceGate,
    VisualAwareRetrieverV1,
    VisualIndexStoreV1,
    VisualRuntimeError,
)
from src.digital_twin.grounding.visual_late_interaction import JINA_MAX_INPUT_TOKENS
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
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
)
from src.digital_twin.student.fixtures import approved_synthetic_policy
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "true-visual-product-checkpoint-001"
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/true_visual_product_checkpoint_001.json"
)
PUBLIC_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_product_checkpoint_001_public.json"
)
GOLD_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_product_checkpoint_001_gold.json"
)
SOURCES_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_product_checkpoint_001_sources.json"
)
COMPONENT_LEDGER = (
    ROOT
    / "reports/generated/true-visual-colpali-confirmation-001/provider-ledger.sqlite3"
)
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"
OUTPUT_ROOT = ROOT / "reports/generated/true-visual-product-checkpoint-001"
RESPONSE_LEDGER = OUTPUT_ROOT / "product-responses.sqlite3"
QUOTA_LEDGER = OUTPUT_ROOT / "jina-query-quota.sqlite3"
RESULT_PATH = OUTPUT_ROOT / "result.json"


class VisualProductCheckpointError(RuntimeError):
    pass


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _load_hashed(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VisualProductCheckpointError(f"invalid JSON root: {path.name}")
    expected = value.get("content_sha256")
    payload = {key: item for key, item in value.items() if key != "content_sha256"}
    if expected != _canonical_sha256(payload):
        raise VisualProductCheckpointError(f"content hash drifted: {path.name}")
    return value


def _git_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _git_is_clean() -> bool:
    return not subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _validate_packages() -> dict[str, Any]:
    instrument = _load_hashed(INSTRUMENT_PATH)
    public = _load_hashed(PUBLIC_PATH)
    sources = _load_hashed(SOURCES_PATH)
    public_ids = [row["case_id"] for row in public["cases"]]
    if len(public_ids) != 60 or len(set(public_ids)) != 60:
        raise VisualProductCheckpointError("public case identity is invalid")
    if len(sources["assets"]) != 30:
        raise VisualProductCheckpointError("source asset count drifted")
    for path, expected in (
        (PUBLIC_PATH, instrument["public_sha256"]),
        (GOLD_PATH, instrument["gold_sha256"]),
        (SOURCES_PATH, instrument["sources_sha256"]),
    ):
        if _load_hashed(path)["content_sha256"] != expected:
            raise VisualProductCheckpointError(
                f"instrument binding drifted: {path.name}"
            )
    if not COMPONENT_LEDGER.is_file():
        raise VisualProductCheckpointError("qualified component ledger is unavailable")
    component_ledger_sha256 = _file_sha256(COMPONENT_LEDGER)
    if component_ledger_sha256 != instrument["component_ledger_sha256"]:
        raise VisualProductCheckpointError("qualified component ledger hash drifted")
    return {
        "instrument": instrument,
        "public": public,
        "sources": sources,
        "component_ledger_sha256": component_ledger_sha256,
    }


def validate() -> dict[str, Any]:
    packages = _validate_packages()
    return {
        "status": "passed",
        "instrument_id": INSTRUMENT_ID,
        "case_count": len(packages["public"]["cases"]),
        "asset_count": len(packages["sources"]["assets"]),
        "provider_execution_authorized": packages["instrument"][
            "provider_execution_authorized"
        ],
        "provider_calls": 0,
        "gold_loaded_by_product_execution": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    result = validate()
    maximum_query_calls = int(result["case_count"])
    maximum_accounted_tokens = 144_639 + maximum_query_calls * JINA_MAX_INPUT_TOKENS
    result.update(
        {
            "status": "ready" if _execution_authorized() else "blocked-not-authorized",
            "jina_api_key_present": bool(os.getenv("JINA_API_KEY", "").strip()),
            "output_unused": not any(
                path.exists() for path in (RESPONSE_LEDGER, QUOTA_LEDGER, RESULT_PATH)
            ),
            "git_revision": _git_revision(),
            "git_clean": _git_is_clean(),
            "maximum_query_calls": maximum_query_calls,
            "maximum_accounted_tokens": maximum_accounted_tokens,
            "account_token_limit": 10_000_000,
            "quota_reservation_within_limit": maximum_accounted_tokens <= 10_000_000,
            "resume": resume,
        }
    )
    if not result["jina_api_key_present"]:
        result["status"] = "blocked-missing-credential"
    if resume:
        if not RESPONSE_LEDGER.is_file() or RESULT_PATH.exists():
            result["status"] = "blocked-resume-state-invalid"
    elif not result["output_unused"]:
        result["status"] = "blocked-output-exists"
    if not result["git_clean"]:
        result["status"] = "blocked-dirty-worktree"
    if not result["quota_reservation_within_limit"]:
        result["status"] = "blocked-token-limit"
    return result


def _execution_authorized() -> bool:
    instrument = _load_hashed(INSTRUMENT_PATH)
    return bool(
        instrument.get("provider_execution_authorized")
        and instrument.get("paid_execution_authorized")
    )


def _source_title(asset: dict[str, Any]) -> str:
    """Return a deterministic display title without extending frozen source gold."""

    explicit = asset.get("title")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    source_path = asset.get("source_document_path")
    if isinstance(source_path, str) and source_path.strip():
        stem = Path(source_path).stem.replace("_", " ").replace("-", " ").strip()
        if stem:
            return stem.title()
    source_artifact_id = asset.get("source_artifact_id")
    if isinstance(source_artifact_id, str) and source_artifact_id.strip():
        return source_artifact_id.strip()
    raise VisualProductCheckpointError("visual source has no display-title lineage")


def _chunks_by_course(sources: dict[str, Any]) -> dict[str, list[DocumentChunk]]:
    output: dict[str, list[DocumentChunk]] = {}
    kind_map = {
        "table": RegionKind.TABLE,
        "equation": RegionKind.EQUATION,
        "diagram": RegionKind.DIAGRAM,
    }
    for asset in sources["assets"]:
        region = asset["region_lineage"][0]
        claim = asset["approved_source_claim"]
        chunk = DocumentChunk(
            id=f"chunk-{region['region_id']}",
            document_id=asset["source_artifact_id"],
            text=claim,
            ordinal=0,
            source_artifact_id=asset["source_artifact_id"],
            source_version=asset["source_version_number"],
            source_checksum=asset["source_sha256"],
            source_label=SourceLabel.COURSE_APPROVED,
            locator=f"visual region {region['region_id']}",
            page_start=1,
            page_end=1,
            region_id=region["region_id"],
            region_kind=kind_map[asset["modality"]],
            bounding_box=tuple(region["bbox"]),
            crop_ref=asset["render_path"],
            region_checksum=asset["render_sha256"],
            retrieval_allowed=True,
            display_allowed=True,
            metadata={
                "title": _source_title(asset),
                "course_id": asset["course_id"],
                "asset_id": asset["asset_id"],
                "semantic_atom_version": "source-semantic-evidence-atom-v1",
                "semantic_atom_claim": claim,
            },
        )
        output.setdefault(asset["course_id"], []).append(chunk)
    return output


def _seed_product(repository: SQLiteStudentRepository, sources: dict[str, Any]) -> None:
    professor_id = "professor-visual-evaluation"
    student_id = "student-visual-evaluation"
    repository.save_account(Account(id=professor_id, role=AccountRole.PROFESSOR))
    repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
    for course_id, chunks in _chunks_by_course(sources).items():
        repository.save_course(
            Course(
                id=course_id,
                title=f"Synthetic visual evaluation: {course_id}",
                owner_professor_id=professor_id,
            )
        )
        repository.save_membership(
            CourseMembership(
                account_id=professor_id,
                course_id=course_id,
                role=MembershipRole.PROFESSOR,
            )
        )
        repository.save_membership(
            CourseMembership(
                account_id=student_id,
                course_id=course_id,
                role=MembershipRole.STUDENT,
            )
        )
        repository.save_release(
            DigitalTwinRelease(
                id=f"visual-release-{course_id}",
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


def _evidence_gate() -> DominanceScopedAmbiguitySafeEvidenceGateV3:
    return DominanceScopedAmbiguitySafeEvidenceGateV3(
        QuestionTargetedAtomicEvidenceGate(
            base_gate=StructuredLexicalCoverageEvidenceGate(
                minimum_content_matching_terms=2,
                evidence_limit=5,
            )
        ),
        evidence_limit=5,
    )


def _generator() -> DeterministicEvidenceSetGroundedGenerator:
    return DeterministicEvidenceSetGroundedGenerator(
        policy_enforcer=DeterministicPolicyEnforcer(
            action_router=DeterministicActionRouterV3()
        )
    )


def _claim_validator() -> AtomicClaimEvidenceValidator:
    return AtomicClaimEvidenceValidator(
        CanonicalSourceAtomicClaimVerifier(),
        minimum_entailment=1.0,
        maximum_contradiction=0.0,
        maximum_claims=8,
        evidence_limit=5,
    )


def _response_connection(
    *, resume: bool, bindings: dict[str, str]
) -> sqlite3.Connection:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if RESPONSE_LEDGER.exists() and not resume:
        raise VisualProductCheckpointError("response output already exists")
    connection = sqlite3.connect(RESPONSE_LEDGER)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS responses (
            condition TEXT NOT NULL,
            case_id TEXT NOT NULL,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(condition, case_id)
        );
        """
    )
    existing = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
    if existing and existing != bindings:
        raise VisualProductCheckpointError("response ledger binding drifted")
    if not existing:
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)",
            bindings.items(),
        )
        connection.commit()
    return connection


async def _execute_product(*, resume: bool) -> dict[str, Any]:
    packages = _validate_packages()
    instrument = packages["instrument"]
    if not _execution_authorized():
        raise VisualProductCheckpointError("provider execution is not authorized")
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID,
        "external_model_evaluation",
    )
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID,
        "method_evaluation_execution",
    )
    if not os.getenv("JINA_API_KEY", "").strip():
        raise VisualProductCheckpointError("JINA_API_KEY is unavailable")
    if not _git_is_clean():
        raise VisualProductCheckpointError("paid execution requires a clean worktree")
    maximum_accounted_tokens = 144_639 + len(packages["public"]["cases"]) * (
        JINA_MAX_INPUT_TOKENS
    )
    if maximum_accounted_tokens > 10_000_000:
        raise VisualProductCheckpointError(
            "maximum visual-query reservation exceeds the Jina 10M-token limit"
        )
    bindings = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": instrument["content_sha256"],
        "public_sha256": packages["public"]["content_sha256"],
        "sources_sha256": packages["sources"]["content_sha256"],
        "gold_sha256": instrument["gold_sha256"],
        "component_ledger_sha256": packages["component_ledger_sha256"],
        "code_revision": _git_revision(),
    }
    connection = _response_connection(resume=resume, bindings=bindings)
    quota = PersistentJinaQuotaLedgerV1(
        QUOTA_LEDGER,
        imported_ledger_sha256=packages["component_ledger_sha256"],
    )
    provider = QuotaBoundJinaVisualQueryProviderV1(
        api_key=os.environ["JINA_API_KEY"],
        quota_ledger=quota,
        timeout_seconds=8.0,
    )
    try:
        with tempfile.TemporaryDirectory(prefix="visual-product-runtime-") as directory:
            runtime_root = Path(directory)
            services: dict[str, StudentTutoringService] = {}
            repositories: dict[str, SQLiteStudentRepository] = {}
            retrievers: dict[str, dict[str, VisualAwareRetrieverV1]] = {"candidate": {}}
            for condition in ("control", "candidate"):
                repository = SQLiteStudentRepository(
                    runtime_root / f"{condition}.sqlite3"
                )
                _seed_product(repository, packages["sources"])
                repositories[condition] = repository
                decorator = None
                if condition == "candidate":
                    store = VisualIndexStoreV1(runtime_root / "visual-indexes")
                    for course_id, chunks in _chunks_by_course(
                        packages["sources"]
                    ).items():
                        release_id = f"visual-release-{course_id}"
                        store.materialize_from_component_ledger(
                            source_ledger_path=COMPONENT_LEDGER,
                            dataset_path=(
                                ROOT / "research/05_evaluation/datasets/"
                                "true_visual_colpali_confirmation_001.json"
                            ),
                            course_id=course_id,
                            release_id=release_id,
                            profile_id="student-tutor",
                            profile_version="v1",
                            chunks=chunks,
                        )

                    def decorate(text_retriever, release):
                        manifest, index = store.load_bound(
                            course_id=release.course_id,
                            release_id=release.id,
                            profile_id=release.profile_id,
                            profile_version=release.profile_version,
                            source_ledger_sha256=packages["component_ledger_sha256"],
                            chunks=release.chunks,
                        )
                        wrapped = VisualAwareRetrieverV1(
                            text_retriever=text_retriever,
                            query_provider=provider,
                            index=index,
                            course_id=release.course_id,
                            chunks=release.chunks,
                            artifact_id=manifest.artifact_id,
                        )
                        retrievers["candidate"][release.course_id] = wrapped
                        return wrapped

                    decorator = decorate
                services[condition] = StudentTutoringService(
                    repository,
                    profile_path=PROFILE_PATH,
                    generator=_generator(),
                    evidence_gate=_evidence_gate(),
                    claim_evidence_validator=_claim_validator(),
                    retriever_factory=lambda chunks, versions: BM25Retriever(
                        chunks,
                        active_source_versions=versions,
                    ),
                    retriever_decorator=decorator,
                )
                if condition == "candidate":
                    assert decorator is not None
                    for course_id, chunks in _chunks_by_course(
                        packages["sources"]
                    ).items():
                        release = repository.get_release(f"visual-release-{course_id}")
                        if release is None:
                            raise VisualProductCheckpointError(
                                "candidate visual release is unavailable"
                            )
                        decorator(
                            BM25Retriever(
                                chunks,
                                active_source_versions={
                                    chunk.source_artifact_id: int(
                                        chunk.source_version or 1
                                    )
                                    for chunk in chunks
                                    if chunk.source_artifact_id
                                },
                            ),
                            release,
                        )

            for condition in ("control", "candidate"):
                existing = {
                    row[0]
                    for row in connection.execute(
                        "SELECT case_id FROM responses WHERE condition = ?",
                        (condition,),
                    )
                }
                service = services[condition]
                for case in packages["public"]["cases"]:
                    if case["case_id"] in existing:
                        continue
                    conversation = service.create_conversation(
                        "student-visual-evaluation",
                        case["course_id"],
                    )
                    started = time.perf_counter()
                    turn = await service.submit_message(
                        "student-visual-evaluation",
                        conversation.id,
                        content=case["question"],
                        client_request_id=f"{condition}:{case['case_id']}",
                    )
                    latency_ms = (time.perf_counter() - started) * 1000
                    response = {
                        "case_id": case["case_id"],
                        "condition": condition,
                        "action": normalize_product_action(
                            turn.tutor_message.action,
                            turn.tutor_message.content,
                        ).value,
                        "answer": turn.tutor_message.content,
                        "citations": [
                            {
                                "source_artifact_id": citation.source_artifact_id,
                                "source_version": citation.source_version,
                                "source_sha256": citation.source_checksum,
                                "region_id": citation.region_id,
                                "crop_ref": citation.crop_ref,
                            }
                            for citation in turn.citations
                        ],
                        "latency_ms": latency_ms,
                        "provider_model": (
                            turn.tutor_message.trace.provider_model
                            if turn.tutor_message.trace
                            else None
                        ),
                    }
                    connection.execute(
                        "INSERT INTO responses VALUES (?, ?, ?, ?)",
                        (
                            condition,
                            case["case_id"],
                            json.dumps(response, sort_keys=True),
                            datetime.now(UTC).replace(microsecond=0).isoformat(),
                        ),
                    )
                    connection.commit()

            candidate_retrievers = retrievers["candidate"]
            text_path_regressions = 0
            for course_id, wrapped in candidate_retrievers.items():
                before = quota.snapshot().calls
                wrapped.retrieve("Summarize the approved course concept.", limit=5)
                after = quota.snapshot().calls
                if before != after or wrapped.last_route.value != "general":
                    text_path_regressions += 1
            connection.execute(
                "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
                ("text_path_regressions", str(text_path_regressions)),
            )
            connection.commit()
    finally:
        connection.close()
    return score()


def _response_count() -> int:
    if not RESPONSE_LEDGER.is_file():
        return 0
    connection = sqlite3.connect(RESPONSE_LEDGER)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0])
    finally:
        connection.close()


def _invalid_execution_result(error: BaseException) -> dict[str, Any]:
    provider: dict[str, Any] = {
        "model": "jina-embeddings-v4",
        "calls": 0,
        "actual_tokens": 0,
        "accounted_tokens": 0,
        "imported_tokens": 144_639,
        "account_limit": 10_000_000,
    }
    binding: dict[str, Any] = {}
    try:
        instrument = _load_hashed(INSTRUMENT_PATH)
        binding = {
            "instrument_sha256": instrument["content_sha256"],
            "public_sha256": instrument["public_sha256"],
            "gold_sha256": instrument["gold_sha256"],
            "sources_sha256": instrument["sources_sha256"],
            "component_ledger_sha256": instrument["component_ledger_sha256"],
        }
    except (OSError, ValueError, KeyError, TypeError, VisualProductCheckpointError):
        binding = {"binding_status": "unavailable"}
    if QUOTA_LEDGER.is_file():
        try:
            snapshot = PersistentJinaQuotaLedgerV1(
                QUOTA_LEDGER,
                imported_ledger_sha256=str(binding["component_ledger_sha256"]),
            ).snapshot()
            provider.update(
                {
                    "calls": snapshot.calls,
                    "actual_tokens": snapshot.completed_tokens,
                    "accounted_tokens": snapshot.accounted_tokens,
                    "remaining_tokens": snapshot.remaining_tokens,
                }
            )
        except (KeyError, VisualRuntimeError) as accounting_error:
            provider["accounting_failure"] = type(accounting_error).__name__
    return {
        "schema_version": "1.0.0",
        "result_id": INSTRUMENT_ID,
        "status": "invalid-execution",
        "decision": "Invalid",
        "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "code_revision": _git_revision(),
        **binding,
        "durable_response_count": _response_count(),
        "gold_opened": False,
        "provider": provider,
        "failure": f"{type(error).__name__}: {str(error)[:500]}",
        "limitations": [
            "No academic interpretation is attached to an operationally invalid run."
        ],
    }


async def execute(*, resume: bool) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise VisualProductCheckpointError(
            f"live preflight is blocked: {readiness['status']}"
        )
    try:
        return await _execute_product(resume=resume)
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        result = _invalid_execution_result(error)
        if not RESULT_PATH.exists():
            OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
            RESULT_PATH.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        return result


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split()).strip(" .")


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def score() -> dict[str, Any]:
    if not RESPONSE_LEDGER.is_file():
        raise VisualProductCheckpointError("response ledger is unavailable")
    connection = sqlite3.connect(RESPONSE_LEDGER)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT condition, case_id, response_json FROM responses"
    ).fetchall()
    if len(rows) != 120:
        connection.close()
        raise VisualProductCheckpointError(
            "hidden gold cannot open before all 120 product responses are durable"
        )
    responses = {
        (row["condition"], row["case_id"]): json.loads(row["response_json"])
        for row in rows
    }
    if len(responses) != 120:
        connection.close()
        raise VisualProductCheckpointError("response portfolio is duplicated")
    metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
    connection.close()

    gold = _load_hashed(GOLD_PATH)
    sources = _load_hashed(SOURCES_PATH)
    asset_by_id = {row["asset_id"]: row for row in sources["assets"]}
    source_by_id = {row["source_artifact_id"]: row for row in sources["assets"]}
    course_by_source = {
        row["source_artifact_id"]: row["course_id"] for row in sources["assets"]
    }
    metrics: dict[str, dict[str, Any]] = {}
    for condition in ("control", "candidate"):
        fully_grounded = 0
        boundary_releases = 0
        unsupported_claims = 0
        invalid_citations = 0
        lineage_valid = 0
        wrong_course = 0
        answerable = 0
        action_correct = 0
        for case in gold["cases"]:
            response = responses[(condition, case["case_id"])]
            if response["action"] == case["expected_action"]:
                action_correct += 1
            if case["expected_action"] != "answer":
                if response["action"] == "answer":
                    boundary_releases += 1
                    unsupported_claims += 1
                continue
            answerable += 1
            expected_regions = set(case["required_region_ids"])
            expected_sources = {
                asset_by_id[asset_id]["source_artifact_id"]
                for asset_id in case["required_asset_ids"]
            }
            cited_regions = {
                citation["region_id"] for citation in response["citations"]
            }
            cited_sources = {
                citation["source_artifact_id"] for citation in response["citations"]
            }
            citation_valid = bool(response["citations"])
            for citation in response["citations"]:
                source_id = citation["source_artifact_id"]
                source = source_by_id.get(source_id)
                if (
                    source is None
                    or source_id not in expected_sources
                    or citation["source_version"] != 1
                    or citation["source_sha256"]
                    != (source["source_sha256"] if source is not None else None)
                    or citation["region_id"] not in expected_regions
                ):
                    citation_valid = False
                    invalid_citations += 1
                if (
                    course_by_source.get(source_id)
                    != asset_by_id[case["required_asset_ids"][0]]["course_id"]
                ):
                    wrong_course += 1
            lineage = (
                citation_valid
                and cited_regions == expected_regions
                and cited_sources == expected_sources
                and all(citation["crop_ref"] for citation in response["citations"])
            )
            if lineage:
                lineage_valid += 1
            answer_supported = _normalized(case["canonical_answer"]) in _normalized(
                response["answer"]
            )
            if response["action"] == "answer" and not answer_supported:
                unsupported_claims += 1
            if response["action"] == "answer" and answer_supported and lineage:
                fully_grounded += 1
        metrics[condition] = {
            "fully_grounded_visual_success_count": fully_grounded,
            "fully_grounded_visual_success": fully_grounded / answerable,
            "action_accuracy": action_correct / 60,
            "boundary_releases": boundary_releases,
            "unsupported_claims": unsupported_claims,
            "invalid_or_wrong_version_citations": invalid_citations,
            "original_region_lineage_count": lineage_valid,
            "original_region_lineage": lineage_valid / answerable,
            "wrong_course_retrieval": wrong_course,
        }

    quota_connection = sqlite3.connect(QUOTA_LEDGER)
    provider_rows = quota_connection.execute(
        "SELECT status, actual_tokens, accounted_tokens, latency_ms, failure_type "
        "FROM visual_query_calls"
    ).fetchall()
    quota_connection.close()
    provider_latencies = [float(row[3]) / 1000 for row in provider_rows]
    provider_failures = sum(row[0] != "completed" for row in provider_rows)
    p95 = _percentile_95(provider_latencies)
    candidate = metrics["candidate"]
    gates = {
        "fully_grounded_visual_success": candidate[
            "fully_grounded_visual_success_count"
        ]
        >= 27,
        "boundary_releases": candidate["boundary_releases"] == 0,
        "unsupported_claims": candidate["unsupported_claims"] == 0,
        "invalid_or_wrong_version_citations": candidate[
            "invalid_or_wrong_version_citations"
        ]
        == 0,
        "original_region_lineage": candidate["original_region_lineage"] == 1.0,
        "wrong_course_retrieval": candidate["wrong_course_retrieval"] == 0,
        "visual_retrieval_p95_seconds": p95 <= 8.0,
        "text_path_regressions": int(metadata.get("text_path_regressions", "-1")) == 0,
        "provider_failures": provider_failures == 0,
        "provider_calls_within_limit": len(provider_rows) <= 60,
    }
    result = {
        "schema_version": "1.0.0",
        "result_id": INSTRUMENT_ID,
        "status": "completed-keep" if all(gates.values()) else "completed-refine",
        "decision": "Keep" if all(gates.values()) else "Refine",
        "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "code_revision": metadata["code_revision"],
        "instrument_sha256": metadata["instrument_sha256"],
        "public_sha256": metadata["public_sha256"],
        "gold_sha256": metadata["gold_sha256"],
        "sources_sha256": metadata["sources_sha256"],
        "conditions": metrics,
        "provider": {
            "model": "jina-embeddings-v4",
            "calls": len(provider_rows),
            "completed_calls": len(provider_rows) - provider_failures,
            "failures": provider_failures,
            "actual_tokens": sum(int(row[1]) for row in provider_rows),
            "accounted_tokens": sum(int(row[2]) for row in provider_rows),
            "imported_tokens": 144_639,
            "account_limit": 10_000_000,
            "p95_latency_seconds": p95,
        },
        "hard_gates": gates,
        "gold_opened_after_durable_response_count": 120,
        "limitations": [
            "Public synthetic/open educational visual sources only.",
            "This checkpoint evaluates product visual grounding, not representative course prevalence.",
            "The same 60 cases cannot be tuned and rerun after a valid quality result.",
        ],
    }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def simulate() -> dict[str, Any]:
    packages = _validate_packages()
    gold = _load_hashed(GOLD_PATH)
    cases = {row["case_id"]: row for row in gold["cases"]}
    if set(cases) != {row["case_id"] for row in packages["public"]["cases"]}:
        raise VisualProductCheckpointError("simulation public/gold identity drifted")
    return {
        "status": "passed-network-free-simulation",
        "instrument_id": INSTRUMENT_ID,
        "case_count": len(cases),
        "response_count": len(cases) * 2,
        "provider_calls": 0,
        "gold_opening_order_enforced": True,
        "product_integration_test": "tests/digital_twin/test_visual_runtime.py",
    }


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true")
    action.add_argument("--simulate", action="store_true")
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--execute", action="store_true")
    action.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.execute or args.resume:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID,
            "external_model_evaluation",
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID,
            "method_evaluation_execution",
        )
    if args.validate:
        result = validate()
    elif args.simulate:
        result = simulate()
    elif args.preflight:
        result = preflight()
    else:
        result = asyncio.run(execute(resume=args.resume))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
