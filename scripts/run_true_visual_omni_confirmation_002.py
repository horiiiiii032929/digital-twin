#!/usr/bin/env python3
"""Run the fresh Jina v5 omni actual-product visual confirmation once."""

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

from scripts import run_true_visual_product_checkpoint as historical
from src.digital_twin.evaluation.factual_qa_adapters import normalize_product_action
from src.digital_twin.grounding import (
    BM25Retriever,
    DocumentChunk,
    JINA_CUMULATIVE_PRIOR_TOKENS,
    JINA_OMNI_MODEL,
    JinaOmniEmbeddingProviderV1,
    PersistentJinaQuotaLedgerV1,
    VisualAwareRetrieverV2,
    VisualLateInteractionIndexV1,
    VisualRegionEmbeddingV1,
)
from src.digital_twin.grounding.models import RegionKind, RetrievalHit
from src.digital_twin.grounding.visual_runtime import JINA_ACCOUNT_TOKEN_LIMIT
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student import SQLiteStudentRepository, StudentTutoringService
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "true-visual-omni-confirmation-002"
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/true_visual_omni_confirmation_002.json"
)
PUBLIC_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_omni_confirmation_002_public.json"
)
GOLD_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_omni_confirmation_002_gold.json"
)
SOURCES_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_omni_confirmation_002_sources.json"
)
OUTPUT_ROOT = ROOT / "reports/generated/true-visual-omni-confirmation-002"
RESPONSE_LEDGER = OUTPUT_ROOT / "responses.sqlite3"
QUOTA_LEDGER = OUTPUT_ROOT / "jina-quota.sqlite3"
RESULT_PATH = OUTPUT_ROOT / "result.json"
PRIOR_LEDGER_SHA256 = (
    "b49846c34ad283f2e662f52857178960da7306265f428177c281dc2dcaeab4ad"
)


class VisualOmniConfirmationError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VisualOmniConfirmationError(f"invalid JSON root: {path.name}")
    return value


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _validate_hashed(value: dict[str, Any]) -> None:
    expected = value.get("content_sha256")
    payload = {key: row for key, row in value.items() if key != "content_sha256"}
    if expected != _canonical_sha256(payload):
        raise VisualOmniConfirmationError("dataset package hash drifted")


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


def _packages() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    public = _load(PUBLIC_PATH)
    gold = _load(GOLD_PATH)
    sources = _load(SOURCES_PATH)
    for value in (public, gold, sources):
        _validate_hashed(value)
    dataset = instrument["dataset"]
    if (
        public["content_sha256"] != dataset["public_sha256"]
        or gold["content_sha256"] != dataset["gold_sha256"]
        or sources["content_sha256"] != dataset["sources_sha256"]
    ):
        raise VisualOmniConfirmationError("instrument dataset binding drifted")
    public_ids = [row["case_id"] for row in public["cases"]]
    gold_ids = [row["case_id"] for row in gold["cases"]]
    if len(public_ids) != 60 or public_ids != gold_ids or len(set(public_ids)) != 60:
        raise VisualOmniConfirmationError("public/gold case identity drifted")
    if len(sources["assets"]) != 30:
        raise VisualOmniConfirmationError("source asset count drifted")
    if instrument["provider"]["model"] != JINA_OMNI_MODEL:
        raise VisualOmniConfirmationError("Jina model binding drifted")
    return {
        "instrument": instrument,
        "public": public,
        "gold": gold,
        "sources": sources,
    }


def validate() -> dict[str, Any]:
    packages = _packages()
    return {
        "status": "passed",
        "instrument_id": INSTRUMENT_ID,
        "case_count": len(packages["public"]["cases"]),
        "asset_count": len(packages["sources"]["assets"]),
        "source_disjoint": packages["instrument"]["dataset"][
            "source_disjoint_from_prior_visual_sets"
        ],
        "gold_loaded_by_execution": False,
        "provider_calls": 0,
    }


def _authorized() -> bool:
    execution = _load(INSTRUMENT_PATH)["execution"]
    return bool(
        execution.get("provider_execution_authorized")
        and execution.get("paid_execution_authorized")
    )


