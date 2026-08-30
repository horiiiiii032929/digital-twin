"""Live factual stages for the finite Course Digital Twin program."""

from __future__ import annotations

import asyncio
from datetime import UTC
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
from typing import Any

from services.embeddings import Qwen3TextEmbedder
from services.embeddings import OpenAITextEmbedder
from services.retrieval_provider import RetrievalUsageLedger
from scripts.run_academic_factual_qa_api_retrieval_selection import (
    _CachedQueryEmbedder,
    _query_vectors,
)
from scripts.academic_factual_qa_open_10000_t0_adapter import (
    PROFILE_PATH,
    RETRIEVAL_INDEX_ROOT,
    _chunks_by_course,
    build_live_t0_adapter,
)
from src.digital_twin.evaluation import (
    EvaluationCaseV1,
    EvaluationGoldV1,
    EvaluationResponseV1,
    ProgramStageStatus,
    SystemUnderTestManifestV1,
    build_atomic_final_rows,
    load_release_profile,
    package_rows,
    paired_control_subset,
)
from src.digital_twin.evaluation.factual_qa_execution import (
    ResponseLedgerV1,
    canonical_json_sha256,
    execute_cases,
)
from src.digital_twin.evaluation.finite_product_evaluation import (
    complete_product_decision,
    score_product_responses,
)
from src.digital_twin.evaluation.finite_program import ProgramStageName
from src.digital_twin.evaluation.finite_program_dataset import apply_reviewed_wording
from src.digital_twin.evaluation.finite_program_io import (
    atomic_write_json,
    file_sha256,
    load_json_object,
    model_binding,
    verify_hashed_package,
)
from src.digital_twin.evaluation.finite_program_runner import (
    StageExecutionContext,
    StageResultEnvelopeV1,
    build_stage_result,
)
from src.digital_twin.evaluation.finite_retrieval_evaluation import (
    evaluate_retrieval_method,
    select_retrieval_successor,
    select_untouched_retrieval_cases,
    validate_exact_reference_matchability,
)
from src.digital_twin.evaluation.provider_json import (
    DirectProviderJsonTransport,
    ProviderCallLedgerV1,
    ProviderJsonError,
)
from src.digital_twin.evaluation.retrieval_materialization import (
    materialize_retrieval_indexes,
)
from src.digital_twin.grounding import (
    ApiRetrievalIndexBindingV2,
    BM25Retriever,
    RetrievalIndexStoreV1,
    StreamingRetrievalIndexMaterializerV2,
    StructuredHierarchicalRetriever,
    build_retrieval_index_binding,
    should_use_semantic_reranking,
    source_set_sha256,
)


CONTROL_CASES = (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_control_mixed_wording_005_cases.json"
)
CONTROL_GOLD = (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_control_gold_002.json"
)
NANO_ROLE = "bounded-evidence-ranker-wording-visual-audit"
MINI_ROLE = "product-answer-generator"
LUNA_ROLE = "independent-question-action-verifier"


class FactualStageError(RuntimeError):
    """Raised when a factual stage cannot preserve its frozen contract."""


def _revision(root: Path) -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _rows(root: Path, context: StageExecutionContext):
    public = verify_hashed_package(
        root / context.manifest.development_cases_path, rows_key="cases"
    )
    gold = verify_hashed_package(
        root / context.manifest.development_gold_path, rows_key="gold"
    )
    cases = [EvaluationCaseV1.model_validate(row) for row in public["cases"]]
    references = [EvaluationGoldV1.model_validate(row) for row in gold["gold"]]
    return cases, references


def _development_source_path(context: StageExecutionContext) -> Path:
    return context.root / (
        context.manifest.development_source_path
        or context.manifest.source_plan_path
    )


def _profile_retriever_selection():
    profile = load_release_profile(PROFILE_PATH)
    return next(row for row in profile.components if row.component.value == "retriever")


def _qwen_embedder(selection, *, execution_device: str, execution_dtype: str):
    implementation = selection.implementation
    if implementation is None:
        raise FactualStageError("selected hybrid retriever is unavailable")
    configuration = implementation.configuration
    revision = str(configuration["embedding_revision"])
    model_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                Path(__file__).resolve().parents[1]
                / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    return Qwen3TextEmbedder(
        model_root / revision,
        instruction=str(configuration["query_instruction"]),
        device=execution_device,
        dtype=execution_dtype,
        batch_size=int(configuration["embedding_batch_size"]),
        max_length=int(configuration["embedding_max_length"]),
        model_revision=revision,
    )


def _local_retrievers(context: StageExecutionContext, *, source_path: Path):
    chunks_by_course, _ = _chunks_by_course(source_path)
    selection = _profile_retriever_selection()
    embedder = _qwen_embedder(
        selection,
        execution_device=context.manifest.retrieval_execution_device,
        execution_dtype=context.manifest.retrieval_execution_dtype,
    )
    profile_payload = load_json_object(PROFILE_PATH)
    model_root = Path(
        os.getenv(
            "ACADEMIC_EVAL_QWEN_MODEL_ROOT",
            str(
                Path(__file__).resolve().parents[1]
                / "data/external/huggingface/hub/"
                "models--Qwen--Qwen3-Embedding-0.6B/snapshots"
            ),
        )
    )
    materialize_retrieval_indexes(
        chunks_by_course=chunks_by_course,
        profile=profile_payload,
        model_root=model_root,
        output_root=RETRIEVAL_INDEX_ROOT,
    )
    bm25 = {
        course_id: BM25Retriever(chunks)
        for course_id, chunks in chunks_by_course.items()
    }
    implementation = selection.implementation
    if implementation is None:
        raise FactualStageError("hybrid retrieval selection is missing")
    chunker = next(
        row
        for row in profile_payload["components"]
        if row["component"] == "chunker"
    )["implementation"]
    store = RetrievalIndexStoreV1(RETRIEVAL_INDEX_ROOT)
    hybrid = {}
    for course_id, chunks in chunks_by_course.items():
        binding = build_retrieval_index_binding(
            course_id=course_id,
            release_id=f"{course_id}-academic-open-release",
            profile_id=str(profile_payload["profile_id"]),
            profile_version=str(profile_payload["profile_version"]),
            chunker_id=str(chunker["implementation_id"]),
            chunker_version=str(chunker["version"]),
            chunks=chunks,
            configuration=implementation.configuration,
        )
        hybrid[course_id] = store.load_bound(binding, embedder).retriever
    hierarchical = {
        course_id: StructuredHierarchicalRetriever(hybrid[course_id], chunks)
        for course_id, chunks in chunks_by_course.items()
    }
    return chunks_by_course, bm25, hybrid, hierarchical, {
        "provider_calls": 0,
        "reported_cost_usd": 0.0,
        "input_tokens": 0,
    }


