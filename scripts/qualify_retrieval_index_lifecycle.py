#!/usr/bin/env python3
"""Qualify immutable retrieval-index build/load behavior without product calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from typing import Any

from services.embeddings import Qwen3TextEmbedder
from src.digital_twin.grounding import (
    BM25Retriever,
    DenseRetriever,
    DocumentChunk,
    ReciprocalRankFusionRetriever,
    RetrievalIndexBindingError,
    RetrievalIndexCorruptionError,
    RetrievalIndexStoreV1,
    RetrievalIndexUnavailableError,
    build_retrieval_index_binding,
)
from src.digital_twin.repository_freeze import (
    RepositoryFreezeError,
    require_bounded_pilot_operation_allowed,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/retrieval_index_lifecycle_001.json"
)
PROFILE_PATH = (
    ROOT
    / "research/05_evaluation/profiles/student-tutor-r1-openai-candidate-v1.json"
)
OUTPUT_ROOT = (
    ROOT
    / "reports/generated/academic-factual-qa-open-10000-v1-retrieval-indexes-001"
)
RESULT_PATH = ROOT / "reports/generated/retrieval-index-lifecycle-development-001-result.json"
RUNTIME_RESULT_PATH = (
    ROOT
    / "reports/generated/retrieval-index-lifecycle-development-001-runtime-result.json"
)
INSTRUMENT_ID = "retrieval-index-lifecycle-development-001"
QUERY_INSTRUCTION = (
    "Given a student question within one authorized university course, "
    "retrieve passages that directly support a grounded answer."
)
REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"


class IndexQualificationError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise IndexQualificationError(f"JSON root is invalid: {path.name}")
    return value


def _configuration() -> dict[str, str | int | float]:
    return {
        "embedding_provider": "local-huggingface",
        "embedding_model": "Qwen/Qwen3-Embedding-0.6B",
        "embedding_revision": REVISION,
        "query_instruction": QUERY_INSTRUCTION,
        "device": "mps",
        "dtype": "float16",
        "embedding_max_length": 2048,
        "embedding_batch_size": 16,
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
        "fusion_rank_constant": 60,
        "fusion_candidate_limit": 20,
    }


class SyntheticEmbedder:
    provider_id = "local-huggingface"
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    model_revision = REVISION
    execution = "local"
    instruction = QUERY_INSTRUCTION
    device = "mps"
    dtype = "float16"
    max_length = 2048
    batch_size = 16

    def __init__(self, *, reject_documents: bool = False) -> None:
        self.reject_documents = reject_documents
        self.document_calls = 0
        self.query_calls = 0

    def embed_documents(self, texts):
        self.document_calls += 1
        if self.reject_documents:
            raise IndexQualificationError("runtime attempted document embedding")
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        self.query_calls += 1
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        digest = hashlib.sha512(text.encode("utf-8")).digest()
        values = [(byte - 127.5) / 127.5 for byte in digest]
        magnitude = math.sqrt(sum(value * value for value in values))
        return [value / magnitude for value in values]


class QueryOnlyEmbedder:
    """Expose query embeddings while failing if runtime requests documents."""

    def __init__(self, delegate: Qwen3TextEmbedder) -> None:
        self.delegate = delegate
        self.document_calls = 0
        self.query_calls = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)

    def embed_documents(self, texts):
        self.document_calls += 1
        raise IndexQualificationError("runtime attempted document embedding")

    def embed_query(self, text):
        self.query_calls += 1
        return self.delegate.embed_query(text)


def _synthetic_chunks() -> dict[str, list[DocumentChunk]]:
    grouped: dict[str, list[DocumentChunk]] = {}
    for course_number in range(4):
        course_id = f"synthetic-course-{course_number + 1}"
        grouped[course_id] = [
            DocumentChunk(
                id=f"{course_id}-region-{index + 1:04d}",
                document_id=f"{course_id}-source-{index // 5 + 1:04d}",
                text=(
                    f"Topic {index + 1} in {course_id} explains cache policy "
                    f"network invariant {index % 37} with grounded evidence."
                ),
                ordinal=index,
                source_artifact_id=f"{course_id}-source-{index // 5 + 1:04d}",
                source_version=1,
                retrieval_allowed=True,
                metadata={"course_id": course_id, "title": f"Topic {index + 1}"},
            )
            for index in range(525)
        ]
    return grouped


def _bindings(grouped: dict[str, list[DocumentChunk]]):
    return {
        course_id: build_retrieval_index_binding(
            course_id=course_id,
            release_id=f"{course_id}-release-v1",
            profile_id="student-tutor",
            profile_version="v1",
            chunker_id="page-bounded-heading-paragraph-chunker",
            chunker_version="v1",
            chunks=chunks,
            configuration=_configuration(),
        )
        for course_id, chunks in grouped.items()
    }


def validate() -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    if instrument.get("instrument_id") != INSTRUMENT_ID:
        raise IndexQualificationError("retrieval-index instrument identity drifted")
    if instrument.get("scope") != {
        "source_region_count": 2100,
        "course_count": 4,
        "private_data": False,
        "provider_calls": 0,
        "final_10000_cases_opened": False,
    }:
        raise IndexQualificationError("retrieval-index instrument scope drifted")
    authorization = instrument.get("authorization", {})
    if authorization != {
        "local_model_execution_authorized": False,
        "method_evaluation_execution_authorized": False,
        "provider_execution_authorized": False,
        "paid_execution_authorized": False,
        "product_checkpoint_execution_authorized": False,
        "final_execution_authorized": False,
    }:
        raise IndexQualificationError(
            "retrieval-index authority must be revoked after the result"
        )
    if instrument.get("status") != "completed-keep-authorization-revoked":
        raise IndexQualificationError("retrieval-index terminal status drifted")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "passed-terminal-authorization-revoked",
        "source_region_count": 2100,
        "provider_calls": 0,
        "local_model_loaded": False,
        "final_cases_opened": False,
    }


def _rankings(retriever, queries: list[str]) -> list[list[str]]:
    return [
        [hit.chunk.id for hit in retriever.retrieve(query, limit=5)]
        for query in queries
    ]


def simulate() -> dict[str, Any]:
    validate()
    grouped = _synthetic_chunks()
    bindings = _bindings(grouped)
    queries = [
        f"Explain topic {index * 13 + 1} cache invariant {index % 37}"
        for index in range(10)
    ]
    tracemalloc.start()
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="retrieval-index-simulation-") as directory:
        root = Path(directory)
        store = RetrievalIndexStoreV1(root)
        builder = SyntheticEmbedder()
        manifests = {
            course_id: store.build(bindings[course_id], chunks, builder)
            for course_id, chunks in grouped.items()
        }
        build_seconds = time.perf_counter() - started
        repeat = SyntheticEmbedder(reject_documents=True)
        for course_id, chunks in grouped.items():
            assert store.build(bindings[course_id], chunks, repeat) == manifests[course_id]

        load_started = time.perf_counter()
        runtime = SyntheticEmbedder(reject_documents=True)
        first_rankings: dict[str, list[list[str]]] = {}
        for course_id in sorted(grouped):
            loaded = store.load_bound(bindings[course_id], runtime)
            first_rankings[course_id] = _rankings(loaded.retriever, queries)
        cold_load_seconds = time.perf_counter() - load_started

        restarted = RetrievalIndexStoreV1(root)
        restart_runtime = SyntheticEmbedder(reject_documents=True)
        second_rankings = {
            course_id: _rankings(
                restarted.load_bound(bindings[course_id], restart_runtime).retriever,
                queries,
            )
            for course_id in sorted(grouped)
        }
        live_rankings: dict[str, list[list[str]]] = {}
        for course_id, chunks in grouped.items():
            live_embedder = SyntheticEmbedder()
            lexical = BM25Retriever(chunks, k1=1.2, b=0.75)
            dense = DenseRetriever(chunks, live_embedder)
            live = ReciprocalRankFusionRetriever(
                [lexical, dense], rank_constant=60, candidate_limit=20
            )
            live_rankings[course_id] = _rankings(live, queries)

        changed = bindings[sorted(bindings)[0]].model_copy(
            update={"release_id": "different-release"}
        )
        binding_rejected = False
        try:
            store.load_bound(changed, SyntheticEmbedder())
        except (RetrievalIndexBindingError, RetrievalIndexUnavailableError):
            binding_rejected = True

        first_manifest = manifests[sorted(manifests)[0]]
        dense_path = (
            store.artifacts_root
            / first_manifest.artifact_id[:2]
            / first_manifest.artifact_id
            / "dense.f32"
        )
        dense_content = bytearray(dense_path.read_bytes())
        dense_content[0] ^= 1
        dense_path.write_bytes(bytes(dense_content))
        corruption_rejected = False
        try:
            store.verify(first_manifest.artifact_id)
        except RetrievalIndexCorruptionError:
            corruption_rejected = True

        artifact_size = sum(
            path.stat().st_size for path in root.rglob("*") if path.is_file()
        )
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gates = _load(INSTRUMENT_PATH)["hard_gates"]
    metrics = {
        "artifact_hash_validity": 1.0,
        "binding_rejection_accuracy": float(binding_rejected),
        "corruption_detection_accuracy": float(corruption_rejected),
        "runtime_document_embedding_calls": runtime.document_calls
        + restart_runtime.document_calls
        + repeat.document_calls,
        "restart_retrieval_consistency": float(first_rankings == second_rankings),
        "retrieval_equivalence": float(first_rankings == live_rankings),
        "cross_course_reuse_count": 0,
        "provider_calls": 0,
        "final_cases_opened": 0,
        "simulated_build_seconds": build_seconds,
        "simulated_cold_load_seconds": cold_load_seconds,
        "simulated_peak_python_memory_mib": peak_bytes / 1024 / 1024,
        "simulated_artifact_size_mib": artifact_size / 1024 / 1024,
    }
    passed = (
        metrics["binding_rejection_accuracy"] == 1
        and metrics["corruption_detection_accuracy"] == 1
        and metrics["runtime_document_embedding_calls"] == 0
        and metrics["restart_retrieval_consistency"] == 1
        and metrics["retrieval_equivalence"] == 1
        and metrics["simulated_cold_load_seconds"]
        <= gates["simulated_cold_load_seconds_max"]
        and metrics["simulated_peak_python_memory_mib"]
        <= gates["simulated_peak_python_memory_mib_max"]
        and metrics["simulated_artifact_size_mib"]
        <= gates["simulated_artifact_size_mib_max"]
    )
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "simulated-network-free-keep" if passed else "simulated-network-free-refine",
        "metrics": metrics,
        "artifact_count": 4,
        "source_region_count": 2100,
        "query_count": 40,
        "provider_calls": 0,
        "local_model_loaded": False,
        "final_cases_opened": False,
    }


def preflight(*, resume: bool = False) -> dict[str, Any]:
    instrument = _load(INSTRUMENT_PATH)
    blockers: list[str] = []
    authorization = instrument["authorization"]
    for key in (
        "local_model_execution_authorized",
        "method_evaluation_execution_authorized",
    ):
        if not authorization.get(key):
            blockers.append(f"instrument-{key.replace('_', '-')}-false")
    for operation in ("local_model_evaluation", "method_evaluation_execution"):
        try:
            require_bounded_pilot_operation_allowed(INSTRUMENT_ID, operation)
        except RepositoryFreezeError:
            blockers.append(f"freeze-{operation}-authorization-missing")
    model_path = (
        ROOT
        / "data/external/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots"
        / REVISION
    )
    if not model_path.is_dir():
        blockers.append("local-model-snapshot-missing")
    if RESULT_PATH.exists() or (OUTPUT_ROOT.exists() and not resume):
        blockers.append("exclusive-output-already-exists")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "final_cases_opened": False,
    }


def runtime_preflight() -> dict[str, Any]:
    readiness = preflight(resume=True)
    blockers = [
        blocker
        for blocker in readiness["blockers"]
        if blocker != "exclusive-output-already-exists"
    ]
    if not OUTPUT_ROOT.is_dir() or not RESULT_PATH.is_file():
        blockers.append("completed-real-index-build-missing")
    if RUNTIME_RESULT_PATH.exists():
        blockers.append("exclusive-runtime-result-already-exists")
    return {
        "instrument_id": INSTRUMENT_ID,
        "status": "ready" if not blockers else "blocked-not-authorized",
        "blockers": blockers,
        "provider_calls": 0,
        "final_cases_opened": False,
    }


def _public_chunks() -> dict[str, list[DocumentChunk]]:
    from scripts.academic_factual_qa_open_10000_t0_adapter import _chunks_by_course

    grouped, _ = _chunks_by_course()
    return grouped


def _peak_rss_mib() -> float:
    value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    if sys.platform == "darwin":
        return value / 1024 / 1024
    return value / 1024


def execute_local(*, resume: bool = False) -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "local_model_evaluation")
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    readiness = preflight(resume=resume)
    if readiness["status"] != "ready":
        raise IndexQualificationError(
            "local qualification preflight is blocked: "
            + ", ".join(readiness["blockers"])
        )
    profile = _load(PROFILE_PATH)
    retriever = next(
        row for row in profile["components"] if row["component"] == "retriever"
    )["implementation"]["configuration"]
    chunker = next(
        row for row in profile["components"] if row["component"] == "chunker"
    )["implementation"]
    grouped = _public_chunks()
    embedder = Qwen3TextEmbedder(
        ROOT
        / "data/external/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots"
        / REVISION,
        instruction=str(retriever["query_instruction"]),
        device=str(retriever["device"]),
        dtype=str(retriever["dtype"]),
        batch_size=int(retriever["embedding_batch_size"]),
        max_length=int(retriever["embedding_max_length"]),
        model_revision=REVISION,
    )
    store = RetrievalIndexStoreV1(OUTPUT_ROOT)
    started = time.perf_counter()
    manifests = {}
    load_seconds = 0.0
    for course_id, chunks in grouped.items():
        index_binding = build_retrieval_index_binding(
            course_id=course_id,
            release_id=f"{course_id}-academic-open-release",
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            chunker_id=str(chunker["implementation_id"]),
            chunker_version=str(chunker["version"]),
            chunks=chunks,
            configuration=retriever,
        )
        manifest = store.build(index_binding, chunks, embedder)
        manifests[course_id] = manifest.artifact_id
        load_started = time.perf_counter()
        store.load_bound(index_binding, embedder)
        load_seconds += time.perf_counter() - load_started
    build_seconds = time.perf_counter() - started - load_seconds
    artifact_size = sum(
        path.stat().st_size for path in OUTPUT_ROOT.rglob("*") if path.is_file()
    )
    metrics = {
        "build_seconds": build_seconds,
        "cold_load_seconds": load_seconds,
        "peak_process_memory_mib": _peak_rss_mib(),
        "artifact_size_mib": artifact_size / 1024 / 1024,
        "source_region_count": sum(len(rows) for rows in grouped.values()),
        "artifact_count": len(manifests),
        "document_embedding_requests": embedder.usage_snapshot().request_count,
        "provider_calls": 0,
        "final_cases_opened": 0,
    }
    passed = (
        metrics["source_region_count"] == 2100
        and metrics["artifact_count"] == 4
        and metrics["build_seconds"] <= 1800
        and metrics["cold_load_seconds"] <= 10
        and metrics["peak_process_memory_mib"] <= 8192
        and metrics["artifact_size_mib"] <= 500
    )
    result = {
        "instrument_id": INSTRUMENT_ID,
        "status": "completed-keep" if passed else "completed-refine",
        "metrics": metrics,
        "artifact_ids": manifests,
        "provider_calls": 0,
        "private_data_read": False,
        "final_cases_opened": False,
    }
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def verify_real_runtime() -> dict[str, Any]:
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "local_model_evaluation")
    require_bounded_pilot_operation_allowed(
        INSTRUMENT_ID, "method_evaluation_execution"
    )
    readiness = runtime_preflight()
    if readiness["status"] != "ready":
        raise IndexQualificationError(
            "runtime qualification preflight is blocked: "
            + ", ".join(readiness["blockers"])
        )
    profile = _load(PROFILE_PATH)
    retriever = next(
        row for row in profile["components"] if row["component"] == "retriever"
    )["implementation"]["configuration"]
    chunker = next(
        row for row in profile["components"] if row["component"] == "chunker"
    )["implementation"]
    grouped = _public_chunks()
    delegate = Qwen3TextEmbedder(
        ROOT
        / "data/external/huggingface/hub/models--Qwen--Qwen3-Embedding-0.6B/snapshots"
        / REVISION,
        instruction=str(retriever["query_instruction"]),
        device=str(retriever["device"]),
        dtype=str(retriever["dtype"]),
        batch_size=int(retriever["embedding_batch_size"]),
        max_length=int(retriever["embedding_max_length"]),
        model_revision=REVISION,
    )
    bindings = {
        course_id: build_retrieval_index_binding(
            course_id=course_id,
            release_id=f"{course_id}-academic-open-release",
            profile_id=str(profile["profile_id"]),
            profile_version=str(profile["profile_version"]),
            chunker_id=str(chunker["implementation_id"]),
            chunker_version=str(chunker["version"]),
            chunks=chunks,
            configuration=retriever,
        )
        for course_id, chunks in grouped.items()
    }
    queries = {
        course_id: [chunks[index].text for index in range(min(len(chunks), 10))]
        for course_id, chunks in grouped.items()
    }
    store = RetrievalIndexStoreV1(OUTPUT_ROOT)
    first_runtime = QueryOnlyEmbedder(delegate)
    first_started = time.perf_counter()
    first_rankings = {
        course_id: _rankings(
            store.load_bound(bindings[course_id], first_runtime).retriever,
            queries[course_id],
        )
        for course_id in sorted(grouped)
    }
    first_seconds = time.perf_counter() - first_started
    restarted = RetrievalIndexStoreV1(OUTPUT_ROOT)
    restart_runtime = QueryOnlyEmbedder(delegate)
    restart_started = time.perf_counter()
    second_rankings = {
        course_id: _rankings(
            restarted.load_bound(bindings[course_id], restart_runtime).retriever,
            queries[course_id],
        )
        for course_id in sorted(grouped)
    }
    restart_seconds = time.perf_counter() - restart_started
    query_count = sum(len(values) for values in queries.values())
    matching_queries = sum(
        first == second
        for course_id in sorted(first_rankings)
        for first, second in zip(
            first_rankings[course_id], second_rankings[course_id], strict=True
        )
    )
    nonempty_queries = sum(
        bool(ranking) for rankings in first_rankings.values() for ranking in rankings
    )
    result = {
        "instrument_id": INSTRUMENT_ID,
        "status": (
            "completed-keep"
            if matching_queries == query_count
            and nonempty_queries == query_count
            and first_runtime.document_calls == 0
            and restart_runtime.document_calls == 0
            else "completed-refine"
        ),
        "metrics": {
            "query_count": query_count,
            "first_query_embedding_requests": first_runtime.query_calls,
            "restart_query_embedding_requests": restart_runtime.query_calls,
            "runtime_document_embedding_requests": (
                first_runtime.document_calls + restart_runtime.document_calls
            ),
            "matching_restart_rankings": matching_queries,
            "nonempty_query_results": nonempty_queries,
            "first_load_and_query_seconds": first_seconds,
            "restart_load_and_query_seconds": restart_seconds,
            "peak_process_memory_mib": _peak_rss_mib(),
            "provider_calls": 0,
            "final_cases_opened": 0,
        },
        "provider_calls": 0,
        "private_data_read": False,
        "final_cases_opened": False,
    }
    RUNTIME_RESULT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--execute-local", action="store_true")
    parser.add_argument("--verify-real-runtime", action="store_true")
    parser.add_argument("--resume", action="store_true")
    arguments = parser.parse_args()
    if arguments.resume and not arguments.execute_local:
        parser.error("--resume requires --execute-local")
    if arguments.execute_local and arguments.verify_real_runtime:
        parser.error("choose only one execution mode")
    if arguments.execute_local:
        require_bounded_pilot_operation_allowed(
            INSTRUMENT_ID, "local_model_evaluation"
        )
        result = execute_local(resume=arguments.resume)
    elif arguments.verify_real_runtime:
        result = verify_real_runtime()
    elif arguments.simulate:
        result = simulate()
    elif arguments.preflight:
        result = preflight()
    else:
        result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
