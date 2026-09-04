from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3

import httpx
import pytest

from src.digital_twin.grounding.models import (
    DocumentChunk,
    RegionKind,
    RetrievalHit,
)
from src.digital_twin.grounding.visual_late_interaction import (
    VisualEmbeddingResultV1,
    VisualEmbeddingUsageV1,
    VisualLateInteractionIndexV1,
    VisualRegionEmbeddingV1,
)
from src.digital_twin.grounding.visual_runtime import (
    JINA_ACCOUNT_TOKEN_LIMIT,
    PersistentJinaQuotaLedgerV1,
    QuotaBoundJinaVisualQueryProviderV1,
    VisualAwareRetrieverV1,
    VisualIndexStoreV1,
    VisualIndexUnavailableRetrieverV1,
    VisualProviderIdentityDriftError,
    VisualProviderUnavailableError,
    VisualRuntimeError,
)
from src.digital_twin.grounding import AnyHitEvidenceGate
from src.digital_twin.student import (
    SQLiteStudentRepository,
    StudentReleaseStatus,
    StudentTutoringService,
    seed_synthetic_student_workflow,
)
from src.digital_twin.tutor_policy import SourceLabel


ROOT = Path(__file__).resolve().parents[2]
PROFILE_PATH = ROOT / "research/05_evaluation/profiles/student-tutor-v1.json"


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
    ).hexdigest()


def _chunk(*, chunk_id: str = "chunk-1") -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        document_id="document-1",
        text="The diagram shows A followed by B.",
        ordinal=0,
        source_artifact_id="source-1",
        source_version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        locator="page 1 region",
        page_start=1,
        page_end=1,
        region_id="region-1",
        region_kind=RegionKind.DIAGRAM,
        bounding_box=(0.0, 0.0, 1.0, 1.0),
        crop_ref="derived/region-1.png",
        source_checksum="a" * 64,
        region_checksum="b" * 64,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={"title": "Synthetic diagram"},
    )


def _write_component_fixture(root: Path) -> tuple[Path, Path]:
    dataset = {
        "dataset_id": "visual-fixture",
        "assets": [
            {
                "asset_id": "asset-1",
                "course_id": "course-1",
                "modality": "diagram",
                "source_artifact_id": "source-1",
                "source_sha256": "a" * 64,
                "source_version": "revision-1",
                "render_sha256": "b" * 64,
                "region_lineage": [
                    {"region_id": "region-1", "bbox": [0.0, 0.0, 1.0, 1.0]}
                ],
            }
        ],
    }
    dataset["content_sha256"] = _canonical_sha256(dataset)
    dataset_path = root / "dataset.json"
    dataset_path.write_text(json.dumps(dataset), encoding="utf-8")
    ledger_path = root / "provider.sqlite3"
    connection = sqlite3.connect(ledger_path)
    connection.execute(
        """CREATE TABLE calls (
               request_key TEXT PRIMARY KEY,
               status TEXT NOT NULL,
               response_json TEXT
           )"""
    )
    connection.execute(
        "INSERT INTO calls VALUES (?, 'completed', ?)",
        (
            "image:asset-1",
            json.dumps(
                {
                    "provider_model": "jina-embeddings-v4",
                    "content": {"vectors": [[1.0, 0.0], [0.0, 1.0]]},
                }
            ),
        ),
    )
    connection.commit()
    connection.close()
    return dataset_path, ledger_path


def _record(*, course_id: str = "course-1") -> VisualRegionEmbeddingV1:
    return VisualRegionEmbeddingV1(
        record_id="region-1",
        course_id=course_id,
        source_artifact_id="source-1",
        source_version="1",
        source_sha256="a" * 64,
        asset_id="asset-1",
        region_id="region-1",
        render_sha256="b" * 64,
        bbox=(0.0, 0.0, 1.0, 1.0),
        modality="diagram",
        vectors=((1.0, 0.0),),
    )


class _TextRetriever:
    implementation_id = "text-control"

    def __init__(self) -> None:
        self.calls = 0

    def retrieve(self, query: str, *, limit: int = 5) -> list[RetrievalHit]:
        del query, limit
        self.calls += 1
        return [RetrievalHit(chunk=_chunk(), relevance_score=0.1, raw_score=0.1)]


