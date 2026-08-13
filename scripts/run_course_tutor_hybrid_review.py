#!/usr/bin/env python3
"""Run the frozen cross-provider ensemble and prepare a blinded human audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, AuthenticationError
from openai import OpenAI, OpenAIError

from scripts.build_course_tutor_splits import validate_split_isolation
from scripts.it5002_rapid_common import load_course_corpus
from scripts.validate_course_tutor_dataset import (
    load_json,
    validate_dataset,
    validate_schema,
)


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
DEFAULT_INPUT = ROOT / "data/processed/course_tutor_v1/review_v1_2_3"
DEFAULT_OUTPUT = (
    ROOT / "reports/generated/course-tutor-v1.2.3-hybrid-authoring-review"
)
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
EVIDENCE_ROOT = ROOT / "data/interim/course_tutor_v1/evidence"
MANIFEST_PATH = ROOT / "research/05_evaluation/it5002_lectures_v1.manifest.json"
CASE_SCHEMA_PATH = ROOT / "research/05_evaluation/course_tutor_v1.schema.json"
CONDITION_SCHEMA_PATH = (
    ROOT / "research/05_evaluation/course_tutor_v1_condition.schema.json"
)
PERMISSION_PATH = ROOT / "research/03_data/academics-source-permission.md"
PLAN_PATH = (
    ROOT
    / "research/04_experiments/"
    "2026-08-14-course-tutor-hybrid-authoring-review-v6-plan.md"
)
EXPECTED_PERMISSION_SHA256 = (
    "0595f2163c70b6a81e2b3bfe019a584f8adc47c0e2d5791cc485ccfc14988d9b"
)
EXPECTED_PLAN_SHA256 = (
    "821c4c3e4575a9bfb2af1c345121475ca079c62c02ab6593f09c7f67ffd77851"
)
PLAN_ID = "course-tutor-hybrid-authoring-review-v6"
ENSEMBLE_ID = "course-tutor-v1.2.3-cross-provider-ensemble-v6-001"
HUMAN_AUDIT_ID = "course-tutor-v1.2.3-hybrid-human-audit-v6-001"
PROMPT_VERSION = "course-tutor-hybrid-authoring-review-v6"
SAMPLE_SEED = "course-tutor-hybrid-human-sample-v5"
MAX_HUMAN_CASES = 48
NEIGHBOR_COUNT = 8
BASELINE_PER_STRATUM = 1
DEEPSEEK_MODEL = "deepseek-v4-pro"
DEEPSEEK_DOCUMENTED_REVISION = "DeepSeek-V4-Pro-0813"
DEEPSEEK_CALL_LIMIT = 314
DEEPSEEK_COST_STOP_USD = 2.0
DEEPSEEK_PUBLIC_PROBE_COUNT = 10
DEEPSEEK_PUBLIC_PROBE_MIN_VALID = 9
DEEPSEEK_PRIVATE_MAX_ATTEMPTS = 2
DEEPSEEK_MAX_OUTPUT_TOKENS = 8192
DEEPSEEK_INPUT_PRICE_PER_MILLION_USD = 0.435
DEEPSEEK_OUTPUT_PRICE_PER_MILLION_USD = 0.87
DEEPSEEK_USER_ID = "digital-twin-course-tutor-review-v6"
CHECK_FIELDS = (
    "question_authentic_and_synthetic",
    "expected_behavior_correct",
    "claims_atomic_and_correct",
    "evidence_supports_claims",
    "permission_and_version_correct",
    "split_assignment_acceptable",
)
SCENARIOS = (
    "ambiguity",
    "assessed_work",
    "direct",
    "misconception",
    "multi_evidence",
    "no_evidence",
    "paraphrase",
    "permission_version",
)
MODEL_BINDINGS = (
    {
        "reviewer_id": "deepseek-v4-pro-reviewer-v6",
        "model": DEEPSEEK_MODEL,
        "litellm_model": None,
        "family": "DeepSeek V4",
        "endpoint_class": "external",
        "thinking": True,
        "reasoning_effort": "high",
        "digest": None,
        "documented_revision": DEEPSEEK_DOCUMENTED_REVISION,
    },
    {
        "reviewer_id": "local-qwen3-4b-reviewer-v6",
        "model": "qwen3:4b",
        "litellm_model": None,
        "family": "Qwen 3",
        "endpoint_class": "local",
        "thinking": False,
        "reasoning_effort": None,
        "digest": (
            "359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7"
        ),
        "documented_revision": None,
    },
    {
        "reviewer_id": "local-huihui-qwen3-4b-reviewer-v6",
        "model": "huihui_ai/qwen3-abliterated:4b-thinking-2507-q8_0",
        "litellm_model": None,
        "family": "Qwen 3 derivative",
        "endpoint_class": "local",
        "thinking": False,
        "reasoning_effort": None,
        "digest": (
            "f5046078f1f6b4dc2ad23265d7d9e616aeb77088bc9092623b2f3f056f7b19d4"
        ),
        "documented_revision": None,
    },
)
DECISION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["decision", *CHECK_FIELDS, "reason"],
    "properties": {
        "decision": {"enum": ["approve", "revise"]},
        **{field: {"type": "boolean"} for field in CHECK_FIELDS},
        "reason": {"type": "string", "minLength": 1},
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--allow-external-provider", action="store_true")
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_external_authorization(allow_external_provider: bool) -> None:
    if not allow_external_provider:
        raise ValueError(
            "the frozen v6 review requires --allow-external-provider"
        )
    if sha256(PERMISSION_PATH) != EXPECTED_PERMISSION_SHA256:
        raise ValueError("DeepSeek permission record hash drifted")
    if sha256(PLAN_PATH) != EXPECTED_PLAN_SHA256:
        raise ValueError("frozen v6 review plan hash drifted")


def _write_private_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        f"{json.dumps(value, indent=2, ensure_ascii=False)}\n",
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def _write_private_exclusive(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(value)
    except FileExistsError as error:
        raise ValueError(f"refusing to overwrite review artifact: {path}") from error
    path.chmod(0o600)


def _git_binding() -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {"revision": revision, "dirty": dirty}


def _stable_sample_key(case: dict[str, Any]) -> str:
    identity = "\x1f".join(
        (
            SAMPLE_SEED,
            case["split"],
            case["scenario_type"],
            case["case_id"],
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def select_baseline_case_ids(
    datasets: dict[str, dict[str, Any]],
) -> list[str]:
    selected: list[str] = []
    for split in ("development", "heldout"):
        cases = datasets[split]["cases"]
        for scenario in SCENARIOS:
            stratum = sorted(
                (
                    case
                    for case in cases
                    if case["scenario_type"] == scenario
                ),
                key=_stable_sample_key,
            )
            if len(stratum) < BASELINE_PER_STRATUM:
                raise ValueError(f"insufficient cases for {split}/{scenario}")
            selected.extend(
                case["case_id"]
                for case in stratum[:BASELINE_PER_STRATUM]
            )
    if len(selected) != 16 or len(set(selected)) != 16:
        raise ValueError("baseline human sample must contain 16 unique cases")
    return selected


def validate_model_decision(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("model decision must be an object")
    if set(value) != {"decision", *CHECK_FIELDS, "reason"}:
        raise ValueError("model decision fields do not match the frozen schema")
    if value["decision"] not in {"approve", "revise"}:
        raise ValueError("model decision must be approve or revise")
    for field in CHECK_FIELDS:
        if not isinstance(value[field], bool):
            raise ValueError(f"model decision field {field} must be boolean")
    if not isinstance(value["reason"], str) or not value["reason"].strip():
        raise ValueError("model decision reason must be non-empty")
    all_pass = all(value[field] for field in CHECK_FIELDS)
    if (value["decision"] == "approve") != all_pass:
        raise ValueError("model decision is inconsistent with its check booleans")
    return value


def _tokens(value: str) -> list[str]:
    stop = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "be",
        "by",
        "do",
        "does",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "should",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "why",
        "with",
    }
    return [
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 2 and token not in stop
    ]


def build_no_evidence_neighbors(
    cases: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    corpus = load_course_corpus()
    chunks = corpus.structured_chunks
    chunk_tf = [Counter(_tokens(chunk.text)) for chunk in chunks]
    document_frequency = Counter(token for row in chunk_tf for token in row)
    corpus_size = len(chunks)

    def vector(tokens: list[str]) -> dict[str, float]:
        frequencies = Counter(tokens)
        return {
            token: count
            * (math.log((corpus_size + 1) / (document_frequency[token] + 1)) + 1)
            for token, count in frequencies.items()
        }

    def cosine(left: dict[str, float], right: dict[str, float]) -> float:
        dot = sum(value * right.get(key, 0.0) for key, value in left.items())
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if not left_norm or not right_norm:
            return 0.0
        return dot / (left_norm * right_norm)

    chunk_vectors = [vector(list(row.elements())) for row in chunk_tf]
    result: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        query_vector = vector(_tokens(case["student_input"]["question"]))
        ranked = sorted(
            (
                (cosine(query_vector, chunk_vector), chunk)
                for chunk_vector, chunk in zip(chunk_vectors, chunks, strict=True)
            ),
            key=lambda item: (-item[0], item[1].id),
        )[:NEIGHBOR_COUNT]
        result[case["case_id"]] = [
            {
                "source_artifact_id": chunk.document_id,
                "passage_id": chunk.id,
                "locator": chunk.locator,
                "content_sha256": chunk.content_hash,
                "lexical_tfidf_cosine": round(score, 6),
                "text": chunk.text,
            }
            for score, chunk in ranked
        ]
    return result


def _case_payload(
    case: dict[str, Any],
    neighbors: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    ground_truth = case["ground_truth"]
    evidence = []
    for item in ground_truth["evidence_units"]:
        evidence.append(
            {
                **item,
                "text": (
                    EVIDENCE_ROOT / f"{item['passage_id']}.txt"
                ).read_text(encoding="utf-8").strip(),
            }
        )
    return {
        "case_id": case["case_id"],
        "split": case["split"],
        "scenario_type": case["scenario_type"],
        "topic_stratum": case["topic_stratum"],
        "difficulty": case["difficulty"],
        "difficulty_rationale": case["difficulty_rationale"],
        "lineage": case["lineage"],
        "student_input": case["student_input"],
        "corpus_answerability": ground_truth["corpus_answerability"],
        "expected_behavior": ground_truth["expected_behavior"],
        "required_claims": ground_truth["required_claims"],
        "optional_claims": ground_truth["optional_claims"],
        "evidence_units": evidence,
        "policy_rule_ids": ground_truth["policy_rule_ids"],
        "reference_rationale": ground_truth["reference_rationale"],
        "nearest_approved_passages": neighbors.get(case["case_id"], []),
    }


def review_prompt(case_payload: dict[str, Any]) -> str:
    scenario = case_payload["scenario_type"]
    scenario_rule = ""
    if scenario == "no_evidence":
        scenario_rule = (
            "For this no-evidence case, evidence_supports_claims is true only if "
            "there are no authored positive claims/evidence and none of the eight "
            "supplied nearest approved passages directly answers the question. "
            "Do not fail this bounded check solely because eight lexical neighbors "
            "cannot prove corpus-wide absence; every no-evidence case is separately "
            "assigned to a human reviewer."
        )
    elif scenario == "multi_evidence":
        scenario_rule = (
            "For this multi-evidence case, evidence_supports_claims is true only if "
            "every claim is directly supported by its mapped passage and each "
            "authored passage is necessary for the complete expected answer."
        )
    elif scenario == "assessed_work":
        scenario_rule = (
            "For this assessed-work case, intentionally absent positive factual "
            "claims and course evidence are correct when the expected behavior "
            "enforces bounded scaffold/hints-only support from the declared "
            "assessment context. Do not fail claim or evidence checks merely "
            "because the case correctly withholds an answer."
        )
    elif scenario == "ambiguity":
        scenario_rule = (
            "For this ambiguity case, intentionally absent positive factual claims "
            "and essential evidence are correct when the question is genuinely "
            "underspecified and the expected action is to clarify without guessing."
        )
    output_example = {
        "decision": "approve",
        **{field: True for field in CHECK_FIELDS},
        "reason": "All six checks pass because the expected behavior and exact evidence align.",
    }
    return "\n".join(
        (
            "You are an independent reviewer of a synthetic course-tutor evaluation case.",
            "Do not assume the authored labels are correct. Judge only the supplied case and exact evidence.",
            "Return exactly one JSON object matching the supplied JSON schema; do not return markdown.",
            f"JSON OUTPUT EXAMPLE: {json.dumps(output_example)}",
            "Set decision=approve if and only if every one of the six checks is true; otherwise set revise.",
            "Check definitions:",
            "- question_authentic_and_synthetic: realistic student wording, answerable or intentionally unanswerable as labeled, and no real-student data.",
            "- expected_behavior_correct: action, support level, tutoring moves, citation rule, alternatives, and forbidden actions fit the question and assessment context.",
            "- claims_atomic_and_correct: each required/optional claim is one checkable proposition and is factually consistent with the exact evidence; true when no positive claim is intentionally required.",
            "- evidence_supports_claims: exact passages support every mapped claim and the evidence set is sufficient without unsupported inference.",
            "- permission_and_version_correct: evidence is approved or intentionally prohibited/superseded for a version-conflict case, source/version/replacement metadata is coherent, and expected behavior respects that boundary.",
            "- split_assignment_acceptable: the case says one valid split, its family identifier is split-specific, and its scenario label is coherent. The frozen family-token aliases are development=dev and heldout=test; these matching aliases are valid even though the words differ. A development/test or heldout/dev mismatch fails. Static validators separately enforce cross-split isolation.",
            scenario_rule,
            "Give a short concrete reason emphasizing any failed check or the strongest approval evidence.",
            "CASE:",
            json.dumps(case_payload, ensure_ascii=False),
        )
    )


def _assert_local_ollama_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.path != "/api/generate"
    ):
        raise ValueError("Ollama URL must be a local HTTP /api/generate endpoint")
    return parsed


def _installed_model_digests(url: str) -> dict[str, str]:
    parsed = _assert_local_ollama_url(url)
    tags_url = urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, "/api/tags", "", "", "")
    )
    try:
        with urllib.request.urlopen(tags_url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError(f"local Ollama model lookup failed: {error}") from error
    return {item["name"]: item["digest"] for item in payload.get("models", [])}


def assert_model_bindings(url: str) -> None:
    installed = _installed_model_digests(url)
    for binding in MODEL_BINDINGS:
        if binding["endpoint_class"] != "local":
            continue
        if installed.get(binding["model"]) != binding["digest"]:
            raise ValueError(
                f"local model binding mismatch for {binding['reviewer_id']}"
            )


def _decision_seed(reviewer_id: str, case_id: str) -> int:
    digest = hashlib.sha256(
        f"{PROMPT_VERSION}\x1f{reviewer_id}\x1f{case_id}".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


def call_ollama(
    *,
    url: str,
    model: str,
    prompt: str,
    seed: int,
    thinking: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _assert_local_ollama_url(url)
    request = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": thinking,
                "format": DECISION_SCHEMA,
                "keep_alive": "30m",
                "options": {
                    "temperature": 0,
                    "seed": seed,
                    "num_predict": 350,
                },
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode("utf-8"))
    elapsed_seconds = time.perf_counter() - started
    decision = validate_model_decision(json.loads(result["response"]))
    return decision, {
        "elapsed_seconds": round(elapsed_seconds, 6),
        "prompt_eval_count": result.get("prompt_eval_count"),
        "eval_count": result.get("eval_count"),
        "total_duration_ns": result.get("total_duration"),
    }


def _deepseek_upper_bound_cost(input_tokens: int, output_tokens: int) -> float:
    """Price every input token as a cache miss for a conservative run cap."""
    return (
        input_tokens * DEEPSEEK_INPUT_PRICE_PER_MILLION_USD
        + output_tokens * DEEPSEEK_OUTPUT_PRICE_PER_MILLION_USD
    ) / 1_000_000


def _deepseek_client() -> OpenAI:
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY is required for the frozen v6 review")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        timeout=300,
        max_retries=0,
    )


def call_deepseek(
    *,
    client: OpenAI,
    prompt: str,
    expected_revision: str | None,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=DEEPSEEK_MAX_OUTPUT_TOKENS,
            response_format={"type": "json_object"},
            reasoning_effort="high",
            extra_body={
                "thinking": {"type": "enabled"},
                "user_id": DEEPSEEK_USER_ID,
            },
        )
    except AuthenticationError as error:
        return {
            "status": "invalid",
            "decision": None,
            "usage": None,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "provider_model": None,
            "provider_revision": None,
            "failure_class": "authentication_error",
            "retryable": False,
            "hard_stop": True,
            "error": f"{type(error).__name__}: provider authentication failed",
        }
    except (APITimeoutError, APIConnectionError) as error:
        return {
            "status": "invalid",
            "decision": None,
            "usage": None,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "provider_model": None,
            "provider_revision": None,
            "failure_class": "transient_provider_error",
            "retryable": True,
            "hard_stop": False,
            "error": f"{type(error).__name__}: transient provider request failed",
        }
    except OpenAIError as error:
        return {
            "status": "invalid",
            "decision": None,
            "usage": None,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "provider_model": None,
            "provider_revision": None,
            "failure_class": "provider_configuration_error",
            "retryable": False,
            "hard_stop": True,
            "error": f"{type(error).__name__}: provider request failed",
        }
    elapsed_seconds = time.perf_counter() - started
    response_usage = response.usage
    choice = response.choices[0] if response.choices else None
    finish_reason = getattr(choice, "finish_reason", None)
    completion_details = (
        getattr(response_usage, "completion_tokens_details", None)
        if response_usage
        else None
    )
    input_tokens = int(response_usage.prompt_tokens if response_usage else 0)
    output_tokens = int(response_usage.completion_tokens if response_usage else 0)
    total_tokens = int(response_usage.total_tokens if response_usage else 0)
    usage = {
        "elapsed_seconds": round(elapsed_seconds, 6),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "reasoning_tokens": int(
            getattr(completion_details, "reasoning_tokens", 0) or 0
        ),
        "approximate_cost_usd": _deepseek_upper_bound_cost(
            input_tokens, output_tokens
        ),
        "cost_method": "upper_bound_all_input_tokens_priced_as_cache_miss",
    }
    base = {
        "usage": usage,
        "provider_model": response.model,
        "provider_revision": response.system_fingerprint,
        "finish_reason": finish_reason,
    }
    if response.model != DEEPSEEK_MODEL:
        return {
            **base,
            "status": "invalid",
            "decision": None,
            "failure_class": "provider_model_mismatch",
            "retryable": False,
            "hard_stop": True,
            "error": "provider model differs from frozen deepseek-v4-pro binding",
        }
    if not response.system_fingerprint:
        return {
            **base,
            "status": "invalid",
            "decision": None,
            "failure_class": "provider_revision_missing",
            "retryable": False,
            "hard_stop": True,
            "error": "provider omitted the required system fingerprint",
        }
    if (
        expected_revision is not None
        and response.system_fingerprint != expected_revision
    ):
        return {
            **base,
            "status": "invalid",
            "decision": None,
            "failure_class": "provider_revision_mismatch",
            "retryable": False,
            "hard_stop": True,
            "error": "provider system fingerprint drifted during the frozen run",
        }
    content = choice.message.content if choice else None
    if not isinstance(content, str) or not content.strip():
        return {
            **base,
            "status": "invalid",
            "decision": None,
            "failure_class": (
                "output_limit_exhausted"
                if finish_reason == "length"
                else "empty_content"
            ),
            "retryable": True,
            "hard_stop": False,
            "error": "provider returned empty structured content",
        }
    try:
        decision = validate_model_decision(json.loads(content))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        return {
            **base,
            "status": "invalid",
            "decision": None,
            "failure_class": "malformed_structured_content",
            "retryable": True,
            "hard_stop": False,
            "error": f"{type(error).__name__}: structured decision invalid",
        }
    return {
        **base,
        "status": "valid",
        "decision": decision,
        "failure_class": None,
        "retryable": False,
        "hard_stop": False,
    }


def _transport_preflight_prompt(probe_index: int | None = None) -> str:
    example = {
        "decision": "approve",
        **{field: True for field in CHECK_FIELDS},
        "reason": "Synthetic transport preflight passes all checks.",
    }
    return "\n".join(
        (
            "This is a public synthetic JSON transport preflight.",
            f"Probe index: {probe_index}." if probe_index is not None else "",
            "Return exactly the supplied object and no markdown.",
            json.dumps(example),
        )
    )


def run_transport_preflights(
    url: str,
    *,
    deepseek_client: OpenAI,
) -> list[dict[str, Any]]:
    rows = []
    for binding in MODEL_BINDINGS:
        probe_indexes = (
            range(1, DEEPSEEK_PUBLIC_PROBE_COUNT + 1)
            if binding["endpoint_class"] == "external"
            else (None,)
        )
        for probe_index in probe_indexes:
            seed = _decision_seed(
                binding["reviewer_id"],
                f"public-synthetic-transport-preflight-{probe_index}",
            )
            row = {
                "reviewer_id": binding["reviewer_id"],
                "model": binding["model"],
                "model_digest": binding["digest"],
                "documented_revision": binding["documented_revision"],
                "family": binding["family"],
                "endpoint_class": binding["endpoint_class"],
                "thinking": binding["thinking"],
                "reasoning_effort": binding["reasoning_effort"],
                "probe_index": probe_index,
                "seed": seed,
                "private_data_used": False,
            }
            if binding["endpoint_class"] == "external":
                row.update(
                    call_deepseek(
                        client=deepseek_client,
                        prompt=_transport_preflight_prompt(probe_index),
                        expected_revision=None,
                    )
                )
            else:
                try:
                    decision, usage = call_ollama(
                        url=url,
                        model=binding["model"],
                        prompt=_transport_preflight_prompt(),
                        seed=seed,
                        thinking=binding["thinking"],
                    )
                    row.update(
                        {"status": "valid", "decision": decision, "usage": usage}
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                    json.JSONDecodeError,
                    urllib.error.URLError,
                    TimeoutError,
                ) as error:
                    row.update(
                        {
                            "status": "invalid",
                            "decision": None,
                            "usage": None,
                            "error": f"{type(error).__name__}: {error}",
                        }
                    )
            rows.append(row)
    return rows


def validate_transport_preflights(rows: Any) -> list[dict[str, Any]]:
    expected_count = DEEPSEEK_PUBLIC_PROBE_COUNT + len(MODEL_BINDINGS) - 1
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise ValueError("ten DeepSeek probes and two local preflights are required")
    expected = {binding["reviewer_id"]: binding for binding in MODEL_BINDINGS}
    if {row.get("reviewer_id") for row in rows} != set(expected):
        raise ValueError("transport preflight reviewer set is invalid")
    external_rows = [row for row in rows if row.get("endpoint_class") == "external"]
    local_rows = [row for row in rows if row.get("endpoint_class") == "local"]
    if (
        len(external_rows) != DEEPSEEK_PUBLIC_PROBE_COUNT
        or len(local_rows) != len(MODEL_BINDINGS) - 1
        or {row.get("probe_index") for row in external_rows}
        != set(range(1, DEEPSEEK_PUBLIC_PROBE_COUNT + 1))
        or any(row.get("probe_index") is not None for row in local_rows)
    ):
        raise ValueError("transport probe allocation is invalid")
    for row in rows:
        binding = expected[row["reviewer_id"]]
        if any(
            (
                row.get("model") != binding["model"],
                row.get("model_digest") != binding["digest"],
                row.get("documented_revision")
                != binding["documented_revision"],
                row.get("family") != binding["family"],
                row.get("endpoint_class") != binding["endpoint_class"],
                row.get("thinking") is not binding["thinking"],
                row.get("reasoning_effort") != binding["reasoning_effort"],
                row.get("private_data_used") is not False,
            )
        ):
            raise ValueError("transport preflight differs from its frozen binding")
        if binding["endpoint_class"] == "external":
            usage = row.get("usage") or {}
            if any(
                (
                    row.get("provider_model") != DEEPSEEK_MODEL,
                    not isinstance(row.get("provider_revision"), str),
                    not row.get("provider_revision", "").strip(),
                    not isinstance(row.get("finish_reason"), str),
                    not row.get("finish_reason", "").strip(),
                    not isinstance(usage.get("approximate_cost_usd"), (int, float)),
                    not isinstance(usage.get("reasoning_tokens"), int),
                    usage.get("reasoning_tokens", -1) < 0,
                    row.get("hard_stop") is True,
                )
            ):
                raise ValueError("DeepSeek transport preflight lacks its provider binding")
            if row.get("status") == "valid":
                decision = validate_model_decision(row.get("decision"))
                if decision["decision"] != "approve":
                    raise ValueError("DeepSeek probe did not approve synthetic input")
            elif row.get("status") != "invalid" or row.get("retryable") is not True:
                raise ValueError("DeepSeek probe has an unapproved failure class")
        else:
            if row.get("status") != "valid":
                raise ValueError("local transport preflight failed")
            decision = validate_model_decision(row.get("decision"))
            if decision["decision"] != "approve":
                raise ValueError("local transport preflight did not approve")
    if sum(row["status"] == "valid" for row in external_rows) < (
        DEEPSEEK_PUBLIC_PROBE_MIN_VALID
    ):
        raise ValueError("DeepSeek public stress gate failed")
    if len({row["provider_revision"] for row in external_rows}) != 1:
        raise ValueError("DeepSeek public stress fingerprints differ")
    return rows


def required_human_case_ids(
    model_decisions: list[dict[str, Any]],
    baseline_case_ids: list[str],
) -> tuple[list[str], dict[str, list[str]]]:
    reasons: dict[str, set[str]] = defaultdict(set)
    for case_id in baseline_case_ids:
        reasons[case_id].add("frozen_baseline_sample")
    rows_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in model_decisions:
        rows_by_case[row["case_id"]].append(row)
        if row.get("scenario_type") == "no_evidence":
            reasons[row["case_id"]].add("mandatory_no_evidence_census")
    for case_id, rows in rows_by_case.items():
        if len(rows) != len(MODEL_BINDINGS):
            reasons[case_id].add("missing_model_decision")
        deepseek_rows = [
            row for row in rows if row.get("endpoint_class") == "external"
        ]
        local_rows = [
            row for row in rows if row.get("endpoint_class") == "local"
        ]
        if not any(
            row.get("status") == "valid"
            and row.get("decision", {}).get("decision") == "approve"
            for row in deepseek_rows
        ):
            reasons[case_id].add("deepseek_not_approve")
        if not any(
            row.get("status") == "valid"
            and row.get("decision", {}).get("decision") == "approve"
            for row in local_rows
        ):
            reasons[case_id].add("no_local_family_approve")
    ordered = sorted(reasons)
    return ordered, {
        case_id: sorted(reasons[case_id]) for case_id in ordered
    }


def selection_commitment_sha256(
    baseline_case_ids: list[str], required_case_ids: list[str]
) -> str:
    value = {
        "sample_seed": SAMPLE_SEED,
        "baseline_case_ids": baseline_case_ids,
        "required_human_case_ids": required_case_ids,
    }
    serialized = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _summary(
    decisions: list[dict[str, Any]],
    baseline: list[str],
    required: list[str],
    escalation_reasons: dict[str, list[str]],
) -> dict[str, Any]:
    valid = [row for row in decisions if row["status"] == "valid"]
    invalid = [row for row in decisions if row["status"] != "valid"]
    by_reviewer = {}
    for binding in MODEL_BINDINGS:
        rows = [
            row
            for row in decisions
            if row["reviewer_id"] == binding["reviewer_id"]
        ]
        by_reviewer[binding["reviewer_id"]] = {
            "decision_records": len(rows),
            "underlying_attempts": sum(
                len(row.get("attempts", []))
                if binding["endpoint_class"] == "external"
                else 1
                for row in rows
            ),
            "valid": sum(row["status"] == "valid" for row in rows),
            "invalid": sum(row["status"] != "valid" for row in rows),
            "approve": sum(
                row.get("decision", {}).get("decision") == "approve"
                for row in rows
            ),
            "revise": sum(
                row.get("decision", {}).get("decision") == "revise"
                for row in rows
            ),
        }
    rows_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        rows_by_case[row["case_id"]].append(row)
    unanimous_approve = sum(
        len(rows) == len(MODEL_BINDINGS)
        and all(
            row["status"] == "valid"
            and row["decision"]["decision"] == "approve"
            for row in rows
        )
        for rows in rows_by_case.values()
    )
    unanimous_revise = sum(
        len(rows) == len(MODEL_BINDINGS)
        and all(
            row["status"] == "valid"
            and row["decision"]["decision"] == "revise"
            for row in rows
        )
        for rows in rows_by_case.values()
    )
    disagreement = sum(
        len(
            {
                row["decision"]["decision"]
                for row in rows
                if row["status"] == "valid"
            }
        )
        > 1
        for rows in rows_by_case.values()
    )
    two_family_approve = sum(
        any(
            row["endpoint_class"] == "external"
            and row["status"] == "valid"
            and row["decision"]["decision"] == "approve"
            for row in rows
        )
        and any(
            row["endpoint_class"] == "local"
            and row["status"] == "valid"
            and row["decision"]["decision"] == "approve"
            for row in rows
        )
        for rows in rows_by_case.values()
    )
    return {
        "attempt_records": len(decisions),
        "valid_model_decisions": len(valid),
        "invalid_model_decisions": len(invalid),
        "unanimous_approve_cases": unanimous_approve,
        "unanimous_revise_cases": unanimous_revise,
        "disagreement_cases": disagreement,
        "two_family_approve_cases": two_family_approve,
        "baseline_human_cases": len(baseline),
        "mandatory_no_evidence_cases": sum(
            "mandatory_no_evidence_census" in reasons
            for reasons in escalation_reasons.values()
        ),
        "model_escalated_human_cases": sum(
            any(
                reason
                in {
                    "missing_model_decision",
                    "deepseek_not_approve",
                    "no_local_family_approve",
                }
                for reason in escalation_reasons[case_id]
            )
            for case_id in required
        ),
        "required_human_cases": len(required),
        "escalation_reason_counts": dict(
            sorted(
                Counter(
                    reason
                    for reasons in escalation_reasons.values()
                    for reason in reasons
                    if reason != "frozen_baseline_sample"
                ).items()
            )
        ),
        "by_reviewer": by_reviewer,
    }


def _render_case(
    case: dict[str, Any],
    index: int,
    neighbors: dict[str, list[dict[str, Any]]],
) -> list[str]:
    payload = _case_payload(case, neighbors)
    expected = payload["expected_behavior"]
    lines = [
        f"## {index}. {case['case_id']}",
        "",
        f"- Split: `{case['split']}`",
        f"- Scenario: `{case['scenario_type']}`",
        f"- Topic: `{case['topic_stratum']}`",
        f"- Difficulty: `{case['difficulty']}` — {case['difficulty_rationale']}",
        f"- Corpus answerability: `{payload['corpus_answerability']}`",
        f"- Student question: {case['student_input']['question']}",
        f"- Expected primary action: `{expected['primary_action']}`",
        f"- Acceptable alternatives: {', '.join(expected['acceptable_alternatives']) or 'none'}",
        f"- Forbidden actions: {', '.join(expected['forbidden_actions']) or 'none'}",
        f"- Allowed support: `{expected['allowed_support_level']}`",
        f"- Required tutoring moves: {', '.join(expected['required_tutoring_moves']) or 'none'}",
        f"- Citation requirement: `{expected['citation_requirement']}`",
        "",
        "### Required claims",
        "",
    ]
    if payload["required_claims"]:
        for claim in payload["required_claims"]:
            lines.append(
                f"- `{claim['claim_id']}` ({claim['severity']}): "
                f"{claim['claim_text']} — evidence "
                f"{', '.join(claim['evidence_unit_ids'])}"
            )
    else:
        lines.append("- None; verify that the non-answer behavior is appropriate.")
    lines.extend(["", "### Authored evidence", ""])
    if not payload["evidence_units"]:
        lines.append("No authored evidence. Confirm that this is intentional.")
    for item in payload["evidence_units"]:
        lines.extend(
            [
                f"#### {item['evidence_unit_id']} — {item['passage_id']}",
                "",
                f"- Source: `{item['source_artifact_id']}@{item['source_version']}`",
                f"- Locator: {item['locator']}",
                f"- Role/permission: `{item['role']}` / `{item['permission_status']}`",
                f"- Supports: {', '.join(item['supports_claim_ids']) or 'none'}",
                "",
                item["text"],
                "",
            ]
        )
    if payload["nearest_approved_passages"]:
        lines.extend(["### Eight nearest approved corpus passages", ""])
        lines.append(
            "These lexical neighbors support an absence check but cannot prove corpus-wide semantic absence."
        )
        lines.append("")
        for item in payload["nearest_approved_passages"]:
            lines.extend(
                [
                    f"#### {item['passage_id']}",
                    "",
                    f"- Source/locator: `{item['source_artifact_id']}` / {item['locator']}",
                    f"- Lexical score: `{item['lexical_tfidf_cosine']}`",
                    "",
                    item["text"],
                    "",
                ]
            )
    lines.extend(
        [
            "### Review checklist",
            "",
            *[f"- [ ] {field.replace('_', ' ')}" for field in CHECK_FIELDS],
            "- [ ] Record the decision and notes in `human_audit_template.json`.",
            "",
        ]
    )
    return lines


def prepare_human_audit(
    *,
    output_root: Path,
    ensemble: dict[str, Any],
    ensemble_sha256: str,
    cases_by_id: dict[str, dict[str, Any]],
    neighbors: dict[str, list[dict[str, Any]]],
) -> dict[str, str]:
    required = ensemble["selection"]["required_human_case_ids"]
    lines = [
        "# Course-tutor v1.2.3 targeted independent-human audit",
        "",
        "This packet contains private course material. Do not commit or share it.",
        "Model verdicts and reasons are intentionally absent. Do not inspect `ensemble_review.json` until this audit is complete.",
        "Approve a case only when all six checks pass. Mark uncertainty or any defect `revise` and explain it.",
        "",
    ]
    decisions = []
    for index, case_id in enumerate(required, start=1):
        case = cases_by_id[case_id]
        lines.extend(_render_case(case, index, neighbors))
        decisions.append(
            {
                "case_id": case_id,
                "split": case["split"],
                "scenario_type": case["scenario_type"],
                **{field: None for field in CHECK_FIELDS},
                "decision": None,
                "notes": "",
            }
        )
    template = {
        "schema_version": "1.0.0-draft",
        "review_id": HUMAN_AUDIT_ID,
        "plan_id": PLAN_ID,
        "ensemble_id": ENSEMBLE_ID,
        "ensemble_sha256": ensemble_sha256,
        "status": "draft",
        "reviewed_at": None,
        "reviewer": {
            "reviewer_id": None,
            "role": None,
            "human_review": True,
            "independent_human_audit": True,
            "codex_assisted": False,
            "blinded_to_model_decisions": True,
            "model_decisions_inspected": False,
        },
        "draft_hashes": ensemble["draft_hashes"],
        "selection_commitment_sha256": selection_commitment_sha256(
            ensemble["selection"]["baseline_case_ids"], required
        ),
        "required_case_count": len(required),
        "case_decisions": decisions,
    }
    packet_path = output_root / "human_audit_packet.md"
    template_path = output_root / "human_audit_template.json"
    _write_private_exclusive(packet_path, "\n".join(lines) + "\n")
    _write_private_exclusive(
        template_path,
        f"{json.dumps(template, indent=2, ensure_ascii=False)}\n",
    )
    return {"packet": str(packet_path), "template": str(template_path)}


def _load_and_validate_draft(
    input_root: Path,
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, Any],
]:
    review_manifest = load_json(input_root / "review_manifest.json")
    manifest = load_json(MANIFEST_PATH)
    case_schema = load_json(CASE_SCHEMA_PATH)
    condition_schema = load_json(CONDITION_SCHEMA_PATH)
    datasets = {}
    conditions = {}
    for split, expected_count in (("development", 48), ("heldout", 104)):
        dataset_path = input_root / f"{split}.json"
        condition_path = input_root / f"{split}_conditions.json"
        recorded = review_manifest["splits"][split]
        if sha256(dataset_path) != recorded["dataset_sha256"]:
            raise ValueError(f"{split} draft dataset hash drifted")
        if sha256(condition_path) != recorded["conditions_sha256"]:
            raise ValueError(f"{split} draft conditions hash drifted")
        datasets[split] = load_json(dataset_path)
        conditions[split] = load_json(condition_path)
        validate_schema(datasets[split], case_schema)
        validate_schema(conditions[split], condition_schema)
        validate_dataset(
            datasets[split],
            conditions[split],
            manifest,
            EVIDENCE_ROOT,
            expected_count,
        )
    validate_split_isolation(datasets["development"], datasets["heldout"])
    return datasets, conditions, review_manifest


def run_review(
    *,
    input_root: Path,
    output_root: Path,
    ollama_url: str,
    allow_external_provider: bool,
) -> dict[str, Any]:
    final_path = output_root / "ensemble_review.json"
    checkpoint_path = output_root / "checkpoint.json"
    if final_path.exists():
        raise ValueError(f"refusing to overwrite completed ensemble: {final_path}")
    assert_external_authorization(allow_external_provider)
    code_binding = _git_binding()
    if code_binding["dirty"]:
        raise ValueError("the frozen v6 review must run from a clean revision")
    datasets, _, review_manifest = _load_and_validate_draft(input_root)
    assert_model_bindings(ollama_url)
    deepseek_client = _deepseek_client()
    baseline = select_baseline_case_ids(datasets)
    all_cases = sorted(
        [
            *datasets["development"]["cases"],
            *datasets["heldout"]["cases"],
        ],
        key=lambda case: case["case_id"],
    )
    cases_by_id = {case["case_id"]: case for case in all_cases}
    base_binding = {
        "plan_id": PLAN_ID,
        "ensemble_id": ENSEMBLE_ID,
        "prompt_version": PROMPT_VERSION,
        "sample_seed": SAMPLE_SEED,
        "draft_hashes": review_manifest["splits"],
        "models": list(MODEL_BINDINGS),
        "code": code_binding,
        "local_only": False,
        "authorization": {
            "permission_sha256": EXPECTED_PERMISSION_SHA256,
            "plan_sha256": EXPECTED_PLAN_SHA256,
            "external_provider_allowed": True,
        },
        "external_provider": {
            "provider": "DeepSeek",
            "endpoint": "https://api.deepseek.com",
            "model": DEEPSEEK_MODEL,
            "documented_revision": DEEPSEEK_DOCUMENTED_REVISION,
            "thinking": True,
            "reasoning_effort": "high",
            "user_id": DEEPSEEK_USER_ID,
            "transport": "openai-python-direct-chat-completions",
            "public_stress_probes": DEEPSEEK_PUBLIC_PROBE_COUNT,
            "public_stress_min_valid": DEEPSEEK_PUBLIC_PROBE_MIN_VALID,
            "private_max_attempts": DEEPSEEK_PRIVATE_MAX_ATTEMPTS,
            "max_output_tokens": DEEPSEEK_MAX_OUTPUT_TOKENS,
            "request_limit": DEEPSEEK_CALL_LIMIT,
            "cost_stop_usd": DEEPSEEK_COST_STOP_USD,
            "retries": (
                "one-only-after-empty-output-limit-malformed-timeout-or-connection-failure"
            ),
        },
    }
    if checkpoint_path.exists():
        checkpoint = load_json(checkpoint_path)
        binding = checkpoint.get("binding", {})
        if any(binding.get(key) != value for key, value in base_binding.items()):
            raise ValueError("checkpoint binding differs from the current review")
        validate_transport_preflights(binding.get("transport_preflights"))
        decisions = checkpoint.get("model_decisions", [])
        if any(row.get("status") == "in_progress" for row in decisions):
            raise ValueError("checkpoint contains an ambiguous in-flight request")
    else:
        preflights = run_transport_preflights(
            ollama_url,
            deepseek_client=deepseek_client,
        )
        try:
            validate_transport_preflights(preflights)
        except ValueError:
            _write_private_exclusive(
                output_root / "transport_preflight_failure.json",
                f"{json.dumps(preflights, indent=2, ensure_ascii=False)}\n",
            )
            raise
        binding = {
            **base_binding,
            "transport_preflights": preflights,
        }
        decisions = []
    deepseek_preflights = [
        row
        for row in binding["transport_preflights"]
        if row["endpoint_class"] == "external"
    ]
    frozen_provider_revision = deepseek_preflights[0]["provider_revision"]

    def external_totals() -> tuple[int, float]:
        attempts = [
            attempt
            for row in decisions
            if row.get("endpoint_class") == "external"
            for attempt in row.get("attempts", [])
        ]
        cost = sum(
            (row.get("usage") or {}).get("approximate_cost_usd") or 0.0
            for row in deepseek_preflights
        ) + sum(
            (attempt.get("usage") or {}).get("approximate_cost_usd") or 0.0
            for attempt in attempts
        )
        return len(deepseek_preflights) + len(attempts), cost

    def aggregate_attempt_usage(attempts: list[dict[str, Any]]) -> dict[str, Any]:
        usage_rows = [attempt.get("usage") for attempt in attempts]
        known = [usage for usage in usage_rows if isinstance(usage, dict)]
        return {
            "elapsed_seconds": round(
                sum(usage.get("elapsed_seconds", 0.0) for usage in known), 6
            ),
            "input_tokens": sum(usage.get("input_tokens", 0) for usage in known),
            "output_tokens": sum(usage.get("output_tokens", 0) for usage in known),
            "total_tokens": sum(usage.get("total_tokens", 0) for usage in known),
            "reasoning_tokens": sum(
                usage.get("reasoning_tokens", 0) for usage in known
            ),
            "approximate_cost_usd": sum(
                usage.get("approximate_cost_usd", 0.0) for usage in known
            ),
            "attempts_with_known_usage": len(known),
            "attempts_total": len(attempts),
            "cost_method": "upper_bound_all_input_tokens_priced_as_cache_miss",
        }

    preflight_calls, preflight_cost = external_totals()
    if preflight_calls > DEEPSEEK_CALL_LIMIT or preflight_cost >= DEEPSEEK_COST_STOP_USD:
        raise ValueError("DeepSeek preflight exhausted the frozen external budget")
    no_evidence = [
        case for case in all_cases if case["scenario_type"] == "no_evidence"
    ]
    neighbors = build_no_evidence_neighbors(no_evidence)
    completed = {
        (row["reviewer_id"], row["case_id"])
        for row in decisions
        if row.get("status") in {"valid", "invalid"}
    }
    mandatory_human_ids = set(baseline) | {
        case["case_id"] for case in no_evidence
    }
    total = len(MODEL_BINDINGS) * len(all_cases)
    for model_binding in MODEL_BINDINGS:
        for case in all_cases:
            key = (model_binding["reviewer_id"], case["case_id"])
            if key in completed:
                continue
            prompt = review_prompt(_case_payload(case, neighbors))
            row = {
                "reviewer_id": model_binding["reviewer_id"],
                "model": model_binding["model"],
                "model_digest": model_binding["digest"],
                "documented_revision": model_binding["documented_revision"],
                "family": model_binding["family"],
                "endpoint_class": model_binding["endpoint_class"],
                "thinking": model_binding["thinking"],
                "reasoning_effort": model_binding["reasoning_effort"],
                "case_id": case["case_id"],
                "split": case["split"],
                "scenario_type": case["scenario_type"],
                "seed": _decision_seed(
                    model_binding["reviewer_id"], case["case_id"]
                ),
            }
            if model_binding["endpoint_class"] == "external":
                row.update(
                    {
                        "status": "in_progress",
                        "decision": None,
                        "attempts": [],
                    }
                )
                decisions.append(row)
                _write_private_atomic(
                    checkpoint_path,
                    {"binding": binding, "model_decisions": decisions},
                )
                for attempt_index in range(1, DEEPSEEK_PRIVATE_MAX_ATTEMPTS + 1):
                    call_count, cumulative_cost = external_totals()
                    if call_count >= DEEPSEEK_CALL_LIMIT:
                        raise ValueError("DeepSeek request limit reached")
                    if cumulative_cost >= DEEPSEEK_COST_STOP_USD:
                        raise ValueError("DeepSeek cost stop reached")
                    attempt = call_deepseek(
                        client=deepseek_client,
                        prompt=prompt,
                        expected_revision=frozen_provider_revision,
                    )
                    attempt["attempt_index"] = attempt_index
                    row["attempts"].append(attempt)
                    _write_private_atomic(
                        checkpoint_path,
                        {"binding": binding, "model_decisions": decisions},
                    )
                    _, cumulative_cost = external_totals()
                    if cumulative_cost >= DEEPSEEK_COST_STOP_USD:
                        raise ValueError(
                            f"DeepSeek cost stop reached: USD {cumulative_cost:.6f}"
                        )
                    if attempt.get("hard_stop") is True:
                        raise ValueError(attempt["error"])
                    if attempt["status"] == "valid":
                        break
                    if attempt.get("retryable") is not True:
                        break
                final_attempt = row["attempts"][-1]
                row.update(
                    {
                        "status": final_attempt["status"],
                        "decision": final_attempt["decision"],
                        "provider_model": (
                            final_attempt.get("provider_model") or DEEPSEEK_MODEL
                        ),
                        "provider_revision": (
                            final_attempt.get("provider_revision")
                            or frozen_provider_revision
                        ),
                        "provider_identity_source": (
                            "response"
                            if final_attempt.get("provider_revision")
                            else "frozen_request_binding"
                        ),
                        "finish_reason": final_attempt.get("finish_reason"),
                        "usage": aggregate_attempt_usage(row["attempts"]),
                        "error": final_attempt.get("error"),
                    }
                )
                _write_private_atomic(
                    checkpoint_path,
                    {"binding": binding, "model_decisions": decisions},
                )
                deepseek_escalations = {
                    decision_row["case_id"]
                    for decision_row in decisions
                    if decision_row.get("endpoint_class") == "external"
                    and (
                        decision_row.get("status") != "valid"
                        or decision_row.get("decision", {}).get("decision")
                        != "approve"
                    )
                }
                human_lower_bound = len(
                    mandatory_human_ids | deepseek_escalations
                )
                if human_lower_bound > MAX_HUMAN_CASES:
                    _write_private_exclusive(
                        output_root / "instrument_refinement_required.md",
                        (
                            "# Hybrid authoring review stopped\n\n"
                            f"The DeepSeek-stage human lower bound is {human_lower_bound}, "
                            f"above the frozen maximum of {MAX_HUMAN_CASES}.\n"
                        ),
                    )
                    raise ValueError("DeepSeek-stage human lower bound exceeded")
            else:
                try:
                    decision, usage = call_ollama(
                        url=ollama_url,
                        model=model_binding["model"],
                        prompt=prompt,
                        seed=row["seed"],
                        thinking=model_binding["thinking"],
                    )
                    row.update(
                        {"status": "valid", "decision": decision, "usage": usage}
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                    json.JSONDecodeError,
                    urllib.error.URLError,
                    TimeoutError,
                ) as error:
                    row.update(
                        {
                            "status": "invalid",
                            "decision": None,
                            "usage": None,
                            "error": f"{type(error).__name__}: {error}",
                        }
                    )
                decisions.append(row)
                _write_private_atomic(
                    checkpoint_path,
                    {"binding": binding, "model_decisions": decisions},
                )
            print(
                json.dumps(
                    {
                        "progress": f"{len(decisions)}/{total}",
                        "reviewer_id": row["reviewer_id"],
                        "case_id": row["case_id"],
                        "status": row["status"],
                        "decision": (
                            row["decision"]["decision"]
                            if row["decision"]
                            else None
                        ),
                        "underlying_attempts": len(row.get("attempts", [])) or 1,
                    }
                ),
                flush=True,
            )
    required, escalation_reasons = required_human_case_ids(decisions, baseline)
    protocol_status = (
        "blocked_instrument_refinement_required"
        if len(required) > MAX_HUMAN_CASES
        else "awaiting_human_audit"
    )
    external_provider_calls, external_provider_cost_usd = external_totals()
    minimum_external_calls = DEEPSEEK_PUBLIC_PROBE_COUNT + len(all_cases)
    if not minimum_external_calls <= external_provider_calls <= DEEPSEEK_CALL_LIMIT:
        raise ValueError("completed run has an invalid DeepSeek request count")
    ensemble = {
        **binding,
        "external_provider_calls": external_provider_calls,
        "external_provider_cost_usd": round(external_provider_cost_usd, 9),
        "external_provider_revision": frozen_provider_revision,
        "created_at": datetime.now().astimezone().isoformat(),
        "ensemble_status": "complete",
        "protocol_status": protocol_status,
        "committee_limitation": (
            "Three model artifacts represent only two base-model families; "
            "agreement is triage evidence, not independent proof."
        ),
        "no_evidence_limitation": (
            "Eight deterministic lexical neighbors cannot prove corpus-wide "
            "semantic absence."
        ),
        "selection": {
            "baseline_case_ids": baseline,
            "required_human_case_ids": required,
            "escalation_reasons": escalation_reasons,
            "maximum_human_cases": MAX_HUMAN_CASES,
        },
        "summary": _summary(
            decisions,
            baseline,
            required,
            escalation_reasons,
        ),
        "model_decisions": decisions,
        "heldout_boundary": {
            "tutor_outputs_opened": False,
            "blinded_mapping_created": False,
            "seal_created": False,
            "heldout_ledger_created": False,
        },
    }
    _write_private_exclusive(
        final_path,
        f"{json.dumps(ensemble, indent=2, ensure_ascii=False)}\n",
    )
    checkpoint_path.unlink(missing_ok=True)
    result = {
        "ensemble": str(final_path),
        "protocol_status": protocol_status,
        "summary": ensemble["summary"],
        "human_audit": None,
    }
    if protocol_status == "awaiting_human_audit":
        result["human_audit"] = prepare_human_audit(
            output_root=output_root,
            ensemble=ensemble,
            ensemble_sha256=sha256(final_path),
            cases_by_id=cases_by_id,
            neighbors=neighbors,
        )
    else:
        _write_private_exclusive(
            output_root / "instrument_refinement_required.md",
            "\n".join(
                (
                    "# Hybrid authoring review stopped",
                    "",
                    f"The frozen protocol requires human review of {len(required)} cases, exceeding the limit of {MAX_HUMAN_CASES}.",
                    "Do not transfer this workload to the human reviewer. Preserve this result and prospectively refine the review instrument.",
                    "",
                )
            ),
        )
    return result


def main() -> None:
    arguments = parse_args()
    print(
        json.dumps(
            run_review(
                input_root=arguments.input_root,
                output_root=arguments.output_root,
                ollama_url=arguments.ollama_url,
                allow_external_provider=arguments.allow_external_provider,
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
