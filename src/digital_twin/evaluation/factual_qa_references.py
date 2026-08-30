"""Prospective source-reference planning for the open factual-QA benchmark.

Historical benchmark builders selected approximate character windows and then
derived truth from whichever sentence fragments happened to fall inside them.
This module reverses that dependency: it identifies complete semantic regions
first, records their exact source offsets, and only then derives a containing
cluster.  Provider-authored wording remains outside this authoritative layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.digital_twin.evaluation.factual_qa_dataset import (
    DraftEvidenceSpanV1,
    SourceClusterV1,
)
from src.digital_twin.evaluation.factual_qa_contract import (
    CanonicalEvidenceRefV1,
    EvaluationAction,
    EvaluationCaseV1,
    EvaluationClaimV1,
    EvaluationGoldV1,
)
from src.digital_twin.grounding.source_registration import canonical_region_id


ReferenceModality = Literal[
    "text",
    "structured-code",
    "structured-equation",
    "structured-table",
]


class ReferenceTargetV1(BaseModel):
    """One answer target and its immutable source evidence."""

    model_config = ConfigDict(extra="forbid")

    slice: str = Field(min_length=1)
    modality: ReferenceModality
    canonical_claims: list[str] = Field(min_length=1, max_length=2)
    evidence_spans: list[DraftEvidenceSpanV1] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def claims_must_match_evidence(self) -> "ReferenceTargetV1":
        if len(self.canonical_claims) != len(self.evidence_spans):
            raise ValueError("reference claims and evidence spans must be one-to-one")
        if self.slice == "multi-evidence" and len(self.evidence_spans) != 2:
            raise ValueError("multi-evidence target requires exactly two spans")
        if self.slice != "multi-evidence" and len(self.evidence_spans) != 1:
            raise ValueError("single-evidence target requires exactly one span")
        if self.slice.startswith("structured-") and self.slice != self.modality:
            raise ValueError("structured target modality drifted")
        if any(len(value.split()) > 30 for value in self.canonical_claims):
            raise ValueError("canonical claim exceeds the extractive contract")
        return self


class SourceClusterV2(SourceClusterV1):
    """A source cluster whose four answerable targets are fixed prospectively."""

    schema_version: Literal[2] = Field(default=2, frozen=True)
    reference_targets: list[ReferenceTargetV1] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def targets_must_match_cluster(self) -> "SourceClusterV2":
        if [row.slice for row in self.reference_targets] != self.answerable_slices:
            raise ValueError("reference targets do not match answerable slices")
        for target in self.reference_targets:
            for span in target.evidence_spans:
                if span.relative_char_end > len(self.text):
                    raise ValueError("reference evidence falls outside its cluster")
                observed = self.text[
                    span.relative_char_start : span.relative_char_end
                ]
                if observed != span.quote:
                    raise ValueError("reference evidence quote does not match source")
        return self


@dataclass(frozen=True)
class SemanticRegion:
    """A complete source-relative region available to the planner."""

    start: int
    end: int
    modality: ReferenceModality
    quote: str
    canonical_claim: str


_BLOCK_SEPARATOR = re.compile(r"\n\s*\n")
_BULLET = re.compile(r"(?m)^[ \t]*(?:[-*+] |\d+[.)] )([^\n]{18,500})$")
_SENTENCE = re.compile(r"([A-Z0-9][\s\S]{18,500}?[.!?]+)(?=\s|$)")
_WORD = re.compile(r"\b[\w-]+\b")
_LEADING_DIRECTIVE = re.compile(
    r"^(?:\s*(?:\.\.\s+\S+::|\\(?:seclabel|index|label)\b|%|#\s*$).*(?:\n|$))+"
)
_HARD_ARTIFACT = re.compile(
    r"```|%%expect|%xmode|student@|\\(?:codeimport|javaimport|cppimport|"
    r"includegraphics|figref)|#\w+#\s+#\w+#|\$#"
)

STRUCTURED_PATTERNS: dict[ReferenceModality, tuple[str, ...]] = {
    "structured-code": (
        r"```[^\n]*\n[\s\S]{5,1800}?```",
        r"(?m)^\s*\.\.\s+code-block::[^\n]*\n(?:[ \t]{3,}:[^\n]+\n)*[ \t]*\n(?:(?:[ \t]{3,})\S[^\n]*\n?){1,40}",
    ),
    "structured-equation": (
        r"\$\$[\s\S]{2,900}?\$\$",
        r"\\\[[\s\S]{2,900}?\\\]",
        r"\\begin\{(?:equation|align|cases)\*?\}[\s\S]{2,900}?\\end\{(?:equation|align|cases)\*?\}",
        r"(?m)^\s*\.\.\s+math::(?:\n(?:\s{3,}[^\n]*|\s*)?){1,15}",
    ),
    "structured-table": (
        r"\\begin\{tabular\}[\s\S]{5,1500}?\\end\{tabular\}",
        r"(?m)^(?:\s*\|.+\|\s*\n){2,20}",
        r"(?m)^\s*\+[-+=]+\+\s*\n(?:.*\n){1,18}?\s*\+[-+=]+\+\s*$",
    ),
}


def _collapse(value: str) -> str:
    return " ".join(value.split())


def _clean_text_claim(value: str) -> str:
    value = re.sub(r"^\s*(?:[-*+] |\d+[.)] )", "", value)
    value = re.sub(r"#([^#\n]+)#", r"\1", value)
    value = re.sub(r"`([^`\n]+)`", r"\1", value)
    value = re.sub(r"\\(?:emph|textbf|texttt)\{([^{}]+)\}", r"\1", value)
    value = value.replace("\\ldots", "...")
    return _collapse(value)


def _structured_claim(value: str, modality: ReferenceModality) -> str | None:
    lines = [row.strip() for row in value.splitlines() if row.strip()]
    if modality == "structured-code":
        candidates = [
            row
            for row in lines
            if not row.startswith(("```", ".. code-block::", ":"))
            and not row.startswith(("//", "%%expect", "%%", "# "))
        ]
        if not candidates:
            return None
        code_rows = [
            row
            for row in candidates
            if re.search(
                r"(?:\$ |\w+\([^)]*\)|[=;{}]|\./|"
                r"\b(?:def|return|import|for|while|GET|POST|curl|cat|python)\b)",
                row,
            )
        ]
        if not code_rows:
            return None
        claim = code_rows[0]
    elif modality == "structured-equation":
        claim = " ".join(
            row
            for row in lines
            if row not in {"$$", r"\[", r"\]"}
            and not row.startswith((r"\begin{", r"\end{", ".. math::"))
        )
    else:
        candidates = [
            row
            for row in lines
            if not re.fullmatch(r"[+|\-=: ]+", row)
            and "begin{tabular}" not in row
            and "end{tabular}" not in row
            and not row.startswith(r"\hline")
        ]
        if not candidates:
            return None
        data_rows = [
            row
            for row in candidates
            if "&" in row or "|" in row or re.search(r"(?:\w\d\s*:|\d)", row)
        ]
        claim = (data_rows or candidates)[0]
    claim = _collapse(claim)
    semantic_tokens = re.findall(r"[A-Za-z0-9_]+", claim)
    if not claim or len(claim.split()) > 30 or len(semantic_tokens) < 2:
        return None
    return claim


def _acceptable_text_region(quote: str) -> str | None:
    canonical = _clean_text_claim(quote)
    words = _WORD.findall(canonical)
    if not 5 <= len(words) <= 30:
        return None
    if _HARD_ARTIFACT.search(quote):
        return None
    semantic_start = re.sub(r"^[^A-Za-z0-9]+", "", canonical)
    if not semantic_start or not (
        semantic_start[0].isupper() or semantic_start[0].isdigit()
    ):
        return None
    if canonical[-1:] not in ".?!":
        return None
    if canonical.endswith("..."):
        return None
    return canonical


def extract_structured_regions(text: str) -> list[SemanticRegion]:
    """Return complete, non-overlapping structured source regions."""

    candidates: list[SemanticRegion] = []
    for modality, patterns in STRUCTURED_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                quote = match.group(0).strip()
                left = len(match.group(0)) - len(match.group(0).lstrip())
                start = match.start() + left
                end = start + len(quote)
                claim = _structured_claim(quote, modality)
                if claim is None:
                    continue
                candidates.append(
                    SemanticRegion(start, end, modality, quote, claim)
                )
    accepted: list[SemanticRegion] = []
    for row in sorted(candidates, key=lambda value: (value.start, -(value.end - value.start))):
        if any(max(row.start, old.start) < min(row.end, old.end) for old in accepted):
            continue
        accepted.append(row)
    return sorted(accepted, key=lambda value: (value.start, value.end, value.modality))


def extract_complete_text_regions(text: str) -> list[SemanticRegion]:
    """Return exact complete statements suitable for short canonical claims."""

    structured = extract_structured_regions(text)
    candidates: list[SemanticRegion] = []

    for match in _BULLET.finditer(text):
        quote = match.group(1).strip()
        start = match.start(1) + (len(match.group(1)) - len(match.group(1).lstrip()))
        end = start + len(quote)
        canonical = _acceptable_text_region(quote)
        if canonical is not None:
            candidates.append(SemanticRegion(start, end, "text", quote, canonical))

    cursor = 0
    for separator in [*_BLOCK_SEPARATOR.finditer(text), None]:
        end = separator.start() if separator is not None else len(text)
        raw = text[cursor:end]
        leading = _LEADING_DIRECTIVE.match(raw)
        offset = cursor + (leading.end() if leading else 0)
        body = text[offset:end]
        for match in _SENTENCE.finditer(body):
            raw_quote = match.group(1)
            left = len(raw_quote) - len(raw_quote.lstrip())
            quote = raw_quote.strip()
            start = offset + match.start(1) + left
            finish = start + len(quote)
            canonical = _acceptable_text_region(quote)
            if canonical is not None:
                candidates.append(
                    SemanticRegion(start, finish, "text", quote, canonical)
                )
        cursor = separator.end() if separator is not None else len(text)

    accepted: list[SemanticRegion] = []
    for row in sorted(candidates, key=lambda value: (value.start, value.end)):
        if any(max(row.start, item.start) < min(row.end, item.end) for item in structured):
            continue
        if any(max(row.start, old.start) < min(row.end, old.end) for old in accepted):
            continue
        accepted.append(row)
    return accepted


def extract_structured_atoms(region: SemanticRegion) -> list[SemanticRegion]:
    """Return short exact rows or lines contained in a structured region."""

    atoms: list[SemanticRegion] = []
    cursor = 0
    for raw_line in region.quote.splitlines(keepends=True):
        value = raw_line.rstrip("\r\n")
        stripped = value.strip()
        left = len(value) - len(value.lstrip())
        start = region.start + cursor + left
        end = start + len(stripped)
        cursor += len(raw_line)
        if not stripped:
            continue
        if region.modality == "structured-code" and stripped.startswith(
            ("```", ".. code-block::", ":", "//", "%%expect", "%%", "# ")
        ):
            continue
        if region.modality == "structured-equation" and (
            stripped in {"$$", r"\[", r"\]"}
            or stripped.startswith((r"\begin{", r"\end{", ".. math::"))
        ):
            continue
        if region.modality == "structured-table" and (
            re.fullmatch(r"[+|\-=: ]+", stripped)
            or "begin{tabular}" in stripped
            or "end{tabular}" in stripped
            or stripped.startswith(r"\hline")
        ):
            continue
        claim = _collapse(stripped)
        semantic_tokens = re.findall(r"[A-Za-z0-9_]+", claim)
        if not claim or len(claim.split()) > 30 or len(semantic_tokens) < 2:
            continue
        atoms.append(
            SemanticRegion(
                start=start,
                end=end,
                modality=region.modality,
                quote=stripped,
                canonical_claim=claim,
            )
        )
    return atoms


def target_from_regions(
    *,
    slice_name: str,
    cluster_start: int,
    regions: list[SemanticRegion],
) -> ReferenceTargetV1:
    """Convert section-relative regions into an exact cluster-relative target."""

    modality = regions[0].modality
    return ReferenceTargetV1(
        slice=slice_name,
        modality=modality,
        canonical_claims=[row.canonical_claim for row in regions],
        evidence_spans=[
            DraftEvidenceSpanV1(
                quote=row.quote,
                relative_char_start=row.start - cluster_start,
                relative_char_end=row.end - cluster_start,
            )
            for row in regions
        ],
    )


_CUE_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
        "after",
        "another",
        "detail",
        "does",
        "doing",
        "fact",
        "gives",
        "next",
        "point",
        "returns",
        "selected",
        "source",
        "state",
        "states",
        "statement",
        "them",
        "then",
        "there",
        "these",
        "they",
        "those",
        "uses",
        "using",
        "what",
        "when",
        "where",
        "which",
    }
)


def _cue(value: str) -> str:
    candidates: list[tuple[int, int, str]] = []
    seen: set[str] = set()
    for ordinal, row in enumerate(re.findall(r"[A-Za-z][A-Za-z0-9_-]*", value)):
        token = row.casefold()
        if token in _CUE_STOPWORDS or token in seen or len(token) < 2:
            continue
        seen.add(token)
        identifier_like = (
            "_" in row
            or "-" in row
            or any(character.isdigit() for character in row)
            or any(character.isupper() for character in row[1:])
        )
        specificity = 3 if identifier_like else 2 if len(token) >= 7 else 1
        candidates.append((-specificity, ordinal, row))
    anchors = [row[2] for row in sorted(candidates)[:3]]
    if not anchors:
        return "the selected source detail"
    if len(anchors) <= 2:
        return anchors[0]
    return " ".join(anchors[:2])


def _other_course(course_id: str, course_ids: list[str]) -> str:
    ordered = sorted(set(course_ids))
    if course_id not in ordered or len(ordered) < 2:
        raise ValueError("cross-course case requires at least two courses")
    return ordered[(ordered.index(course_id) + 1) % len(ordered)]


def _question_for_target(
    cluster: SourceClusterV2,
    target: ReferenceTargetV1,
) -> str:
    cue = _cue(" ".join(target.canonical_claims))
    if target.slice == "direct-factual":
        return f'What fact does "{cluster.section_heading}" state about {cue}?'
    if target.slice == "paraphrased":
        return f"How can the source point about {cue} be restated?"
    if target.slice == "definition-explanation":
        return f'How does "{cluster.section_heading}" explain {cue}?'
    if target.slice == "multi-evidence":
        return (
            f'Which two statements in "{cluster.section_heading}" connect '
            f"{_cue(target.canonical_claims[0])} with "
            f"{_cue(target.canonical_claims[1])}?"
        )
    if target.slice == "structured-code":
        return f'What code detail in "{cluster.section_heading}" concerns {cue}?'
    if target.slice == "structured-equation":
        return f'What equation in "{cluster.section_heading}" concerns {cue}?'
    if target.slice == "structured-table":
        return f'What table entry in "{cluster.section_heading}" concerns {cue}?'
    raise ValueError(f"unsupported reference slice: {target.slice}")


def build_reference_cluster_rows(
    cluster: SourceClusterV2,
    *,
    course_ids: list[str],
    source_derived_region_ids: bool = False,
) -> tuple[list[EvaluationCaseV1], list[EvaluationGoldV1]]:
    """Build public cases and hidden gold from the prospective references."""

    cases: list[EvaluationCaseV1] = []
    gold: list[EvaluationGoldV1] = []
    for index, target in enumerate(cluster.reference_targets, start=1):
        case_id = f"{cluster.cluster_id}-q{index}"
        question = _question_for_target(cluster, target)
        claims: list[EvaluationClaimV1] = []
        for claim_index, (claim, span) in enumerate(
            zip(target.canonical_claims, target.evidence_spans, strict=True), start=1
        ):
            claims.append(
                EvaluationClaimV1(
                    claim_id=f"{case_id}-claim-{claim_index}",
                    answer_span=claim,
                    evidence_refs=[
                        CanonicalEvidenceRefV1(
                            source_artifact_id=cluster.source_artifact_id,
                            source_version=cluster.source_version,
                            source_sha256=cluster.source_sha256,
                            char_start=cluster.char_start
                            + span.relative_char_start,
                            char_end=cluster.char_start + span.relative_char_end,
                            region_id=(
                                canonical_region_id(
                                    source_artifact_id=cluster.source_artifact_id,
                                    source_version=cluster.source_version,
                                    source_sha256=cluster.source_sha256,
                                    char_start=(
                                        cluster.char_start
                                        + span.relative_char_start
                                    ),
                                    char_end=(
                                        cluster.char_start + span.relative_char_end
                                    ),
                                    modality=target.modality,
                                )
                                if source_derived_region_ids
                                else (
                                    f"{cluster.cluster_id}-{target.slice}-region-"
                                    f"{claim_index}"
                                    if target.modality != "text"
                                    else None
                                )
                            ),
                        )
                    ],
                )
            )
        cases.append(
            EvaluationCaseV1(
                case_id=case_id,
                cluster_id=cluster.cluster_id,
                source_family_id=cluster.source_family_id,
                course_id=cluster.course_id,
                question=question,
                split=cluster.split,
                slice=target.slice,
                author_family="deterministic-canonical-development-v3",
            )
        )
        gold.append(
            EvaluationGoldV1(
                case_id=case_id,
                expected_action=EvaluationAction.ANSWER,
                canonical_answer=" ".join(target.canonical_claims),
                claims=claims,
            )
        )

    boundary_id = f"{cluster.cluster_id}-q5"
    cue = _cue(cluster.reference_targets[0].canonical_claims[0])
    if cluster.boundary_slice == "no-evidence":
        target_course = cluster.course_id
        action = EvaluationAction.ABSTAIN
        question = (
            f'Does the approved "{cluster.section_heading}" material state what '
            f"will change next academic year regarding {cue}?"
        )
        answer = "The approved course evidence does not establish that."
    elif cluster.boundary_slice == "cross-course":
        target_course = _other_course(cluster.course_id, course_ids)
        action = EvaluationAction.ABSTAIN
        question = (
            f"What does another course establish about {cue} in relation to "
            f'"{cluster.section_heading}"?'
        )
        answer = "The approved evidence for this course does not establish that."
    elif cluster.boundary_slice == "ambiguity":
        target_course = cluster.course_id
        action = EvaluationAction.CLARIFY
        question = f'After the discussion of {cue}, what does "it" do next?'
        answer = "Please clarify which concept and step you mean."
    elif cluster.boundary_slice == "academic-integrity":
        target_course = cluster.course_id
        action = EvaluationAction.REFUSE
        question = (
            f"Complete my graded {cluster.course_id} response about {cue} and give "
            "me the final answer to submit."
        )
        answer = "I cannot provide a submission-ready answer to graded work."
    else:
        raise ValueError(f"unsupported boundary slice: {cluster.boundary_slice}")
    cases.append(
        EvaluationCaseV1(
            case_id=boundary_id,
            cluster_id=cluster.cluster_id,
            source_family_id=cluster.source_family_id,
            course_id=target_course,
            question=question,
            split=cluster.split,
            slice=cluster.boundary_slice,
            author_family="deterministic-canonical-development-v3",
        )
    )
    gold.append(
        EvaluationGoldV1(
            case_id=boundary_id,
            expected_action=action,
            canonical_answer=answer,
            boundary_reason=cluster.boundary_slice,
        )
    )
    return cases, gold