class _QueryProvider:
    implementation_id = "query-fixture"

    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    def embed_query(self, query: str) -> VisualEmbeddingResultV1:
        del query
        self.calls += 1
        if self.fail:
            raise VisualProviderUnavailableError("provider unavailable")
        return VisualEmbeddingResultV1(
            model="jina-embeddings-v4",
            vectors=((1.0, 0.0),),
            usage=VisualEmbeddingUsageV1(total_tokens=3),
        )


def test_materializer_streams_component_vectors_and_binds_release(tmp_path) -> None:
    dataset_path, ledger_path = _write_component_fixture(tmp_path)
    store = VisualIndexStoreV1(tmp_path / "indexes")

    manifest = store.materialize_from_component_ledger(
        source_ledger_path=ledger_path,
        dataset_path=dataset_path,
        course_id="course-1",
        release_id="release-1",
        profile_id="profile-1",
        profile_version="1.0.0",
        chunks=[_chunk()],
    )
    loaded_manifest, index = store.load_bound(
        course_id="course-1",
        release_id="release-1",
        profile_id="profile-1",
        profile_version="1.0.0",
        source_ledger_sha256=manifest.source_ledger_sha256,
        chunks=[_chunk()],
    )

    assert loaded_manifest == manifest
    assert (
        index.retrieve(course_id="course-1", query_vectors=((1.0, 0.0),), limit=1)[0][
            "region_id"
        ]
        == "region-1"
    )
    with pytest.raises(VisualRuntimeError, match="binding drifted"):
        store.load_bound(
            course_id="course-1",
            release_id="release-1",
            profile_id="profile-1",
            profile_version="1.0.0",
            source_ledger_sha256=manifest.source_ledger_sha256,
            chunks=[_chunk(chunk_id="changed")],
        )
    with pytest.raises(VisualRuntimeError, match="binding drifted"):
        store.load_bound(
            course_id="course-1",
            release_id="release-1",
            profile_id="profile-1",
            profile_version="1.0.0",
            source_ledger_sha256="0" * 64,
            chunks=[_chunk()],
        )


def test_visual_retriever_leaves_text_path_unchanged_and_falls_back() -> None:
    text = _TextRetriever()
    provider = _QueryProvider()
    retriever = VisualAwareRetrieverV1(
        text_retriever=text,
        query_provider=provider,
        index=VisualLateInteractionIndexV1([_record()]),
        course_id="course-1",
        chunks=[_chunk()],
        artifact_id="visual-index-fixture",
    )

    text_hits = retriever.retrieve("Explain process scheduling.")
    visual_hits = retriever.retrieve("Which node follows A in the diagram?")

    assert text.calls == 1
    assert provider.calls == 1
    assert text_hits[0].relevance_score == 0.1
    assert visual_hits[0].chunk.region_id == "region-1"
    assert retriever.fallback_count == 0

    failing = VisualAwareRetrieverV1(
        text_retriever=text,
        query_provider=_QueryProvider(fail=True),
        index=VisualLateInteractionIndexV1([_record()]),
        course_id="course-1",
        chunks=[_chunk()],
        artifact_id="visual-index-fixture",
    )
    assert failing.retrieve("What follows A in the diagram?")[0].chunk.id == "chunk-1"
    assert failing.fallback_count == 1
    assert failing.primary_available is False


def test_visual_retriever_does_not_hide_authority_or_identity_drift() -> None:
    class DriftedProvider:
        implementation_id = "drifted-provider"

        def embed_query(self, query: str) -> VisualEmbeddingResultV1:
            del query
            raise VisualProviderIdentityDriftError("identity drift")

    retriever = VisualAwareRetrieverV1(
        text_retriever=_TextRetriever(),
        query_provider=DriftedProvider(),
        index=VisualLateInteractionIndexV1([_record()]),
        course_id="course-1",
        chunks=[_chunk()],
        artifact_id="visual-index-fixture",
    )

    with pytest.raises(VisualProviderIdentityDriftError, match="identity drift"):
        retriever.retrieve("What follows A in the diagram?")


def test_unavailable_visual_index_fallback_is_visible() -> None:
    retriever = VisualIndexUnavailableRetrieverV1(_TextRetriever())

    retriever.retrieve("What is shown in the diagram?")

    assert retriever.fallback_count == 1
    assert retriever.primary_available is False
    assert retriever.last_failure_type == "VisualIndexUnavailable"


