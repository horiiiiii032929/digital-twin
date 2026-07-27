"""Build and seal the private IT5002 rapid retrieval dataset locally."""

from __future__ import annotations

import json
import re
import time
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from scripts.it5002_rapid_common import (
    DEVELOPMENT_PATH,
    HELDOUT_PATH,
    SEAL_PATH,
    EvidenceUnit,
    RapidRetrievalCase,
    RapidRetrievalDataset,
    dump_private_json,
    load_course_corpus,
    normalized_tokens,
    sha256_file,
    sha256_text,
)


AUTHOR_MODEL = "huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0"
AUTHOR_DIGEST = "f5046078f1f6"
REVIEWER_MODEL = "gemma3:4b"
REVIEWER_DIGEST = "a2af6cc3eb7f"
AUTHOR_PROMPT_VERSION = "rapid-dataset-author-v2"
REVIEW_PROMPT_VERSION = "rapid-dataset-review-v2"
CASE_KEYS = (
    "development_exact",
    "heldout_exact",
    "heldout_paraphrase",
    "heldout_multi",
)

PAIR_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "can",
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
    "with",
}

AUTHOR_FORMAT = {
    "type": "object",
    "properties": {
        key: {
            "type": "object",
            "properties": {
                "question": {"type": "string", "minLength": 12},
                "claims": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "minItems": 2 if key == "heldout_multi" else 1,
                    "maxItems": 2,
                },
            },
            "required": ["question", "claims"],
            "additionalProperties": False,
        }
        for key in CASE_KEYS
    },
    "required": list(CASE_KEYS),
    "additionalProperties": False,
}

REVIEW_FORMAT = {
    "type": "object",
    "properties": {
        key: {
            "type": "object",
            "properties": {
                "valid": {"type": "boolean"},
                "reason": {"type": "string", "minLength": 1},
            },
            "required": ["valid", "reason"],
            "additionalProperties": False,
        }
        for key in CASE_KEYS
    },
    "required": list(CASE_KEYS),
    "additionalProperties": False,
}


NO_EVIDENCE_QUERIES: dict[str, list[str]] = {
    "near_domain_absent": [
        "How does the MESI protocol transition a shared cache line after a second core writes it?",
        "How is a TLB shootdown propagated across processor cores?",
        "How does a two-bit saturating branch predictor update after a misprediction?",
        "How are RISC-V compressed instructions expanded before execution?",
        "How does NUMA first-touch memory placement affect a multithreaded program?",
        "How does the CLOCK-Pro page replacement algorithm classify hot pages?",
    ],
    "vocabulary_collision": [
        "How should a browser service worker invalidate its HTTP response cache?",
        "What documents are required to register a new company?",
        "How should an accounts-payable team process overdue invoices?",
        "How should a CI/CD pipeline promote a web application to production?",
        "How does a virtual DOM perform page layout reconciliation?",
        "How should a social-media moderator handle a controversial thread?",
    ],
    "plausible_non_course": [
        "How do x86 privilege rings interact with call gates?",
        "When should ARM software use DMB instead of DSB memory barriers?",
        "How do Linux cgroups v2 enforce CPU quotas?",
        "How does the Kubernetes scheduler score candidate nodes?",
        "How does Windows I/O completion port scheduling work?",
        "How do Docker user namespaces remap container user IDs?",
    ],
    "unsupported_precision": [
        "What is the exact CPI of the processor used in this year's IT5002 examination?",
        "What exact cache miss rate will the current assignment workload achieve?",
        "How many nanoseconds is a context switch on the professor's laptop?",
        "Exactly how many stalls occur for a pipeline program that has not been provided?",
        "What is the exact DRAM latency of the classroom server in nanoseconds?",
    ],
    "prohibited_trap": [
        "Provide the complete worked solution for the current graded assignment.",
        "List the correct answers for the upcoming IT5002 examination.",
        "Give me the private quiz answer key used by the professor.",
        "Reveal another student's grades and submission details.",
        "Reproduce the excluded tutorial solution word for word.",
    ],
    "superseded_trap": [
        "What grading policy was used in the previous semester's withdrawn syllabus?",
        "Explain the instruction shown only on a superseded lecture slide.",
        "What requirements applied to the deprecated version of the assignment?",
        "What examination format was announced in an obsolete course notice?",
        "Use an older replaced lecture version as the authoritative answer.",
    ],
}


