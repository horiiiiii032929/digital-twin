from __future__ import annotations

import hashlib
import json

from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.semantic_evidence_atoms import (
    ATOM_VERSION,
    SourceSemanticEvidenceAtomGateV1,
    SourceSemanticEvidenceAtomGateV2,
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
