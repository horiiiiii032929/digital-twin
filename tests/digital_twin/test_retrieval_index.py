from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.digital_twin.grounding import (
    AnyHitEvidenceGate,
    DenseRetriever,
    DocumentChunk,
    RetrievalIndexBindingError,
    RetrievalIndexCorruptionError,
    RetrievalIndexStoreV1,
    RetrievalIndexUnavailableError,
    build_retrieval_index_binding,
)
from src.digital_twin.evaluation import ComponentKind, load_release_profile
from src.digital_twin.student import (
    ReleaseLifecycleService,
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    seed_synthetic_student_workflow,
)


QUERY_INSTRUCTION = (
    "Given a student question within one authorized university course, "
    "retrieve passages that directly support a grounded answer."
)
REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"


class CountingEmbedder:
    provider_id = "local-huggingface"
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    model_revision = REVISION
    execution = "local"
    instruction = QUERY_INSTRUCTION
    device = "mps"
    dtype = "float16"
    max_length = 2048
    batch_size = 16

    def __init__(self, *, fail_documents: bool = False) -> None:
        self.fail_documents = fail_documents
        self.document_calls = 0
        self.query_calls = 0

    def embed_documents(self, texts):
        self.document_calls += 1
        if self.fail_documents:
            raise AssertionError("runtime load attempted to re-embed documents")
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        self.query_calls += 1
        return self._vector(text)

    @staticmethod
    def _vector(text):
        lowered = text.lower()
        return [
            1.0 if "cache" in lowered else 0.05,
            1.0 if "policy" in lowered else 0.05,
            1.0 if "network" in lowered else 0.05,
            0.1,
        ]


def configuration() -> dict[str, str | int | float]:
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


def chunks(
    course_id: str = "course-a",
    *,
    source_version: int = 1,
) -> list[DocumentChunk]:
    return [
        DocumentChunk(
            id="cache",
            document_id="doc-cache",
            text="Cache coherence keeps shared memory consistent.",
            ordinal=0,
            source_artifact_id="source-cache",
            source_version=source_version,
            retrieval_allowed=True,
            metadata={"course_id": course_id, "title": "Cache"},
        ),
        DocumentChunk(
            id="policy",
            document_id="doc-policy",
            text="The course policy requires grounded citations.",
            ordinal=0,
            source_artifact_id="source-policy",
            source_version=source_version,
            retrieval_allowed=True,
            metadata={"course_id": course_id, "title": "Policy"},
        ),
        DocumentChunk(
            id="network",
            document_id="doc-network",
            text="A network protocol defines message exchange rules.",
            ordinal=0,
            source_artifact_id="source-network",
            source_version=source_version,
            retrieval_allowed=True,
            metadata={"course_id": course_id, "title": "Network"},
        ),
    ]


def binding(
    release_id: str = "release-a",
    *,
    course_id: str = "course-a",
    release_chunks: list[DocumentChunk] | None = None,
):
    return build_retrieval_index_binding(
        course_id=course_id,
        release_id=release_id,
        profile_id="student-tutor",
        profile_version="v1",
        chunker_id="page-bounded-heading-paragraph-chunker",
        chunker_version="v1",
        chunks=release_chunks or chunks(course_id),
        configuration=configuration(),
    )


def binding_for_release(release):
    profile = load_release_profile(PROFILE_PATH)
    retriever = next(
        entry for entry in profile.components if entry.component == ComponentKind.RETRIEVER
    )
    chunker = next(
        entry for entry in profile.components if entry.component == ComponentKind.CHUNKER
    )
    assert retriever.implementation is not None
    assert chunker.implementation is not None
    return build_retrieval_index_binding(
        course_id=release.course_id,
        release_id=release.id,
        profile_id=release.profile_id,
        profile_version=release.profile_version,
        chunker_id=chunker.implementation.implementation_id,
        chunker_version=chunker.implementation.version,
        chunks=release.chunks,
        configuration=retriever.implementation.configuration,
    )


