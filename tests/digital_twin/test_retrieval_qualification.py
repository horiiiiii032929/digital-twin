from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.digital_twin.evaluation import (
    CourseIsolationViolation,
    CourseScopedRetriever,
    ProviderQualificationConfig,
    RetrievalLadderConfig,
    SealedDevelopmentError,
    build_course_scoped_ladders,
    evaluate_development_cases,
    evaluate_cases,
    load_provider_qualification_config,
    load_sealed_development,
)
from src.digital_twin.grounding import DocumentChunk, RetrievalHit


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "cross_course_provider_qualification_v1.json"
)


def chunk(identifier: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        id=identifier,
        document_id=f"document-{identifier}",
        text=text,
        ordinal=0,
        retrieval_allowed=True,
    )


class KeywordEmbedder:
    def embed_documents(self, texts):
        return [self._vector(text) for text in texts]

    def embed_query(self, text):
        return self._vector(text)

    @staticmethod
    def _vector(text):
        lowered = text.lower()
        return [
            float("cache" in lowered),
            float("policy" in lowered),
            0.1,
        ]


class IdentityReranker:
    def score(self, query, documents):
        del query
        return [1 - index * 0.01 for index, _ in enumerate(documents)]


def test_frozen_provider_instrument_is_valid_and_balanced() -> None:
    config = load_provider_qualification_config(CONFIG_PATH)

    assert config.qualification_id == "cross-course-provider-qualification-v1"
    assert config.heldout_access_allowed is False
    assert config.spend_cap_usd == 5
    assert [provider.role for provider in config.providers] == [
        "control",
        "candidate",
    ]
    assert config.providers[1].embedding.model == ("jina-embeddings-v5-text-small")


def test_sealed_loader_never_requires_the_heldout_file(tmp_path: Path) -> None:
    development = {
        "dataset_id": "cross-course-retrieval-v1",
        "dataset_version": "draft-6",
        "dataset_status": "sealed",
        "cases": [
            {
                "case_id": f"case-{index}",
                "split": "development",
            }
            for index in range(40)
        ],
    }
    development_path = tmp_path / "private/development.json"
    development_path.parent.mkdir()
    development_path.write_text(
        f"{json.dumps(development)}\n",
        encoding="utf-8",
    )
    development_sha256 = hashlib.sha256(development_path.read_bytes()).hexdigest()
    heldout_sha256 = "b" * 64
    seal = {
        "seal_id": "seal-v1",
        "development_path": "private/development.json",
        "development_sha256": development_sha256,
        "heldout_path": "private/heldout-does-not-exist.json",
        "heldout_sha256": heldout_sha256,
        "heldout_access_allowed": False,
        "heldout_status": "unopened",
    }
    ledger = {
        "seal_id": "seal-v1",
        "heldout_sha256": heldout_sha256,
        "status": "unopened",
        "attempts": [],
    }
    seal_path = tmp_path / "seal.json"
    ledger_path = tmp_path / "ledger.json"
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    ledger_path.write_text(json.dumps(ledger), encoding="utf-8")
    config = ProviderQualificationConfig.model_validate(
        {
            **load_provider_qualification_config(CONFIG_PATH).model_dump(),
            "dataset_seal_id": "seal-v1",
            "development_sha256": development_sha256,
            "heldout_sha256": heldout_sha256,
        }
    )

    loaded, loaded_seal = load_sealed_development(
        root=tmp_path,
        seal_path=seal_path,
        ledger_path=ledger_path,
        config=config,
    )

    assert loaded == development
    assert loaded_seal["heldout_status"] == "unopened"
    assert not (tmp_path / seal["heldout_path"]).exists()