def preflight(*, resume: bool = False) -> dict[str, Any]:
    result = validate()
    result.update(
        {
            "status": "ready" if _authorized() else "blocked-not-authorized",
            "jina_api_key_present": bool(os.getenv("JINA_API_KEY", "").strip()),
            "git_revision": _git_revision(),
            "git_clean": _git_is_clean(),
            "output_unused": not any(
                path.exists() for path in (RESPONSE_LEDGER, QUOTA_LEDGER, RESULT_PATH)
            ),
            "resume": resume,
            "maximum_calls": 90,
            "prior_accounted_tokens": JINA_CUMULATIVE_PRIOR_TOKENS,
            "account_token_limit": JINA_ACCOUNT_TOKEN_LIMIT,
            "maximum_reserved_tokens": (
                JINA_CUMULATIVE_PRIOR_TOKENS + 90 * 32_768
            ),
        }
    )
    if not result["jina_api_key_present"]:
        result["status"] = "blocked-missing-credential"
    if not result["git_clean"]:
        result["status"] = "blocked-dirty-worktree"
    if resume:
        if not RESPONSE_LEDGER.is_file() or RESULT_PATH.exists():
            result["status"] = "blocked-resume-state-invalid"
    elif not result["output_unused"]:
        result["status"] = "blocked-output-exists"
    if result["maximum_reserved_tokens"] > JINA_ACCOUNT_TOKEN_LIMIT:
        result["status"] = "blocked-token-limit"
    return result


def _open_response_ledger(
    *, resume: bool, bindings: dict[str, str]
) -> sqlite3.Connection:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    if RESPONSE_LEDGER.exists() and not resume:
        raise VisualOmniConfirmationError("response ledger already exists")
    connection = sqlite3.connect(RESPONSE_LEDGER)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS image_embeddings (
            asset_id TEXT PRIMARY KEY,
            response_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
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
        raise VisualOmniConfirmationError("response ledger binding drifted")
    if not existing:
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", bindings.items()
        )
        connection.commit()
    return connection


def _records_from_embeddings(
    connection: sqlite3.Connection,
    sources: dict[str, Any],
) -> list[VisualRegionEmbeddingV1]:
    rows = {
        row["asset_id"]: json.loads(row["response_json"])
        for row in connection.execute(
            "SELECT asset_id, response_json FROM image_embeddings"
        )
    }
    records: list[VisualRegionEmbeddingV1] = []
    for asset in sources["assets"]:
        payload = rows.get(asset["asset_id"])
        if payload is None:
            raise VisualOmniConfirmationError("image embedding is incomplete")
        if payload.get("model") != JINA_OMNI_MODEL:
            raise VisualOmniConfirmationError("persisted image identity drifted")
        region = asset["region_lineage"][0]
        records.append(
            VisualRegionEmbeddingV1(
                record_id=region["region_id"],
                course_id=asset["course_id"],
                source_artifact_id=asset["source_artifact_id"],
                source_version=str(asset["source_version_number"]),
                source_sha256=asset["source_sha256"],
                asset_id=asset["asset_id"],
                region_id=region["region_id"],
                render_sha256=asset["render_sha256"],
                bbox=tuple(region["bbox"]),
                modality=asset["modality"],
                vectors=tuple(tuple(float(value) for value in row) for row in payload["vectors"]),
            )
        )
    return records


