"""The confirmation harness must be able to publish a real course corpus.

Confirmations 012 through 024 published exactly one chunk per release, so the
selected evidence gate never had to choose between competing approved sources.
The successor needs that regime, and the earlier confirmations must keep
reproducing byte for byte, so the extra sources are opt-in.
"""

from __future__ import annotations

import inspect

from scripts import governed_full_autonomy_v2_1_actual_product_runtime as runtime
from src.digital_twin.grounding import DocumentChunk
from src.digital_twin.grounding.semantic_evidence_atoms import (
    ATOM_VERSION,
    materialize_semantic_evidence_atoms,
)
from src.digital_twin.tutor_policy import SourceLabel


def _template() -> DocumentChunk:
    text = "placeholder"
    return DocumentChunk(
        id="chunk-template",
        document_id="document-template",
        text=text,
        ordinal=0,
        source_artifact_id="template",
        source_version=1,
        source_label=SourceLabel.COURSE_APPROVED,
        locator="template paragraph 1",
        source_checksum="0" * 64,
        region_id="region-template",
        retrieval_allowed=True,
        display_allowed=True,
        metadata={"course_id": "course-a", "modality": "text"},
    )


def _source(number: int) -> dict[str, str]:
    return {
        "source_id": f"synthetic-persona-confirmation-source-{number:03d}",
        "statement": (
            f"Adaptive review protocol {number:03d} records the approved "
            "evidence and learner-goal version before an interruption."
        ),
        "label": f"Adaptive review protocol {number:03d}",
    }


def test_distractor_sources_are_off_by_default() -> None:
    """Confirmations 012-024 must keep publishing a single-chunk release."""

    parameter = inspect.signature(runtime._install_release).parameters[
        "distractor_resolver"
    ]

    assert parameter.default is None


def test_a_release_chunk_keeps_its_canonical_lineage() -> None:
    chunk = runtime._build_release_chunk(
        _template(),
        _source(517),
        course_id="course-a",
        source_label="Adaptive review protocol 517",
    )

    assert chunk.region_id == "region-synthetic-persona-confirmation-source-517"
    assert chunk.source_checksum == chunk.content_hash
    assert chunk.metadata["char_end"] == str(len(_source(517)["statement"]))
    assert chunk.metadata["title"] == "Adaptive review protocol 517"
    assert chunk.retrieval_allowed is True


def test_many_sources_materialize_into_distinct_citable_atoms() -> None:
    """A multi-source release must stay individually citable after atom work."""

    template = _template()
    chunks = [
        runtime._build_release_chunk(
            template,
            _source(number),
            course_id="course-a",
            source_label=f"Adaptive review protocol {number:03d}",
        )
        for number in (517, 518, 519)
    ]

    materialized = materialize_semantic_evidence_atoms(chunks)

    assert len({row.id for row in materialized}) == 3
    assert len({row.region_id for row in materialized}) == 3
    assert len({row.metadata["semantic_atom_claim"] for row in materialized}) == 3
    for row in materialized:
        assert row.metadata["semantic_atom_version"] == ATOM_VERSION


def test_the_v4_successor_is_a_selectable_grounding_architecture() -> None:
    """The runtime must accept the successor without touching v3's branch."""

    source = inspect.getsource(runtime.build_runtime_factory)

    assert "dominance-scoped-source-semantic-evidence-atoms-v4" in source
    assert "pedagogy-aware-source-semantic-evidence-atoms-v3" in source


def test_v4_is_materialized_like_the_other_atom_architectures() -> None:
    source = inspect.getsource(runtime._install_release)
    marker = source.index("materialize_semantic_evidence_atoms")
    guard = source[:marker]

    assert "dominance-scoped-source-semantic-evidence-atoms-v4" in guard
