#!/usr/bin/env python3
"""Construct the QC-amended private cross-course benchmark draft 2."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.draft_cross_course_benchmark import (
    BASE_SEED,
    COURSES,
    MODEL,
    MODEL_DIGEST,
    ROOT,
    blank_review,
    content_tokens,
    eligible,
    evidence_from,
    load_corpus,
    ollama_json,
    sha256_file,
    stable_order,
    write_review,
)
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


PROMPT_PATH = (
    ROOT
    / "research/05_evaluation/instruments/"
    "cross_course_benchmark_author_v2.prompt.md"
)
DEFAULT_OUTPUT = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_2.json"
)
DEFAULT_REVIEW = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/review/"
    "researcher_review_draft_2.md"
)
DEFAULT_CACHE = (
    ROOT / "data/processed/cross_course_retrieval_v1/draft_2_cache"
)
SINGLE_COUNTS = {
    "IT5002": 13,
    "CS5421": 13,
    "IT5100B": 12,
    "IT5100E": 12,
}
MULTI_COUNTS = {
    "IT5002": 2,
    "CS5421": 2,
    "IT5100B": 3,
    "IT5100E": 3,
}
CONFUSION_TARGETS = {
    "IT5002": 4,
    "CS5421": 4,
    "IT5100B": 4,
    "IT5100E": 3,
}


def semantic_eligible(record: dict[str, Any]) -> bool:
    if not eligible(record):
        return False
    lines = [
        re.findall(r"[A-Za-z][A-Za-z0-9_-]*", line)
        for line in record["chunk"].text.splitlines()
    ]
    prose_lines = [words for words in lines if len(words) >= 6]
    return len(prose_lines) >= 4 and sum(map(len, prose_lines)) >= 35


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            os.environ.get(
                "ACADEMIA_VAULT_ROOT",
                Path.home() / "Documents" / "academia_vault",
            )
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--ollama-url",
        default=os.environ.get(
            "OLLAMA_GENERATE_URL",
            "http://127.0.0.1:11434/api/generate",
        ),
    )
    return parser.parse_args()


def prompt_single(
    instructions: str,
    target: dict[str, Any],
    *,
    kind: str,
    requested_difficulty: str,
    distractor: dict[str, Any] | None = None,
    retry_note: str = "",
) -> str:
    parts = [
        instructions,
        f"CASE TYPE: {kind}",
        f"REQUESTED DIFFICULTY: {requested_difficulty}",
        f"TARGET COURSE: {target['course_id']}",
        "TARGET TEXT START",
        target["chunk"].text,
        "TARGET TEXT END",
    ]
    if distractor is not None:
        parts.extend(
            [
                f"DISTRACTOR COURSE: {distractor['course_id']}",
                "DISTRACTOR TEXT START",
                distractor["chunk"].text,
                "DISTRACTOR TEXT END",
            ]
        )
    if retry_note:
        parts.append(f"PREVIOUS OUTPUT ERROR: {retry_note}")
    return "\n\n".join(parts)


def resolve_quote(candidate: Any, target_text: str) -> str | None:
    if not isinstance(candidate, str):
        return None
    if candidate in target_text:
        return candidate
    stripped = candidate.strip().strip("\"'“”")
    if stripped in target_text:
        return stripped

    normalized_target_chars: list[str] = []
    original_indexes: list[int] = []
    previous_space = False
    for index, character in enumerate(target_text):
        if character.isspace():
            if previous_space:
                continue
            normalized_target_chars.append(" ")
            original_indexes.append(index)
            previous_space = True
        else:
            normalized_target_chars.append(character)
            original_indexes.append(index)
            previous_space = False
    normalized_target = "".join(normalized_target_chars)
    normalized_candidate = " ".join(stripped.split())
    start = normalized_target.find(normalized_candidate)
    if start < 0:
        return None
    end = start + len(normalized_candidate) - 1
    return target_text[original_indexes[start] : original_indexes[end] + 1]


def validate_single(
    draft: dict[str, Any],
    target_text: str,
    requested_difficulty: str,
) -> str | None:
    if draft.get("reject"):
        return str(draft.get("reason", "model rejected source"))
    required = {
        "query",
        "required_claim",
        "supporting_quote",
        "topic",
        "difficulty",
        "visual_dependency",
    }
    if not required <= set(draft):
        return "missing required keys"
    if draft["difficulty"] != requested_difficulty:
        return "difficulty does not match the request"
    if draft["visual_dependency"] != "text_sufficient":
        return "source marked visual unsupported"
    quote = resolve_quote(draft["supporting_quote"], target_text)
    if quote is None:
        return "supporting quote is not an exact target substring"
    if len(quote.strip()) < 20:
        return "supporting quote is too short to establish direct support"
    if len(str(draft["query"]).strip()) < 12:
        return "query is too short"
    if len(str(draft["required_claim"]).strip()) < 8:
        return "claim is too short"
    return None


def single_case(
    *,
    case_id: str,
    split: str,
    slice_name: str,
    target: dict[str, Any],
    difficulty: str,
    instructions: str,
    url: str,
    cache_root: Path,
    seed: int,
    distractor: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    retry_note = ""
    for attempt in range(4):
        prompt = prompt_single(
            instructions,
            target,
            kind=slice_name,
            requested_difficulty=difficulty,
            distractor=distractor,
            retry_note=retry_note,
        )
        try:
            draft = ollama_json(
                url=url,
                prompt=prompt,
                seed=seed + attempt,
                cache_root=cache_root,
            )
        except (KeyError, TypeError, json.JSONDecodeError):
            retry_note = "model output was not valid JSON"
            continue
        error = validate_single(draft, target["chunk"].text, difficulty)
        if error is None:
            quote = resolve_quote(
                draft["supporting_quote"],
                target["chunk"].text,
            )
            if quote is None:
                raise AssertionError("validated quote cannot be unresolved")
            return {
                "case_id": case_id,
                "split": split,
                "slice": slice_name,
                "target_course_id": target["course_id"],
                "query": str(draft["query"]).strip(),
                "expected_action": "retrieve",
                "difficulty": difficulty,
                "topic": str(draft["topic"]).strip()[:120],
                "required_claims": [str(draft["required_claim"]).strip()],
                "gold_evidence": [
                    evidence_from(target, quote)
                ],
                "distractor_source_ids": (
                    [distractor["source_artifact_id"]]
                    if distractor is not None
                    else []
                ),
                "review": blank_review(),
            }
        retry_note = error
    return None


def prompt_multi(
    instructions: str,
    first: dict[str, Any],
    second: dict[str, Any],
    retry_note: str,
) -> str:
    parts = [
        instructions,
        "CASE TYPE: multi-evidence answerable",
        "REQUESTED DIFFICULTY: multi_step",
        f"TARGET COURSE: {first['course_id']}",
        "TARGET A TEXT START",
        first["chunk"].text,
        "TARGET A TEXT END",
        "TARGET B TEXT START",
        second["chunk"].text,
        "TARGET B TEXT END",
    ]
    if retry_note:
        parts.append(f"PREVIOUS OUTPUT ERROR: {retry_note}")
    return "\n\n".join(parts)


def validate_multi(
    draft: dict[str, Any],
    first_text: str,
    second_text: str,
) -> str | None:
    if draft.get("reject"):
        return str(draft.get("reason", "model rejected source pair"))
    required = {
        "query",
        "required_claims",
        "supporting_quotes",
        "topic",
        "difficulty",
        "visual_dependency",
    }
    if not required <= set(draft):
        return "missing required keys"
    claims = draft["required_claims"]
    quotes = draft["supporting_quotes"]
    if not isinstance(claims, list) or len(claims) != 2:
        return "multi-evidence case requires two claims"
    if not isinstance(quotes, list) or len(quotes) != 2:
        return "multi-evidence case requires two quotes"
    first_quote = resolve_quote(quotes[0], first_text)
    second_quote = resolve_quote(quotes[1], second_text)
    if first_quote is None or second_quote is None:
        return "quotes must be exact aligned target substrings"
    if min(len(str(quote).strip()) for quote in quotes) < 20:
        return "each quote must contain at least 20 characters"
    if draft["difficulty"] != "multi_step":
        return "difficulty must be multi_step"
    if draft["visual_dependency"] != "text_sufficient":
        return "source pair marked visual unsupported"
    return None


def multi_case(
    *,
    case_id: str,
    split: str,
    first: dict[str, Any],
    second: dict[str, Any],
    instructions: str,
    url: str,
    cache_root: Path,
    seed: int,
) -> dict[str, Any] | None:
    retry_note = ""
    for attempt in range(4):
        try:
            draft = ollama_json(
                url=url,
                prompt=prompt_multi(instructions, first, second, retry_note),
                seed=seed + attempt,
                cache_root=cache_root,
            )
        except (KeyError, TypeError, json.JSONDecodeError):
            retry_note = "model output was not valid JSON"
            continue
        error = validate_multi(
            draft,
            first["chunk"].text,
            second["chunk"].text,
        )
        if error is None:
            first_quote = resolve_quote(
                draft["supporting_quotes"][0],
                first["chunk"].text,
            )
            second_quote = resolve_quote(
                draft["supporting_quotes"][1],
                second["chunk"].text,
            )
            if first_quote is None or second_quote is None:
                raise AssertionError("validated multi quote cannot be unresolved")
            return {
                "case_id": case_id,
                "split": split,
                "slice": "answerable",
                "target_course_id": first["course_id"],
                "query": str(draft["query"]).strip(),
                "expected_action": "retrieve",
                "difficulty": "multi_step",
                "topic": str(draft["topic"]).strip()[:120],
                "required_claims": [
                    str(claim).strip() for claim in draft["required_claims"]
                ],
                "gold_evidence": [
                    evidence_from(first, first_quote),
                    evidence_from(second, second_quote),
                ],
                "distractor_source_ids": [],
                "review": blank_review(),
            }
        retry_note = error
    return None


def pair_candidates(
    records: list[dict[str, Any]],
    course_id: str,
    used_chunks: set[str],
) -> list[tuple[int, dict[str, Any], dict[str, Any]]]:
    candidates = [
        record
        for record in records
        if record["course_id"] == course_id
        and record["chunk"].id not in used_chunks
        and semantic_eligible(record)
    ]
    pairs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for index, first in enumerate(candidates):
        first_tokens = content_tokens(first["chunk"].text)
        for second in candidates[index + 1 :]:
            if first["relative_path"] == second["relative_path"]:
                continue
            overlap = len(first_tokens & content_tokens(second["chunk"].text))
            if overlap < 2:
                continue
            pairs.append((overlap, first, second))
    return sorted(
        pairs,
        key=lambda item: (
            -item[0],
            item[1]["chunk"].id,
            item[2]["chunk"].id,
        ),
    )


def answerable_cases(
    records: list[dict[str, Any]],
    *,
    instructions: str,
    url: str,
    cache_root: Path,
) -> tuple[list[dict[str, Any]], set[str]]:
    by_course: dict[str, list[dict[str, Any]]] = {}
    used_chunks: set[str] = set()
    for course_id in COURSES:
        singles: list[dict[str, Any]] = []
        candidates = stable_order(
            [
                record
                for record in records
                if record["course_id"] == course_id
                and semantic_eligible(record)
            ],
            f"draft-2-single-{course_id}",
        )
        direct_target = (SINGLE_COUNTS[course_id] + 1) // 2
        for candidate_index, target in enumerate(candidates):
            difficulty = (
                "direct" if len(singles) < direct_target else "paraphrase"
            )
            case = single_case(
                case_id="temporary",
                split="development",
                slice_name="answerable",
                target=target,
                difficulty=difficulty,
                instructions=instructions,
                url=url,
                cache_root=cache_root,
                seed=BASE_SEED + 10_000 + candidate_index,
            )
            if case is None:
                continue
            singles.append(case)
            used_chunks.add(target["chunk"].id)
            print(
                f"accepted {course_id} single "
                f"{len(singles)}/{SINGLE_COUNTS[course_id]} "
                f"({difficulty})",
                flush=True,
            )
            if len(singles) == SINGLE_COUNTS[course_id]:
                break
        if len(singles) != SINGLE_COUNTS[course_id]:
            raise RuntimeError(f"insufficient single cases for {course_id}")

        multis: list[dict[str, Any]] = []
        for pair_index, (_, first, second) in enumerate(
            pair_candidates(records, course_id, used_chunks)
        ):
            case = multi_case(
                case_id="temporary",
                split="development",
                first=first,
                second=second,
                instructions=instructions,
                url=url,
                cache_root=cache_root,
                seed=BASE_SEED + 20_000 + pair_index,
            )
            if case is None:
                continue
            multis.append(case)
            used_chunks.update((first["chunk"].id, second["chunk"].id))
            print(
                f"accepted {course_id} multi "
                f"{len(multis)}/{MULTI_COUNTS[course_id]}",
                flush=True,
            )
            if len(multis) == MULTI_COUNTS[course_id]:
                break
        if len(multis) != MULTI_COUNTS[course_id]:
            raise RuntimeError(f"insufficient multi cases for {course_id}")

        combined: list[dict[str, Any]] = []
        multi_positions = (
            {5, 11}
            if len(multis) == 2
            else {4, 9, 14}
        )
        single_index = 0
        multi_index = 0
        for position in range(1, 16):
            if position in multi_positions:
                case = multis[multi_index]
                multi_index += 1
            else:
                case = singles[single_index]
                single_index += 1
            case["case_id"] = f"ccr1-{course_id.casefold()}-{position:02d}"
            case["split"] = "development" if position <= 8 else "heldout_draft"
            combined.append(case)
        by_course[course_id] = combined
        print(f"drafted 15 answerable cases for {course_id}", flush=True)
    return [
        case for course_id in COURSES for case in by_course[course_id]
    ], used_chunks


def confusion_cases(
    records: list[dict[str, Any]],
    used_chunks: set[str],
    *,
    instructions: str,
    url: str,
    cache_root: Path,
) -> list[dict[str, Any]]:
    targets = [
        record
        for record in records
        if semantic_eligible(record) and record["chunk"].id not in used_chunks
    ]
    distractors = [record for record in records if semantic_eligible(record)]
    pairs: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
    for target in targets:
        target_tokens = content_tokens(target["chunk"].text)
        for distractor in distractors:
            if target["course_id"] == distractor["course_id"]:
                continue
            overlap = len(
                target_tokens & content_tokens(distractor["chunk"].text)
            )
            if overlap >= 2:
                pairs.append((overlap, target, distractor))
    pairs.sort(
        key=lambda item: (
            -item[0],
            item[1]["chunk"].id,
            item[2]["chunk"].id,
        )
    )
    cases: list[dict[str, Any]] = []
    target_use: Counter[str] = Counter()
    pair_use: Counter[tuple[str, str]] = Counter()
    used_targets: set[str] = set()
    for pair_index, (_, target, distractor) in enumerate(pairs):
        target_course = target["course_id"]
        course_pair = tuple(sorted((target_course, distractor["course_id"])))
        if (
            target["chunk"].id in used_targets
            or target_use[target_course] >= CONFUSION_TARGETS[target_course]
            or pair_use[course_pair] >= 4
        ):
            continue
        difficulty = "direct" if len(cases) % 2 == 0 else "paraphrase"
        case = single_case(
            case_id=f"ccr1-confusion-{len(cases) + 1:02d}",
            split="development" if len(cases) < 3 else "heldout_draft",
            slice_name="cross_course_confusion",
            target=target,
            difficulty=difficulty,
            distractor=distractor,
            instructions=instructions,
            url=url,
            cache_root=cache_root,
            seed=BASE_SEED + 30_000 + pair_index,
        )
        if case is None:
            continue
        cases.append(case)
        used_targets.add(target["chunk"].id)
        target_use[target_course] += 1
        pair_use[course_pair] += 1
        print(f"drafted {case['case_id']}", flush=True)
        if len(cases) == 15:
            break
    if len(cases) != 15:
        raise RuntimeError(f"insufficient confusion cases: {len(cases)}/15")
    return cases


def no_evidence_cases() -> list[dict[str, Any]]:
    drafts = [
        (
            "What branch-prediction accuracy did the course's MIPS processor "
            "achieve on SPEC CPU2017?",
            "unsupported processor benchmark",
        ),
        (
            "Which transaction isolation level is configured on the "
            "university's live PostgreSQL service?",
            "unsupported database deployment",
        ),
        (
            "What end-to-end latency did the course's Bytewax pipeline achieve "
            "on a 100-node production cluster?",
            "unsupported streaming deployment",
        ),
        (
            "What was the exact production throughput of the university Kafka "
            "cluster last month?",
            "unsupported operational fact",
        ),
        (
            "Which PostgreSQL settings are currently deployed on the "
            "university's production database?",
            "unsupported operational fact",
        ),
        (
            "How does ARMv9 pointer authentication encode and rotate its "
            "hardware keys?",
            "unsupported architecture",
        ),
        (
            "Which CVE identifiers were found during the latest penetration "
            "test of the course platform?",
            "unsupported security result",
        ),
        (
            "Which cloud region hosts the live course platform and what is its "
            "current SLA?",
            "unsupported deployment",
        ),
        (
            "How should a CDN invalidate cached video segments across global "
            "edge locations?",
            "shared cache vocabulary",
        ),
        (
            "What MongoDB sharding configuration should be used for a "
            "billion-document collection?",
            "shared database vocabulary",
        ),
        (
            "What exact Kafka broker count guarantees one million events per "
            "second?",
            "unsupported capacity",
        ),
        (
            "How did the instructor configure OAuth for the live university "
            "identity provider?",
            "unsupported security configuration",
        ),
        (
            "What legal retention period applies to student chat logs in every "
            "country?",
            "unsupported policy",
        ),
        (
            "Which GPU model and batch size were used to train the security "
            "lecture's language model?",
            "unsupported model provenance",
        ),
        (
            "What was the average examination score for every student in these "
            "courses?",
            "absent student data",
        ),
    ]
    return [
        {
            "case_id": f"ccr1-no-evidence-{index + 1:02d}",
            "split": "development" if index < 3 else "heldout_draft",
            "slice": "no_evidence",
            "target_course_id": None,
            "query": query,
            "expected_action": "abstain",
            "difficulty": "boundary",
            "topic": topic,
            "required_claims": [],
            "gold_evidence": [],
            "distractor_source_ids": [],
            "review": blank_review(),
        }
        for index, (query, topic) in enumerate(drafts)
    ]


def adversarial_cases() -> list[dict[str, Any]]:
    from scripts.draft_cross_course_benchmark import adversarial_cases as v1_cases

    return v1_cases()


def main() -> int:
    args = parse_args()
    require_pre_evaluation_operation_allowed("dataset_generation")
    started = time.monotonic()
    try:
        _, records = load_corpus(args.source_root)
        instructions = PROMPT_PATH.read_text(encoding="utf-8")
        answerable, used_chunks = answerable_cases(
            records,
            instructions=instructions,
            url=args.ollama_url,
            cache_root=args.cache_root,
        )
        confusion = confusion_cases(
            records,
            used_chunks,
            instructions=instructions,
            url=args.ollama_url,
            cache_root=args.cache_root,
        )
        cases = [
            *answerable,
            *no_evidence_cases(),
            *confusion,
            *adversarial_cases(),
        ]
        dataset = {
            "schema_version": 1,
            "dataset_id": "cross-course-retrieval-v1",
            "dataset_version": "draft-2",
            "dataset_status": "machine_draft",
            "corpus_id": "cross-course-portfolio-v2",
            "authoring": {
                "method": "local-model-draft-with-exact-quote-validation",
                "model": MODEL,
                "model_digest": MODEL_DIGEST,
                "prompt_path": str(PROMPT_PATH.relative_to(ROOT)),
                "prompt_sha256": sha256_file(PROMPT_PATH),
                "temperature": 0,
                "base_seed": BASE_SEED,
            },
            "cases": cases,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            f"{json.dumps(dataset, indent=2, ensure_ascii=False)}\n",
            encoding="utf-8",
        )
        write_review(args.review_output, dataset)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"benchmark draft-2 failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "status": "machine_draft_created",
                "dataset_version": "draft-2",
                "cases": len(cases),
                "unique_gold_chunks": len(
                    {
                        evidence["chunk_id"]
                        for case in cases
                        for evidence in case["gold_evidence"]
                    }
                ),
                "elapsed_seconds": time.monotonic() - started,
                "dataset": str(args.output),
                "review": str(args.review_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