def _api_retrievers(
    context: StageExecutionContext,
    cases: list[EvaluationCaseV1],
    *,
    source_path: Path,
):
    embedding = context.manifest.retrieval_embedding
    if embedding is None:
        raise FactualStageError("API retrieval binding is unavailable")
    chunks_by_course, _ = _chunks_by_course(source_path)
    ledger = RetrievalUsageLedger(
        max_cost_usd=max(0.01, context.remaining_stage_budget_usd),
        price_per_million_input_tokens_usd=(
            embedding.input_price_usd_per_million
        ),
    )
    embedder = OpenAITextEmbedder(
        os.environ[context.manifest.credential_environment_variable],
        ledger=ledger,
        model=embedding.model,
        dimensions=embedding.dimensions,
        batch_size=embedding.batch_size,
        request_token_limit=embedding.request_token_limit,
    )
    shared_root = (
        context.root / embedding.artifact_root_path
        if embedding.artifact_root_path is not None
        else context.output_root.parent / "_shared-api-retrieval-index-v2"
    )
    artifact_instrument_id = (
        embedding.artifact_instrument_id or context.manifest.program_id
    )
    store = StreamingRetrievalIndexMaterializerV2(shared_root)
    bindings: dict[str, ApiRetrievalIndexBindingV2] = {}
    artifact_ids: dict[str, str] = {}
    for course_id, chunks in sorted(chunks_by_course.items()):
        binding = ApiRetrievalIndexBindingV2(
            instrument_id=artifact_instrument_id,
            course_id=course_id,
            release_id=f"{course_id}-academic-open-release-api-v2",
            profile_id="course-digital-twin-api-retrieval-v2",
            profile_version="v2",
            chunker_id="source-range-clusterer",
            chunker_version="v1",
            source_set_sha256=source_set_sha256(chunks),
            chunk_count=len(chunks),
            embedding_model=embedding.model,
            embedding_dimensions=embedding.dimensions,
            embedding_batch_size=embedding.batch_size,
            embedding_request_token_limit=embedding.request_token_limit,
            input_price_usd_per_million=embedding.input_price_usd_per_million,
            metadata_verified_at=context.manifest.metadata_verified_at.astimezone(UTC),
            bm25_k1=1.2,
            bm25_b=0.75,
            fusion_rank_constant=60,
            fusion_candidate_limit=30,
        )
        work_path = store.work_root / f"{binding.binding_sha256}.sqlite3"
        manifest = store.materialize(
            binding,
            chunks,
            embedder,
            resume=work_path.exists(),
        )
        bindings[course_id] = binding
        artifact_ids[course_id] = manifest.artifact_id

    query_path = context.output_root / "api-query-vectors.sqlite3"
    vectors, _ = _query_vectors(
        path=query_path,
        cases=cases,
        embedder=embedder,
        model=embedding.model,
        dimensions=embedding.dimensions,
        instrument_sha256=context.manifest.content_sha256,
        resume=query_path.exists(),
    )
    cached = _CachedQueryEmbedder(
        model=embedding.model,
        dimensions=embedding.dimensions,
        vectors=vectors,
        batch_size=embedding.batch_size,
        request_token_limit=embedding.request_token_limit,
    )
    bm25 = {
        course_id: BM25Retriever(chunks)
        for course_id, chunks in chunks_by_course.items()
    }
    hybrid = {
        course_id: store.load(
            artifact_ids[course_id],
            expected_binding=bindings[course_id],
            embedder=cached,
        ).retriever
        for course_id in chunks_by_course
    }
    hierarchical = {
        course_id: StructuredHierarchicalRetriever(hybrid[course_id], chunks)
        for course_id, chunks in chunks_by_course.items()
    }
    usage = ledger.usage_snapshot()
    return chunks_by_course, bm25, hybrid, hierarchical, {
        "provider_calls": usage.request_count,
        "reported_cost_usd": usage.approximate_cost_usd,
        "input_tokens": usage.input_tokens,
        "failure_count": usage.failure_count,
    }


def _retrievers(
    context: StageExecutionContext,
    cases: list[EvaluationCaseV1],
    *,
    source_path: Path,
):
    if context.manifest.retrieval_embedding is not None:
        return _api_retrievers(context, cases, source_path=source_path)
    return _local_retrievers(context, source_path=source_path)


def _rerank_schema(expected: dict[str, list[str]]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(expected),
                "maxItems": len(expected),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["case_id", "ranked_chunk_ids"],
                    "properties": {
                        "case_id": {"type": "string", "enum": sorted(expected)},
                        "ranked_chunk_ids": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 12,
                            "items": {"type": "string"},
                        },
                    },
                },
            }
        },
    }


async def _nano_rankings(
    *,
    context: StageExecutionContext,
    cases: list[EvaluationCaseV1],
    hierarchical: dict[str, StructuredHierarchicalRetriever],
    ledger_path: Path,
    maximum_cost_usd: float,
    resume: bool,
) -> tuple[dict[str, list[str]], dict[str, Any]]:
    eligible: list[EvaluationCaseV1] = []
    candidates: dict[str, list[Any]] = {}
    for case in cases:
        plan = hierarchical[case.course_id].plan(case.question, limit=12)
        hits = list(plan.hits)
        margin = (
            hits[0].relevance_score - hits[1].relevance_score
            if len(hits) > 1
            else (hits[0].relevance_score if hits else 0.0)
        )
        if should_use_semantic_reranking(case.question, top_score_margin=margin):
            eligible.append(case)
            candidates[case.case_id] = hits
    maximum = math.floor(len(cases) * 0.40)
    selected = sorted(
        eligible,
        key=lambda row: hashlib.sha256(
            f"nano-rerank-v1:{row.case_id}".encode("utf-8")
        ).hexdigest(),
    )[:maximum]
    if not selected:
        return {}, {"provider_calls": 0, "reported_cost_usd": 0.0}
    batches = [selected[index : index + 10] for index in range(0, len(selected), 10)]
    binding = model_binding(
        context.manifest,
        role=NANO_ROLE,
        maximum_output_tokens=1_400,
        maximum_transport_retries=0,
    )
    if ledger_path.is_file():
        connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if metadata.get("status") == "completed":
                contents = [
                    json.loads(row[0])["content"]
                    for row in connection.execute(
                        "SELECT response_json FROM calls "
                        "WHERE status = 'completed' ORDER BY sequence"
                    )
                ]
            else:
                contents = []
        finally:
            connection.close()
        if contents:
            return (
                {
                    row["case_id"]: list(row["ranked_chunk_ids"])
                    for content in contents
                    for row in content["items"]
                },
                _provider_snapshot(ledger_path),
            )
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding={
            "program_id": context.manifest.program_id,
            "program_manifest_sha256": context.manifest.content_sha256,
            "stage": context.stage.value,
            "purpose": "bounded-question-only-semantic-reranking",
            "case_ids": [row.case_id for row in selected],
            "binding": binding,
        },
        maximum_calls=len(batches),
        maximum_cost_usd=maximum_cost_usd,
        resume=resume and ledger_path.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    rankings: dict[str, list[str]] = {}
    try:
        for number, batch in enumerate(batches, start=1):
            expected = {
                case.case_id: [hit.chunk.id for hit in candidates[case.case_id]]
                for case in batch
            }
            prompt_rows = [
                {
                    "case_id": case.case_id,
                    "question": case.question,
                    "candidates": [
                        {
                            "chunk_id": hit.chunk.id,
                            "text": hit.chunk.text[:1_000],
                        }
                        for hit in candidates[case.case_id]
                    ],
                }
                for case in batch
            ]
            response = await transport.call_with_ledger(
                ledger=ledger,
                request_key=f"nano-rerank-{number:04d}",
                provider_role="bounded-evidence-ranker",
                system=(
                    "Rank only the supplied chunk IDs by how completely they support "
                    "the supplied question. Never introduce an ID or answer the question."
                ),
                prompt=json.dumps(prompt_rows, sort_keys=True),
                task="finite-program-evidence-reranking",
                schema=_rerank_schema(expected),
            )
            rows = response.content["items"]
            if {row["case_id"] for row in rows} != set(expected):
                raise FactualStageError("nano reranker case IDs drifted")
            for row in rows:
                identifiers = list(row["ranked_chunk_ids"])
                if (
                    len(identifiers) != len(set(identifiers))
                    or not set(identifiers) <= set(expected[row["case_id"]])
                ):
                    raise FactualStageError("nano reranker chunk IDs drifted")
                rankings[row["case_id"]] = identifiers
        ledger.mark_complete()
        snapshot = ledger.snapshot()
    except BaseException:
        if ledger.snapshot()["status"] == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()
    return rankings, snapshot


