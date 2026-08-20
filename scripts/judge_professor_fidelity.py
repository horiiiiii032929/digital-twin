#!/usr/bin/env python3
"""Run frozen-schema, blinded pedagogy judging.

DeepSeek V4 Pro is the active primary judge. Local Qwen remains available only
as a sensitivity reviewer. Historical Gemma judgments remain reproducible from
their recorded artifacts but are not an active option in this runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from src.digital_twin.model_policy import (
    LOCAL_GENERAL_MODEL,
    require_model_allowed,
)
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
ANCHOR_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v1"
PRIVATE_ROOT = ROOT / "data/processed/course_tutor_v1/sealed_v2"
DEFAULT_RUN = (
    ROOT / "experiments/runs/professor_fidelity_v2/development-001/result.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "experiments/runs/professor_fidelity_v2/development-001/judgments-deepseek-v4-pro.json"
)
PROMPT_PATH = ROOT / "research/05_evaluation/instruments/llm_judge_v1.prompt.md"
ANCHOR_JUDGE_V4_PROBE_PATH = (
    ROOT / "reports/generated/professor-fidelity-judge-v4-empty-response-probe-001.json"
)
EXPECTED_ANCHOR_JUDGE_V4_PROBE_SHA256 = (
    "c7650bbeb4fbf659c63193e6635c6c143d0606bceccd79cb5f178bc3e5d31430"
)
LABELS = ("A", "B", "C", "D")
VALID = {"pass", "partial", "fail"}
CONDITIONS = ("C0", "C1", "C2", "C3")
JUDGE_MODELS = ("deepseek-v4-pro", LOCAL_GENERAL_MODEL)
DEEPSEEK_MODEL = "deepseek-v4-pro"
DEEPSEEK_DOCUMENTED_REVISION = "DeepSeek-V4-Pro-0813"
DEEPSEEK_EXPECTED_FINGERPRINT = "a307abda487cd1b463329ccb945ce396"
DEEPSEEK_MAX_OUTPUT_TOKENS = 8192
DEEPSEEK_INPUT_PRICE_PER_MILLION_USD = 0.435
DEEPSEEK_OUTPUT_PRICE_PER_MILLION_USD = 0.87
DEEPSEEK_USER_ID = "digital-twin-professor-fidelity-judge-v3"
JUDGE_CONTRACT_REVISION = "per-dimension-pairwise-v4-empty-response-display"
EMPTY_RESPONSE_DISPLAY = "[EMPTY RESPONSE]"
SAMPLE_SELECTION_SALT = "professor-fidelity-judge-v3-shared-sample"
REPEAT_SELECTION_SALT = "professor-fidelity-judge-v3-repeat"
DEEPSEEK_DEFAULT_CALL_LIMITS = {"anchor": 100, "development": 350, "heldout": 750}
DEEPSEEK_DEFAULT_COST_STOPS_USD = {
    "anchor": 1.0,
    "development": 3.0,
    "heldout": 6.0,
}


class JudgeError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--dataset", type=Path)
    parser.add_argument("--model", choices=JUDGE_MODELS, default=DEEPSEEK_MODEL)
    parser.add_argument("--allow-external-provider", action="store_true")
    parser.add_argument("--call-limit", type=int)
    parser.add_argument("--cost-stop-usd", type=float)
    parser.add_argument("--sample-rate", type=float, default=1.0)
    parser.add_argument("--swap-order", action="store_true")
    parser.add_argument("--repeat-rate", type=float, default=0.2)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--attempt-id", default="001")
    parser.add_argument("--confirm-historical-reproduction", action="store_true")
    arguments = parser.parse_args()
    if arguments.model == DEEPSEEK_MODEL and not arguments.allow_external_provider:
        parser.error("DeepSeek judging requires --allow-external-provider")
    if arguments.call_limit is not None and arguments.call_limit < 1:
        parser.error("--call-limit must be positive")
    if arguments.cost_stop_usd is not None and arguments.cost_stop_usd <= 0:
        parser.error("--cost-stop-usd must be positive")
    if not re.fullmatch(r"[0-9]{3}", arguments.attempt_id):
        parser.error("--attempt-id must be exactly three digits")
    return arguments


def _enforce_cli_execution_policy(arguments: argparse.Namespace) -> None:
    """Fail before opening a run whose split is paused or historical."""

    from scripts.execute_professor_fidelity import _load_execution_policy

    run_path = arguments.run.as_posix()
    if "anchor-002" in run_path:
        if not arguments.confirm_historical_reproduction:
            raise JudgeError(
                "anchor judging is historical reproduction and requires "
                "--confirm-historical-reproduction"
            )
        return
    split = next(
        (name for name in ("development", "heldout") if name in run_path), None
    )
    if split is None:
        raise JudgeError("cannot infer an authorized split from --run")
    policy = _load_execution_policy()
    if policy["splits"][split].get("authorized") is not True:
        raise JudgeError(
            f"{split} judging is not authorized by {policy['policy_id']}"
        )


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_anchor_judge_v4_qualification() -> dict[str, Any]:
    if not ANCHOR_JUDGE_V4_PROBE_PATH.is_file():
        raise JudgeError("anchor judge-v4 public qualification is missing")
    observed_sha256 = hashlib.sha256(
        ANCHOR_JUDGE_V4_PROBE_PATH.read_bytes()
    ).hexdigest()
    if observed_sha256 != EXPECTED_ANCHOR_JUDGE_V4_PROBE_SHA256:
        raise JudgeError("anchor judge-v4 public qualification hash drifted")
    probe = load_json(ANCHOR_JUDGE_V4_PROBE_PATH)
    judgments = probe.get("judgment", {}).get("single_judgments", [])
    judgment = judgments[0] if isinstance(judgments, list) and judgments else {}
    transport = probe.get("transport", {})
    if (
        probe.get("probe_id") != "professor-fidelity-judge-v4-empty-response-probe-001"
        or probe.get("status") != "passed"
        or probe.get("private_text_used") is not False
        or probe.get("heldout_used") is not False
        or probe.get("contract_revision") != JUDGE_CONTRACT_REVISION
        or probe.get("empty_response_display") != EMPTY_RESPONSE_DISPLAY
        or probe.get("working_tree_dirty") is not False
        or transport.get("calls") != 1
        or transport.get("provider_model") != DEEPSEEK_MODEL
        or transport.get("provider_revision") != DEEPSEEK_EXPECTED_FINGERPRINT
        or judgment.get("label") != "fail"
        or judgment.get("evidence_quote") != EMPTY_RESPONSE_DISPLAY
    ):
        raise JudgeError("anchor judge-v4 public qualification is invalid")
    return {
        "probe_id": probe["probe_id"],
        "raw_sha256": observed_sha256,
        "code_revision": probe["code_revision"],
        "status": probe["status"],
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            stream.write(f"{json.dumps(value, indent=2, ensure_ascii=False)}\n")
    except FileExistsError as error:
        raise JudgeError(f"refusing to overwrite judge result: {path}") from error


def _selected(case_id: str, rate: float, salt: str) -> bool:
    if rate == 0:
        return False
    if not 0 < rate <= 1:
        raise JudgeError("selection rate must be in [0, 1]")
    bucket = (
        int(hashlib.sha256(f"{salt}:{case_id}".encode()).hexdigest()[:8], 16)
        / 0xFFFFFFFF
    )
    return bucket < rate


def _dataset_path(run: dict[str, Any], supplied: Path | None) -> Path:
    if supplied:
        return supplied
    if run["split"] == "anchor":
        return ANCHOR_ROOT / "anchor.json"
    return PRIVATE_ROOT / f"{run['split']}.json"


def _ollama(
    prompt: str,
    model: str,
    schema: dict[str, Any],
    *,
    seed: int,
) -> dict[str, Any]:
    require_model_allowed(model)
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "format": schema,
                "options": {
                    "temperature": 0,
                    "seed": seed,
                    "num_predict": 1200,
                },
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        envelope = json.load(response)
    try:
        return json.loads(envelope["response"])
    except (KeyError, json.JSONDecodeError) as error:
        raise JudgeError("local judge returned malformed JSON") from error


def _deepseek_upper_bound_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        input_tokens * DEEPSEEK_INPUT_PRICE_PER_MILLION_USD
        + output_tokens * DEEPSEEK_OUTPUT_PRICE_PER_MILLION_USD
    ) / 1_000_000


class JudgeTransport:
    """Exact active judge transport with bounded calls and inspectable usage."""

    def __init__(
        self,
        model: str,
        *,
        split: str,
        call_limit: int | None = None,
        cost_stop_usd: float | None = None,
        deepseek_client: Any | None = None,
    ) -> None:
        require_model_allowed(model)
        if model not in JUDGE_MODELS:
            raise JudgeError(f"unsupported judge model: {model}")
        self.model = model
        self.split = split
        self.call_limit = call_limit
        self.cost_stop_usd = cost_stop_usd
        self.call_records: list[dict[str, Any]] = []
        self.total_cost_usd = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_reasoning_tokens = 0
        if model == DEEPSEEK_MODEL:
            self.call_limit = call_limit or DEEPSEEK_DEFAULT_CALL_LIMITS[split]
            self.cost_stop_usd = (
                cost_stop_usd
                if cost_stop_usd is not None
                else DEEPSEEK_DEFAULT_COST_STOPS_USD[split]
            )
            api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if deepseek_client is None and not api_key:
                raise JudgeError("DEEPSEEK_API_KEY is required for DeepSeek judging")
            self.deepseek_client = deepseek_client or OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
                timeout=180,
                max_retries=0,
            )
            self.model_digest = DEEPSEEK_EXPECTED_FINGERPRINT
        else:
            self.deepseek_client = None
            self.model_digest = _model_digest(model)

    def call(
        self,
        *,
        prompt: str,
        schema: dict[str, Any],
        seed: int,
        task_id: str,
        input_sha256: str,
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{64}", input_sha256):
            raise JudgeError("judge input SHA-256 is invalid")
        if self.call_limit is not None and len(self.call_records) >= self.call_limit:
            raise JudgeError("judge call limit reached")
        if self.model != DEEPSEEK_MODEL:
            value = _ollama(prompt, self.model, schema, seed=seed)
            self.call_records.append(
                {
                    "task_id": task_id,
                    "input_sha256": input_sha256,
                    "endpoint_class": "local",
                    "provider_model": self.model,
                    "provider_revision": self.model_digest,
                    "finish_reason": "stop",
                    "usage": None,
                }
            )
            return value

        request_prompt = "\n".join(
            (
                prompt,
                "OUTPUT JSON SCHEMA:",
                json.dumps(schema, ensure_ascii=False, sort_keys=True),
            )
        )
        started = time.perf_counter()
        try:
            response = self.deepseek_client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": request_prompt}],
                max_tokens=DEEPSEEK_MAX_OUTPUT_TOKENS,
                response_format={"type": "json_object"},
                reasoning_effort="high",
                extra_body={
                    "thinking": {"type": "enabled"},
                    "user_id": DEEPSEEK_USER_ID,
                },
            )
        except OpenAIError as error:
            raise JudgeError(
                f"DeepSeek judge request failed: {type(error).__name__}"
            ) from error
        elapsed_seconds = time.perf_counter() - started
        if response.model != DEEPSEEK_MODEL:
            raise JudgeError("DeepSeek judge model identity drifted")
        if response.system_fingerprint != DEEPSEEK_EXPECTED_FINGERPRINT:
            raise JudgeError("DeepSeek judge fingerprint drifted")
        if not response.choices:
            raise JudgeError("DeepSeek judge returned no choice")
        choice = response.choices[0]
        content = choice.message.content
        if not isinstance(content, str) or not content.strip():
            raise JudgeError("DeepSeek judge returned empty content")
        try:
            value = json.loads(content)
        except json.JSONDecodeError as error:
            raise JudgeError("DeepSeek judge returned malformed JSON") from error

        usage = response.usage
        input_tokens = int(usage.prompt_tokens if usage else 0)
        output_tokens = int(usage.completion_tokens if usage else 0)
        completion_details = (
            getattr(usage, "completion_tokens_details", None) if usage else None
        )
        reasoning_tokens = int(getattr(completion_details, "reasoning_tokens", 0) or 0)
        call_cost = _deepseek_upper_bound_cost(input_tokens, output_tokens)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_reasoning_tokens += reasoning_tokens
        self.total_cost_usd += call_cost
        self.call_records.append(
            {
                "task_id": task_id,
                "input_sha256": input_sha256,
                "endpoint_class": "external",
                "provider_model": response.model,
                "provider_revision": response.system_fingerprint,
                "finish_reason": getattr(choice, "finish_reason", None),
                "elapsed_seconds": round(elapsed_seconds, 6),
                "usage": {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "approximate_cost_usd": call_cost,
                    "cost_method": (
                        "upper_bound_all_input_tokens_priced_as_cache_miss"
                    ),
                },
            }
        )
        if self.cost_stop_usd is not None and self.total_cost_usd >= self.cost_stop_usd:
            raise JudgeError(
                f"DeepSeek judge cost stop reached: USD {self.total_cost_usd:.6f}"
            )
        return value

    def summary(self) -> dict[str, Any]:
        return {
            "endpoint_class": ("external" if self.model == DEEPSEEK_MODEL else "local"),
            "provider_model": self.model,
            "documented_revision": (
                DEEPSEEK_DOCUMENTED_REVISION if self.model == DEEPSEEK_MODEL else None
            ),
            "provider_revision": self.model_digest,
            "call_limit": self.call_limit,
            "calls": len(self.call_records),
            "cost_stop_usd": self.cost_stop_usd,
            "cost_usd": self.total_cost_usd,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "reasoning_tokens": self.total_reasoning_tokens,
        }


def _judgment_schema(
    *,
    task_id: str,
    mode: str,
    dimensions: list[str],
) -> dict[str, Any]:
    single_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dimension": {"type": "string", "enum": dimensions},
            "label": {"type": "string", "enum": sorted(VALID)},
            "evidence_quote": {"type": "string", "minLength": 1},
            "reason": {"type": "string", "minLength": 1},
        },
        "required": ["dimension", "label", "evidence_quote", "reason"],
    }
    pair_item = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "dimension": {"type": "string", "enum": dimensions},
            "preference": {"type": "string", "enum": ["A", "B", "tie"]},
            "evidence_quote_a": {"type": "string", "minLength": 1},
            "evidence_quote_b": {"type": "string", "minLength": 1},
            "reason": {"type": "string", "minLength": 1},
        },
        "required": [
            "dimension",
            "preference",
            "evidence_quote_a",
            "evidence_quote_b",
            "reason",
        ],
    }
    single_schema: dict[str, Any]
    pair_schema: dict[str, Any]
    if mode == "single":
        single_schema = {
            "type": "array",
            "minItems": len(dimensions),
            "maxItems": len(dimensions),
            "items": single_item,
        }
        pair_schema = {"type": "null"}
    else:
        single_schema = {"type": "null"}
        pair_schema = {
            "type": "array",
            "minItems": len(dimensions),
            "maxItems": len(dimensions),
            "items": pair_item,
        }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string", "enum": ["1.0.0"]},
            "instrument_id": {"type": "string", "enum": ["llm-judge-v1"]},
            "task_id": {"type": "string", "enum": [task_id]},
            "mode": {"type": "string", "enum": [mode]},
            "single_judgments": single_schema,
            "pairwise_judgments": pair_schema,
        },
        "required": [
            "schema_version",
            "instrument_id",
            "task_id",
            "mode",
            "single_judgments",
            "pairwise_judgments",
        ],
    }


def _mapping(case_id: str, swap: bool) -> dict[str, str]:
    conditions = list(("C0", "C1", "C2", "C3"))
    shift = int(hashlib.sha256(case_id.encode()).hexdigest()[:2], 16) % 4
    conditions = conditions[shift:] + conditions[:shift]
    if swap:
        conditions.reverse()
    return dict(zip(LABELS, conditions, strict=True))


def _pair_mapping(swap: bool) -> dict[str, str]:
    return {"A": "C2", "B": "C1"} if swap else {"A": "C1", "B": "C2"}


def _assessment_context(case: dict[str, Any]) -> str:
    value = case["student_input"]["student_state"]["assessment_context"]
    return {
        "summative": "assessed_current",
        "unassessed": "unassessed",
        "practice": "practice",
    }.get(value, "unknown")


def _dimension_specs(case: dict[str, Any]) -> list[dict[str, Any]]:
    expected = case["ground_truth"]["expected_behavior"]
    required_moves = ", ".join(expected["required_tutoring_moves"]) or "none"
    forbidden = expected["forbidden_actions"] or ["miss the case-specific expectation"]
    return [
        {
            "dimension": dimension,
            "case_specific_expectation": (
                f"Expected action {expected['primary_action']}; required tutoring moves: "
                f"{required_moves}; support level: {expected['allowed_support_level']}."
            ),
            "material_failure_conditions": forbidden,
        }
        for dimension in case["rubric"]["required_pedagogy_dimensions"]
    ]


def _judge_input(
    case: dict[str, Any],
    *,
    task_id: str,
    mode: str,
    response_a: str,
    response_b: str | None,
    presentation_order: str | None,
) -> dict[str, Any]:
    state = case["student_input"]["student_state"]
    return {
        "schema_version": "1.0.0",
        "instrument_id": "llm-judge-v1",
        "task_id": task_id,
        "mode": mode,
        "case_ref": case["case_id"],
        "student_context": {
            "question": case["student_input"]["question"],
            "dialogue_history": case["student_input"]["dialogue_history"],
            "state_summary": json.dumps(state, ensure_ascii=False, sort_keys=True),
            "assessment_context": _assessment_context(case),
        },
        "policy_excerpt": (
            "Judge only the supplied pedagogical expectations. Do not evaluate "
            "factual correctness, citations, permissions, or hard gates."
        ),
        "dimensions": _dimension_specs(case),
        "response_a": _display_response(response_a),
        "response_b": (
            _display_response(response_b) if response_b is not None else None
        ),
        "blinding": {
            "model_names_removed": True,
            "provider_names_removed": True,
            "condition_ids_removed": True,
            "irrelevant_style_metadata_removed": True,
        },
        "hard_gate_results_visible": False,
        "gold_claims_visible": False,
        "randomization": (
            None
            if mode == "single"
            else {
                "assignment_id": f"{task_id}-assignment",
                "seed": 5002,
                "presentation_order": presentation_order,
            }
        ),
    }


def _display_response(response: str) -> str:
    return response if response.strip() else EMPTY_RESPONSE_DISPLAY


def _alphanumeric_index(value: str) -> tuple[str, list[int]]:
    characters: list[str] = []
    positions: list[int] = []
    for index, character in enumerate(value):
        if not character.isalnum():
            continue
        for folded in character.casefold():
            characters.append(folded)
            positions.append(index)
    return "".join(characters), positions


def _align_quote(quote: str, response: str) -> tuple[str, str]:
    if quote in response:
        return quote, "exact"
    normalized_quote, _ = _alphanumeric_index(quote)
    normalized_response, response_positions = _alphanumeric_index(response)
    if not normalized_quote:
        raise JudgeError("evidence quote has no alphanumeric content")
    start = normalized_response.find(normalized_quote)
    if start < 0 or normalized_response.find(normalized_quote, start + 1) >= 0:
        raise JudgeError("evidence quote is not uniquely source-aligned")
    end = start + len(normalized_quote) - 1
    aligned = response[response_positions[start] : response_positions[end] + 1]
    return aligned, "punctuation-case-normalized"


def _align_judgment_quotes(
    value: dict[str, Any],
    *,
    mode: str,
    response_a: str,
    response_b: str | None,
) -> list[dict[str, Any]]:
    alignments = []
    records = (
        value.get("single_judgments")
        if mode == "single"
        else value.get("pairwise_judgments")
    )
    if not isinstance(records, list):
        return alignments
    fields = (
        (("evidence_quote", response_a),)
        if mode == "single"
        else (
            ("evidence_quote_a", response_a),
            ("evidence_quote_b", response_b),
        )
    )
    for item in records:
        if not isinstance(item, dict):
            continue
        for field, response in fields:
            quote = item.get(field)
            if not isinstance(quote, str) or response is None:
                continue
            aligned, method = _align_quote(quote, response)
            if method != "exact":
                alignments.append(
                    {
                        "dimension": item.get("dimension"),
                        "field": field,
                        "method": method,
                        "original_quote": quote,
                        "aligned_quote": aligned,
                    }
                )
                item[field] = aligned
    return alignments


def _canonical_judge_input(payload: dict[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _judge_input_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_judge_input(payload).encode("utf-8")).hexdigest()


def _prompt(payload: dict[str, Any]) -> str:
    return (
        PROMPT_PATH.read_text(encoding="utf-8")
        + "\nINPUT JSON:\n"
        + _canonical_judge_input(payload)
    )


def _validate_judgment(
    value: dict[str, Any],
    *,
    task_id: str,
    mode: str,
    dimensions: list[str],
    response_a: str,
    response_b: str | None,
) -> None:
    if set(value) != {
        "schema_version",
        "instrument_id",
        "task_id",
        "mode",
        "single_judgments",
        "pairwise_judgments",
    }:
        raise JudgeError("judge output contract drifted")
    if value["schema_version"] != "1.0.0" or value["instrument_id"] != "llm-judge-v1":
        raise JudgeError("judge instrument identity drifted")
    if value["task_id"] != task_id or value["mode"] != mode:
        raise JudgeError("judge task identity drifted")
    records = (
        value["single_judgments"] if mode == "single" else value["pairwise_judgments"]
    )
    if not isinstance(records, list) or {
        item.get("dimension") for item in records
    } != set(dimensions):
        raise JudgeError("judge dimensions drifted")
    if mode == "single":
        if value["pairwise_judgments"] is not None or any(
            item.get("label") not in VALID
            or not item.get("evidence_quote")
            or not item.get("reason")
            for item in records
        ):
            raise JudgeError("single-response judgment is invalid")
        if any(item["evidence_quote"] not in response_a for item in records):
            raise JudgeError("single-response evidence quote is not exact")
    elif value["single_judgments"] is not None or any(
        item.get("preference") not in {"A", "B", "tie"}
        or not item.get("evidence_quote_a")
        or not item.get("evidence_quote_b")
        or not item.get("reason")
        for item in records
    ):
        raise JudgeError("pairwise judgment is invalid")
    elif response_b is None or any(
        item["evidence_quote_a"] not in response_a
        or item["evidence_quote_b"] not in response_b
        for item in records
    ):
        raise JudgeError("pairwise evidence quote is not exact")


def _judge_case(
    case: dict[str, Any],
    rows: dict[str, dict[str, Any]],
    mapping: dict[str, str],
    transport: JudgeTransport,
    *,
    swap: bool,
) -> dict[str, Any]:
    dimensions = case["rubric"]["required_pedagogy_dimensions"]
    responses = []
    quote_alignments = []
    for label, condition in mapping.items():
        task_id = f"judge-{case['case_id']}-{label.lower()}"
        payload = _judge_input(
            case,
            task_id=task_id,
            mode="single",
            response_a=rows[condition]["answer"],
            response_b=None,
            presentation_order=None,
        )
        value = transport.call(
            prompt=_prompt(payload),
            schema=_judgment_schema(
                task_id=task_id,
                mode="single",
                dimensions=dimensions,
            ),
            seed=5002,
            task_id=task_id,
            input_sha256=_judge_input_sha256(payload),
        )
        quote_alignments.extend(
            {
                "task_id": task_id,
                **alignment,
            }
            for alignment in _align_judgment_quotes(
                value,
                mode="single",
                response_a=payload["response_a"],
                response_b=None,
            )
        )
        _validate_judgment(
            value,
            task_id=task_id,
            mode="single",
            dimensions=dimensions,
            response_a=payload["response_a"],
            response_b=None,
        )
        responses.append(
            {
                "label": label,
                "input_sha256": _judge_input_sha256(payload),
                "dimensions": value["single_judgments"],
            }
        )

    pair_mapping = _pair_mapping(swap)
    pair_task_id = f"judge-{case['case_id']}-c1-c2-{'ba' if swap else 'ab'}"
    pair_payload = _judge_input(
        case,
        task_id=pair_task_id,
        mode="pairwise",
        response_a=rows[pair_mapping["A"]]["answer"],
        response_b=rows[pair_mapping["B"]]["answer"],
        presentation_order="BA" if swap else "AB",
    )
    pair = transport.call(
        prompt=_prompt(pair_payload),
        schema=_judgment_schema(
            task_id=pair_task_id,
            mode="pairwise",
            dimensions=dimensions,
        ),
        seed=5002,
        task_id=pair_task_id,
        input_sha256=_judge_input_sha256(pair_payload),
    )
    quote_alignments.extend(
        {
            "task_id": pair_task_id,
            **alignment,
        }
        for alignment in _align_judgment_quotes(
            pair,
            mode="pairwise",
            response_a=pair_payload["response_a"],
            response_b=pair_payload["response_b"],
        )
    )
    _validate_judgment(
        pair,
        task_id=pair_task_id,
        mode="pairwise",
        dimensions=dimensions,
        response_a=pair_payload["response_a"],
        response_b=pair_payload["response_b"],
    )
    normalized = []
    for item in pair["pairwise_judgments"]:
        preference = item["preference"]
        normalized.append(
            {
                **item,
                "preference": (
                    pair_mapping[preference] if preference in {"A", "B"} else "tie"
                ),
            }
        )
    return {
        "responses": responses,
        "c1_c2_pairwise": normalized,
        "pairwise_input_sha256": _judge_input_sha256(pair_payload),
        "pair_mapping": pair_mapping,
        "quote_alignments": quote_alignments,
    }


def _validate_case_result(
    value: dict[str, Any],
    case: dict[str, Any],
    mapping: dict[str, str],
) -> None:
    expected_dimensions = set(case["rubric"]["required_pedagogy_dimensions"])
    records = value.get("responses", [])
    if {record.get("label") for record in records} != set(LABELS):
        raise JudgeError("judge response labels are incomplete")
    for record in records:
        dimensions = record.get("dimensions", [])
        if {item.get("dimension") for item in dimensions} != expected_dimensions:
            raise JudgeError("judge dimensions drifted")
        if record["label"] not in mapping:
            raise JudgeError("judge response label is invalid")
        if not re.fullmatch(r"[a-f0-9]{64}", str(record.get("input_sha256", ""))):
            raise JudgeError("judge response input digest is invalid")
    pairwise = value.get("c1_c2_pairwise", [])
    if {item.get("dimension") for item in pairwise} != expected_dimensions:
        raise JudgeError("pairwise dimensions drifted")
    if any(item.get("preference") not in {"C1", "C2", "tie"} for item in pairwise):
        raise JudgeError("pairwise preference is invalid")
    if not re.fullmatch(
        r"[a-f0-9]{64}", str(value.get("pairwise_input_sha256", ""))
    ):
        raise JudgeError("pairwise input digest is invalid")


def run_judging(arguments: argparse.Namespace) -> dict[str, Any]:
    run = load_json(arguments.run)
    judge_qualification = (
        _load_anchor_judge_v4_qualification() if run["split"] == "anchor" else None
    )
    transport = JudgeTransport(
        arguments.model,
        split=run["split"],
        call_limit=arguments.call_limit,
        cost_stop_usd=arguments.cost_stop_usd,
    )
    dataset_path = _dataset_path(run, arguments.dataset)
    dataset = load_json(dataset_path)
    if hashlib.sha256(dataset_path.read_bytes()).hexdigest() != run["dataset_sha256"]:
        raise JudgeError("judge dataset hash does not match source run")
    case_by_id = {case["case_id"]: case for case in dataset["cases"]}
    rows_by_case: dict[str, dict[str, dict[str, Any]]] = {}
    for row in run["results"]:
        rows_by_case.setdefault(row["case_id"], {})[row["condition"]] = row
    results = []
    judge_run_id = (
        f"{run['run_id']}-{arguments.model.replace(':', '-')}"
        f"{'-swapped' if arguments.swap_order else ''}"
        f"-{JUDGE_CONTRACT_REVISION}-attempt-{arguments.attempt_id}"
    )
    selected_case_ids = [
        case_id
        for case_id in sorted(rows_by_case)
        if _selected(case_id, arguments.sample_rate, SAMPLE_SELECTION_SALT)
    ]
    for index, case_id in enumerate(selected_case_ids, start=1):
        rows = rows_by_case[case_id]
        if set(rows) != set(CONDITIONS):
            raise JudgeError(f"incomplete condition portfolio: {case_id}")
        mapping = _mapping(case_id, arguments.swap_order)
        value = _judge_case(
            case_by_id[case_id],
            rows,
            mapping,
            transport,
            swap=arguments.swap_order,
        )
        _validate_case_result(value, case_by_id[case_id], mapping)
        results.append(
            {
                "case_id": case_id,
                "mapping": mapping,
                "judgment": value,
                "repeat": False,
            }
        )
        if _selected(
            case_id,
            arguments.repeat_rate,
            f"{REPEAT_SELECTION_SALT}-{arguments.model}",
        ):
            repeated = _judge_case(
                case_by_id[case_id],
                rows,
                mapping,
                transport,
                swap=arguments.swap_order,
            )
            _validate_case_result(repeated, case_by_id[case_id], mapping)
            results.append(
                {
                    "case_id": case_id,
                    "mapping": mapping,
                    "judgment": repeated,
                    "repeat": True,
                }
            )
        write_json(
            arguments.output.with_name(f"{arguments.output.stem}-checkpoint.json"),
            {
                "status": "running",
                "judge_run_id": judge_run_id,
                "source_run_id": run["run_id"],
                "model": arguments.model,
                "contract_revision": JUDGE_CONTRACT_REVISION,
                "attempt_id": arguments.attempt_id,
                "judge_qualification": judge_qualification,
                "transport": transport.summary(),
                "completed_cases": index,
                "expected_cases": len(selected_case_ids),
                "case_judgments": results,
            },
        )
        print(
            f"judge={arguments.model} case={index}/{len(selected_case_ids)}",
            flush=True,
        )
    return {
        "judge_run_id": judge_run_id,
        "status": "complete",
        "source_run_id": run["run_id"],
        "instrument_id": "llm-judge-v1",
        "contract_revision": JUDGE_CONTRACT_REVISION,
        "attempt_id": arguments.attempt_id,
        "judge_qualification": judge_qualification,
        "model": arguments.model,
        "model_digest": transport.model_digest,
        "temperature": 0 if arguments.model != DEEPSEEK_MODEL else None,
        "seed": 5002 if arguments.model != DEEPSEEK_MODEL else None,
        "selection_seed": 5002,
        "sample_selection_salt": SAMPLE_SELECTION_SALT,
        "thinking": arguments.model == DEEPSEEK_MODEL,
        "reasoning_effort": ("high" if arguments.model == DEEPSEEK_MODEL else None),
        "max_output_tokens_per_call": (
            DEEPSEEK_MAX_OUTPUT_TOKENS if arguments.model == DEEPSEEK_MODEL else 1200
        ),
        "calls_per_nonrepeat_case": 5,
        "sample_rate": arguments.sample_rate,
        "repeat_rate": arguments.repeat_rate,
        "swapped_order": arguments.swap_order,
        "transport": transport.summary(),
        "call_records": transport.call_records,
        "case_judgments": results,
    }


def _model_digest(model: str) -> str:
    completed = subprocess_run(["ollama", "list"])
    for line in completed.splitlines()[1:]:
        columns = line.split()
        if len(columns) >= 2 and columns[0] == model:
            return columns[1]
    raise JudgeError(f"Ollama model digest is unavailable: {model}")


def subprocess_run(command: list[str]) -> str:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def main() -> None:
    arguments = parse_args()
    require_pre_evaluation_operation_allowed("method_evaluation_execution")
    _enforce_cli_execution_policy(arguments)
    checkpoint = arguments.output.with_name(f"{arguments.output.stem}-checkpoint.json")
    if arguments.output.exists() or checkpoint.exists():
        raise JudgeError(
            f"refusing to overwrite judge result or checkpoint: {arguments.output}"
        )
    result = run_judging(arguments)
    write_json_exclusive(arguments.output, result)
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "case_judgments"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