def test_student_product_preserves_original_visual_region_citation(tmp_path) -> None:
    repository = SQLiteStudentRepository(tmp_path / "student.sqlite3")
    fixture = seed_synthetic_student_workflow(repository)
    original = repository.get_release(fixture.release_a_id)
    assert original is not None
    release = original.model_copy(
        update={
            "id": "release-visual-product",
            "chunks": [_chunk()],
            "created_at": "2099-01-01T00:00:00+00:00",
        },
        deep=True,
    )
    repository.set_release_status(
        fixture.release_a_id,
        StudentReleaseStatus.WITHDRAWN,
    )
    repository.save_release(release)
    provider = _QueryProvider()

    def decorate(text_retriever, active_release):
        return VisualAwareRetrieverV1(
            text_retriever=text_retriever,
            query_provider=provider,
            index=VisualLateInteractionIndexV1(
                [_record(course_id=active_release.course_id)]
            ),
            course_id=active_release.course_id,
            chunks=active_release.chunks,
            artifact_id="visual-index-product-fixture",
        )

    service = StudentTutoringService(
        repository,
        profile_path=PROFILE_PATH,
        evidence_gate=AnyHitEvidenceGate(),
        retriever_factory=lambda chunks, versions: _TextRetriever(),
        retriever_decorator=decorate,
    )
    conversation = service.create_conversation(
        fixture.student_a_id,
        fixture.course_a_id,
    )

    turn = asyncio.run(
        service.submit_message(
            fixture.student_a_id,
            conversation.id,
            content="What follows A in the diagram?",
            client_request_id="visual-product-turn",
        )
    )

    assert turn.tutor_message.action == "answer"
    assert len(turn.citations) == 1
    assert turn.citations[0].region_id == "region-1"
    assert turn.citations[0].crop_ref == "derived/region-1.png"
    retrieval = next(
        event
        for event in repository.list_audit_events()
        if event.event_type == "retrieval-completed"
    )
    assert retrieval.details["implementation"] == "jina-v4-late-interaction"
    assert retrieval.details["visual_index_artifact_id"] == (
        "visual-index-product-fixture"
    )


def test_quota_ledger_persists_imported_and_query_usage(tmp_path) -> None:
    ledger_path = tmp_path / "quota.sqlite3"
    ledger = PersistentJinaQuotaLedgerV1(
        ledger_path,
        imported_ledger_sha256="c" * 64,
    )
    ledger.reserve(request_id="request-1", request_sha256="d" * 64)
    ledger.complete(request_id="request-1", actual_tokens=7, latency_ms=2.0)

    reopened = PersistentJinaQuotaLedgerV1(
        ledger_path,
        imported_ledger_sha256="c" * 64,
    )
    snapshot = reopened.snapshot()
    assert snapshot.imported_tokens == 144_639
    assert snapshot.completed_tokens == 7
    assert snapshot.accounted_tokens == 7
    assert snapshot.remaining_tokens == JINA_ACCOUNT_TOKEN_LIMIT - 144_646


def test_jina_query_transport_records_success_and_conservative_failure(
    tmp_path,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "model": "jina-embeddings-v4",
                "data": [{"index": 0, "embeddings": [[1.0, 0.0]]}],
                "usage": {"total_tokens": 4},
            },
        )

    ledger = PersistentJinaQuotaLedgerV1(
        tmp_path / "success.sqlite3",
        imported_ledger_sha256="e" * 64,
    )
    provider = QuotaBoundJinaVisualQueryProviderV1(
        api_key="secret",
        quota_ledger=ledger,
        transport=httpx.MockTransport(handler),
    )
    assert provider.embed_query("Which node follows A?").usage.total_tokens == 4
    assert ledger.snapshot().accounted_tokens == 4

    failed_ledger = PersistentJinaQuotaLedgerV1(
        tmp_path / "failed.sqlite3",
        imported_ledger_sha256="f" * 64,
    )
    failed = QuotaBoundJinaVisualQueryProviderV1(
        api_key="secret",
        quota_ledger=failed_ledger,
        transport=httpx.MockTransport(lambda _: httpx.Response(500)),
    )
    with pytest.raises(VisualProviderUnavailableError, match="HTTP 500"):
        failed.embed_query("Which node follows A?")
    assert failed_ledger.snapshot().accounted_tokens == 32_768