def _rank_all_cases(
    cases: list[EvaluationCaseV1],
    *,
    method_id: str,
    bm25,
    hybrid,
    hierarchical,
    nano_rankings: dict[str, list[str]],
) -> dict[str, list[str]]:
    output: dict[str, list[str]] = {}
    for case in cases:
        if method_id == "bm25-v1":
            hits = bm25[case.course_id].retrieve(case.question, limit=5)
        elif method_id in {"qwen3-hybrid-v1", "openai-small-hybrid-v2"}:
            hits = hybrid[case.course_id].retrieve(case.question, limit=5)
        else:
            ranked_ids = nano_rankings.get(case.case_id)
            plan = hierarchical[case.course_id].plan(
                case.question,
                limit=5,
                allow_semantic_reranking=(
                    method_id == "hierarchical-nano-rerank-v1"
                    and ranked_ids is not None
                ),
                ranked_ids=ranked_ids,
            )
            hits = list(plan.hits)
        output[case.case_id] = [row.chunk.id for row in hits]
    return output


def run_retrieval_decision(context: StageExecutionContext) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    cases, references = _rows(context.root, context)
    source_path = _development_source_path(context)
    chunks_by_course, _ = _chunks_by_course(source_path)
    matchability = validate_exact_reference_matchability(
        gold=references,
        chunks=[chunk for rows in chunks_by_course.values() for chunk in rows],
    )
    selected_cases = select_untouched_retrieval_cases(cases)
    selected_ids = {row.case_id for row in selected_cases}
    gold = {row.case_id: row for row in references if row.case_id in selected_ids}
    _, bm25, hybrid, hierarchical, embedding_snapshot = _retrievers(
        context, cases, source_path=source_path
    )
    nano_enabled = context.manifest.retrieval_nano_reranking_enabled is not False
    if nano_enabled:
        nano_rankings, nano_snapshot = asyncio.run(
            _nano_rankings(
                context=context,
                cases=cases,
                hierarchical=hierarchical,
                ledger_path=context.output_root / "nano-reranking-provider.sqlite3",
                maximum_cost_usd=context.remaining_stage_budget_usd,
                resume=context.resume,
            )
        )
    else:
        nano_rankings = {}
        nano_snapshot = {
            "provider_calls": 0,
            "reported_cost_usd": 0.0,
            "status": "disabled-after-program-003-operational-failure",
        }
    methods = []
    observations: dict[str, list[dict[str, Any]]] = {}
    method_contracts = [
        ("bm25-v1", bm25, False, None),
        (
            "openai-small-hybrid-v2"
            if context.manifest.retrieval_embedding is not None
            else "qwen3-hybrid-v1",
            hybrid,
            False,
            None,
        ),
        ("hierarchical-deterministic-v1", hierarchical, True, None),
    ]
    if nano_enabled:
        method_contracts.append(
            (
                "hierarchical-nano-rerank-v1",
                hierarchical,
                True,
                lambda question, hits: nano_rankings.get(
                    next(
                        row.case_id
                        for row in selected_cases
                        if row.question == question
                    ),
                    [hit.chunk.id for hit in hits],
                ),
            )
        )
    for method_id, retrievers, use_hierarchy, rerank in method_contracts:
        rows, summary = evaluate_retrieval_method(
            method_id=method_id,
            cases=selected_cases,
            hidden_gold=gold,
            retrievers_by_course=retrievers,
            hierarchical=use_hierarchy,
            semantic_ranker=rerank,
        )
        methods.append(summary)
        observations[method_id] = [row.__dict__ for row in rows]
    selected = select_retrieval_successor(methods)
    status = (
        ProgramStageStatus.COMPLETED_KEEP
        if selected is not None
        else ProgramStageStatus.COMPLETED_REFINE
    )
    selected_method = selected.method_id if selected is not None else "none"
    rankings = (
        _rank_all_cases(
            cases,
            method_id=selected_method,
            bm25=bm25,
            hybrid=hybrid,
            hierarchical=hierarchical,
            nano_rankings=nano_rankings,
        )
        if selected is not None
        else {}
    )
    ranking_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": context.manifest.program_id,
        "program_manifest_sha256": context.manifest.content_sha256,
        "selected_method": selected_method,
        "case_count": len(rankings),
        "ranked_chunk_ids": rankings,
        "gold_loaded_by_product": False,
    }
    ranking_payload["content_sha256"] = canonical_json_sha256(ranking_payload)
    ranking_path = context.output_root / "selected-development-rankings.json"
    atomic_write_json(ranking_path, ranking_payload)
    result_payload = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "selected_method": selected_method,
        "summaries": [row.__dict__ for row in methods],
        "observations": observations,
        "exact_reference_matchability": matchability,
        "nano_ledger": nano_snapshot,
    }
    result_path = context.output_root / "retrieval-result.json"
    atomic_write_json(result_path, result_payload)
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=status,
        provider_calls=(
            int(embedding_snapshot.get("provider_calls", 0))
            + int(nano_snapshot.get("provider_calls", 0))
        ),
        cost_usd=(
            float(embedding_snapshot.get("reported_cost_usd", 0.0))
            + float(nano_snapshot.get("reported_cost_usd", 0.0))
        ),
        severe_release_count=sum(row.severe_release_count for row in methods),
        metrics={
            "selected_method": selected_method,
            "selected_complete_evidence_at_3": (
                selected.complete_evidence_at_3 if selected else 0.0
            ),
            "selected_evidence_recall_at_5": (
                selected.evidence_recall_at_5 if selected else 0.0
            ),
            "selected_boundary_accuracy": (
                selected.boundary_accuracy if selected else 0.0
            ),
            "required_reference_count": matchability["required_reference_count"],
            "missing_reference_count": matchability["missing_reference_count"],
        },
        artifacts={
            "result": str(result_path.relative_to(context.root)),
            "development_rankings": str(ranking_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
            "rankings_sha256": file_sha256(ranking_path),
        },
        limitations=(
            [
                "Nano-assisted retrieval was excluded prospectively after program "
                "003 returned an incomplete response. Stable deterministic methods "
                "remain compared under unchanged cases, gold, and gates."
            ]
            if not nano_enabled
            else []
        ),
    )


