from __future__ import annotations

import hashlib
import json

from src.digital_twin.grounding.ambiguity_safe_evidence import (
    AmbiguitySafeEvidenceGateV1,
)
from src.digital_twin.grounding.evidence_sufficiency import (
    StructuredLexicalCoverageEvidenceGate,
)
from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit
from src.digital_twin.grounding.reference_uniqueness import (
    prefer_specific_source_regions,
)
from src.digital_twin.grounding.semantic_evidence_atoms import (
    ATOM_VERSION,
    SourceSemanticEvidenceAtomGateV1,
    SourceSemanticEvidenceAtomGateV2,
    SourceSemanticEvidenceAtomGateV3,
    SourceSemanticEvidenceAtomRetrieverV1,
    materialize_semantic_evidence_atoms,
)


CHECKSUM = hashlib.sha256(b"source-semantic-atom-test").hexdigest()


def _chunk(
    identifier: str,
    text: str,
    *,
    title: str,
    cluster: str,
    ordinal: int,
    modality: str = "text",
) -> DocumentChunk:
    start = ordinal * 200
    return DocumentChunk(
        id=identifier,
        document_id="course:notes.md",
        source_artifact_id="course:notes.md",
        source_version=1,
        source_checksum=CHECKSUM,
        source_label="course-approved",
        text=text,
        locator=f"notes.md:{start}",
        region_id=identifier,
        ordinal=ordinal,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "title": title,
            "parent_cluster_id": cluster,
            "course_id": "course",
            "source_path": "notes.md",
            "char_start": str(start),
            "char_end": str(start + len(text)),
            "modality": modality,
        },
    )


def test_materializer_preserves_citable_text_and_adds_atom_specific_relations() -> None:
    first = _chunk(
        "first",
        "Round-robin scheduling rotates runnable processes after a time slice.",
        title="Scheduling",
        cluster="scheduling",
        ordinal=0,
    )
    second = _chunk(
        "second",
        "A context switch saves one process state before restoring another.",
        title="Scheduling",
        cluster="scheduling",
        ordinal=1,
    )

    atoms = materialize_semantic_evidence_atoms([first, second])

    assert [row.text for row in atoms] == [first.text, second.text]
    assert all(
        row.metadata["semantic_atom_version"] == ATOM_VERSION for row in atoms
    )
    assert json.loads(atoms[0].metadata["semantic_related_atom_ids"]) == ["second"]
    assert json.loads(atoms[1].metadata["semantic_adjacent_atom_ids"]) == ["first"]
    assert first.text in atoms[0].metadata["semantic_search_text"]
    assert second.text not in atoms[0].metadata["semantic_search_text"]


