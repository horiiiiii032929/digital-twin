"""Validate or execute the source-linked factual-QA quality pilot.

This workflow evaluates whether a dataset-generation method is trustworthy. It
does not rank models. Failed or disputed cases are quarantined, and any failed
gate produces a Refine decision before scale work can begin.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

from services.llm import LiteLlmClient
from src.digital_twin.llm import LlmMessage


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/"
    "factual_qa_quality_pilot_v1_attempt_002.json"
)
MULTIMODAL_FIXTURE_PATH = (
    ROOT / "research/05_evaluation/multimodal_retrieval_v1_synthetic.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-quality-pilot-v1-attempt-002.json"
SUPPORTED_INSTRUMENT_IDS = {
    "factual-qa-quality-pilot-v1-attempt-001",
    "factual-qa-quality-pilot-v1-attempt-002",
}
EXPECTED_SLICES = {
    "direct-text": 4,
    "paraphrase-text": 4,
    "multi-evidence-text": 3,
    "multimodal": 6,
    "no-evidence": 3,
    "ambiguous": 2,
    "cross-course-confusion": 1,
    "adversarial-integrity": 1,
}
BOUNDARY_ACTIONS = {"abstain", "clarify", "refuse"}
DEEPSEEK_PRICES = {
    "deepseek-v4-pro": {"input": 0.435, "output": 0.87},
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
}

AUTHOR_SCHEMA = {
    "type": "object",
    "required": [
        "question",
        "answer",
        "action",
        "selected_claim_ids",
        "citations",
    ],
    "properties": {
        "question": {"type": "string", "minLength": 1},
        "answer": {"type": "string", "minLength": 1},
        "action": {
            "type": "string",
            "enum": ["answer", "abstain", "clarify", "refuse"],
        },
        "selected_claim_ids": {
            "type": "array",
            "items": {"type": "string"},
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source_unit_id", "quote"],
                "properties": {
                    "source_unit_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
            },
        },
    },
}

REVIEW_SCHEMA = {
    "type": "object",
    "required": [
        "verdict",
        "question_matches_blueprint",
        "answer_or_action_correct",
        "fully_supported",
        "citation_lineage_correct",
        "no_external_knowledge",
        "course_boundary_respected",
        "failure_categories",
        "rationale",
    ],
    "properties": {
        "verdict": {"type": "string", "enum": ["accept", "reject"]},
        "question_matches_blueprint": {"type": "boolean"},
        "answer_or_action_correct": {"type": "boolean"},
        "fully_supported": {"type": "boolean"},
        "citation_lineage_correct": {"type": "boolean"},
        "no_external_knowledge": {"type": "boolean"},
        "course_boundary_respected": {"type": "boolean"},
        "failure_categories": {
            "type": "array",
            "items": {"type": "string"},
        },
        "rationale": {"type": "string"},
    },
}


class FactualQaPilotError(ValueError):
    """Raised when the frozen pilot contract is incomplete or has drifted."""


@dataclass(frozen=True)
class JsonCall:
    value: dict[str, Any]
    provider_model: str
    provider_revision: str | None
    input_tokens: int
    output_tokens: int
    approximate_cost_usd: float
    latency_ms: float


class JsonTransport(Protocol):
    async def call_json(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> JsonCall: ...


class DeepSeekJsonTransport:
    """Bounded DeepSeek JSON transport using the repository adapter."""

    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding
        provider_model = binding["provider_model"]
        self.client = LiteLlmClient(
            binding["litellm_model"],
            timeout_seconds=binding["timeout_seconds"],
            max_output_tokens=binding["max_output_tokens"],
            temperature=binding["temperature"],
            response_format={"type": "json_object"},
            provider_options=_provider_options(binding),
            cost_calculator=_deepseek_cost_calculator(provider_model),
        )

    async def call_json(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> JsonCall:
        request = "\n".join(
            (prompt, "OUTPUT JSON SCHEMA:", json.dumps(schema, sort_keys=True))
        )
        started = time.perf_counter()
        response = await self.client.chat(
            [
                LlmMessage(role="system", content=system),
                LlmMessage(role="user", content=request),
            ],
            task=task,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            value = json.loads(response.content)
        except json.JSONDecodeError as error:
            raise FactualQaPilotError("DeepSeek returned malformed JSON") from error
        if not isinstance(value, dict):
            raise FactualQaPilotError("DeepSeek JSON root must be an object")
        usage = response.usage
        return JsonCall(
            value=value,
            provider_model=response.provider_model,
            provider_revision=response.provider_revision,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            approximate_cost_usd=usage.approximate_cost_usd or 0.0,
            latency_ms=elapsed_ms,
        )


class OllamaJsonTransport:
    """Local deterministic JSON transport for the independent Qwen review."""

    def __init__(self, binding: dict[str, Any], *, url: str) -> None:
        self.binding = binding
        self.url = _assert_local_ollama_url(url)

    async def call_json(
        self,
        *,
        system: str,
        prompt: str,
        task: str,
        schema: dict[str, Any],
    ) -> JsonCall:
        del task
        return await asyncio.to_thread(
            self._call_sync,
            system=system,
            prompt=prompt,
            schema=schema,
        )

    def _call_sync(
        self, *, system: str, prompt: str, schema: dict[str, Any]
    ) -> JsonCall:
        body = {
            "model": self.binding["model"],
            "system": system,
            "prompt": "\n".join(
                (prompt, "OUTPUT JSON SCHEMA:", json.dumps(schema, sort_keys=True))
            ),
            "stream": False,
            "think": False,
            "format": schema,
            "options": {
                "temperature": self.binding["temperature"],
                "seed": self.binding["seed"],
                "num_predict": self.binding["max_output_tokens"],
            },
        }
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        started = time.perf_counter()
        with urllib.request.urlopen(
            request, timeout=self.binding["timeout_seconds"]
        ) as response:
            envelope = json.load(response)
        elapsed_ms = (time.perf_counter() - started) * 1000
        try:
            value = json.loads(envelope["response"])
        except (KeyError, json.JSONDecodeError) as error:
            raise FactualQaPilotError("Qwen returned malformed JSON") from error
        if not isinstance(value, dict):
            raise FactualQaPilotError("Qwen JSON root must be an object")
        return JsonCall(
            value=value,
            provider_model=str(envelope.get("model", self.binding["model"])),
            provider_revision=self.binding["model_digest"],
            input_tokens=int(envelope.get("prompt_eval_count", 0) or 0),
            output_tokens=int(envelope.get("eval_count", 0) or 0),
            approximate_cost_usd=0.0,
            latency_ms=elapsed_ms,
        )


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FactualQaPilotError(f"cannot load JSON: {path}") from error
    if not isinstance(value, dict):
        raise FactualQaPilotError(f"JSON root must be an object: {path}")
    return value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_assets(
    instrument_path: Path = INSTRUMENT_PATH,
) -> dict[str, Any]:
    instrument = load_json(instrument_path)
    _validate_instrument(instrument)
    corpus_record = instrument["corpus"]
    corpus_path = ROOT / corpus_record["path"]
    digest = sha256_file(corpus_path)
    if digest != corpus_record["sha256"]:
        raise FactualQaPilotError("factual-QA corpus hash drifted")
    corpus = load_json(corpus_path)
    source_summary = validate_corpus(corpus)
    if corpus["corpus_id"] != corpus_record["corpus_id"]:
        raise FactualQaPilotError("factual-QA corpus identity drifted")
    if len(corpus["case_blueprints"]) != corpus_record["case_blueprints"]:
        raise FactualQaPilotError("factual-QA blueprint count drifted")
    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "corpus": corpus,
        "corpus_path": corpus_path,
        "corpus_sha256": digest,
        "source_summary": source_summary,
    }


def _validate_instrument(instrument: dict[str, Any]) -> None:
    if instrument.get("schema_version") != 1:
        raise FactualQaPilotError("unsupported instrument schema")
    instrument_id = instrument.get("instrument_id")
    if instrument_id not in SUPPORTED_INSTRUMENT_IDS:
        raise FactualQaPilotError("unexpected factual-QA instrument ID")
    if instrument.get("status") != "frozen-pending-execution":
        raise FactualQaPilotError("factual-QA instrument is not frozen")
    roles = instrument.get("model_roles", {})
    expected_models = {
        "author": "deepseek-v4-pro",
        "cross_reviewer": "deepseek-v4-flash",
        "independent_sensitivity_reviewer": "qwen3:4b",
    }
    for role, expected_model in expected_models.items():
        binding = roles.get(role, {})
        actual = binding.get("provider_model", binding.get("model"))
        if actual != expected_model:
            raise FactualQaPilotError(f"model binding drifted: {role}")
    if "gemma3:4b" not in instrument.get("excluded_models", []):
        raise FactualQaPilotError("Gemma exclusion is missing")
    execution = instrument.get("execution", {})
    if execution.get("concurrency") != 1 or execution.get("retry_attempts") != 0:
        raise FactualQaPilotError("execution or retry policy drifted")
    if execution.get("cost_stop_usd") != 1.0:
        raise FactualQaPilotError("cost stop drifted")
    if instrument.get("human_audit", {}).get("sample_size") != 6:
        raise FactualQaPilotError("human audit size drifted")
    if (
        instrument.get("quality_gates", {}).get("model_identity_stable_required")
        is not True
    ):
        raise FactualQaPilotError("model identity gate drifted")
    if instrument_id == "factual-qa-quality-pilot-v1-attempt-002":
        for role in ("author", "cross_reviewer"):
            binding = roles[role]
            if binding.get("thinking") != "disabled" or binding.get("temperature") != 0:
                raise FactualQaPilotError(
                    f"attempt 002 deterministic binding drifted: {role}"
                )


def validate_corpus(corpus: dict[str, Any]) -> dict[str, Any]:
    if corpus.get("schema_version") != 1:
        raise FactualQaPilotError("unsupported corpus schema")
    if corpus.get("corpus_id") != "factual-qa-pilot-corpus-v1":
        raise FactualQaPilotError("unexpected corpus ID")
    if corpus.get("status") != "approved-synthetic-pilot":
        raise FactualQaPilotError("corpus is not approved for the pilot")
    boundary = corpus.get("data_boundary", {})
    if boundary != {
        "content_class": "synthetic-public",
        "private_course_text": False,
        "student_data": False,
        "solution_files": False,
        "external_provider_allowed": True,
    }:
        raise FactualQaPilotError("synthetic-public data boundary drifted")

    sources = corpus.get("source_units")
    blueprints = corpus.get("case_blueprints")
    if not isinstance(sources, list) or not sources:
        raise FactualQaPilotError("source units are missing")
    if not isinstance(blueprints, list) or len(blueprints) != 24:
        raise FactualQaPilotError("the pilot requires exactly 24 blueprints")
    source_ids = [source.get("source_unit_id") for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise FactualQaPilotError("source unit IDs are not unique")
    source_map = {source["source_unit_id"]: source for source in sources}
    claim_ids: list[str] = []
    visual_fixture = load_json(MULTIMODAL_FIXTURE_PATH)
    visual_assets = {item["path"]: item for item in visual_fixture["source_assets"]}
    for source in sources:
        _validate_source(source, visual_assets=visual_assets)
        claim_ids.extend(claim["claim_id"] for claim in source["claims"])
    if len(claim_ids) != len(set(claim_ids)):
        raise FactualQaPilotError("claim IDs are not globally unique")

    blueprint_ids = [item.get("blueprint_id") for item in blueprints]
    if len(blueprint_ids) != len(set(blueprint_ids)):
        raise FactualQaPilotError("blueprint IDs are not unique")
    if Counter(item.get("slice") for item in blueprints) != Counter(EXPECTED_SLICES):
        raise FactualQaPilotError("pilot slice composition drifted")
    for blueprint in blueprints:
        _validate_blueprint(blueprint, source_map=source_map)
    return {
        "source_units": len(sources),
        "text_units": sum(source["modality"] == "text" for source in sources),
        "visual_units": sum(source["modality"] != "text" for source in sources),
        "courses": len({source["course_id"] for source in sources}),
        "case_blueprints": len(blueprints),
        "slice_counts": dict(
            sorted(Counter(item["slice"] for item in blueprints).items())
        ),
        "source_integrity_rate": 1.0,
    }


def _validate_source(
    source: dict[str, Any], *, visual_assets: dict[str, dict[str, Any]]
) -> None:
    required = {
        "source_unit_id",
        "course_id",
        "document_id",
        "modality",
        "path",
        "sha256",
        "locator",
        "permission",
        "evidence_text",
        "claims",
    }
    if not required.issubset(source):
        raise FactualQaPilotError("source unit is missing required fields")
    if source["permission"] != "synthetic-approved":
        raise FactualQaPilotError(f"source is not approved: {source['source_unit_id']}")
    path = ROOT / source["path"]
    if not path.is_file() or sha256_file(path) != source["sha256"]:
        raise FactualQaPilotError(f"source hash drifted: {source['source_unit_id']}")
    evidence_text = source["evidence_text"]
    if not isinstance(evidence_text, str) or not evidence_text.strip():
        raise FactualQaPilotError(
            f"source truth is missing: {source['source_unit_id']}"
        )
    claims = source["claims"]
    if not isinstance(claims, list) or not claims:
        raise FactualQaPilotError(f"claims are missing: {source['source_unit_id']}")
    if len({claim.get("claim_id") for claim in claims}) != len(claims):
        raise FactualQaPilotError(f"duplicate claims: {source['source_unit_id']}")
    if any(not claim.get("text", "").strip() for claim in claims):
        raise FactualQaPilotError(f"empty claim: {source['source_unit_id']}")
    if source["modality"] == "text":
        normalized_file = " ".join(path.read_text(encoding="utf-8").split())
        if " ".join(evidence_text.split()) not in normalized_file:
            raise FactualQaPilotError(
                f"text evidence is not verbatim: {source['source_unit_id']}"
            )
        return
    asset = visual_assets.get(source["path"])
    if asset is None or asset["sha256"] != source["sha256"]:
        raise FactualQaPilotError(
            f"visual asset is not bound to the synthetic fixture: {source['source_unit_id']}"
        )
    region_ids = {region["region_id"] for region in asset["regions"]}
    if source["locator"] not in region_ids:
        raise FactualQaPilotError(
            f"visual locator is invalid: {source['source_unit_id']}"
        )


def _validate_blueprint(
    blueprint: dict[str, Any], *, source_map: dict[str, dict[str, Any]]
) -> None:
    if blueprint.get("expected_action") not in {
        "answer",
        "abstain",
        "clarify",
        "refuse",
    }:
        raise FactualQaPilotError(f"invalid action: {blueprint.get('blueprint_id')}")
    evidence_ids = blueprint.get("evidence_unit_ids")
    if not isinstance(evidence_ids, list):
        raise FactualQaPilotError("blueprint evidence IDs must be a list")
    if len(evidence_ids) != len(set(evidence_ids)):
        raise FactualQaPilotError("blueprint evidence IDs are duplicated")
    for source_id in evidence_ids:
        if source_id not in source_map:
            raise FactualQaPilotError(f"unknown source unit: {source_id}")
        if source_map[source_id]["course_id"] != blueprint["course_id"]:
            raise FactualQaPilotError("answer evidence crosses a course boundary")
    if blueprint["expected_action"] == "answer" and not evidence_ids:
        raise FactualQaPilotError("answer blueprint has no evidence")
    if blueprint["expected_action"] in {"abstain", "refuse"} and evidence_ids:
        raise FactualQaPilotError("abstain/refuse blueprint has answer evidence")
    distractors = blueprint.get("distractor_unit_ids", [])
    for source_id in distractors:
        if source_id not in source_map:
            raise FactualQaPilotError(f"unknown distractor source: {source_id}")
        if source_map[source_id]["course_id"] == blueprint["course_id"]:
            raise FactualQaPilotError("cross-course distractor is in the target course")
    if blueprint["slice"] == "cross-course-confusion" and not distractors:
        raise FactualQaPilotError("cross-course blueprint needs a distractor")
    if not str(blueprint.get("question_intent", "")).strip():
        raise FactualQaPilotError("blueprint question intent is missing")


def build_preflight(assets: dict[str, Any], *, ollama_url: str) -> dict[str, Any]:
    instrument = assets["instrument"]
    credential_name = instrument["model_roles"]["author"][
        "credential_environment_variable"
    ]
    credential_present = bool(os.environ.get(credential_name, "").strip())
    local_binding = instrument["model_roles"]["independent_sensitivity_reviewer"]
    installed_digest = _installed_ollama_digest(
        local_binding["model"], ollama_url=ollama_url
    )
    local_model_ready = installed_digest == local_binding["model_digest"]
    return {
        "run_type": "factual-qa-quality-pilot-preflight",
        "instrument_id": instrument["instrument_id"],
        "method_version": instrument["method_version"],
        "status": (
            "ready-for-pilot-execution"
            if credential_present and local_model_ready
            else "blocked"
        ),
        "corpus": {
            "path": str(assets["corpus_path"].relative_to(ROOT)),
            "sha256": assets["corpus_sha256"],
            **assets["source_summary"],
        },
        "model_roles": {
            "author": instrument["model_roles"]["author"]["provider_model"],
            "cross_reviewer": instrument["model_roles"]["cross_reviewer"][
                "provider_model"
            ],
            "independent_sensitivity_reviewer": local_binding["model"],
        },
        "credential_environment_variable": credential_name,
        "credential_present": credential_present,
        "credential_value_emitted": False,
        "local_model_expected_digest": local_binding["model_digest"],
        "local_model_installed_digest": installed_digest,
        "local_model_ready": local_model_ready,
        "excluded_models": instrument["excluded_models"],
        "external_call_enabled": False,
        "private_data_read": False,
        "private_data_emitted": False,
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
    }


async def execute(
    assets: dict[str, Any],
    *,
    author_transport: JsonTransport,
    cross_reviewer_transport: JsonTransport,
    independent_reviewer_transport: JsonTransport,
) -> dict[str, Any]:
    instrument = assets["instrument"]
    corpus = assets["corpus"]
    source_map = {source["source_unit_id"]: source for source in corpus["source_units"]}
    call_limits = {
        "author": instrument["execution"]["author_call_limit"],
        "cross": instrument["execution"]["cross_reviewer_call_limit"],
        "independent": instrument["execution"]["independent_reviewer_call_limit"],
    }
    call_counts = {"author": 0, "cross": 0, "independent": 0}
    external_cost = 0.0
    results: list[dict[str, Any]] = []

    for blueprint in corpus["case_blueprints"]:
        if call_counts["author"] >= call_limits["author"]:
            raise FactualQaPilotError("author call limit reached")
        source_context = _source_context(blueprint, source_map=source_map)
        author_prompt = _author_prompt(blueprint, source_context=source_context)
        call_counts["author"] += 1
        try:
            author_call = await author_transport.call_json(
                system=_author_system_prompt(),
                prompt=author_prompt,
                task="factual_qa_case_authoring",
                schema=AUTHOR_SCHEMA,
            )
            authored = author_call.value
            author_error = None
        except Exception as error:
            authored = None
            author_call = None
            author_error = type(error).__name__
        else:
            external_cost += author_call.approximate_cost_usd
            _enforce_cost(instrument, external_cost)

        deterministic = deterministic_case_checks(
            blueprint,
            authored,
            source_map=source_map,
        )
        cross_call = None
        independent_call = None
        cross_review_raw = None
        independent_review_raw = None
        cross_review = None
        independent_review = None
        review_errors: list[str] = []
        if authored is not None:
            review_prompt = _review_prompt(
                blueprint,
                authored=authored,
                source_context=source_context,
            )
            if call_counts["cross"] >= call_limits["cross"]:
                raise FactualQaPilotError("cross-reviewer call limit reached")
            call_counts["cross"] += 1
            try:
                cross_call = await cross_reviewer_transport.call_json(
                    system=_review_system_prompt(),
                    prompt=review_prompt,
                    task="factual_qa_case_cross_review",
                    schema=REVIEW_SCHEMA,
                )
                cross_review_raw = cross_call.value
                external_cost += cross_call.approximate_cost_usd
                _enforce_cost(instrument, external_cost)
                cross_review = validate_review(cross_review_raw)
            except Exception as error:
                review_errors.append(f"cross:{type(error).__name__}")
            if call_counts["independent"] >= call_limits["independent"]:
                raise FactualQaPilotError("independent-reviewer call limit reached")
            call_counts["independent"] += 1
            try:
                independent_call = await independent_reviewer_transport.call_json(
                    system=_review_system_prompt(),
                    prompt=review_prompt,
                    task="factual_qa_case_independent_review",
                    schema=REVIEW_SCHEMA,
                )
                independent_review_raw = independent_call.value
                independent_review = validate_review(independent_review_raw)
            except Exception as error:
                review_errors.append(f"independent:{type(error).__name__}")

        retained = bool(
            deterministic["passed"]
            and cross_review
            and cross_review["verdict"] == "accept"
        )
        quarantine_reasons = _quarantine_reasons(
            deterministic=deterministic,
            cross_review=cross_review,
            author_error=author_error,
            review_errors=review_errors,
        )
        results.append(
            {
                "blueprint_id": blueprint["blueprint_id"],
                "slice": blueprint["slice"],
                "course_id": blueprint["course_id"],
                "expected_action": blueprint["expected_action"],
                "evidence_unit_ids": blueprint["evidence_unit_ids"],
                "distractor_unit_ids": blueprint.get("distractor_unit_ids", []),
                "authored_case": authored,
                "author_error": author_error,
                "author_call": _call_record(author_call),
                "deterministic": deterministic,
                "cross_review_raw": cross_review_raw,
                "cross_review": cross_review,
                "cross_review_call": _call_record(cross_call),
                "independent_review_raw": independent_review_raw,
                "independent_review": independent_review,
                "independent_review_call": _call_record(independent_call),
                "review_errors": review_errors,
                "retained": retained,
                "quarantine_reasons": quarantine_reasons,
                "sensitivity_flags": _sensitivity_flags(
                    cross_review=cross_review,
                    independent_review=independent_review,
                    review_errors=review_errors,
                ),
            }
        )

    summary = analyze_results(
        instrument,
        results,
        external_cost_usd=external_cost,
        source_integrity_rate=assets["source_summary"]["source_integrity_rate"],
    )
    audit_packet = (
        build_human_audit_packet(
            instrument_id=instrument["instrument_id"],
            corpus_sha256=assets["corpus_sha256"],
            results=results,
        )
        if summary["machine_gates_passed"]
        else None
    )
    return {
        "run_type": instrument["instrument_id"],
        "status": summary["status"],
        "method_version": instrument["method_version"],
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "instrument_path": str(assets["instrument_path"].relative_to(ROOT)),
        "instrument_sha256": sha256_file(assets["instrument_path"]),
        "corpus_path": str(assets["corpus_path"].relative_to(ROOT)),
        "corpus_sha256": assets["corpus_sha256"],
        "data_boundary": corpus["data_boundary"],
        "private_data_read": False,
        "private_data_emitted": False,
        "call_counts": call_counts,
        "summary": summary,
        "results": results,
        "human_audit_packet": audit_packet,
    }


def deterministic_case_checks(
    blueprint: dict[str, Any],
    authored: dict[str, Any] | None,
    *,
    source_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    if not isinstance(authored, dict):
        return {"passed": False, "checks": {"author_completed": False}}
    checks["author_completed"] = True
    checks["schema_fields"] = all(
        field in authored
        for field in (
            "question",
            "answer",
            "action",
            "selected_claim_ids",
            "citations",
        )
    )
    question = authored.get("question")
    answer = authored.get("answer")
    claims = authored.get("selected_claim_ids")
    citations = authored.get("citations")
    checks["nonempty_question"] = isinstance(question, str) and bool(question.strip())
    checks["nonempty_answer"] = isinstance(answer, str) and bool(answer.strip())
    checks["action_matches"] = authored.get("action") == blueprint["expected_action"]
    checks["claim_list"] = isinstance(claims, list) and all(
        isinstance(claim, str) and claim for claim in claims
    )
    checks["citation_list"] = isinstance(citations, list)
    if not checks["claim_list"] or not checks["citation_list"]:
        return {"passed": False, "checks": checks}

    allowed_source_ids = set(blueprint["evidence_unit_ids"])
    allowed_claims = {
        claim["claim_id"]: source_id
        for source_id in allowed_source_ids
        for claim in source_map[source_id]["claims"]
    }
    checks["claim_ids_valid"] = len(claims) == len(set(claims)) and all(
        claim in allowed_claims for claim in claims
    )
    citation_source_ids: list[str] = []
    citation_quotes_exact = True
    citation_shape = True
    for citation in citations:
        if not isinstance(citation, dict):
            citation_shape = False
            continue
        source_id = citation.get("source_unit_id")
        quote = citation.get("quote")
        if not isinstance(source_id, str) or not isinstance(quote, str):
            citation_shape = False
            continue
        citation_source_ids.append(source_id)
        source = source_map.get(source_id)
        if source is None or " ".join(quote.split()) not in " ".join(
            source["evidence_text"].split()
        ):
            citation_quotes_exact = False
    checks["citation_shape"] = citation_shape
    checks["citation_sources_valid"] = set(citation_source_ids).issubset(
        allowed_source_ids
    )
    checks["citation_quotes_exact"] = citation_quotes_exact

    if blueprint["expected_action"] == "answer":
        checks["answer_has_claims"] = bool(claims)
        checks["answer_has_citations"] = bool(citations)
        covered_sources = {
            allowed_claims[claim] for claim in claims if claim in allowed_claims
        }
        checks["required_sources_covered"] = covered_sources == allowed_source_ids
        checks["citation_sources_complete"] = (
            set(citation_source_ids) == allowed_source_ids
        )
    else:
        checks["boundary_has_no_claims"] = claims == []
        checks["boundary_has_no_citations"] = citations == []
    if blueprint["slice"] == "cross-course-confusion":
        distractors = set(blueprint.get("distractor_unit_ids", []))
        checks["cross_course_not_cited"] = not distractors.intersection(
            citation_source_ids
        )
    return {"passed": all(checks.values()), "checks": checks}


def validate_review(review: dict[str, Any]) -> dict[str, Any]:
    boolean_fields = (
        "question_matches_blueprint",
        "answer_or_action_correct",
        "fully_supported",
        "citation_lineage_correct",
        "no_external_knowledge",
        "course_boundary_respected",
    )
    if review.get("verdict") not in {"accept", "reject"}:
        raise FactualQaPilotError("review verdict is invalid")
    if any(not isinstance(review.get(field), bool) for field in boolean_fields):
        raise FactualQaPilotError("review boolean fields are invalid")
    failures = review.get("failure_categories")
    if not isinstance(failures, list) or any(
        not isinstance(item, str) for item in failures
    ):
        raise FactualQaPilotError("review failure categories are invalid")
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
        raise FactualQaPilotError("review rationale is missing")
    expected_accept = all(review[field] for field in boolean_fields)
    reported_verdict = review["verdict"]
    contract_mismatch = (reported_verdict == "accept") != expected_accept
    normalized = dict(review)
    normalized["reported_verdict"] = reported_verdict
    normalized["contract_mismatch"] = contract_mismatch
    if contract_mismatch:
        normalized["verdict"] = "reject"
        normalized["failure_categories"] = sorted(
            set((*failures, "review_contract_mismatch"))
        )
    return normalized


def analyze_results(
    instrument: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    external_cost_usd: float,
    source_integrity_rate: float,
) -> dict[str, Any]:
    total = len(results)
    completed = [item for item in results if item["authored_case"] is not None]
    deterministic_passed = [item for item in results if item["deterministic"]["passed"]]
    boundary = [item for item in results if item["expected_action"] in BOUNDARY_ACTIONS]
    boundary_passed = [
        item
        for item in boundary
        if item["authored_case"] is not None
        and item["authored_case"].get("action") == item["expected_action"]
    ]
    reviewed = [
        item
        for item in results
        if item["cross_review"] is not None and item["independent_review"] is not None
    ]
    agreements = [
        item
        for item in reviewed
        if item["cross_review"]["verdict"] == item["independent_review"]["verdict"]
    ]
    retained = [item for item in results if item["retained"]]
    multimodal = [item for item in results if item["slice"] == "multimodal"]
    retained_multimodal = [item for item in multimodal if item["retained"]]
    normalized_questions = [
        _normalize_question(item["authored_case"]["question"])
        for item in completed
        if isinstance(item["authored_case"].get("question"), str)
    ]
    duplicate_count = len(normalized_questions) - len(set(normalized_questions))
    cross_course_leakage_count = sum(
        bool(
            item["authored_case"]
            and set(item.get("distractor_unit_ids", [])).intersection(
                citation.get("source_unit_id")
                for citation in item["authored_case"].get("citations", [])
                if isinstance(citation, dict)
            )
        )
        for item in results
        if item["slice"] == "cross-course-confusion"
    )
    model_identity_stable = _model_identity_stable(instrument, results)
    metrics = {
        "source_integrity_rate": source_integrity_rate,
        "author_completion_rate": _rate(len(completed), total),
        "deterministic_provenance_rate": _rate(len(deterministic_passed), total),
        "boundary_action_rate": _rate(len(boundary_passed), len(boundary)),
        "cross_course_leakage_count": cross_course_leakage_count,
        "duplicate_question_rate": _rate(duplicate_count, len(normalized_questions)),
        "near_duplicate_question_rate": _near_duplicate_rate(normalized_questions),
        "reviewer_agreement_rate": _rate(len(agreements), len(reviewed)),
        "cross_reviewer_completion_rate": _rate(
            sum(item["cross_review"] is not None for item in results), total
        ),
        "retained_case_rate": _rate(len(retained), total),
        "quarantine_rate": _rate(total - len(retained), total),
        "retained_multimodal_rate": _rate(len(retained_multimodal), len(multimodal)),
        "model_identity_stable": model_identity_stable,
        "private_data_calls": 0,
        "cost_usd": external_cost_usd,
    }
    gates = instrument["quality_gates"]
    gate_results = {
        "source_integrity_rate": metrics["source_integrity_rate"]
        >= gates["source_integrity_rate_min"],
        "author_completion_rate": metrics["author_completion_rate"]
        >= gates["author_completion_rate_min"],
        "deterministic_provenance_rate": metrics["deterministic_provenance_rate"]
        >= gates["deterministic_provenance_rate_min"],
        "boundary_action_rate": metrics["boundary_action_rate"]
        >= gates["boundary_action_rate_min"],
        "cross_course_leakage_count": metrics["cross_course_leakage_count"]
        <= gates["cross_course_leakage_count_max"],
        "duplicate_question_rate": metrics["duplicate_question_rate"]
        <= gates["duplicate_question_rate_max"],
        "near_duplicate_question_rate": metrics["near_duplicate_question_rate"]
        <= gates["near_duplicate_question_rate_max"],
        "cross_reviewer_completion_rate": metrics["cross_reviewer_completion_rate"]
        >= gates["cross_reviewer_completion_rate_min"],
        "retained_case_rate": metrics["retained_case_rate"]
        >= gates["retained_case_rate_min"],
        "quarantine_rate": metrics["quarantine_rate"] <= gates["quarantine_rate_max"],
        "retained_multimodal_rate": metrics["retained_multimodal_rate"]
        >= gates["retained_multimodal_rate_min"],
        "model_identity_stable": metrics["model_identity_stable"]
        is gates["model_identity_stable_required"],
        "private_data_calls": metrics["private_data_calls"]
        <= gates["private_data_calls_max"],
        "cost_usd": metrics["cost_usd"] <= gates["cost_usd_max"],
    }
    machine_gates_passed = all(gate_results.values())
    diagnostic_alerts = []
    if (
        metrics["reviewer_agreement_rate"]
        < instrument["diagnostic_alerts"]["qwen_agreement_rate_below"]
    ):
        diagnostic_alerts.append("qwen-reviewer-agreement-below-alert")
    failure_counts = Counter(
        reason for item in results for reason in item["quarantine_reasons"]
    )
    latencies = [
        call["latency_ms"]
        for item in results
        for call in (
            item["author_call"],
            item["cross_review_call"],
            item["independent_review_call"],
        )
        if call is not None
    ]
    return {
        "status": (
            "machine-gates-passed-human-audit-required"
            if machine_gates_passed
            else "machine-gates-failed-refine"
        ),
        "decision": "go-deeper" if machine_gates_passed else "refine",
        "machine_gates_passed": machine_gates_passed,
        "scale_authorized": False,
        "human_audit_required": machine_gates_passed,
        "case_count": total,
        "retained_cases": len(retained),
        "quarantined_cases": total - len(retained),
        "metrics": metrics,
        "gate_results": gate_results,
        "failed_gates": sorted(
            name for name, passed in gate_results.items() if not passed
        ),
        "diagnostic_alerts": diagnostic_alerts,
        "failures_by_category": dict(sorted(failure_counts.items())),
        "slice_metrics": {
            slice_name: {
                "cases": len(slice_cases),
                "retained": sum(item["retained"] for item in slice_cases),
                "retained_rate": _rate(
                    sum(item["retained"] for item in slice_cases), len(slice_cases)
                ),
            }
            for slice_name in EXPECTED_SLICES
            if (
                slice_cases := [item for item in results if item["slice"] == slice_name]
            )
        },
        "operational": {
            "external_cost_usd": external_cost_usd,
            "input_tokens": sum(
                call["input_tokens"]
                for item in results
                for call in (item["author_call"], item["cross_review_call"])
                if call is not None
            ),
            "output_tokens": sum(
                call["output_tokens"]
                for item in results
                for call in (item["author_call"], item["cross_review_call"])
                if call is not None
            ),
            "call_latency_p50_ms": statistics.median(latencies) if latencies else None,
            "call_latency_p95_ms": _nearest_rank(latencies, 0.95),
        },
    }


def build_human_audit_packet(
    *,
    instrument_id: str,
    corpus_sha256: str,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    retained = {item["blueprint_id"]: item for item in results if item["retained"]}
    preferred_slices = (
        "direct-text",
        "paraphrase-text",
        "multi-evidence-text",
        "multimodal",
        "no-evidence",
        "ambiguous",
    )
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    for slice_name in preferred_slices:
        candidates = sorted(
            (
                item
                for item in retained.values()
                if item["slice"] == slice_name and item["blueprint_id"] not in used
            ),
            key=lambda item: (
                "reviewer-disagreement" not in item.get("sensitivity_flags", []),
                hashlib.sha256(
                    f"{instrument_id}:{item['blueprint_id']}".encode()
                ).hexdigest(),
            ),
        )
        if candidates:
            chosen = candidates[0]
            used.add(chosen["blueprint_id"])
            selected.append(_audit_case(chosen))
    if len(selected) < 6:
        remaining = sorted(
            (item for item in retained.values() if item["blueprint_id"] not in used),
            key=lambda item: hashlib.sha256(item["blueprint_id"].encode()).hexdigest(),
        )
        selected.extend(_audit_case(item) for item in remaining[: 6 - len(selected)])
    if len(selected) != 6:
        raise FactualQaPilotError("machine pass did not yield six auditable cases")
    return {
        "packet_id": f"{instrument_id}-human-audit-001",
        "instrument_id": instrument_id,
        "corpus_sha256": corpus_sha256,
        "status": "pending-human-review",
        "instructions": {
            "pass_only_if": [
                "question is clear for the intended slice",
                "answer or safe action is correct",
                "every factual statement is supported by the cited source truth",
                "all required evidence is cited",
                "course and privacy boundaries are respected",
            ],
            "scale_rule": "all six cases must pass; otherwise refine the method",
        },
        "cases": selected,
    }


def _audit_case(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "blueprint_id": item["blueprint_id"],
        "slice": item["slice"],
        "course_id": item["course_id"],
        "expected_action": item["expected_action"],
        "evidence_unit_ids": item["evidence_unit_ids"],
        "question": item["authored_case"]["question"],
        "answer": item["authored_case"]["answer"],
        "citations": item["authored_case"]["citations"],
        "human_decision": None,
        "human_failure_categories": [],
        "human_notes": "",
    }


def _author_system_prompt() -> str:
    return (
        "You create one source-grounded factual-QA dataset case. Use only the "
        "provided source truth and claim IDs. Never add outside facts. Follow the "
        "expected action. For answer cases, cite exact verbatim substrings from "
        "every required source unit. Always return a non-empty user-visible answer. "
        "For abstain, clarify, or refuse cases, return no claim IDs and no citations. "
        "Return JSON only."
    )


def _review_system_prompt() -> str:
    return (
        "You independently audit one factual-QA dataset case against its frozen "
        "blueprint and supplied source truth. Reject any unsupported detail, missing "
        "required evidence, wrong action, unclear question, citation mismatch, or "
        "course-boundary violation. For an abstain, clarify, or refuse case, an "
        "appropriate non-factual safe response with no claims and no citations is "
        "fully supported and has correct citation lineage. Do not reward fluency. "
        "Return JSON only."
    )


def _author_prompt(blueprint: dict[str, Any], *, source_context: dict[str, Any]) -> str:
    payload = {
        "blueprint": blueprint,
        "approved_target_course_sources": source_context["approved_sources"],
        "unapproved_other_course_distractors": source_context["distractors"],
        "requirements": {
            "question_count": 1,
            "nonempty_user_visible_answer_required": True,
            "answer_length": "one to three concise sentences",
            "answer_cases": "select only supplied claim IDs and cite one exact quote from every required source unit",
            "boundary_cases": {
                "common": "use the expected safe action; selected_claim_ids and citations must be empty",
                "abstain_answer": "state concisely that the approved sources do not provide the requested information",
                "clarify_answer": "ask one targeted clarification question",
                "refuse_answer": "state a concise permission, privacy, or academic-integrity refusal",
            },
            "cross_course_rule": "never use or cite a distractor as target-course evidence",
        },
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _review_prompt(
    blueprint: dict[str, Any],
    *,
    authored: dict[str, Any],
    source_context: dict[str, Any],
) -> str:
    payload = {
        "blueprint": blueprint,
        "approved_target_course_sources": source_context["approved_sources"],
        "unapproved_other_course_distractors": source_context["distractors"],
        "authored_case": authored,
        "verdict_rule": "accept only when every boolean dimension is true",
        "boundary_review_rule": "For abstain, clarify, and refuse, a correct non-factual safe response with empty claim IDs and citations counts as fully_supported=true and citation_lineage_correct=true.",
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _source_context(
    blueprint: dict[str, Any], *, source_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    return {
        "approved_sources": [
            _model_source(source_map[source_id])
            for source_id in blueprint["evidence_unit_ids"]
        ],
        "distractors": [
            _model_source(source_map[source_id])
            for source_id in blueprint.get("distractor_unit_ids", [])
        ],
    }


def _model_source(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_unit_id": source["source_unit_id"],
        "course_id": source["course_id"],
        "modality": source["modality"],
        "locator": source["locator"],
        "source_truth": source["evidence_text"],
        "allowed_claims": source["claims"],
    }


def _quarantine_reasons(
    *,
    deterministic: dict[str, Any],
    cross_review: dict[str, Any] | None,
    author_error: str | None,
    review_errors: list[str],
) -> list[str]:
    reasons: list[str] = []
    if author_error:
        reasons.append("author")
    if not deterministic["passed"]:
        reasons.extend(
            f"deterministic:{name}"
            for name, passed in deterministic["checks"].items()
            if not passed
        )
    if cross_review and cross_review["verdict"] == "reject":
        reasons.append("cross-reviewer")
        reasons.extend(
            f"cross-reviewer:{item}" for item in cross_review["failure_categories"]
        )
    reasons.extend(
        error for error in review_errors if not error.startswith("independent:")
    )
    return sorted(set(reasons))


def _sensitivity_flags(
    *,
    cross_review: dict[str, Any] | None,
    independent_review: dict[str, Any] | None,
    review_errors: list[str],
) -> list[str]:
    flags = [error for error in review_errors if error.startswith("independent:")]
    if independent_review and independent_review["verdict"] == "reject":
        flags.append("independent-reviewer-reject")
        flags.extend(
            f"independent-reviewer:{item}"
            for item in independent_review["failure_categories"]
        )
    if (
        cross_review
        and independent_review
        and (cross_review["verdict"] != independent_review["verdict"])
    ):
        flags.append("reviewer-disagreement")
    return sorted(set(flags))


def _call_record(call: JsonCall | None) -> dict[str, Any] | None:
    if call is None:
        return None
    return {
        "provider_model": call.provider_model,
        "provider_revision": call.provider_revision,
        "input_tokens": call.input_tokens,
        "output_tokens": call.output_tokens,
        "approximate_cost_usd": call.approximate_cost_usd,
        "latency_ms": call.latency_ms,
    }


def _provider_options(binding: dict[str, Any]) -> dict[str, Any]:
    extra_body: dict[str, Any] = {
        "thinking": {"type": binding["thinking"]},
        "user_id": "digital-twin-factual-qa-quality-pilot",
    }
    options: dict[str, Any] = {"extra_body": extra_body}
    if binding.get("reasoning_effort"):
        options["reasoning_effort"] = binding["reasoning_effort"]
    return options


def _model_identity_stable(
    instrument: dict[str, Any], results: list[dict[str, Any]]
) -> bool:
    role_records = {
        "author": [item["author_call"] for item in results],
        "cross_reviewer": [item["cross_review_call"] for item in results],
        "independent_sensitivity_reviewer": [
            item["independent_review_call"] for item in results
        ],
    }
    for role, records in role_records.items():
        if any(record is None for record in records):
            return False
        binding = instrument["model_roles"][role]
        expected_model = binding.get("provider_model", binding.get("model"))
        expected_revision = binding.get("model_digest")
        rendered = [record for record in records if record is not None]
        if any(record["provider_model"] != expected_model for record in rendered):
            return False
        revisions = {record["provider_revision"] for record in rendered}
        if None in revisions or "" in revisions or len(revisions) != 1:
            return False
        if expected_revision is not None and revisions != {expected_revision}:
            return False
    return True


def _deepseek_cost_calculator(model: str):
    prices = DEEPSEEK_PRICES[model]

    def calculate(*, completion_response: Any) -> float:
        usage = _field(completion_response, "usage", {})
        input_tokens = int(_field(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(_field(usage, "completion_tokens", 0) or 0)
        return (
            input_tokens * prices["input"] + output_tokens * prices["output"]
        ) / 1_000_000

    return calculate


def _field(value: Any, name: str, default: Any) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _enforce_cost(instrument: dict[str, Any], cost: float) -> None:
    if cost > instrument["execution"]["cost_stop_usd"]:
        raise FactualQaPilotError(f"cost stop reached: USD {cost:.6f}")


def _normalize_question(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _near_duplicate_rate(questions: list[str]) -> float:
    near_duplicates = 0
    prior: list[set[str]] = []
    for question in questions:
        tokens = set(question.split())
        if any(_jaccard(tokens, candidate) >= 0.9 for candidate in prior):
            near_duplicates += 1
        prior.append(tokens)
    return _rate(near_duplicates, len(questions))


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 1.0


def _rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _nearest_rank(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(quantile * len(ordered) + 0.9999) - 1))
    return ordered[index]


def _assert_local_ollama_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise FactualQaPilotError("Ollama reviewer must use a loopback HTTP URL")
    if parsed.path.rstrip("/") != "/api/generate":
        raise FactualQaPilotError("unexpected Ollama generation path")
    return value


def _installed_ollama_digest(model: str, *, ollama_url: str) -> str | None:
    _assert_local_ollama_url(ollama_url)
    try:
        completed = subprocess.run(
            ["ollama", "list"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    for line in completed.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 2 and fields[0] == model:
            return fields[1]
    return None


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


def _write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
    except FileExistsError as error:
        raise FactualQaPilotError(
            f"refusing to overwrite run output: {path}"
        ) from error


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-external-provider", action="store_true")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.execute and not arguments.allow_external_provider:
        parser.error("execution requires --allow-external-provider")
    return arguments


def main() -> None:
    arguments = _arguments()
    instrument_path = (
        arguments.instrument
        if arguments.instrument.is_absolute()
        else ROOT / arguments.instrument
    )
    output_path = (
        arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    )
    load_dotenv(ROOT / ".env", override=False)
    assets = validate_assets(instrument_path)
    preflight = build_preflight(assets, ollama_url=arguments.ollama_url)
    if not arguments.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return
    if preflight["status"] != "ready-for-pilot-execution":
        raise FactualQaPilotError("pilot preflight is blocked")
    if _working_tree_dirty():
        raise FactualQaPilotError("pilot execution requires a clean working tree")
    roles = assets["instrument"]["model_roles"]
    result = asyncio.run(
        execute(
            assets,
            author_transport=DeepSeekJsonTransport(roles["author"]),
            cross_reviewer_transport=DeepSeekJsonTransport(roles["cross_reviewer"]),
            independent_reviewer_transport=OllamaJsonTransport(
                roles["independent_sensitivity_reviewer"], url=arguments.ollama_url
            ),
        )
    )
    _write_json_exclusive(output_path, result)
    summary = {
        "run_type": result["run_type"],
        "status": result["status"],
        "decision": result["summary"]["decision"],
        "machine_gates_passed": result["summary"]["machine_gates_passed"],
        "scale_authorized": False,
        "retained_cases": result["summary"]["retained_cases"],
        "quarantined_cases": result["summary"]["quarantined_cases"],
        "failed_gates": result["summary"]["failed_gates"],
        "metrics": result["summary"]["metrics"],
        "human_audit_packet_created": result["human_audit_packet"] is not None,
        "output": str(output_path.relative_to(ROOT)),
        "private_data_read": False,
        "private_data_emitted": False,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