async def _execute(*, resume: bool) -> dict[str, Any]:
    packages = _packages()
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "external_model_evaluation"
    )
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    if not _authorized():
        raise VisualOmniConfirmationError("provider execution is not authorized")
    if not _git_is_clean():
        raise VisualOmniConfirmationError("provider execution requires a clean worktree")
    bindings = {
        "instrument_id": INSTRUMENT_ID,
        "instrument_sha256": _file_sha256(INSTRUMENT_PATH),
        "public_sha256": packages["public"]["content_sha256"],
        "gold_sha256": packages["gold"]["content_sha256"],
        "sources_sha256": packages["sources"]["content_sha256"],
        "code_revision": _git_revision(),
        "provider_model": JINA_OMNI_MODEL,
    }
    connection = _open_response_ledger(resume=resume, bindings=bindings)
    quota = PersistentJinaQuotaLedgerV1(
        QUOTA_LEDGER,
        imported_tokens=JINA_CUMULATIVE_PRIOR_TOKENS,
        imported_ledger_sha256=PRIOR_LEDGER_SHA256,
    )
    provider = JinaOmniEmbeddingProviderV1(
        api_key=os.environ["JINA_API_KEY"],
        quota_ledger=quota,
    )
    try:
        embedded = {
            row[0]
            for row in connection.execute("SELECT asset_id FROM image_embeddings")
        }
        for asset in packages["sources"]["assets"]:
            if asset["asset_id"] in embedded:
                continue
            path = ROOT / asset["render_path"]
            if _file_sha256(path) != asset["render_sha256"]:
                raise VisualOmniConfirmationError("visual asset hash drifted")
            result = provider.embed_image(
                path.read_bytes(), mime_type=asset["mime_type"]
            )
            connection.execute(
                "INSERT INTO image_embeddings VALUES (?, ?, ?)",
                (
                    asset["asset_id"],
                    json.dumps(
                        {
                            "model": result.model,
                            "vectors": [list(row) for row in result.vectors],
                            "tokens": result.usage.total_tokens,
                        },
                        sort_keys=True,
                    ),
                    datetime.now(UTC).replace(microsecond=0).isoformat(),
                ),
            )
            connection.commit()
        index = VisualLateInteractionIndexV1(
            _records_from_embeddings(connection, packages["sources"])
        )
        with tempfile.TemporaryDirectory(prefix="visual-omni-product-") as directory:
            services: dict[str, StudentTutoringService] = {}
            repositories: list[SQLiteStudentRepository] = []
            wrapped_retrievers: list[VisualAwareRetrieverV2] = []
            for condition in ("control", "candidate"):
                repository = SQLiteStudentRepository(
                    Path(directory) / f"{condition}.sqlite3"
                )
                repositories.append(repository)
                historical._seed_product(repository, packages["sources"])
                decorator = None
                if condition == "candidate":

                    def decorate(text_retriever, release):
                        wrapped = VisualAwareRetrieverV2(
                            text_retriever=text_retriever,
                            query_provider=provider,
                            index=index,
                            course_id=release.course_id,
                            chunks=release.chunks,
                            artifact_id=(
                                "visual-omni-"
                                + packages["sources"]["content_sha256"][:24]
                            ),
                        )
                        wrapped_retrievers.append(wrapped)
                        return wrapped

                    decorator = decorate
                services[condition] = StudentTutoringService(
                    repository,
                    profile_path=historical.PROFILE_PATH,
                    generator=historical._generator(),
                    evidence_gate=historical._evidence_gate(),
                    claim_evidence_validator=historical._claim_validator(),
                    retriever_factory=lambda chunks, versions: BM25Retriever(
                        chunks, active_source_versions=versions
                    ),
                    retriever_decorator=decorator,
                )
            try:
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
                            "student-visual-evaluation", case["course_id"]
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
                                    "source_artifact_id": row.source_artifact_id,
                                    "source_version": row.source_version,
                                    "source_sha256": row.source_checksum,
                                    "region_id": row.region_id,
                                    "crop_ref": row.crop_ref,
                                }
                                for row in turn.citations
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
                connection.execute(
                    "INSERT OR REPLACE INTO metadata(key, value) VALUES (?, ?)",
                    (
                        "visual_call_count",
                        str(sum(row.visual_call_count for row in wrapped_retrievers)),
                    ),
                )
                connection.commit()
            finally:
                for repository in repositories:
                    repository.close()
    finally:
        connection.close()
    return score()


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split()).strip(" .")


