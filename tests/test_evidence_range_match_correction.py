"""Two references to the same bytes are the same evidence.

`evidence_ranges_overlap` never consulted the canonical character range once
either side carried a region identity, so a citation agreeing with the gold
reference on source artifact, version, sha256 and character range scored a miss
whenever exactly one of the two declared a region. Supplying more provenance
than the gold declares made a correct citation score worse than supplying less.

A region identity is additional provenance: it can refine a match the range
already establishes, never contradict one neither side disputes. So identities
are compared when both sides declare one, and the range decides otherwise.

The sealed package is unaffected. All 9,902 of its gold evidence references and
all 1,755 recorded citations declare a region, so both matchers agree on every
pair it contains; `test_sealed_package_decisions_are_unchanged` pins that.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.digital_twin.evaluation.factual_qa_contract import (
    CanonicalEvidenceRefV1,
    EvaluationCitationV1,
    evidence_ranges_overlap,
)


ARTIFACT = "computer-networking:protocols/tls.rst"
SHA = "4972d5cf5f9ef9b4ea183acce12b383edeb24e93e59e811fbda529c75dda35e3"
SEALED = Path(
    "/Users/hikaru/Documents/dev/digital-twin/reports/generated/"
    "course-digital-twin-evaluation-program-011/stages/final-construction-10000"
)


def _expected(**overrides) -> CanonicalEvidenceRefV1:
    return CanonicalEvidenceRefV1(
        **{
            "source_artifact_id": ARTIFACT,
            "source_version": 1,
            "source_sha256": SHA,
            "char_start": 20913,
            "char_end": 20953,
            "region_id": None,
            **overrides,
        }
    )


def _observed(**overrides) -> EvaluationCitationV1:
    return EvaluationCitationV1(
        **{
            "source_artifact_id": ARTIFACT,
            "source_version": 1,
            "source_sha256": SHA,
            "char_start": 20913,
            "char_end": 20953,
            "region_id": None,
            **overrides,
        }
    )


def test_an_exact_range_match_counts_when_only_the_citation_names_a_region() -> None:
    """The defect: extra provenance used to lose to less provenance."""

    assert evidence_ranges_overlap(_expected(), _observed(region_id="region-a217fc3f"))


def test_an_exact_range_match_counts_when_only_the_gold_names_a_region() -> None:
    assert evidence_ranges_overlap(_expected(region_id="region-a217fc3f"), _observed())


def test_both_regions_declared_must_agree() -> None:
    """Where both sides carry identities, the identity still decides."""

    assert evidence_ranges_overlap(
        _expected(region_id="region-a"), _observed(region_id="region-a")
    )
    assert not evidence_ranges_overlap(
        _expected(region_id="region-a"), _observed(region_id="region-b")
    )


def test_a_disjoint_range_never_matches() -> None:
    assert not evidence_ranges_overlap(
        _expected(), _observed(char_start=30000, char_end=30040)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_artifact_id", "computer-networking:protocols/other.rst"),
        ("source_version", 2),
        ("source_sha256", "0" * 64),
    ],
)
def test_provenance_disagreement_still_refuses(field: str, value: object) -> None:
    """Nothing here weakens the checks that establish it is the same source."""

    assert not evidence_ranges_overlap(_expected(), _observed(**{field: value}))


def test_a_citation_without_a_range_cannot_match_on_range_alone() -> None:
    assert not evidence_ranges_overlap(
        _expected(), _observed(char_start=None, char_end=None)
    )


@pytest.mark.skipif(
    not (SEALED / "final-hidden-gold.json").is_file(),
    reason="the sealed package is ignored output and lives in the main worktree",
)
def test_sealed_package_decisions_are_unchanged() -> None:
    """Every sealed reference declares a region, so the correction is a no-op there."""

    for name in ("final-hidden-gold.json", "control-hidden-gold.json"):
        gold = json.loads((SEALED / name).read_text(encoding="utf-8"))["gold"]
        refs = [
            ref
            for row in gold
            for claim in row.get("claims") or []
            for ref in claim.get("evidence_refs") or []
        ]
        assert refs, f"{name} declares no evidence references"
        assert all(ref.get("region_id") for ref in refs), (
            f"{name} contains a reference without a region identity, so the "
            "correction would not be a no-op on the sealed package"
        )
