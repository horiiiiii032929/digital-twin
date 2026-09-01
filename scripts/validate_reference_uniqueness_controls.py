#!/usr/bin/env python3
"""Validate planted controls for reference uniqueness and source relationships."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.evaluation.factual_qa_execution import canonical_json_sha256
from src.digital_twin.grounding.models import DocumentChunk
from src.digital_twin.grounding.reference_uniqueness import (
    CandidateRelationship,
    ReferenceUniquenessStatus,
    analyze_public_reference_uniqueness,
    classify_candidate_relationship,
)


DEFAULT_INSTRUMENT = ROOT / (
    "research/05_evaluation/instruments/reference_uniqueness_controls_v1.json"
)
EXPECTED_CLASSES = {
    "unique",
    "alternate-valid",
    "partial",
    "conflicting",
    "unrelated",
    "ambiguous",
}


class ReferenceControlV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    control_id: str = Field(min_length=1)
    control_class: Literal[
        "unique",
        "alternate-valid",
        "partial",
        "conflicting",
        "unrelated",
        "ambiguous",
    ]
    question: str | None = None
    source_claims: list[str] = Field(default_factory=list)
    expected_status: ReferenceUniquenessStatus | None = None
    authoritative_claim: str | None = None
    candidate_claim: str | None = None
    expected_relationship: CandidateRelationship | None = None

    @model_validator(mode="after")
    def complete_control(self) -> "ReferenceControlV1":
        uniqueness = self.expected_status is not None
        relationship = self.expected_relationship is not None
        if uniqueness and (not self.question or not self.source_claims):
            raise ValueError("uniqueness control requires question and source claims")
        if relationship and (not self.authoritative_claim or not self.candidate_claim):
            raise ValueError("relationship control requires both claims")
        if not uniqueness and not relationship:
            raise ValueError("control must exercise at least one decision")
        return self


class ReferenceControlInstrumentV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    instrument_id: Literal["reference-uniqueness-controls-v1"]
    status: Literal["frozen-network-free"]
    controls: list[ReferenceControlV1] = Field(min_length=6)
    control_classes: list[str]
    provider_calls: Literal[0]
    hidden_gold_used_by_runtime: Literal[False]
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def complete_matrix(self) -> "ReferenceControlInstrumentV1":
        identifiers = [row.control_id for row in self.controls]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("control IDs must be unique")
        if set(self.control_classes) != EXPECTED_CLASSES:
            raise ValueError("control class declaration is incomplete")
        if {row.control_class for row in self.controls} != EXPECTED_CLASSES:
            raise ValueError("planted control matrix is incomplete")
        return self


def _chunk(control_id: str, ordinal: int, claim: str, question: str) -> DocumentChunk:
    section = "Scheduling" if "Scheduling" in question else "Queues"
    checksum = hashlib.sha256(f"{control_id}:source".encode()).hexdigest()
    start = ordinal * 200
    return DocumentChunk(
        id=f"{control_id}-region-{ordinal}",
        document_id="course:notes.md",
        source_artifact_id="course:notes.md",
        source_version=1,
        source_checksum=checksum,
        source_label="course-approved",
        text=claim,
        locator=f"notes.md:{start}",
        region_id=f"{control_id}-region-{ordinal}",
        ordinal=ordinal,
        retrieval_allowed=True,
        display_allowed=True,
        metadata={
            "course_id": "course",
            "source_path": "notes.md",
            "title": section,
            "modality": "text",
            "char_start": str(start),
            "char_end": str(start + len(claim)),
        },
    )


def validate(path: Path = DEFAULT_INSTRUMENT) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed_hash = canonical_json_sha256(
        {key: value for key, value in payload.items() if key != "content_sha256"}
    )
    if payload.get("content_sha256") != observed_hash:
        raise ValueError("reference uniqueness control hash drifted")
    instrument = ReferenceControlInstrumentV1.model_validate(payload)
    outcomes = []
    for control in instrument.controls:
        outcome: dict[str, Any] = {
            "control_id": control.control_id,
            "control_class": control.control_class,
        }
        if control.expected_status is not None:
            assert control.question is not None
            chunks = [
                _chunk(control.control_id, index, claim, control.question)
                for index, claim in enumerate(control.source_claims)
            ]
            observed = analyze_public_reference_uniqueness(control.question, chunks)
            if observed.status != control.expected_status:
                raise ValueError(
                    f"{control.control_id} expected {control.expected_status}, "
                    f"observed {observed.status}"
                )
            outcome["uniqueness_status"] = observed.status
        if control.expected_relationship is not None:
            assert control.authoritative_claim is not None
            assert control.candidate_claim is not None
            relationship = classify_candidate_relationship(
                control.authoritative_claim,
                control.candidate_claim,
            )
            if relationship != control.expected_relationship:
                raise ValueError(
                    f"{control.control_id} expected {control.expected_relationship}, "
                    f"observed {relationship}"
                )
            outcome["candidate_relationship"] = relationship
        outcomes.append(outcome)
    return {
        "instrument_id": instrument.instrument_id,
        "status": "passed",
        "control_count": len(outcomes),
        "passed_count": len(outcomes),
        "provider_calls": 0,
        "outcomes": outcomes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=DEFAULT_INSTRUMENT)
    arguments = parser.parse_args()
    print(json.dumps(validate(arguments.instrument), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