def _completed_responses(path: Path) -> list[EvaluationResponseV1]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        if metadata.get("status") != "completed":
            raise FactualStageError("product response ledger is not complete")
        return [
            EvaluationResponseV1.model_validate_json(row[0])
            for row in connection.execute(
                "SELECT payload_json FROM responses ORDER BY sequence"
            )
        ]
    finally:
        connection.close()


def _provider_snapshot(path: Path) -> dict[str, Any]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        row = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(cost_usd), 0), "
            "COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0) "
            "FROM calls"
        ).fetchone()
        return {
            **metadata,
            "provider_calls": int(row[0]),
            "reported_cost_usd": float(row[1]),
            "input_tokens": int(row[2]),
            "output_tokens": int(row[3]),
        }
    finally:
        connection.close()


async def _product_arm(
    *,
    context: StageExecutionContext,
    name: str,
    cases: list[EvaluationCaseV1],
    evidence_gate: str,
    maximum_cost_usd: float,
    precomputed_retrieval_path: Path | None,
    source_package_path: Path,
    tutoring_mode: str = "grounded-assistant",
    conversation_scope: str = "course",
    forced_failure_case_ids: set[str] | None = None,
    maximum_output_tokens: int = 600,
) -> tuple[list[EvaluationResponseV1], dict[str, Any], SystemUnderTestManifestV1]:
    output = context.output_root / name
    output.mkdir(parents=True, exist_ok=True)
    revision = _revision(context.root)
    model = next(row for row in context.manifest.models if row.role == MINI_ROLE)
    manifest = SystemUnderTestManifestV1(
        flow_id=f"{context.manifest.program_id}-{context.stage.value}-{name}",
        adapter_version="v1",
        code_revision=revision,
        profile_sha256=file_sha256(PROFILE_PATH),
        retriever=(
            "selected-api-program-retrieval-v2"
            if context.manifest.retrieval_embedding is not None
            else "selected-program-retrieval-v1"
            if precomputed_retrieval_path is not None
            else "qwen3-hybrid-v1"
        ),
        generator=(
            "openai-gpt-5.4-mini-question-targeted-atomic-v1"
            if context.manifest.retrieval_embedding is not None
            and name == "candidate"
            else "openai-gpt-5.4-mini-live-extractive-boundary"
            if context.manifest.retrieval_embedding is not None
            else "openai-responses-live-atomic-v2"
        ),
        policy="structured-professor-policy-v1",
        evidence_gate=evidence_gate,
        model_bindings={"product-generator": model.model},
        known_benchmark=False,
    )
    rows_hash = canonical_json_sha256(
        [row.model_dump(mode="json") for row in cases]
    )
    provider_path = output / "provider.sqlite3"
    response_path = output / "responses.sqlite3"
    state_path = output / "student-state.sqlite3"
    if response_path.is_file():
        connection = sqlite3.connect(f"file:{response_path}?mode=ro", uri=True)
        try:
            response_status = dict(
                connection.execute("SELECT key, value FROM metadata")
            ).get("status")
        finally:
            connection.close()
        if response_status == "completed":
            return (
                _completed_responses(response_path),
                _provider_snapshot(provider_path),
                manifest,
            )
    resume = context.resume and response_path.exists()
    adapter = build_live_t0_adapter(
        manifest=manifest,
        cases=cases,
        runtime={
            "instrument_id": context.manifest.program_id,
            "cases_sha256": rows_hash,
            "code_revision": revision,
            "provider_ledger_path": str(provider_path),
            "state_path": str(state_path),
            "resume": resume,
            "maximum_calls": len(cases),
            "maximum_cost_usd": maximum_cost_usd,
            "precomputed_retrieval_path": (
                str(precomputed_retrieval_path)
                if precomputed_retrieval_path is not None
                else None
            ),
            "source_package_path": str(source_package_path),
            "model_candidate_manifest": {
                "candidate_id": "finite-program-gpt-5.4-mini",
                "provider_model": model.model,
                "reasoning_effort": "low",
                "max_output_tokens": maximum_output_tokens,
            },
            "tutoring_mode": tutoring_mode,
            "conversation_scope": conversation_scope,
            "forced_failure_case_ids": sorted(forced_failure_case_ids or set()),
        },
    )
    ledger = ResponseLedgerV1(
        response_path,
        cases_sha256=rows_hash,
        system_manifest_sha256=canonical_json_sha256(
            manifest.model_dump(mode="json")
        ),
        run_configuration_sha256=canonical_json_sha256(
            {
                "program_manifest_sha256": context.manifest.content_sha256,
                "stage": context.stage.value,
                "name": name,
                "evidence_gate": evidence_gate,
            }
        ),
        resume=resume,
    )
    try:
        await execute_cases(cases=cases, adapter=adapter, manifest=manifest, ledger=ledger)
    finally:
        ledger.close()
    return _completed_responses(response_path), _provider_snapshot(provider_path), manifest


def _read_case_gold_packages(
    cases_path: Path, gold_path: Path
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1]]:
    public = verify_hashed_package(cases_path, rows_key="cases")
    hidden = verify_hashed_package(gold_path, rows_key="gold")
    return (
        [EvaluationCaseV1.model_validate(row) for row in public["cases"]],
        [EvaluationGoldV1.model_validate(row) for row in hidden["gold"]],
    )


def _read_public_cases(path: Path) -> list[EvaluationCaseV1]:
    payload = verify_hashed_package(path, rows_key="cases")
    return [EvaluationCaseV1.model_validate(row) for row in payload["cases"]]


def _read_hidden_gold(path: Path) -> list[EvaluationGoldV1]:
    payload = verify_hashed_package(path, rows_key="gold")
    return [EvaluationGoldV1.model_validate(row) for row in payload["gold"]]


