"""A cluster-format corpus must be usable by the semantic atom line.

The sealed package ships a `chunks` corpus whose regions already carry
`region_id`, `parent_cluster_id`, and `source_family_id`. The development
package ships the older `clusters` format, which carries none of them, so
`materialize_semantic_evidence_atoms` refuses it and the atom gates cannot be
measured on that corpus at all.

The missing fields are all derivable from the cluster record itself: the
cluster span is the region, so the cluster identity is the region identity and
its own relation group. The derivation lives here rather than in the frozen T0
adapter, and it defers to whatever lineage a corpus already supplies.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.academic_factual_qa_open_10000_winner_adapter import (
    load_corpus_with_atom_lineage,
)
from src.digital_twin.grounding.semantic_evidence_atoms import (
    ATOM_VERSION,
    materialize_semantic_evidence_atoms,
)


COURSES = ("computer-networking", "data-structures", "operating-systems", "python-programming")


def _cluster(course_id: str, ordinal: int) -> dict[str, object]:
    text = (
        f"Cluster {ordinal} of {course_id} states that the approved evidence "
        "version is recorded before an interruption."
    )
    return {
        "cluster_id": f"academic-open-devx-{course_id}-{ordinal:04d}",
        "course_id": course_id,
        "source_artifact_id": f"{course_id}:principles/topic.rst",
        "source_path": "principles/topic.rst",
        "source_version": 1,
        "source_sha256": f"{ordinal:064x}",
        "section_heading": f"{course_id.title()} section {ordinal}",
        "char_start": ordinal * 1000,
        "char_end": ordinal * 1000 + len(text),
        "text": text,
        "source_family_id": f"family-{course_id}",
    }


@pytest.fixture()
def cluster_corpus(tmp_path: Path) -> Path:
    path = tmp_path / "clusters.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "clusters": [
                    _cluster(course_id, ordinal)
                    for course_id in COURSES
                    for ordinal in range(1, 4)
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_cluster_regions_carry_atom_lineage(cluster_corpus: Path) -> None:
    grouped, _by_id = load_corpus_with_atom_lineage(cluster_corpus)

    for chunks in grouped.values():
        for chunk in chunks:
            assert chunk.region_id
            assert chunk.metadata["parent_cluster_id"]
            assert chunk.metadata["char_start"]
            assert chunk.metadata["char_end"]


def test_cluster_regions_materialize_into_atoms(cluster_corpus: Path) -> None:
    grouped, _by_id = load_corpus_with_atom_lineage(cluster_corpus)
    chunks = grouped["computer-networking"]

    materialized = materialize_semantic_evidence_atoms(chunks)

    assert len(materialized) == len(chunks)
    for row in materialized:
        assert row.metadata["semantic_atom_version"] == ATOM_VERSION
        assert row.metadata["semantic_atom_claim"]


def test_region_identity_is_stable_across_loads(cluster_corpus: Path) -> None:
    """A corpus must produce the same region identities every time it loads."""

    first, _ = load_corpus_with_atom_lineage(cluster_corpus)
    second, _ = load_corpus_with_atom_lineage(cluster_corpus)

    assert [row.region_id for row in first["data-structures"]] == [
        row.region_id for row in second["data-structures"]
    ]


def test_region_identity_follows_the_cluster(cluster_corpus: Path) -> None:
    """The cluster span is the region, so the cluster names it."""

    grouped, _ = load_corpus_with_atom_lineage(cluster_corpus)
    chunk = grouped["operating-systems"][0]

    assert chunk.id == chunk.metadata["parent_cluster_id"]
    assert chunk.region_id == chunk.id
