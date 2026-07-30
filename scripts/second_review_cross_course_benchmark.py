#!/usr/bin/env python3
"""Run a blinded local-model second review of private benchmark labels."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/"
    "cross_course_retrieval_v1_draft_6.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "data/processed/cross_course_retrieval_v1/review/"
    "model_second_review_draft_6.json"
)
DEFAULT_MODEL = "huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0"
DEFAULT_URL = "http://127.0.0.1:11434/api/generate"
PROMPT_VERSION = "cross-course-second-review-v1"
SAMPLE_SEED = "cross-course-second-review-v1"
COURSES = ("IT5002", "CS5421", "IT5100B", "IT5100E")
CHECK_FIELDS = (
    "action_correct",
    "claims_supported",
    "evidence_complete",
    "question_natural",
    "text_sufficient",
    "retrieval_fair",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--model-digest", required=True)
    parser.add_argument("--ollama-url", default=DEFAULT_URL)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_key(case: dict[str, Any]) -> str:
    return hashlib.sha256(
        f"{SAMPLE_SEED}\x1f{case['case_id']}".encode()
    ).hexdigest()


def select_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for course_id in COURSES:
        answerable = sorted(
            (
                case
                for case in cases
                if case["target_course_id"] == course_id
                and case["slice"] == "answerable"
            ),
            key=stable_key,
        )
        confusion = sorted(
            (
                case
                for case in cases
                if case["target_course_id"] == course_id
                and case["slice"] == "cross_course_confusion"
            ),
            key=stable_key,
        )
        if len(answerable) < 3 or len(confusion) < 2:
            raise ValueError(f"insufficient second-review cases for {course_id}")
        selected.extend(answerable[:3])
        selected.extend(confusion[:2])
    if len(selected) != 20 or len({case["case_id"] for case in selected}) != 20:
        raise ValueError("second-review sample must contain 20 unique cases")
    return selected


def blinded_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "question": case["query"],
        "expected_action": case["expected_action"],
        "required_claims": case["required_claims"],
        "evidence": [
            {
                "quote": evidence["supporting_quote"],
                "visual_dependency": evidence["visual_dependency"],
            }
            for evidence in case["gold_evidence"]
        ],
    }


def review_prompt(case: dict[str, Any]) -> str:
    return "\n".join(
        [
            "You are a blinded second reviewer for a course retrieval benchmark.",
            "Do not assume the proposed label is correct.",
            "Judge only the supplied question, action, claims, and exact evidence.",
            "Return one JSON object and no markdown.",
            "Required shape:",
            json.dumps(
                {
                    "decision": "accept or reject",
                    **{field: "boolean" for field in CHECK_FIELDS},
                    "reason": "short concrete reason",
                }
            ),
            "A check passes only when:",
            "- the action is appropriate for the question;",
            "- every claim is directly supported;",
            "- the evidence completely answers the question;",
            "- the question is natural and answerable;",
            "- printed text is sufficient without visual inference; and",
            "- wording is fair for retrieval rather than copied or misleading.",
            "CASE:",
            json.dumps(blinded_case(case), ensure_ascii=False),
        ]
    )


def validate_decision(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("decision") not in {"accept", "reject"}:
        raise ValueError("review decision must be accept or reject")
    for field in CHECK_FIELDS:
        if not isinstance(value.get(field), bool):
            raise ValueError(f"review field {field} must be boolean")
    if not isinstance(value.get("reason"), str) or not value["reason"].strip():
        raise ValueError("review reason must be non-empty")
    all_checks_pass = all(value[field] for field in CHECK_FIELDS)
    if (value["decision"] == "accept") != all_checks_pass:
        raise ValueError("review decision does not agree with check booleans")
    return value


def call_ollama(
    *,
    url: str,
    model: str,
    prompt: str,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {
            "temperature": 0,
            "seed": seed,
            "num_predict": 500,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"local Ollama request failed: {error}") from error
    elapsed_seconds = time.perf_counter() - started
    decision = validate_decision(json.loads(result["response"]))
    usage = {
        "elapsed_seconds": elapsed_seconds,
        "prompt_eval_count": result.get("prompt_eval_count"),
        "eval_count": result.get("eval_count"),
        "total_duration_ns": result.get("total_duration"),
    }
    return decision, usage


def main() -> int:
    args = parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    if not all(case["review"]["researcher_verified"] for case in dataset["cases"]):
        raise ValueError("all cases must be researcher-verified before second review")
    selected = select_cases(dataset["cases"])
    decisions = []
    for index, case in enumerate(selected):
        decision, usage = call_ollama(
            url=args.ollama_url,
            model=args.model,
            prompt=review_prompt(case),
            seed=20260730 + index,
        )
        decisions.append(
            {
                "case_id": case["case_id"],
                "target_course_id": case["target_course_id"],
                "slice": case["slice"],
                "decision": decision,
                "usage": usage,
            }
        )
        print(
            json.dumps(
                {
                    "progress": f"{index + 1}/20",
                    "case_id": case["case_id"],
                    "decision": decision["decision"],
                }
            ),
            flush=True,
        )
    output = {
        "review_id": "cross-course-benchmark-model-second-review-v1",
        "dataset_sha256": sha256_file(args.dataset),
        "sample_seed": SAMPLE_SEED,
        "prompt_version": PROMPT_VERSION,
        "model": args.model,
        "model_digest": args.model_digest,
        "private_local_only": True,
        "sample_contract": {
            "courses": list(COURSES),
            "answerable_per_course": 3,
            "confusion_per_course": 2,
            "case_count": 20,
        },
        "decisions": decisions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"{json.dumps(output, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "completed",
                "accepted": sum(
                    item["decision"]["decision"] == "accept"
                    for item in decisions
                ),
                "rejected": sum(
                    item["decision"]["decision"] == "reject"
                    for item in decisions
                ),
                "output": str(args.output),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