def _advisory_schema(case_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(case_ids),
                "maxItems": len(case_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "case_id",
                        "deterministic_result_valid",
                        "semantic_support",
                        "action_consistent",
                        "citation_concern",
                        "source_truth_concern",
                        "rationale",
                    ],
                    "properties": {
                        "case_id": {"type": "string", "enum": case_ids},
                        "deterministic_result_valid": {"type": "boolean"},
                        "semantic_support": {"type": "boolean"},
                        "action_consistent": {"type": "boolean"},
                        "citation_concern": {"type": "boolean"},
                        "source_truth_concern": {"type": "boolean"},
                        "rationale": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 500,
                        },
                    },
                },
            }
        },
    }


def _advisory_case_ids(
    candidate: dict[str, Any],
    *,
    final: bool,
    paired_case_ids: set[str],
) -> list[str]:
    scores = candidate["case_scores"]
    failures = {
        str(row["case_id"])
        for row in scores
        if not (
            bool(row["fully_grounded_success"])
            if bool(row["answerable"])
            else bool(row["boundary_safe"])
        )
    }
    passing = [
        str(row["case_id"])
        for row in scores
        if str(row["case_id"]) not in failures
        and (not final or str(row["case_id"]) not in paired_case_ids)
    ]
    seeded_count = 200 if final else max(1, math.ceil(len(scores) * 0.10))
    seeded = sorted(
        passing,
        key=lambda case_id: hashlib.sha256(
            f"finite-advisory-sample-v1:{case_id}".encode("utf-8")
        ).hexdigest(),
    )[:seeded_count]
    selected = failures | set(seeded)
    if final:
        selected |= paired_case_ids
    return sorted(selected)


def _nonblocking_advisory_failure(error: ProviderJsonError) -> bool:
    value = str(error).casefold()
    blocking = (
        "identity drift",
        "credential missing",
        "cost limit",
        "call limit",
    )
    return not any(fragment in value for fragment in blocking)