def _ordinary_text_path_regression() -> bool:
    """Prove that a high-confidence ordinary text hit makes no visual call."""

    class TextRetriever:
        implementation_id = "ordinary-text-regression"

        def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
            del query, limit
            chunk = DocumentChunk(
                id="ordinary-text-chunk",
                document_id="ordinary-text-source",
                text="Office hours are held on Tuesday.",
                ordinal=0,
                source_artifact_id="ordinary-text-source",
                source_version=1,
                source_label=SourceLabel.COURSE_APPROVED,
                source_checksum="c" * 64,
                region_kind=RegionKind.TEXT,
                retrieval_allowed=True,
                display_allowed=True,
            )
            return [RetrievalHit(chunk=chunk, relevance_score=0.99, raw_score=8.0)]

    class NeverVisualProvider:
        calls = 0

        def embed_query(self, query: str) -> Any:
            del query
            self.calls += 1
            raise AssertionError("ordinary text path invoked the visual provider")

    provider = NeverVisualProvider()
    visual_record = VisualRegionEmbeddingV1(
        record_id="ordinary-visual-region",
        course_id="course",
        source_artifact_id="ordinary-visual-source",
        source_version="1",
        source_sha256="a" * 64,
        asset_id="ordinary-visual-asset",
        region_id="ordinary-visual-region",
        render_sha256="b" * 64,
        bbox=(0.0, 0.0, 1.0, 1.0),
        modality="diagram",
        vectors=((1.0, 0.0),),
    )
    retriever = VisualAwareRetrieverV2(
        text_retriever=TextRetriever(),
        query_provider=provider,  # type: ignore[arg-type]
        index=VisualLateInteractionIndexV1([visual_record]),
        course_id="course",
        chunks=[],
        artifact_id="ordinary-text-regression",
    )
    hits = retriever.retrieve("When are office hours?", limit=1)
    return provider.calls == 0 and hits[0].chunk.id == "ordinary-text-chunk"


def _percentile_95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)]