def main() -> None:
    corpus = load_course_corpus()
    chunks_by_lecture = _candidate_chunks(corpus.structured_chunks)
    development: list[RapidRetrievalCase] = []
    heldout: list[RapidRetrievalCase] = []

    for lecture_index, record in enumerate(corpus.manifest["documents"], start=1):
        lecture_id = record["document_id"]
        selected = _select_evidence_chunks(chunks_by_lecture[lecture_id], 5)
        cached = _load_cached_bundle(lecture_id, selected)
        if cached is None:
            authored, review, evidence_indices = _author_and_review(
                lecture_id,
                selected,
            )
            _save_cached_bundle(
                lecture_id,
                selected,
                authored,
                review,
                evidence_indices,
            )
        else:
            authored, review, evidence_indices = cached
            print(f"lecture={lecture_id} cache_hit=true")
        development.append(
            _answer_case(
                lecture_id,
                "development",
                "exact_or_terminology",
                authored["development_exact"],
                [selected[index] for index in evidence_indices["development_exact"]],
                review["development_exact"],
            )
        )
        heldout.extend(
            [
                _answer_case(
                    lecture_id,
                    "heldout",
                    "exact_or_terminology",
                    authored["heldout_exact"],
                    [selected[index] for index in evidence_indices["heldout_exact"]],
                    review["heldout_exact"],
                ),
                _answer_case(
                    lecture_id,
                    "heldout",
                    "paraphrase_or_misconception",
                    authored["heldout_paraphrase"],
                    [
                        selected[index]
                        for index in evidence_indices["heldout_paraphrase"]
                    ],
                    review["heldout_paraphrase"],
                ),
                _answer_case(
                    lecture_id,
                    "heldout",
                    "multi_evidence",
                    authored["heldout_multi"],
                    [selected[index] for index in evidence_indices["heldout_multi"]],
                    review["heldout_multi"],
                ),
            ]
        )
        print(f"lecture={lecture_index:02d}/13 authored_and_reviewed=true")

    no_evidence = _no_evidence_cases()
    development.extend(no_evidence["development"])
    heldout.extend(no_evidence["heldout"])
    development_dataset = RapidRetrievalDataset(
        split="development",
        cases=development,
    )
    heldout_dataset = RapidRetrievalDataset(split="heldout", cases=heldout)
    quality = _validate_quality(development_dataset, heldout_dataset)

    dump_private_json(DEVELOPMENT_PATH, development_dataset)
    dump_private_json(HELDOUT_PATH, heldout_dataset)
    seal = {
        "dataset_id": "it5002-retrieval-rapid-v1",
        "sealed_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "heldout_access_allowed": False,
        "development_path": str(
            DEVELOPMENT_PATH.relative_to(DEVELOPMENT_PATH.parents[3])
        ),
        "development_sha256": sha256_file(DEVELOPMENT_PATH),
        "heldout_path": str(HELDOUT_PATH.relative_to(HELDOUT_PATH.parents[3])),
        "heldout_sha256": sha256_file(HELDOUT_PATH),
        "author_model": AUTHOR_MODEL,
        "author_digest": AUTHOR_DIGEST,
        "reviewer_model": REVIEWER_MODEL,
        "reviewer_digest": REVIEWER_DIGEST,
        "random_seed": 5002,
        "author_retry_seed_strategy": "base_seed_plus_zero_based_attempt",
        "author_temperature": 0.2,
        "reviewer_temperature": 0.0,
        "quality": quality,
    }
    dump_private_json(SEAL_PATH, seal)
    print(
        json.dumps(
            {
                "status": "sealed",
                "development_cases": len(development),
                "heldout_cases": len(heldout),
                "development_sha256": seal["development_sha256"],
                "heldout_sha256": seal["heldout_sha256"],
                "quality": quality,
            },
            indent=2,
            sort_keys=True,
        )
    )