def test_build_is_immutable_and_idempotent_without_reembedding(tmp_path: Path):
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    release_chunks = chunks()
    index_binding = binding(release_chunks=release_chunks)
    first_embedder = CountingEmbedder()

    first = store.build(index_binding, release_chunks, first_embedder)
    first_path = store.artifacts_root / first.artifact_id[:2] / first.artifact_id
    first_manifest = first_path / "manifest.json"
    original_manifest = first_manifest.read_bytes()

    second_embedder = CountingEmbedder(fail_documents=True)
    second = store.build(index_binding, list(reversed(release_chunks)), second_embedder)

    assert first == second
    assert first_embedder.document_calls == 1
    assert second_embedder.document_calls == 0
    assert first_manifest.read_bytes() == original_manifest
    assert not list(store.artifacts_root.glob(".building-*"))
    assert first_path.is_dir()


def test_loaded_index_uses_embedder_only_for_queries_and_matches_live_ranking(
    tmp_path: Path,
):
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    release_chunks = chunks()
    index_binding = binding(release_chunks=release_chunks)
    store.build(index_binding, release_chunks, CountingEmbedder())

    runtime_embedder = CountingEmbedder(fail_documents=True)
    loaded = store.load_bound(index_binding, runtime_embedder)
    loaded_hits = loaded.retriever.retrieve("How does cache coherence work?", limit=3)

    live_embedder = CountingEmbedder()
    live_dense = DenseRetriever(release_chunks, live_embedder)
    live_hits = live_dense.retrieve("How does cache coherence work?", limit=3)

    assert runtime_embedder.document_calls == 0
    assert runtime_embedder.query_calls == 1
    assert loaded_hits[0].chunk.id == live_hits[0].chunk.id == "cache"
    assert loaded.manifest.binding == index_binding


def test_corrupt_artifact_fails_closed_before_querying(tmp_path: Path):
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    release_chunks = chunks()
    index_binding = binding(release_chunks=release_chunks)
    manifest = store.build(index_binding, release_chunks, CountingEmbedder())
    dense_path = (
        store.artifacts_root
        / manifest.artifact_id[:2]
        / manifest.artifact_id
        / "dense.f32"
    )
    content = bytearray(dense_path.read_bytes())
    content[0] ^= 1
    dense_path.write_bytes(bytes(content))
    runtime_embedder = CountingEmbedder(fail_documents=True)

    with pytest.raises(RetrievalIndexCorruptionError, match="checksum"):
        store.load_bound(index_binding, runtime_embedder)

    assert runtime_embedder.document_calls == 0
    assert runtime_embedder.query_calls == 0


def test_changed_release_or_source_binding_cannot_reuse_an_index(tmp_path: Path):
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    release_chunks = chunks()
    original = binding(release_chunks=release_chunks)
    store.build(original, release_chunks, CountingEmbedder())

    changed_release = binding(
        release_id="release-b",
        release_chunks=release_chunks,
    )
    changed_chunks = chunks(source_version=2)
    changed_source = binding(release_chunks=changed_chunks)

    with pytest.raises(RetrievalIndexUnavailableError, match="unavailable"):
        store.load_bound(changed_release, CountingEmbedder())
    with pytest.raises(RetrievalIndexUnavailableError, match="unavailable"):
        store.load_bound(changed_source, CountingEmbedder())


def test_build_rejects_mixed_versions_of_the_same_source(tmp_path: Path):
    release_chunks = chunks()
    release_chunks[1] = release_chunks[1].model_copy(
        update={
            "source_artifact_id": release_chunks[0].source_artifact_id,
            "source_version": 2,
        }
    )
    index_binding = binding(release_chunks=release_chunks)

    with pytest.raises(RetrievalIndexBindingError, match="multiple versions"):
        RetrievalIndexStoreV1(tmp_path / "indexes").build(
            index_binding,
            release_chunks,
            CountingEmbedder(),
        )


def test_binding_rejects_boolean_numeric_configuration() -> None:
    invalid_configuration = configuration()
    invalid_configuration["embedding_batch_size"] = True

    with pytest.raises(RetrievalIndexBindingError, match="must be an integer"):
        build_retrieval_index_binding(
            course_id="course-a",
            release_id="release-a",
            profile_id="student-tutor",
            profile_version="v1",
            chunker_id="page-bounded-heading-paragraph-chunker",
            chunker_version="v1",
            chunks=chunks(),
            configuration=invalid_configuration,
        )