async def _run_advisory_audit(
    *,
    context: StageExecutionContext,
    cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
    responses: list[EvaluationResponseV1],
    candidate: dict[str, Any],
    paired_case_ids: set[str],
    final: bool,
    maximum_cost_usd: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    selected_ids = _advisory_case_ids(
        candidate,
        final=final,
        paired_case_ids=paired_case_ids,
    )
    case_by_id = {row.case_id: row for row in cases}
    gold_by_id = {row.case_id: row for row in gold}
    response_by_id = {row.case_id: row for row in responses}
    score_by_id = {row["case_id"]: row for row in candidate["case_scores"]}
    if not set(selected_ids) <= (
        set(case_by_id) & set(gold_by_id) & set(response_by_id) & set(score_by_id)
    ):
        raise FactualStageError("advisory audit identities drifted")
    batches = [
        selected_ids[index : index + 10]
        for index in range(0, len(selected_ids), 10)
    ]
    binding = model_binding(
        context.manifest,
        role=NANO_ROLE,
        maximum_output_tokens=3_500,
        maximum_transport_retries=0,
    )
    ledger_path = context.output_root / "advisory-audit-provider.sqlite3"
    if not batches:
        return (
            {
                "authoritative": False,
                "selected_case_count": 0,
                "valid_vote_count": 0,
                "missing_vote_count": 0,
                "source_truth_concern_case_ids": [],
                "selection_sha256": canonical_json_sha256([]),
            },
            {"provider_calls": 0, "reported_cost_usd": 0.0},
        )
    if ledger_path.is_file():
        connection = sqlite3.connect(f"file:{ledger_path}?mode=ro", uri=True)
        try:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            if metadata.get("status") == "completed":
                contents = [
                    json.loads(row[0])["content"]
                    for row in connection.execute(
                        "SELECT response_json FROM calls "
                        "WHERE status = 'completed' ORDER BY sequence"
                    )
                ]
                votes = {
                    row["case_id"]: row
                    for content in contents
                    for row in content["items"]
                }
                concerns = sorted(
                    case_id
                    for case_id, row in votes.items()
                    if bool(row["source_truth_concern"])
                )
                return (
                    {
                        "authoritative": False,
                        "selected_case_count": len(selected_ids),
                        "valid_vote_count": len(votes),
                        "missing_vote_count": len(set(selected_ids) - set(votes)),
                        "source_truth_concern_case_ids": concerns,
                        "selection_sha256": canonical_json_sha256(selected_ids),
                    },
                    _provider_snapshot(ledger_path),
                )
        finally:
            connection.close()
    ledger = ProviderCallLedgerV1(
        ledger_path,
        run_binding={
            "program_manifest_sha256": context.manifest.content_sha256,
            "stage": context.stage.value,
            "purpose": "non-authoritative-deterministic-result-audit",
            "selected_case_ids_sha256": canonical_json_sha256(selected_ids),
            "binding": binding,
        },
        maximum_calls=len(batches),
        maximum_cost_usd=maximum_cost_usd,
        resume=context.resume and ledger_path.exists(),
    )
    transport = DirectProviderJsonTransport(binding)
    votes: dict[str, dict[str, Any]] = {}
    limitations: list[str] = []
    try:
        for number, identifiers in enumerate(batches, start=1):
            prompt = [
                {
                    "case": case_by_id[case_id].model_dump(mode="json"),
                    "canonical_truth": gold_by_id[case_id].model_dump(mode="json"),
                    "product_response": response_by_id[case_id].model_dump(
                        mode="json"
                    ),
                    "deterministic_score": score_by_id[case_id],
                }
                for case_id in identifiers
            ]
            try:
                response = await transport.call_with_ledger(
                    ledger=ledger,
                    request_key=f"advisory-{number:04d}",
                    provider_role="routine-semantic-audit",
                    system=(
                        "Audit the supplied deterministic source-linked evaluation. "
                        "Do not change the canonical truth or score. Flag only a "
                        "genuine semantic, action, citation, or source-truth concern."
                    ),
                    prompt=json.dumps(prompt, sort_keys=True),
                    task="finite-program-product-advisory-audit",
                    schema=_advisory_schema(identifiers),
                    quarantine_failures=True,
                )
            except ProviderJsonError as error:
                if not _nonblocking_advisory_failure(error):
                    raise
                limitations.append(f"batch-{number:04d}:{type(error).__name__}")
                continue
            rows = response.content["items"]
            if {row["case_id"] for row in rows} != set(identifiers):
                limitations.append(f"batch-{number:04d}:case-id-set-drift")
                continue
            votes.update({row["case_id"]: row for row in rows})
        if ledger.snapshot()["status"] == "running":
            ledger.mark_complete()
        snapshot = ledger.snapshot()
    except BaseException:
        if ledger.snapshot()["status"] == "running":
            ledger.mark_interrupted()
        raise
    finally:
        ledger.close()
    concerns = sorted(
        case_id
        for case_id, row in votes.items()
        if bool(row["source_truth_concern"])
    )
    return (
        {
            "authoritative": False,
            "selected_case_count": len(selected_ids),
            "valid_vote_count": len(votes),
            "missing_vote_count": len(set(selected_ids) - set(votes)),
            "source_truth_concern_case_ids": concerns,
            "selection_sha256": canonical_json_sha256(selected_ids),
            "limitations": limitations,
        },
        snapshot,
    )


def _run_product_stage(
    context: StageExecutionContext,
    *,
    cases: list[EvaluationCaseV1],
    control_cases: list[EvaluationCaseV1],
    gold_path: Path,
    control_gold_path: Path,
    rankings_path: Path,
    source_package_path: Path,
    final: bool,
) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    candidate_budget = context.remaining_stage_budget_usd * 0.82
    control_budget = context.remaining_stage_budget_usd * 0.10
    advisory_budget = context.remaining_stage_budget_usd * 0.08
    ranking_payload = load_json_object(rankings_path)
    all_rankings = ranking_payload.get("ranked_chunk_ids")
    if not isinstance(all_rankings, dict):
        raise FactualStageError("selected retrieval rankings are malformed")
    control_ids = {row.case_id for row in control_cases}
    if not control_ids <= set(all_rankings):
        raise FactualStageError("control cases are absent from selected rankings")
    control_ranking_payload = {
        **{
            key: value
            for key, value in ranking_payload.items()
            if key not in {"ranked_chunk_ids", "case_count", "content_sha256"}
        },
        "case_count": len(control_ids),
        "ranked_chunk_ids": {
            case_id: all_rankings[case_id] for case_id in sorted(control_ids)
        },
    }
    control_ranking_payload["content_sha256"] = canonical_json_sha256(
        control_ranking_payload
    )
    control_rankings_path = context.output_root / "control-rankings.json"
    atomic_write_json(control_rankings_path, control_ranking_payload)

    candidate_responses, candidate_provider, candidate_manifest = asyncio.run(
        _product_arm(
            context=context,
            name="candidate",
            cases=cases,
            evidence_gate=(
                "question-targeted-atomic-evidence-gate-v1"
                if context.manifest.retrieval_embedding is not None
                else "structured-hierarchical-coverage-evidence-gate-v1"
            ),
            maximum_cost_usd=candidate_budget,
            precomputed_retrieval_path=rankings_path,
            source_package_path=source_package_path,
            maximum_output_tokens=400,
        )
    )
    control_responses, control_provider, control_manifest = asyncio.run(
        _product_arm(
            context=context,
            name="control",
            cases=control_cases,
            evidence_gate="any-hit-evidence-gate-v1",
            maximum_cost_usd=control_budget,
            precomputed_retrieval_path=control_rankings_path,
            source_package_path=source_package_path,
            maximum_output_tokens=400,
        )
    )
    # Hidden gold is deliberately opened only after both response ledgers are
    # complete and durable. Neither adapter receives a gold path or object.
    gold = _read_hidden_gold(gold_path)
    control_gold = _read_hidden_gold(control_gold_path)
    candidate = score_product_responses(
        cases=cases, gold=gold, responses=candidate_responses
    )
    control = score_product_responses(
        cases=control_cases, gold=control_gold, responses=control_responses
    )
    passed, gates, paired = complete_product_decision(
        candidate=candidate, control=control, final=final
    )
    advisory, advisory_provider = asyncio.run(
        _run_advisory_audit(
            context=context,
            cases=cases,
            gold=gold,
            responses=candidate_responses,
            candidate=candidate,
            paired_case_ids={row.case_id for row in control_cases},
            final=final,
            maximum_cost_usd=advisory_budget,
        )
    )
    result = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "status": "completed-keep" if passed else "completed-refine",
        "candidate": candidate,
        "control": control,
        "gates": gates,
        "paired": paired,
        "candidate_manifest": candidate_manifest.model_dump(mode="json"),
        "control_manifest": control_manifest.model_dump(mode="json"),
        "provider": {
            "candidate": candidate_provider,
            "control": control_provider,
            "advisory": advisory_provider,
        },
        "advisory_review": advisory,
    }
    result_path = context.output_root / "product-result.json"
    atomic_write_json(result_path, result)
    calls = int(candidate_provider["provider_calls"]) + int(
        control_provider["provider_calls"]
    ) + int(advisory_provider["provider_calls"])
    cost = float(candidate_provider["reported_cost_usd"]) + float(
        control_provider["reported_cost_usd"]
    ) + float(advisory_provider["reported_cost_usd"])
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=(
            ProgramStageStatus.COMPLETED_KEEP
            if passed
            else ProgramStageStatus.COMPLETED_REFINE
        ),
        provider_calls=calls,
        cost_usd=cost,
        severe_release_count=int(
            candidate["summary"]["severe_unsupported_release_count"]
        ),
        metrics={
            **candidate["summary"]["metrics"],
            "paired_retention_lower_95": paired[
                "supported_answer_retention_delta_lower_95"
            ],
            "paired_boundary_non_regression": paired[
                "boundary_non_regression_passed"
            ],
        },
        artifacts={
            "result": str(result_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
            "system_manifest_sha256": canonical_json_sha256(
                candidate_manifest.model_dump(mode="json")
            ),
        },
        limitations=[
            "OpenAI nano advisory review is non-authoritative",
            *list(advisory.get("limitations", [])),
        ],
    )


def run_product_development(context: StageExecutionContext) -> StageResultEnvelopeV1:
    cases = _read_public_cases(context.root / context.manifest.development_cases_path)
    control_cases_path = context.root / (
        context.manifest.development_control_cases_path or CONTROL_CASES
    )
    control_gold_path = context.root / (
        context.manifest.development_control_gold_path or CONTROL_GOLD
    )
    control_cases = _read_public_cases(control_cases_path)
    rankings_path = (
        context.output_root.parent
        / ProgramStageName.RETRIEVAL_DECISION.value
        / "selected-development-rankings.json"
    )
    return _run_product_stage(
        context,
        cases=cases,
        control_cases=control_cases,
        gold_path=context.root / context.manifest.development_gold_path,
        control_gold_path=control_gold_path,
        rankings_path=rankings_path,
        source_package_path=_development_source_path(context),
        final=False,
    )


def _wording_schema(case_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(case_ids),
                "maxItems": len(case_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["case_id", "question"],
                    "properties": {
                        "case_id": {"type": "string", "enum": case_ids},
                        "question": {"type": "string", "minLength": 8, "maxLength": 400},
                    },
                },
            }
        },
    }


def _verification_schema(case_ids: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "minItems": len(case_ids),
                "maxItems": len(case_ids),
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "case_id",
                        "action",
                        "answer",
                        "evidence_quotes",
                        "faithful",
                    ],
                    "properties": {
                        "case_id": {"type": "string", "enum": case_ids},
                        "action": {
                            "type": "string",
                            "enum": ["answer", "abstain", "clarify", "refuse"],
                        },
                        "answer": {"type": "string", "maxLength": 4_000},
                        "evidence_quotes": {
                            "type": "array",
                            "maxItems": 5,
                            "items": {"type": "string", "maxLength": 2_000},
                        },
                        "faithful": {"type": "boolean"},
                    },
                },
            }
        },
    }