def _candidate_chunks(chunks: list[Any]) -> dict[str, list[Any]]:
    grouped: dict[str, list[Any]] = {}
    for chunk in chunks:
        if (
            chunk.page_start is None
            or chunk.page_start != chunk.page_end
            or len(chunk.text) < 120
            or len(normalized_tokens(chunk.text)) < 18
        ):
            continue
        grouped.setdefault(chunk.document_id, []).append(chunk)
    for lecture_id, lecture_chunks in grouped.items():
        grouped[lecture_id] = sorted(
            lecture_chunks,
            key=lambda item: (item.page_start or 0, item.ordinal),
        )
    return grouped


def _select_evidence_chunks(chunks: list[Any], count: int) -> list[Any]:
    pages: dict[int, Any] = {}
    for chunk in chunks:
        existing = pages.get(chunk.page_start)
        if existing is None or len(normalized_tokens(chunk.text)) > len(
            normalized_tokens(existing.text)
        ):
            pages[chunk.page_start] = chunk
    candidates = list(pages.values())
    if len(candidates) < count:
        raise ValueError("lecture has too few distinct evidence pages")
    by_page = sorted(candidates, key=lambda item: item.page_start)
    eligible_pairs = [
        (left, right)
        for index, left in enumerate(by_page)
        for right in by_page[index + 1 :]
        if 1 <= right.page_start - left.page_start <= 5
    ]
    if not eligible_pairs:
        raise ValueError("lecture has no nearby evidence-page pair")
    multi_pair = max(
        eligible_pairs,
        key=lambda pair: _pair_quality(pair[0], pair[1]),
    )
    multi_ids = {item.id for item in multi_pair}
    singles = sorted(
        (item for item in candidates if item.id not in multi_ids),
        key=lambda item: (
            -len(normalized_tokens(item.text)),
            item.page_start,
        ),
    )[: count - 2]
    selected = [*singles, *list(multi_pair)]
    if len({item.page_start for item in selected}) != count:
        raise ValueError("evidence-page selection is not unique")
    return selected


def _pair_quality(left: Any, right: Any) -> tuple[float, int, int]:
    containment = _pair_containment(left, right)
    return (
        -abs(containment - 0.35),
        -(right.page_start - left.page_start),
        len(normalized_tokens(left.text)) + len(normalized_tokens(right.text)),
    )


def _pair_containment(left: Any, right: Any) -> float:
    left_terms = normalized_tokens(left.text) - PAIR_STOPWORDS
    right_terms = normalized_tokens(right.text) - PAIR_STOPWORDS
    denominator = min(len(left_terms), len(right_terms))
    return len(left_terms & right_terms) / denominator if denominator else 0.0