def test_retriever_and_gate_resolve_related_multi_atom_evidence() -> None:
    scheduling = _chunk(
        "scheduling",
        "Round-robin scheduling rotates runnable processes after a time slice.",
        title="Scheduling",
        cluster="scheduling-cluster",
        ordinal=0,
    )
    context_switch = _chunk(
        "context-switch",
        "A context switch saves one process state before restoring another.",
        title="Scheduling",
        cluster="scheduling-cluster",
        ordinal=1,
    )
    unrelated = _chunk(
        "virtual-memory",
        "Virtual memory maps process addresses through page tables.",
        title="Virtual memory",
        cluster="memory-cluster",
        ordinal=2,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1(
        [unrelated, context_switch, scheduling]
    )
    question = (
        'Which two statements in "Scheduling" connect round-robin time slice '
        "with context switch process state?"
    )

    hits = retriever.retrieve(question, limit=5)
    decision = SourceSemanticEvidenceAtomGateV1().assess(question, hits)

    assert [row.chunk.id for row in hits[:2]] == ["scheduling", "context-switch"]
    assert decision.sufficient is True
    assert decision.selected_hit_ids == ["scheduling", "context-switch"]
    assert retriever.last_trace is not None
    assert retriever.last_trace.relation_constrained is True


def test_multi_atom_gate_rejects_unrelated_ranges() -> None:
    first = _chunk(
        "first",
        "Round-robin scheduling rotates runnable processes after a time slice.",
        title="Scheduling",
        cluster="one",
        ordinal=0,
    )
    second = _chunk(
        "second",
        "A context switch saves one process state before restoring another.",
        title="Scheduling",
        cluster="two",
        ordinal=1,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([first, second])
    question = (
        'Which two statements in "Scheduling" connect round-robin time slice '
        "with context switch process state?"
    )

    decision = SourceSemanticEvidenceAtomGateV1().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is False
    assert "relation" in decision.reason


def test_v2_gate_clarifies_competing_canonical_claims_before_generation() -> None:
    first = _chunk(
        "first",
        "Round-robin scheduling rotates runnable processes after a time slice.",
        title="Scheduling",
        cluster="one",
        ordinal=0,
    )
    second = _chunk(
        "second",
        "Priority scheduling chooses the highest-priority runnable process.",
        title="Scheduling",
        cluster="two",
        ordinal=1,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([first, second])
    question = 'How does "Scheduling" explain scheduling runnable process?'

    decision = SourceSemanticEvidenceAtomGateV2().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is False
    assert decision.recommended_action == "clarify"
    assert "ambiguous" in decision.reason


def test_v2_gate_accepts_equivalent_alternate_regions() -> None:
    first = _chunk(
        "first",
        "A queue removes items in first-in, first-out order.",
        title="Queues",
        cluster="one",
        ordinal=0,
    )
    second = _chunk(
        "second",
        "A queue removes items in first-in, first-out order.",
        title="Queues",
        cluster="two",
        ordinal=1,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([first, second])
    question = 'How does "Queues" explain queue removes items order?'

    decision = SourceSemanticEvidenceAtomGateV2().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is True
    assert len(decision.selected_hit_ids) == 1


def test_v3_gate_uses_named_public_title_without_instructional_dilution() -> None:
    protocol = _chunk(
        "protocol",
        (
            "Durable tutoring protocol 251 falls back to the approved grounded "
            "tutoring path after a planning-service failure while preserving the "
            "learner-state checkpoint."
        ),
        title="Durable tutoring protocol 251",
        cluster="protocol-251",
        ordinal=0,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([protocol])
    question = (
        "I am confused about how durable tutoring protocol 251 preserves state "
        "during fallback. Can you give a grounded hint?"
    )

    decision = SourceSemanticEvidenceAtomGateV3().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is True
    assert decision.selected_hit_ids == ["protocol"]
    assert decision.features["public_title_anchor_used"] is True


def test_v3_gate_keeps_distinct_named_claims_fail_closed() -> None:
    first = _chunk(
        "first",
        "Protocol recovery preserves learner state in a checkpoint.",
        title="Protocol recovery",
        cluster="one",
        ordinal=0,
    )
    second = _chunk(
        "second",
        "Protocol recovery discards learner state and starts again.",
        title="Protocol recovery",
        cluster="two",
        ordinal=1,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([first, second])
    question = "I am confused about Protocol recovery. Can you give a hint?"

    decision = SourceSemanticEvidenceAtomGateV3().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is False
    assert decision.recommended_action == "clarify"
    assert "ambiguous" in decision.reason


def test_v3_gate_rejects_generic_instruction_without_source_anchor() -> None:
    protocol = _chunk(
        "protocol",
        "Protocol recovery preserves learner state in a checkpoint.",
        title="Protocol recovery",
        cluster="one",
        ordinal=0,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([protocol])
    question = "I am confused. Can you give me a hint?"

    decision = SourceSemanticEvidenceAtomGateV3().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is False
    assert decision.recommended_action == "abstain"


def test_v3_gate_allows_one_canonical_region_to_support_two_targets() -> None:
    protocol = _chunk(
        "protocol",
        (
            "Protocol recovery uses an approved fallback and preserves learner "
            "progress in a checkpoint."
        ),
        title="Protocol recovery",
        cluster="one",
        ordinal=0,
    )
    retriever = SourceSemanticEvidenceAtomRetrieverV1([protocol])
    question = (
        "Could you connect Protocol recovery's approved fallback with its saved "
        "learner progress?"
    )

    decision = SourceSemanticEvidenceAtomGateV3().assess(
        question, retriever.retrieve(question, limit=5)
    )

    assert decision.sufficient is True
    assert decision.selected_hit_ids == ["protocol"]
    assert decision.features["single_region_multi_target"] is True


def test_ambiguity_gate_ignores_page_fallback_when_precise_region_exists() -> None:
    precise = _chunk(
        "precise",
        "CSRF abuses an authenticated browser session.",
        title="CSRF",
        cluster="csrf",
        ordinal=0,
    ).model_copy(
        update={"page_start": 1, "page_end": 1, "region_kind": "text"}
    )
    aggregate = _chunk(
        "aggregate",
        (
            "Synthetic network security notes. CSRF abuses an authenticated "
            "browser session. Figure 1: request flow."
        ),
        title="CSRF",
        cluster="csrf",
        ordinal=1,
    )
    aggregate = aggregate.model_copy(
        update={
            "page_start": 1,
            "page_end": 1,
            "region_kind": "page",
            "metadata": {**aggregate.metadata, "fallback": "selected-text"},
        }
    )
    hits = [
        RetrievalHit(chunk=precise, relevance_score=1.0),
        RetrievalHit(chunk=aggregate, relevance_score=0.9),
    ]
    gate = AmbiguitySafeEvidenceGateV1(
        StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2,
            evidence_limit=3,
        )
    )

    decision = gate.assess(
        "How does CSRF abuse an authenticated browser session?",
        hits,
    )

    assert decision.sufficient is True
    assert decision.selected_hit_ids == ["precise"]


def test_ambiguity_gate_removes_fallback_before_applying_evidence_limit() -> None:
    aggregate = _chunk(
        "aggregate",
        "CSRF abuses an authenticated browser session. Page footer.",
        title="CSRF",
        cluster="csrf",
        ordinal=0,
    ).model_copy(
        update={
            "page_start": 1,
            "page_end": 1,
            "region_kind": "page",
            "metadata": {"fallback": "selected-text"},
        }
    )
    unrelated = _chunk(
        "unrelated",
        "Same-site cookies affect cross-site requests.",
        title="Cookies",
        cluster="cookies",
        ordinal=1,
    )
    precise = _chunk(
        "precise",
        "CSRF abuses an authenticated browser session.",
        title="CSRF",
        cluster="csrf",
        ordinal=2,
    ).model_copy(
        update={"page_start": 1, "page_end": 1, "region_kind": "text"}
    )
    gate = AmbiguitySafeEvidenceGateV1(
        StructuredLexicalCoverageEvidenceGate(
            minimum_content_matching_terms=2,
            evidence_limit=2,
        ),
        evidence_limit=2,
    )

    decision = gate.assess(
        "How does CSRF abuse an authenticated browser session?",
        [
            RetrievalHit(chunk=aggregate, relevance_score=1.0),
            RetrievalHit(chunk=unrelated, relevance_score=0.9),
            RetrievalHit(chunk=precise, relevance_score=0.8),
        ],
    )

    assert decision.sufficient is True
    assert decision.selected_hit_ids == ["precise"]


def test_page_fallback_is_retained_for_unrelated_region_on_same_page() -> None:
    aggregate = _chunk(
        "aggregate",
        "CSRF abuses an authenticated browser session.",
        title="CSRF",
        cluster="csrf",
        ordinal=0,
    ).model_copy(
        update={
            "page_start": 1,
            "page_end": 1,
            "region_kind": "page",
            "metadata": {"fallback": "selected-text"},
        }
    )
    unrelated = _chunk(
        "unrelated",
        "A completely different region on the same page.",
        title="Other",
        cluster="other",
        ordinal=1,
    ).model_copy(
        update={"page_start": 1, "page_end": 1, "region_kind": "text"}
    )

    preferred = prefer_specific_source_regions([aggregate, unrelated])

    assert [row.id for row in preferred] == ["aggregate", "unrelated"]