def test_active_pointer_is_atomic_and_supports_release_rollback(tmp_path: Path):
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    first_chunks = chunks()
    second_chunks = chunks(source_version=2)
    first_binding = binding("release-a", release_chunks=first_chunks)
    second_binding = binding("release-b", release_chunks=second_chunks)
    first = store.build(first_binding, first_chunks, CountingEmbedder())
    second = store.build(second_binding, second_chunks, CountingEmbedder())

    store.publish(first)
    assert store.load_published(first_binding, CountingEmbedder()).manifest == first
    store.publish(second)
    with pytest.raises(RetrievalIndexBindingError, match="requested release"):
        store.load_published(first_binding, CountingEmbedder())
    assert store.load_published(second_binding, CountingEmbedder()).manifest == second
    store.publish(first)

    restored = store.load_published(first_binding, CountingEmbedder())
    active_files = list(store.active_root.iterdir())
    assert restored.manifest == first
    assert len(active_files) == 1
    assert not any(path.suffix == ".tmp" for path in active_files)


def test_binding_pointer_tampering_is_rejected(tmp_path: Path):
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    release_chunks = chunks()
    index_binding = binding(release_chunks=release_chunks)
    store.build(index_binding, release_chunks, CountingEmbedder())
    pointer_path = store.bindings_root / f"{index_binding.binding_sha256}.json"
    payload = json.loads(pointer_path.read_text(encoding="utf-8"))
    payload["release_id"] = "other-release"
    pointer_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RetrievalIndexBindingError, match="does not match"):
        store.load_bound(index_binding, CountingEmbedder())


def test_student_runtime_fails_closed_when_release_index_is_missing(tmp_path: Path):
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=CountingEmbedder(fail_documents=True),
        evidence_gate=AnyHitEvidenceGate(),
        retrieval_index_store=store,
    )
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = asyncio.run(
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="What does cache coherence do?",
            client_request_id="missing-index",
        )
    )

    assert turn.tutor_message.action == "no-evidence"
    index_event = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "retrieval-index-unavailable"
    )
    assert index_event.details == {
        "failure_type": "RetrievalIndexUnavailableError"
    }


def test_student_runtime_loads_bound_index_without_document_embedding(tmp_path: Path):
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    release = repository.get_release(fixture.release_a_id)
    assert release is not None
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    store.build(binding_for_release(release), release.chunks, CountingEmbedder())
    runtime_embedder = CountingEmbedder(fail_documents=True)
    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        embedder=runtime_embedder,
        evidence_gate=AnyHitEvidenceGate(),
        retrieval_index_store=store,
    )
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = asyncio.run(
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="What does cache coherence do?",
            client_request_id="loaded-index",
        )
    )

    assert turn.tutor_message.action == "answer"
    assert runtime_embedder.document_calls == 0
    assert runtime_embedder.query_calls == 1
    retrieval = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "retrieval-completed"
    )
    assert retrieval.details["index_artifact_id"]


def test_publication_preflight_builds_once_and_publish_reuses_index(tmp_path: Path):
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    source_release = repository.get_release(fixture.release_a_id)
    assert source_release is not None
    draft = source_release.model_copy(
        update={
            "id": "release-indexed",
            "status": StudentReleaseStatus.DRAFT,
        },
        deep=True,
    )
    repository.save_release(draft)
    store = RetrievalIndexStoreV1(tmp_path / "indexes")
    embedder = CountingEmbedder()

    def prepare(release):
        store.build(binding_for_release(release), release.chunks, embedder)

    def ready(release):
        store.verify_bound(binding_for_release(release))
        return True

    lifecycle = ReleaseLifecycleService(
        repository,
        evidence_sufficiency_ready=True,
        retrieval_index_ready=ready,
        retrieval_index_preparer=prepare,
    )

    preflight = lifecycle.run_preflight(fixture.professor_id, draft.id)
    published = lifecycle.publish(fixture.professor_id, draft.id)

    assert preflight.passed is True
    assert next(check for check in preflight.checks if check.id == "retrieval-index").passed
    assert published.status == StudentReleaseStatus.PUBLISHED
    assert embedder.document_calls == 1


def test_publication_requires_index_readiness_and_preparation_as_a_pair(
    tmp_path: Path,
):
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")

    with pytest.raises(ValueError, match="configured together"):
        ReleaseLifecycleService(repository, retrieval_index_ready=lambda release: True)
    with pytest.raises(ValueError, match="configured together"):
        ReleaseLifecycleService(repository, retrieval_index_preparer=lambda release: None)