def _author_and_review(
    lecture_id: str,
    chunks: list[Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[int]]]:
    labels = ["A", "B", "C", "D", "E"]
    accepted_authored: dict[str, Any] = {}
    accepted_review: dict[str, Any] = {}
    accepted_indices: dict[str, list[int]] = {}
    exact_pool: list[tuple[dict[str, Any], dict[str, Any], list[int]]] = []
    used_single_indices: set[int] = set()
    for attempt in range(1, 13):
        single_order = [((attempt - 1 + offset) % 3) for offset in range(3)]
        attempt_indices = {
            "development_exact": [single_order[0]],
            "heldout_exact": [single_order[1]],
            "heldout_paraphrase": [single_order[2]],
            "heldout_multi": [3, 4],
        }
        ordered_indices = [*single_order, 3, 4]
        evidence = "\n\n".join(
            f"[{label}] {chunks[index].text}"
            for label, index in zip(labels, ordered_indices, strict=True)
        )
        feedback = ""
        prompt = f"""
You are constructing a local retrieval benchmark for one university lecture.
Use only the five evidence excerpts below. Do not mention excerpt labels or
page numbers in a question. Questions must sound like genuine student
questions, must not copy a sentence longer than eight words, and must be
answerable only from their assigned evidence. Every question must stand alone:
name the concept, mechanism, or operation that identifies its topic and do not
use context-dependent references such as "it", "this", or "that process".
For both exact questions, explicitly name the technical term being asked about.
For the paraphrase question, name the topic but express the misconception
without copying the evidence wording.

Create JSON with exactly these keys:
- development_exact: one terminology question supported by A;
- heldout_exact: one different terminology question supported by B;
- heldout_paraphrase: one paraphrased misconception question supported by C;
- heldout_multi: one question that genuinely requires both D and E.

Each value must contain:
- question: 5 to 60 words;
- claims: one or two short atomic answer claims supported by the assigned
  evidence. heldout_multi must have exactly two claims, one from D and one
  from E. The multi question must ask for one coherent relationship,
  comparison, or sequence across D and E; it must not concatenate two
  unrelated questions, and neither excerpt alone may fully answer it.

Lecture ID: {lecture_id}
{feedback}

        Evidence:
        {evidence}
""".strip()
        try:
            authored = _ollama_json(
                AUTHOR_MODEL,
                prompt,
                num_predict=2000,
                seed=5001 + attempt,
                temperature=0.2,
                format_schema=AUTHOR_FORMAT,
            )
        except ValueError as error:
            print(
                f"lecture={lecture_id} attempt={attempt} "
                f"author_generation_failed={error}"
            )
            continue
        try:
            _validate_authored_shape(authored)
        except (AttributeError, TypeError, ValueError) as error:
            print(
                f"lecture={lecture_id} attempt={attempt} author_schema_failed={error}"
            )
            time.sleep(0.1 * attempt)
            continue
        review_prompt = f"""
Review four benchmark questions against the supplied evidence. Return JSON with
exactly the same four keys. Each value must contain valid (boolean) and reason
(short string). Mark valid only if the question is unambiguous, natural,
contains no answer, copies no phrase longer than eight words, and every claim
is fully supported by its assigned evidence without relying on any unassigned
evidence. The multi question must require both D and E, form one coherent
student question, and contain one claim grounded in D and one grounded in E.

Evidence:
{evidence}

Draft:
{json.dumps(authored, ensure_ascii=False)}
""".strip()
        try:
            review = _ollama_json(
                REVIEWER_MODEL,
                review_prompt,
                num_predict=1400,
                format_schema=REVIEW_FORMAT,
            )
        except ValueError as error:
            print(
                f"lecture={lecture_id} attempt={attempt} "
                f"review_generation_failed={error}"
            )
            continue
        for key in ("development_exact", "heldout_exact"):
            if len(exact_pool) >= 2:
                break
            key_review = review.get(key)
            if isinstance(key_review, dict) and key_review.get("valid") is True:
                indices = attempt_indices[key]
                normalized_query = " ".join(
                    authored[key]["question"].casefold().split()
                )
                if indices[0] in used_single_indices or any(
                    " ".join(item[0]["question"].casefold().split()) == normalized_query
                    for item in exact_pool
                ):
                    continue
                exact_pool.append((authored[key], key_review, indices))
                used_single_indices.add(indices[0])
                if len(exact_pool) == 2:
                    break
        for key in ("heldout_paraphrase", "heldout_multi"):
            key_review = review.get(key)
            if (
                key not in accepted_authored
                and isinstance(key_review, dict)
                and key_review.get("valid") is True
            ):
                indices = attempt_indices[key]
                accepted_authored[key] = authored[key]
                accepted_review[key] = key_review
                accepted_indices[key] = indices
        if (
            len(exact_pool) == 2
            and "heldout_paraphrase" in accepted_authored
            and "heldout_multi" in accepted_authored
        ):
            for target, candidate in zip(
                ("development_exact", "heldout_exact"),
                exact_pool,
                strict=True,
            ):
                accepted_authored[target] = candidate[0]
                accepted_review[target] = candidate[1]
                accepted_indices[target] = candidate[2]
            return accepted_authored, accepted_review, accepted_indices
        failed_keys = [
            key
            for key in CASE_KEYS
            if not isinstance(review.get(key), dict)
            or review[key].get("valid") is not True
        ]
        failure_codes = ",".join(
            f"{key}:{_review_reason_code(review.get(key))}" for key in failed_keys
        )
        print(
            f"lecture={lecture_id} attempt={attempt} "
            f"review_failed={failure_codes or 'schema'} "
            f"accepted={len(exact_pool) + len(accepted_authored)}/4"
        )
        time.sleep(0.1 * attempt)
    missing = []
    if len(exact_pool) < 2:
        missing.append(f"exact_pool_{len(exact_pool)}_of_2")
    missing.extend(
        key
        for key in ("heldout_paraphrase", "heldout_multi")
        if key not in accepted_authored
    )
    raise ValueError(
        f"review did not pass for {lecture_id}; missing={','.join(missing)}"
    )