async def _construct_wording(
    context: StageExecutionContext,
    cases: list[EvaluationCaseV1],
    gold: list[EvaluationGoldV1],
) -> tuple[dict[str, str], dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    batches = [cases[index : index + 20] for index in range(0, len(cases), 20)]
    nano_binding = model_binding(
        context.manifest, role=NANO_ROLE, maximum_output_tokens=4_000
    )
    luna_binding = model_binding(
        context.manifest, role=LUNA_ROLE, maximum_output_tokens=8_000
    )
    half = context.remaining_stage_budget_usd / 2
    nano_path = context.output_root / "wording-provider.sqlite3"
    luna_path = context.output_root / "verification-provider.sqlite3"
    if nano_path.is_file() and luna_path.is_file():
        completed_contents: list[list[dict[str, Any]]] = []
        complete = True
        for path in (nano_path, luna_path):
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                metadata = dict(
                    connection.execute("SELECT key, value FROM metadata")
                )
                if metadata.get("status") != "completed":
                    complete = False
                    completed_contents.append([])
                    continue
                completed_contents.append(
                    [
                        json.loads(row[0])["content"]
                        for row in connection.execute(
                            "SELECT response_json FROM calls "
                            "WHERE status = 'completed' ORDER BY sequence"
                        )
                    ]
                )
            finally:
                connection.close()
        if complete:
            authored = {
                row["case_id"]: row["question"]
                for content in completed_contents[0]
                for row in content["items"]
            }
            verified = {
                row["case_id"]: row
                for content in completed_contents[1]
                for row in content["items"]
            }
            return (
                authored,
                verified,
                _provider_snapshot(nano_path),
                _provider_snapshot(luna_path),
            )
    nano_ledger = ProviderCallLedgerV1(
        nano_path,
        run_binding={
            "program_manifest_sha256": context.manifest.content_sha256,
            "purpose": "final-question-wording",
            "case_ids_sha256": canonical_json_sha256([row.case_id for row in cases]),
            "binding": nano_binding,
        },
        maximum_calls=len(batches),
        maximum_cost_usd=half,
        resume=context.resume and nano_path.exists(),
    )
    luna_ledger = ProviderCallLedgerV1(
        luna_path,
        run_binding={
            "program_manifest_sha256": context.manifest.content_sha256,
            "purpose": "independent-question-action-verification",
            "case_ids_sha256": canonical_json_sha256([row.case_id for row in cases]),
            "binding": luna_binding,
        },
        maximum_calls=len(batches),
        maximum_cost_usd=half,
        resume=context.resume and luna_path.exists(),
    )
    nano = DirectProviderJsonTransport(nano_binding)
    luna = DirectProviderJsonTransport(luna_binding)
    authored: dict[str, str] = {}
    verified: dict[str, dict[str, Any]] = {}
    gold_by_id = {row.case_id: row for row in gold}
    try:
        for number, batch in enumerate(batches, start=1):
            ids = [row.case_id for row in batch]
            try:
                response = await nano.call_with_ledger(
                    ledger=nano_ledger,
                    request_key=f"wording-{number:04d}",
                    provider_role="question-wording",
                    system=(
                        "Rewrite each canonical course question naturally without "
                        "answering it, adding facts, or changing its requested action."
                    ),
                    prompt=json.dumps(
                        [
                            {
                                "case_id": row.case_id,
                                "course_id": row.course_id,
                                "canonical_question": row.question,
                            }
                            for row in batch
                        ],
                        sort_keys=True,
                    ),
                    task="finite-program-final-wording",
                    schema=_wording_schema(ids),
                    quarantine_failures=True,
                )
            except ProviderJsonError as error:
                if "identity drifted" in str(error):
                    raise
            else:
                rows = response.content["items"]
                if {row["case_id"] for row in rows} == set(ids):
                    authored.update({row["case_id"]: row["question"] for row in rows})

            verification_prompt = []
            for case in batch:
                reference = gold_by_id[case.case_id]
                verification_prompt.append(
                    {
                        "case_id": case.case_id,
                        "question": authored.get(case.case_id, case.question),
                        "source_excerpt": "\n".join(
                            claim.answer_span for claim in reference.claims
                        ),
                        "instruction": (
                            "Answer from the excerpt or choose a non-answer action. "
                            "You are not shown another model's answer."
                        ),
                    }
                )
            try:
                response = await luna.call_with_ledger(
                    ledger=luna_ledger,
                    request_key=f"verification-{number:04d}",
                    provider_role="independent-question-action-verifier",
                    system=(
                        "Independently classify and answer each question only from its "
                        "source excerpt. Quote exact evidence and flag unfaithful wording."
                    ),
                    prompt=json.dumps(verification_prompt, sort_keys=True),
                    task="finite-program-final-question-verification",
                    schema=_verification_schema(ids),
                    quarantine_failures=True,
                )
            except ProviderJsonError as error:
                if "identity drifted" in str(error):
                    raise
            else:
                rows = response.content["items"]
                if {row["case_id"] for row in rows} == set(ids):
                    verified.update({row["case_id"]: row for row in rows})
        if nano_ledger.snapshot()["status"] == "running":
            nano_ledger.mark_complete()
        if luna_ledger.snapshot()["status"] == "running":
            luna_ledger.mark_complete()
        return authored, verified, nano_ledger.snapshot(), luna_ledger.snapshot()
    except BaseException:
        for ledger in (nano_ledger, luna_ledger):
            if ledger.snapshot()["status"] == "running":
                ledger.mark_interrupted()
        raise
    finally:
        nano_ledger.close()
        luna_ledger.close()


def run_final_construction(context: StageExecutionContext) -> StageResultEnvelopeV1:
    context.output_root.mkdir(parents=True, exist_ok=True)
    canonical_cases, gold, diagnostics, source_payload = build_atomic_final_rows(
        context.root / context.manifest.source_plan_path,
        program_id=context.manifest.program_id,
    )
    authored, verified, nano, luna = asyncio.run(
        _construct_wording(context, canonical_cases, gold)
    )
    cases, provenance = apply_reviewed_wording(
        canonical_cases,
        gold,
        authored_questions=authored,
        verifier_rows=verified,
    )
    control_cases, control_gold = paired_control_subset(cases, gold)
    public_payload = package_rows(
        dataset_id=(
            f"academic-factual-qa-open-10000-v1-final-{context.manifest.program_id}"
        ),
        split="final",
        rows_key="cases",
        rows=cases,
        source_plan_sha256=diagnostics["source_plan_sha256"],
        program_id=context.manifest.program_id,
    )
    gold_payload = package_rows(
        dataset_id=(
            f"academic-factual-qa-open-10000-v1-final-{context.manifest.program_id}-gold"
        ),
        split="final-hidden",
        rows_key="gold",
        rows=gold,
        source_plan_sha256=diagnostics["source_plan_sha256"],
        program_id=context.manifest.program_id,
    )
    control_public = package_rows(
        dataset_id=(
            f"academic-factual-qa-open-10000-v1-control-{context.manifest.program_id}"
        ),
        split="final-control",
        rows_key="cases",
        rows=control_cases,
        source_plan_sha256=diagnostics["source_plan_sha256"],
        program_id=context.manifest.program_id,
    )
    control_hidden = package_rows(
        dataset_id=(
            f"academic-factual-qa-open-10000-v1-control-{context.manifest.program_id}-gold"
        ),
        split="final-control-hidden",
        rows_key="gold",
        rows=control_gold,
        source_plan_sha256=diagnostics["source_plan_sha256"],
        program_id=context.manifest.program_id,
    )
    paths = {
        "source_corpus": context.output_root / "final-source-corpus.json",
        "public_cases": context.output_root / "final-public-cases.json",
        "hidden_gold": context.output_root / "final-hidden-gold.json",
        "control_cases": context.output_root / "control-public-cases.json",
        "control_gold": context.output_root / "control-hidden-gold.json",
    }
    for path, payload in zip(
        paths.values(),
        (
            source_payload,
            public_payload,
            gold_payload,
            control_public,
            control_hidden,
        ),
        strict=True,
    ):
        atomic_write_json(path, payload)
    accepted = sum(row["decision"] == "accepted-model-wording" for row in provenance)
    result_path = context.output_root / "construction-result.json"
    result = {
        "program_id": context.manifest.program_id,
        "stage": context.stage.value,
        "status": "completed-keep",
        "diagnostics": diagnostics,
        "model_wording_count": accepted,
        "canonical_fallback_count": len(provenance) - accepted,
        "wording_provenance": provenance,
        "provider": {"nano": nano, "luna": luna},
        "packages": {
            key: {"path": str(path.relative_to(context.root)), "sha256": file_sha256(path)}
            for key, path in paths.items()
        },
    }
    atomic_write_json(result_path, result)
    calls = int(nano["provider_calls"]) + int(luna["provider_calls"])
    cost = float(nano["reported_cost_usd"]) + float(luna["reported_cost_usd"])
    return build_stage_result(
        manifest=context.manifest,
        stage=context.stage,
        status=ProgramStageStatus.COMPLETED_KEEP,
        provider_calls=calls,
        cost_usd=cost,
        metrics={
            "case_count": 10_000,
            "answerable_count": 8_000,
            "boundary_count": 2_000,
            "model_wording_count": accepted,
            "canonical_fallback_count": len(provenance) - accepted,
        },
        artifacts={
            **{key: str(path.relative_to(context.root)) for key, path in paths.items()},
            "result": str(result_path.relative_to(context.root)),
            "result_sha256": file_sha256(result_path),
        },
        limitations=[
            "Canonical fallback is explicit when model wording or verification fails"
        ],
    )


def run_final_product(context: StageExecutionContext) -> StageResultEnvelopeV1:
    construction = (
        context.output_root.parent / ProgramStageName.FINAL_CONSTRUCTION.value
    )
    cases = _read_public_cases(construction / "final-public-cases.json")
    control_cases = _read_public_cases(construction / "control-public-cases.json")
    source_path = construction / "final-source-corpus.json"
    # Final rankings are generated from public questions only. Hidden gold remains
    # unopened by the product response process.
    _, bm25, hybrid, hierarchical, embedding_snapshot = _retrievers(
        context, cases, source_path=source_path
    )
    if context.manifest.retrieval_nano_reranking_enabled is False:
        nano_rankings = {}
        nano_snapshot = {
            "provider_calls": 0,
            "reported_cost_usd": 0.0,
            "status": "disabled-by-frozen-program",
        }
    else:
        nano_rankings, nano_snapshot = asyncio.run(
            _nano_rankings(
                context=context,
                cases=cases,
                hierarchical=hierarchical,
                ledger_path=context.output_root / "final-nano-reranking-provider.sqlite3",
                maximum_cost_usd=context.remaining_stage_budget_usd * 0.10,
                resume=context.resume,
            )
        )
    retrieval_result = load_json_object(
        context.output_root.parent
        / ProgramStageName.RETRIEVAL_DECISION.value
        / "retrieval-result.json"
    )
    method_id = str(retrieval_result["selected_method"])
    rankings = _rank_all_cases(
        cases,
        method_id=method_id,
        bm25=bm25,
        hybrid=hybrid,
        hierarchical=hierarchical,
        nano_rankings=nano_rankings,
    )
    ranking_payload: dict[str, Any] = {
        "schema_version": 1,
        "program_id": context.manifest.program_id,
        "program_manifest_sha256": context.manifest.content_sha256,
        "selected_method": method_id,
        "case_count": len(rankings),
        "ranked_chunk_ids": rankings,
        "gold_loaded_by_product": False,
    }
    ranking_payload["content_sha256"] = canonical_json_sha256(ranking_payload)
    rankings_path = context.output_root / "selected-final-rankings.json"
    atomic_write_json(rankings_path, ranking_payload)
    product_context = StageExecutionContext(
        root=context.root,
        output_root=context.output_root,
        manifest=context.manifest,
        stage=context.stage,
        resume=context.resume,
        remaining_stage_budget_usd=(
            context.remaining_stage_budget_usd
            - float(nano_snapshot.get("reported_cost_usd", 0.0))
        ),
        remaining_program_budget_usd=context.remaining_program_budget_usd,
        recorded_stage_provider_calls=context.recorded_stage_provider_calls,
        recorded_stage_cost_usd=context.recorded_stage_cost_usd,
    )
    product = _run_product_stage(
        product_context,
        cases=cases,
        control_cases=control_cases,
        gold_path=construction / "final-hidden-gold.json",
        control_gold_path=construction / "control-hidden-gold.json",
        rankings_path=rankings_path,
        source_package_path=source_path,
        final=True,
    )
    payload = product.model_dump(mode="json", exclude={"result_sha256"})
    payload["provider_calls"] = (
        product.provider_calls
        + int(embedding_snapshot.get("provider_calls", 0))
        + int(nano_snapshot.get("provider_calls", 0))
    )
    payload["cost_usd"] = (
        product.cost_usd
        + float(embedding_snapshot.get("reported_cost_usd", 0.0))
        + float(nano_snapshot.get("reported_cost_usd", 0.0))
    )
    payload["artifacts"]["final_rankings"] = str(
        rankings_path.relative_to(context.root)
    )
    payload["artifacts"]["final_rankings_sha256"] = file_sha256(rankings_path)
    payload["result_sha256"] = canonical_json_sha256(payload)
    return StageResultEnvelopeV1.model_validate(payload)