def test_sealed_loader_rejects_opened_ledger(tmp_path: Path) -> None:
    config = load_provider_qualification_config(CONFIG_PATH)
    seal_path = tmp_path / "seal.json"
    ledger_path = tmp_path / "ledger.json"
    seal_path.write_text(
        json.dumps(
            {
                "seal_id": config.dataset_seal_id,
                "development_sha256": config.development_sha256,
                "heldout_sha256": config.heldout_sha256,
                "heldout_access_allowed": False,
                "heldout_status": "unopened",
            }
        ),
        encoding="utf-8",
    )
    ledger_path.write_text(
        json.dumps(
            {
                "seal_id": config.dataset_seal_id,
                "heldout_sha256": config.heldout_sha256,
                "status": "opened",
                "attempts": [{"attempt": 1}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SealedDevelopmentError, match="not pristine"):
        load_sealed_development(
            root=tmp_path,
            seal_path=seal_path,
            ledger_path=ledger_path,
            config=config,
        )


def test_course_scope_fails_closed_on_injected_chunk() -> None:
    allowed = chunk("allowed", "cache policy")
    leaked = chunk("leaked", "private answer")

    class LeakingRetriever:
        def retrieve(self, query, *, limit=5):
            del query, limit
            return [RetrievalHit(chunk=leaked, relevance_score=1)]

    retriever = CourseScopedRetriever("COURSE-A", LeakingRetriever(), [allowed])

    with pytest.raises(CourseIsolationViolation, match="unauthorized"):
        retriever.retrieve("cache")


def test_shared_ladder_is_course_scoped_and_complete() -> None:
    chunks_by_course = {
        "COURSE-A": [chunk("a-cache", "cache coherence")],
        "COURSE-B": [chunk("b-policy", "policy enforcement")],
    }

    runtimes, index_seconds = build_course_scoped_ladders(
        chunks_by_course,
        embedder=KeywordEmbedder(),
        reranker=IdentityReranker(),
        config=RetrievalLadderConfig(
            bm25_k1=1.2,
            bm25_b=0.75,
            fusion_rank_constant=60,
            fusion_candidate_limit=20,
            rerank_candidate_limit=40,
            result_limit=10,
        ),
    )

    assert set(runtimes) == {"COURSE-A", "COURSE-B"}
    assert set(runtimes["COURSE-A"]) == {"M0", "M1", "M2", "M3"}
    assert all(value >= 0 for value in index_seconds.values())
    for method in runtimes["COURSE-A"].values():
        assert {hit.chunk.id for hit in method.retrieve("cache", limit=10)} <= {
            "a-cache"
        }


def test_development_runner_uses_all_cases_and_no_private_text() -> None:
    target = chunk("gold", "cache coherence")
    runtimes = {
        course: {
            method: CourseScopedRetriever(
                course,
                _StaticRetriever(target),
                [target],
            )
            for method in ("M0", "M1", "M2", "M3")
        }
        for course in ("A", "B", "C", "D")
    }
    cases = [
        {
            "case_id": "positive",
            "split": "development",
            "slice": "answerable",
            "difficulty": "direct",
            "target_course_id": "A",
            "query": "What is cache coherence?",
            "gold_evidence": [{"chunk_id": "gold"}],
        }
    ]
    cases.extend(
        {
            "case_id": f"boundary-{index:02d}",
            "split": "development",
            "slice": "no_evidence",
            "difficulty": "boundary",
            "target_course_id": None,
            "query": f"Unsupported question {index}",
            "gold_evidence": [],
        }
        for index in range(39)
    )

    rows, assignments = evaluate_development_cases(
        cases,
        runtimes=runtimes,
        chunk_course={"gold": "A"},
        result_limit=10,
    )

    assert len(rows) == 160
    assert len(assignments) == 39
    assert all("query" not in row for row in rows)
    assert all("chunk_text" not in row for row in rows)


def test_generic_runner_supports_the_heldout_split_contract() -> None:
    target = chunk("gold", "cache coherence")
    runtimes = {
        course: {
            method: CourseScopedRetriever(
                course,
                _StaticRetriever(target),
                [target],
            )
            for method in ("M0", "M1", "M2", "M3")
        }
        for course in ("A", "B")
    }
    cases = [
        {
            "case_id": "heldout-positive",
            "split": "heldout_draft",
            "slice": "answerable",
            "difficulty": "direct",
            "target_course_id": "A",
            "query": "What is cache coherence?",
            "gold_evidence": [{"chunk_id": "gold"}],
        }
    ]

    rows, assignments = evaluate_cases(
        cases,
        runtimes=runtimes,
        chunk_course={"gold": "A"},
        result_limit=10,
        expected_split="heldout_draft",
        expected_count=1,
    )

    assert len(rows) == 4
    assert assignments == {}
    assert all(row["case_id"] == "heldout-positive" for row in rows)


class _StaticRetriever:
    def __init__(self, returned: DocumentChunk) -> None:
        self.returned = returned

    def retrieve(self, query, *, limit=5):
        del query, limit
        return [RetrievalHit(chunk=self.returned, relevance_score=1, raw_score=1)]