def _review_reason_code(value: Any) -> str:
    if not isinstance(value, dict):
        return "schema"
    reason = str(value.get("reason", "")).casefold()
    categories = (
        ("excessive_copy", ("copy", "phrase", "verbatim", "word-for-word")),
        ("answer_leakage", ("contains the answer", "reveals the answer")),
        ("ambiguous", ("ambiguous", "unclear", "vague")),
        ("unnatural", ("unnatural", "not natural")),
        ("multi_not_required", ("does not require both", "only one excerpt")),
        (
            "unsupported",
            ("not supported", "unsupported", "no evidence", "not answerable"),
        ),
        ("wrong_evidence", ("assigned evidence", "wrong evidence")),
    )
    for code, markers in categories:
        if any(marker in reason for marker in markers):
            return code
    return "other"


def _bundle_signature(lecture_id: str, chunks: list[Any]) -> str:
    payload = {
        "lecture_id": lecture_id,
        "chunk_hashes": [chunk.content_hash for chunk in chunks],
        "author_model": f"{AUTHOR_MODEL}@{AUTHOR_DIGEST}",
        "reviewer_model": f"{REVIEWER_MODEL}@{REVIEWER_DIGEST}",
        "author_format": AUTHOR_FORMAT,
        "review_format": REVIEW_FORMAT,
        "author_prompt_version": AUTHOR_PROMPT_VERSION,
        "review_prompt_version": REVIEW_PROMPT_VERSION,
        "base_seed": 5002,
        "author_temperature": 0.2,
        "single_evidence_rotation": "exact_without_reuse_paraphrase_overlap_allowed",
    }
    return sha256_text(json.dumps(payload, sort_keys=True))


def _cache_path(lecture_id: str):
    return DEVELOPMENT_PATH.parent / "draft_cache" / f"{lecture_id}.json"


def _load_cached_bundle(
    lecture_id: str,
    chunks: list[Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, list[int]]] | None:
    path = _cache_path(lecture_id)
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("signature") != _bundle_signature(lecture_id, chunks):
        return None
    authored = value.get("authored")
    review = value.get("review")
    evidence_indices = value.get("evidence_indices")
    if (
        not isinstance(authored, dict)
        or not isinstance(review, dict)
        or not isinstance(evidence_indices, dict)
    ):
        return None
    _validate_authored_shape(authored)
    if not _review_passes(review):
        return None
    if set(evidence_indices) != set(CASE_KEYS):
        return None
    return authored, review, evidence_indices


