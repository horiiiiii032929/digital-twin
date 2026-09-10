"""Conservative source-bound assessment control for explicit explanations.

This baseline recognizes literal supported statements, not arbitrary paraphrase
or deep understanding. It abstains on negation/uncertain language instead of
marking a keyword-rich contradiction correct. Provider assessment can be compared
separately; no student-facing answer is authored by this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from src.digital_twin.student.autonomy_models import AssessmentOutcome, CourseDomainModelV1
from src.digital_twin.student.models import DigitalTwinRelease


@dataclass(frozen=True)
class SourceAssessment:
    outcome: AssessmentOutcome
    confidence: float
    evidence_keys: tuple[str, ...]
    reason: str


def normalize(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))


def permitted_current_chunks(release: DigitalTwinRelease):
    active_versions = {}
    for chunk in release.chunks:
        active_versions[chunk.source_artifact_id] = max(
            chunk.source_version, active_versions.get(chunk.source_artifact_id, 0))
    return [chunk for chunk in release.chunks if chunk.retrieval_allowed
        and chunk.source_version == active_versions[chunk.source_artifact_id]]


def assess_source_bound_attempt(message: str, concepts: list[str], domain: CourseDomainModelV1,
    release: DigitalTwinRelease) -> SourceAssessment:
    unknown = lambda reason: SourceAssessment(AssessmentOutcome.NOT_ASSESSED, 0, (), reason)
    if len(concepts) != 1 or (domain.course_id, domain.release_id) != (release.course_id, release.id):
        return unknown("assessment-scope-ambiguous")
    matches = [concept for concept in domain.concepts if concept.concept_id == concepts[0]]
    if len(matches) != 1:
        return unknown("assessment-concept-missing")
    concept = matches[0]
    chunks = []
    approved_texts = []
    for chunk in permitted_current_chunks(release):
        for source in concept.canonical_ranges:
            if (chunk.source_artifact_id, chunk.source_version, chunk.source_checksum or chunk.content_hash, chunk.locator) == (
                source.source_artifact_id, source.source_version, source.source_sha256, source.locator):
                # Text assessment requires a bounded textual range; a figure
                # locator alone cannot establish literal support.
                if source.char_start is None or source.char_end is None:
                    continue
                if source.char_end > len(chunk.text):
                    continue
                chunks.append(chunk)
                approved_texts.append(chunk.text[source.char_start:source.char_end])
    if not chunks:
        return unknown("assessment-source-unavailable")
    keys = tuple(dict.fromkeys(":".join((chunk.source_artifact_id or chunk.document_id,
        str(chunk.source_version), chunk.source_checksum or chunk.content_hash, chunk.locator)) for chunk in chunks))[:16]
    # No lexical shortcut may mark a negation or uncertain claim correct.
    if re.search(r"\b(?:not|never|cannot|can't|isn't|doesn't|don't|maybe|unsure)\b", message, re.I) or "?" in message:
        return unknown("assessment-needs-semantic-review")
    submitted = " " + normalize(message) + " "
    required = [normalize(part) for part in re.split(r"[;.!?]+", concept.description) if len(normalize(part).split()) >= 4]
    corpus = [" " + normalize(text) + " " for text in approved_texts]
    # The professor's description is a target only when its statements also occur
    # in the approved source. A configured description cannot invent its own gold.
    if not required or any(not any(" " + part + " " in text for text in corpus) for part in required):
        return unknown("assessment-target-not-literally-supported")
    covered = sum(" " + part + " " in submitted for part in required)
    # Matching a correct clause is insufficient when the student also appends
    # an unsupported claim. Only literal targets and a tiny explicit framing
    # vocabulary belong to this baseline; semantic alternatives must abstain.
    residue = submitted
    for part in sorted(required, key=len, reverse=True):
        residue = residue.replace(" " + part + " ", " ")
    residue = re.sub(r"^\s*i (?:think|believe)\s+", " ", residue)
    residue_tokens = set(residue.split()) - {"and", "because"}
    if covered and residue_tokens:
        return unknown("assessment-additional-content-needs-semantic-review")
    if covered == len(required):
        return SourceAssessment(AssessmentOutcome.CORRECT, .8, keys, "all-literal-source-statements-present")
    if covered:
        return SourceAssessment(AssessmentOutcome.PARTIAL, .6, keys, "some-literal-source-statements-present")
    for misconception in domain.misconceptions:
        if misconception.concept_id == concept.concept_id and any(
            " " + normalize(cue) + " " in submitted for cue in misconception.diagnostic_cues):
            return SourceAssessment(AssessmentOutcome.INCORRECT, .7, keys, "approved-misconception-cue")
    return unknown("assessment-paraphrase-or-insufficient-content")