def score() -> dict[str, Any]:
    connection = sqlite3.connect(RESPONSE_LEDGER)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        "SELECT condition, case_id, response_json FROM responses"
    ).fetchall()
    if len(rows) != 120:
        connection.close()
        raise VisualOmniConfirmationError(
            "hidden gold cannot open before all 120 responses are durable"
        )
    responses = {
        (row["condition"], row["case_id"]): json.loads(row["response_json"])
        for row in rows
    }
    if len(responses) != 120:
        connection.close()
        raise VisualOmniConfirmationError("response portfolio is duplicated")
    metadata = dict(connection.execute("SELECT key, value FROM metadata").fetchall())
    connection.close()
    packages = _packages()
    gold = packages["gold"]
    sources = packages["sources"]
    asset_by_id = {row["asset_id"]: row for row in sources["assets"]}
    source_by_id = {row["source_artifact_id"]: row for row in sources["assets"]}
    metrics: dict[str, dict[str, Any]] = {}
    for condition in ("control", "candidate"):
        counts = {
            "fully_grounded": 0,
            "boundary_releases": 0,
            "unsupported_claims": 0,
            "invalid_citations": 0,
            "lineage_valid": 0,
            "wrong_course": 0,
            "action_correct": 0,
        }
        answerable = 0
        slice_failures: dict[str, int] = {}
        for case in gold["cases"]:
            response = responses[(condition, case["case_id"])]
            if response["action"] == case["expected_action"]:
                counts["action_correct"] += 1
            if case["expected_action"] != "answer":
                if response["action"] == "answer":
                    counts["boundary_releases"] += 1
                    counts["unsupported_claims"] += 1
                continue
            answerable += 1
            expected_regions = set(case["required_region_ids"])
            expected_sources = {
                asset_by_id[asset_id]["source_artifact_id"]
                for asset_id in case["required_asset_ids"]
            }
            cited_regions = {row["region_id"] for row in response["citations"]}
            cited_sources = {
                row["source_artifact_id"] for row in response["citations"]
            }
            citation_valid = bool(response["citations"])
            for citation in response["citations"]:
                source = source_by_id.get(citation["source_artifact_id"])
                if (
                    source is None
                    or citation["source_artifact_id"] not in expected_sources
                    or citation["source_version"] != 1
                    or citation["source_sha256"]
                    != (source["source_sha256"] if source else None)
                    or citation["region_id"] not in expected_regions
                ):
                    citation_valid = False
                    counts["invalid_citations"] += 1
                if source is None or source["course_id"] != "computer-networking":
                    counts["wrong_course"] += 1
            lineage = (
                citation_valid
                and cited_regions == expected_regions
                and cited_sources == expected_sources
                and all(row["crop_ref"] for row in response["citations"])
            )
            if lineage:
                counts["lineage_valid"] += 1
            supported = _normalized(case["canonical_answer"]) in _normalized(
                response["answer"]
            )
            if response["action"] == "answer" and not supported:
                counts["unsupported_claims"] += 1
            if response["action"] == "answer" and supported and lineage:
                counts["fully_grounded"] += 1
            else:
                public_case = next(
                    row
                    for row in packages["public"]["cases"]
                    if row["case_id"] == case["case_id"]
                )
                key = public_case["slice"]
                slice_failures[key] = slice_failures.get(key, 0) + 1
        metrics[condition] = {
            "fully_grounded_visual_success_count": counts["fully_grounded"],
            "fully_grounded_visual_success": counts["fully_grounded"] / answerable,
            "action_accuracy": counts["action_correct"] / 60,
            "boundary_releases": counts["boundary_releases"],
            "unsupported_claims": counts["unsupported_claims"],
            "invalid_or_wrong_version_citations": counts["invalid_citations"],
            "original_region_lineage": counts["lineage_valid"] / answerable,
            "wrong_course_retrieval": counts["wrong_course"],
            "failure_slices": slice_failures,
        }
    quota = PersistentJinaQuotaLedgerV1(
        QUOTA_LEDGER,
        imported_tokens=JINA_CUMULATIVE_PRIOR_TOKENS,
        imported_ledger_sha256=PRIOR_LEDGER_SHA256,
    )
    snapshot = quota.snapshot()
    quota_connection = sqlite3.connect(QUOTA_LEDGER)
    provider_rows = quota_connection.execute(
        "SELECT status, latency_ms FROM visual_query_calls"
    ).fetchall()
    quota_connection.close()
    p95 = _percentile_95([float(row[1]) / 1000 for row in provider_rows])
    candidate = metrics["candidate"]
    control = metrics["control"]
    delta = (
        candidate["fully_grounded_visual_success"]
        - control["fully_grounded_visual_success"]
    )
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
        "candidate_grounded_delta": delta >= 0,
        "provider_failures": all(row[0] == "completed" for row in provider_rows),
        "provider_call_limit": len(provider_rows) <= 90,
        "visual_retrieval_p95_seconds": p95 <= 8.0,
        "ordinary_text_path_provider_calls": _ordinary_text_path_regression(),
    }
    status = "completed-keep" if all(gates.values()) else "completed-refine"
    result = {
        "schema_version": 1,
        "run_id": INSTRUMENT_ID,
        "status": status,
        "decision": "Keep" if status == "completed-keep" else "Refine",
        "selected_for_release": status == "completed-keep",
        "completed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "code_revision": metadata["code_revision"],
        "instrument_sha256": metadata["instrument_sha256"],
        "public_sha256": metadata["public_sha256"],
        "gold_sha256": metadata["gold_sha256"],
        "sources_sha256": metadata["sources_sha256"],
        "conditions": metrics,
        "candidate_grounded_delta": delta,
        "provider": {
            "model": JINA_OMNI_MODEL,
            "calls": snapshot.calls,
            "actual_tokens": snapshot.completed_tokens,
            "accounted_tokens": snapshot.accounted_tokens,
            "prior_accounted_tokens": snapshot.imported_tokens,
            "cumulative_accounted_tokens": (
                snapshot.imported_tokens + snapshot.accounted_tokens
            ),
            "remaining_tokens": snapshot.remaining_tokens,
            "p95_latency_seconds": p95,
            "cost_usd": 0.0,
        },
        "hard_gates": gates,
        "gold_opened_after_durable_response_count": 120,
        "limitations": [
            "Fresh open-licensed networking visuals only; the result is not representative of every course modality.",
            "The Jina v5 omni API is licensed for non-commercial research use and is not production-throughput evidence.",
            "The deterministic generator evaluates extractive visual grounding rather than natural tutoring quality.",
            "No same-case tuning or rerun is permitted after this result.",
        ],
    }
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def simulate() -> dict[str, Any]:
    packages = _packages()
    if [row["case_id"] for row in packages["public"]["cases"]] != [
        row["case_id"] for row in packages["gold"]["cases"]
    ]:
        raise VisualOmniConfirmationError("simulation identity drifted")
    return {
        "status": "passed-network-free-simulation",
        "instrument_id": INSTRUMENT_ID,
        "cases": 60,
        "responses": 120,
        "maximum_provider_calls": 90,
        "gold_opening_order_enforced": True,
        "provider_calls": 0,
    }


async def execute(*, resume: bool) -> dict[str, Any]:
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise VisualOmniConfirmationError(
            f"live preflight is blocked: {readiness['status']}"
        )
    return await _execute(resume=resume)


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
            INSTRUMENT_ID, "external_model_evaluation"
        )
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "method_evaluation_execution"
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