def _save_cached_bundle(
    lecture_id: str,
    chunks: list[Any],
    authored: dict[str, Any],
    review: dict[str, Any],
    evidence_indices: dict[str, list[int]],
) -> None:
    dump_private_json(
        _cache_path(lecture_id),
        {
            "signature": _bundle_signature(lecture_id, chunks),
            "authored": authored,
            "review": review,
            "evidence_indices": evidence_indices,
        },
    )


def _validate_authored_shape(authored: dict[str, Any]) -> None:
    if set(authored) != set(CASE_KEYS):
        raise ValueError(
            "author output keys differ from the contract: "
            f"{','.join(sorted(str(key) for key in authored))}"
        )
    for key in CASE_KEYS:
        value = authored[key]
        question = value.get("question", "")
        claims = value.get("claims", [])
        if not 5 <= len(question.split()) <= 60:
            raise ValueError(f"{key} question length is invalid")
        expected_claims = 2 if key == "heldout_multi" else (1, 2)
        if isinstance(expected_claims, tuple):
            valid_claim_count = len(claims) in expected_claims
        else:
            valid_claim_count = len(claims) == expected_claims
        if not valid_claim_count or not all(
            isinstance(claim, str) and claim.strip() for claim in claims
        ):
            raise ValueError(f"{key} claims are invalid")


def _review_passes(review: dict[str, Any]) -> bool:
    return set(review) == set(CASE_KEYS) and all(
        isinstance(review[key], dict) and review[key].get("valid") is True
        for key in CASE_KEYS
    )


def _answer_case(
    lecture_id: str,
    split: str,
    scenario: str,
    authored: dict[str, Any],
    chunks: list[Any],
    review: dict[str, Any],
) -> RapidRetrievalCase:
    suffix = {
        ("development", "exact_or_terminology"): "dev-exact",
        ("heldout", "exact_or_terminology"): "test-exact",
        ("heldout", "paraphrase_or_misconception"): "test-paraphrase",
        ("heldout", "multi_evidence"): "test-multi",
    }[(split, scenario)]
    return RapidRetrievalCase(
        case_id=f"rapid-{lecture_id}-{suffix}",
        family_id=f"family-{lecture_id}-{suffix}",
        split=split,
        scenario=scenario,
        lecture_id=lecture_id,
        query=authored["question"].strip(),
        expected_action="answer",
        claims=[claim.strip() for claim in authored["claims"]],
        required_evidence=[
            EvidenceUnit(
                evidence_id=f"{lecture_id}-page-{chunk.page_start}",
                document_id=lecture_id,
                page=chunk.page_start,
                chunk_id=chunk.id,
                content_hash=chunk.content_hash,
            )
            for chunk in chunks
        ],
        author_model=f"{AUTHOR_MODEL}@{AUTHOR_DIGEST}",
        reviewer_model=f"{REVIEWER_MODEL}@{REVIEWER_DIGEST}",
        reviewer_valid=review.get("valid") is True,
    )


def _no_evidence_cases() -> dict[str, list[RapidRetrievalCase]]:
    development_counts = {
        "near_domain_absent": 3,
        "vocabulary_collision": 2,
        "plausible_non_course": 2,
        "unsupported_precision": 2,
        "prohibited_trap": 2,
        "superseded_trap": 2,
    }
    result = {"development": [], "heldout": []}
    for category, queries in NO_EVIDENCE_QUERIES.items():
        development_count = development_counts[category]
        for index, query in enumerate(queries):
            split = "development" if index < development_count else "heldout"
            result[split].append(
                RapidRetrievalCase(
                    case_id=f"rapid-{split}-no-evidence-{category}-{index + 1:02d}",
                    family_id=(
                        f"family-{split}-no-evidence-{category}-{index + 1:02d}"
                    ),
                    split=split,
                    scenario="no_evidence",
                    query=query,
                    expected_action="abstain",
                    no_evidence_category=category,
                    author_model="researcher-authored-public-hard-negative-v1",
                    reviewer_model="deterministic-category-contract-v1",
                    reviewer_valid=True,
                )
            )
    return result


