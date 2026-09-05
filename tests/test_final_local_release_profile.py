from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.digital_twin.evaluation import (
    ComponentKind,
    ComponentProfileEntry,
    load_evaluation_record,
)
from src.digital_twin.grounding import BM25Retriever, build_selected_retriever
from src.digital_twin.grounding.models import DocumentChunk


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / (
    "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json"
)
BINDING = ROOT / (
    "research/05_evaluation/records/"
    "governed-full-autonomy-v2-1-final-release-binding-001.json"
)


def test_final_profile_is_complete_and_explicitly_selects_bm25() -> None:
    profile = load_evaluation_record(BINDING)
    release = json.loads(PROFILE.read_text(encoding="utf-8"))
    components = {row["component"]: row for row in release["components"]}

    assert release["stage"] == "release-candidate"
    assert all(row["status"] != "pending" for row in release["components"])
    assert components["retriever"]["implementation"]["implementation_id"] == (
        "bm25-v1"
    )
    assert components["figure-description"]["status"] == "disabled"
    selected = next(
        row for row in profile.candidates if row.role == "candidate"
    )
    assert selected.implementation.configuration["profile_sha256"] == (
        hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    )


def test_final_profile_constructs_bm25_without_a_silent_fallback() -> None:
    release = load_evaluation_record(BINDING)
    del release
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    selection = ComponentProfileEntry.model_validate(
        next(row for row in profile["components"] if row["component"] == "retriever")
    )
    chunk = DocumentChunk(
        id="chunk-final-profile",
        document_id="source-final-profile",
        ordinal=0,
        text="Token bucket shaping permits bounded bursts.",
    )
    retriever = build_selected_retriever(selection, [chunk], embedder=None)

    assert selection.component == ComponentKind.RETRIEVER
    assert isinstance(retriever, BM25Retriever)
    assert not hasattr(retriever, "fallback_count")
