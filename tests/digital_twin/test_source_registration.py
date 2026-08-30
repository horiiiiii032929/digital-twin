from __future__ import annotations

from src.digital_twin.evaluation.factual_qa_references import _cue
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.retrieval import retrieval_text
from src.digital_twin.grounding.hierarchical_retrieval import requires_clarification
from src.digital_twin.grounding.source_registration import (
    canonical_region_id,
    registered_search_description,
    registered_source_chunks,
    semantic_anchors,
)


def test_registration_preserves_section_and_structured_identifiers() -> None:
    description = registered_search_description(
        course_id="data-structures",
        section_heading="AVL tree rotations",
        source_path="notes/avl_trees.md",
        modality="structured-code",
        text="def rotate_left(node): return node.right",
    )

    assert "Section: AVL tree rotations" in description
    assert "Modality: structured-code" in description
    assert "rotate_left" in description
    assert "node.right" not in description


def test_search_description_is_non_authoritative_retrieval_metadata() -> None:
    chunk = DocumentChunk(
        id="chunk-1",
        document_id="document-1",
        text="The citable source statement.",
        ordinal=0,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={"search_description": "Section: Congestion control"},
    )

    assert chunk.text == "The citable source statement."
    assert retrieval_text(chunk).endswith("Section: Congestion control")


def test_semantic_anchors_drop_deictic_and_generic_tail_tokens() -> None:
    anchors = semantic_anchors(
        ("The rotate_left function returns the promoted AVL subtree root.",)
    )

    assert anchors[:2] == ["rotate_left", "AVL"]
    assert "returns" not in anchors
    assert _cue("The rotate_left function returns the promoted AVL subtree root.") == (
        "rotate_left AVL"
    )


def test_semantic_anchors_are_stable_and_unique() -> None:
    first = semantic_anchors(("TCP TCP congestion_window retransmission timeout",))
    second = semantic_anchors(("TCP TCP congestion_window retransmission timeout",))

    assert first == second
    assert len(first) == len(set(value.casefold() for value in first))


def test_canonical_region_identity_is_source_derived() -> None:
    arguments = {
        "source_artifact_id": "course:path.md",
        "source_version": 1,
        "source_sha256": "a" * 64,
        "char_start": 10,
        "char_end": 25,
        "modality": "structured-code",
    }

    first = canonical_region_id(**arguments)
    second = canonical_region_id(**arguments)

    assert first == second
    assert first.startswith("source-region-")
    assert "case" not in first


def test_registered_chunks_use_exact_spans_and_stable_lineage() -> None:
    cluster = {
        "cluster_id": "cluster-1",
        "source_family_id": "family-1",
        "course_id": "python-programming",
        "source_artifact_id": "python:loops.md",
        "source_version": 1,
        "source_sha256": "b" * 64,
        "source_path": "loops.md",
        "section_heading": "Loop control",
        "char_start": 100,
        "text": "A loop can stop with break.",
        "reference_targets": [
            {
                "modality": "text",
                "evidence_spans": [
                    {
                        "quote": "loop can stop",
                        "relative_char_start": 2,
                        "relative_char_end": 15,
                    }
                ],
            }
        ],
    }

    chunks = registered_source_chunks([cluster])

    assert len(chunks) == 1
    assert chunks[0].text == "loop can stop"
    assert chunks[0].metadata["char_start"] == "102"
    assert chunks[0].metadata["char_end"] == "115"
    assert chunks[0].region_id == chunks[0].id
    assert chunks[0].crop_ref is None


def test_deictic_action_question_clarifies_even_after_named_context() -> None:
    assert requires_clarification(
        'After the discussion of the network process, what does "it" do next?'
    )