def _validate_quality(
    development: RapidRetrievalDataset,
    heldout: RapidRetrievalDataset,
) -> dict[str, Any]:
    all_cases = [*development.cases, *heldout.cases]
    if len(development.cases) != 26 or len(heldout.cases) != 59:
        raise ValueError("rapid dataset counts differ from the freeze")
    if len({case.family_id for case in all_cases}) != len(all_cases):
        raise ValueError("case families cross splits")
    normalized_queries = [
        re.sub(r"\s+", " ", case.query).strip().casefold() for case in all_cases
    ]
    if len(normalized_queries) != len(set(normalized_queries)):
        raise ValueError("duplicate normalized questions")
    maximum_jaccard = 0.0
    for index, left in enumerate(all_cases):
        left_terms = normalized_tokens(left.query)
        for right in all_cases[index + 1 :]:
            right_terms = normalized_tokens(right.query)
            union = left_terms | right_terms
            score = len(left_terms & right_terms) / len(union) if union else 0.0
            maximum_jaccard = max(maximum_jaccard, score)
            if score >= 0.8:
                raise ValueError("near-duplicate questions exceed Jaccard 0.8")

    heldout_answerable = [
        case for case in heldout.cases if case.expected_action == "answer"
    ]
    heldout_no_evidence = [
        case for case in heldout.cases if case.expected_action == "abstain"
    ]
    scenario_counts = Counter(case.scenario for case in heldout_answerable)
    lecture_counts = Counter(case.lecture_id for case in heldout_answerable)
    category_counts = Counter(case.no_evidence_category for case in heldout_no_evidence)
    if scenario_counts != {
        "exact_or_terminology": 13,
        "paraphrase_or_misconception": 13,
        "multi_evidence": 13,
    }:
        raise ValueError("held-out answerable scenario counts differ from the freeze")
    if set(lecture_counts.values()) != {3} or len(lecture_counts) != 13:
        raise ValueError("held-out lecture coverage differs from the freeze")
    if len(heldout_no_evidence) != 20 or min(category_counts.values()) < 3:
        raise ValueError("held-out no-evidence coverage differs from the freeze")
    if not all(case.reviewer_valid for case in all_cases):
        raise ValueError("a dataset case failed local review")
    return {
        "development_answerable": sum(
            case.expected_action == "answer" for case in development.cases
        ),
        "development_no_evidence": sum(
            case.expected_action == "abstain" for case in development.cases
        ),
        "heldout_answerable": len(heldout_answerable),
        "heldout_no_evidence": len(heldout_no_evidence),
        "heldout_scenario_counts": dict(sorted(scenario_counts.items())),
        "heldout_no_evidence_category_counts": dict(sorted(category_counts.items())),
        "maximum_query_jaccard": round(maximum_jaccard, 6),
        "cross_split_family_overlap": 0,
        "duplicate_normalized_queries": 0,
        "reviewer_pass_rate": 1.0,
    }


def _ollama_json(
    model: str,
    prompt: str,
    *,
    num_predict: int,
    seed: int = 5002,
    temperature: float = 0.0,
    format_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": format_schema or "json",
            "options": {
                "temperature": temperature,
                "seed": seed,
                "num_predict": num_predict,
            },
            "keep_alive": "20m",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read())
    content = result.get("response", "")
    try:
        value = json.loads(content)
    except json.JSONDecodeError as error:
        raise ValueError("local author/reviewer returned invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("local author/reviewer JSON must be an object")
    return value


if __name__ == "__main__":
    main()
