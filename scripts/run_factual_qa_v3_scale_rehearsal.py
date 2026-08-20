"""Run the frozen 120-case factual-QA v3 scale rehearsal.

This evaluates one dataset-construction method. Deterministic source, claim,
action, and exact-citation checks retain or quarantine cases; model reviews are
advisory diagnostics and never become ground truth.
"""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any, Awaitable, Callable, TypeVar

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_factual_qa_quality_pilot import (
    AUTHOR_SCHEMA,
    DEEPSEEK_PRICES,
    REVIEW_SCHEMA,
    DeepSeekJsonTransport,
    FactualQaPilotError,
    JsonCall,
    _author_prompt,
    _author_system_prompt,
    _call_record,
    _code_revision,
    _review_prompt,
    _review_system_prompt,
    _source_context,
    _working_tree_dirty,
    deterministic_case_checks,
    load_json,
    sha256_file,
    validate_corpus,
    validate_review,
)
from scripts.run_factual_qa_v3_oracle_pilot import (
    ANSWER_ACTION,
    BOUNDARY_ACTIONS,
    _build_product_corpus,
    _retrieval_record,
    _selected_retrieval,
    _write_json_exclusive,
)
from src.digital_twin.llm import LlmMessage
from src.digital_twin.model_policy import (
    OPENROUTER_INDEPENDENT_REVIEW_MODEL,
    require_registered_current_model,
)
from src.digital_twin.repository_freeze import (
    require_bounded_pilot_operation_allowed,
)
from services.llm import LiteLlmClient


INSTRUMENT_PATH = (
    ROOT / "research/05_evaluation/instruments/factual_qa_v3_scale_rehearsal_003.json"
)
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-scale-rehearsal-003.json"
REHEARSAL_ID = "factual-qa-v3-scale-rehearsal-003"
EXPECTED_SLICES = Counter(
    {
        "direct-text": 30,
        "paraphrase-text": 30,
        "multi-evidence-text": 18,
        "multimodal": 18,
        "no-evidence": 6,
        "ambiguous": 6,
        "cross-course-confusion": 6,
        "adversarial-integrity": 6,
    }
)
MUTATION_TYPES = (
    *("truncated-citation" for _ in range(5)),
    *("missing-citation" for _ in range(5)),
    *("invalid-claim-binding" for _ in range(5)),
    *("invalid-source-binding" for _ in range(5)),
)
PROVIDER_HEALTH_SCHEMA = {
    "type": "object",
    "required": ["status"],
    "properties": {"status": {"type": "string", "enum": ["ok"]}},
}
_T = TypeVar("_T")
_R = TypeVar("_R")


class ProviderHealthGateError(FactualQaPilotError):
    """Raised with complete accounting when a pre-bulk provider canary fails."""

    def __init__(
        self,
        stage: str,
        *,
        calls_attempted: int,
        calls_completed: int,
        approximate_cost_usd: float,
    ) -> None:
        super().__init__(f"provider health gate failed: {stage}")
        self.stage = stage
        self.calls_attempted = calls_attempted
        self.calls_completed = calls_completed
        self.approximate_cost_usd = approximate_cost_usd


class OpenRouterJsonTransport:
    """Pinned structured-output OpenRouter transport for Mistral review."""

    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding
        routing = deepcopy(binding["provider_routing"])
        self.client = LiteLlmClient(
            binding["litellm_model"],
            timeout_seconds=binding["timeout_seconds"],
            max_output_tokens=binding["max_output_tokens"],
            temperature=binding["temperature"],
            response_format={"type": "json_object"},
            provider_options={"extra_body": {"provider": routing}},
            expected_provider_model=binding["provider_model"],
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
            raise FactualQaPilotError(
                "OpenRouter Mistral returned malformed JSON"
            ) from error
        if not isinstance(value, dict):
            raise FactualQaPilotError("OpenRouter Mistral JSON root must be an object")
        usage = response.usage
        cost = (
            usage.input_tokens
            * float(self.binding["pricing_usd_per_million_input_tokens"])
            + usage.output_tokens
            * float(self.binding["pricing_usd_per_million_output_tokens"])
        ) / 1_000_000
        return JsonCall(
            value=value,
            provider_model=response.provider_model,
            provider_revision=response.provider_revision,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            approximate_cost_usd=cost,
            latency_ms=elapsed_ms,
        )


def validate_assets(instrument_path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = load_json(instrument_path)
    if instrument.get("instrument_id") != REHEARSAL_ID:
        raise FactualQaPilotError("unexpected scale rehearsal instrument")
    if instrument.get("status") not in {
        "draft-source-reviewed-pending-logic-review",
        "reviewed-pending-execution-authorization",
        "frozen-pending-execution",
    }:
        raise FactualQaPilotError("scale rehearsal instrument status is invalid")
    if instrument.get("model_leaderboard") is not False:
        raise FactualQaPilotError("scale rehearsal must not be a model leaderboard")

    execution = instrument.get("execution", {})
    expected_execution = {
        "provider_health_probe_call_limit": 2,
        "author_call_limit": 120,
        "independent_reviewer_case_call_limit": 120,
        "independent_reviewer_mutation_call_limit": 20,
        "dispute_reviewer_call_limit": 24,
        "total_provider_call_limit": 286,
        "author_concurrency": 8,
        "independent_reviewer_concurrency": 8,
        "dispute_reviewer_concurrency": 4,
        "retry_attempts": 0,
        "cost_stop_usd": 3.0,
        "clean_worktree_required": True,
        "output_overwrite_allowed": False,
    }
    if execution != expected_execution:
        raise FactualQaPilotError("scale rehearsal execution boundary drifted")

    roles = instrument.get("model_roles", {})
    expected_models = {
        "author": "deepseek-v4-flash",
        "independent_reviewer": "mistralai/mistral-small-2603",
        "dispute_reviewer": "deepseek-v4-pro",
    }
    for role, expected_model in expected_models.items():
        binding = roles.get(role, {})
        actual = binding.get("provider_model")
        require_registered_current_model(str(actual or ""))
        if actual != expected_model:
            raise FactualQaPilotError(f"scale rehearsal model drifted: {role}")
    if roles["independent_reviewer"].get("litellm_model") != (
        OPENROUTER_INDEPENDENT_REVIEW_MODEL
    ):
        raise FactualQaPilotError("OpenRouter reviewer route drifted")
    expected_routing = {
        "order": ["Mistral"],
        "allow_fallbacks": False,
        "require_parameters": True,
        "data_collection": "deny",
        "zdr": False,
    }
    if roles["independent_reviewer"].get("provider_routing") != expected_routing:
        raise FactualQaPilotError("OpenRouter provider policy drifted")
    excluded = {str(item).casefold() for item in instrument.get("excluded_models", [])}
    if not {"gemma", "claude", "qwen3:4b", "qwen3.5:4b"}.issubset(excluded):
        raise FactualQaPilotError("prohibited model exclusions drifted")

    base_record = instrument["base_corpus"]
    base_path = ROOT / base_record["path"]
    if sha256_file(base_path) != base_record["sha256"]:
        raise FactualQaPilotError("base factual-QA corpus hash drifted")
    base = load_json(base_path)
    validate_corpus(base)
    source_design_record = instrument["source_design"]
    source_design_path = ROOT / source_design_record["path"]
    if sha256_file(source_design_path) != source_design_record["sha256"]:
        raise FactualQaPilotError("scale rehearsal source design hash drifted")
    source_design = load_json(source_design_path)
    _validate_source_design(base, source_design)
    corpus = _expanded_corpus(base, source_design=source_design)
    _validate_case_design(corpus)
    return {
        "instrument": instrument,
        "instrument_path": instrument_path,
        "base_path": base_path,
        "base_sha256": base_record["sha256"],
        "source_design_path": source_design_path,
        "source_design_sha256": source_design_record["sha256"],
        "corpus": corpus,
    }


def _validate_source_design(base: dict[str, Any], design: dict[str, Any]) -> None:
    if design.get("source_design_id") != (
        "factual-qa-v3-scale-rehearsal-source-design-002"
    ):
        raise FactualQaPilotError("unexpected scale rehearsal source design")
    if design.get("status") != "prospective-reviewed":
        raise FactualQaPilotError("scale rehearsal source design is not reviewed")
    if design.get("base_corpus") != {
        "path": "research/05_evaluation/factual_qa_pilot_corpus_v1.json",
        "sha256": "dd69703503b6ed0883e19e03330f9a4d98fa9c14056a71d7bdfdee0ed4aecd31",
    }:
        raise FactualQaPilotError("source design base-corpus binding drifted")

    sources = base["source_units"]
    source_map = {source["source_unit_id"]: source for source in sources}
    text_claims = {
        claim["claim_id"]: source
        for source in sources
        if source["modality"] == "text"
        for claim in source["claims"]
    }
    quotes = design.get("text_claim_evidence_quotes", {})
    if set(quotes) != set(text_claims):
        raise FactualQaPilotError("text claim evidence-anchor coverage drifted")
    for claim_id, quote in quotes.items():
        if not isinstance(quote, str) or not quote.strip():
            raise FactualQaPilotError(f"empty evidence anchor: {claim_id}")
        if " ".join(quote.split()) not in " ".join(
            text_claims[claim_id]["evidence_text"].split()
        ):
            raise FactualQaPilotError(f"evidence anchor is not exact: {claim_id}")

    visual_sources = {
        source["source_unit_id"]: source
        for source in sources
        if source["modality"] != "text"
    }
    overrides = design.get("visual_source_overrides", [])
    if {item.get("source_unit_id") for item in overrides} != set(visual_sources):
        raise FactualQaPilotError("visual source override coverage drifted")
    visual_claim_ids: list[str] = []
    for override in overrides:
        evidence_text = str(override.get("evidence_text", ""))
        claims = override.get("claims", [])
        if not evidence_text.strip() or len(claims) != 3:
            raise FactualQaPilotError("visual source must expose three facts")
        for claim in claims:
            claim_id = str(claim.get("claim_id", ""))
            quote = str(claim.get("evidence_quote", ""))
            if not claim_id or not str(claim.get("text", "")).strip():
                raise FactualQaPilotError("visual claim is incomplete")
            if " ".join(quote.split()) not in " ".join(evidence_text.split()):
                raise FactualQaPilotError(
                    f"visual evidence anchor is not exact: {claim_id}"
                )
            visual_claim_ids.append(claim_id)
    if len(visual_claim_ids) != 18 or len(set(visual_claim_ids)) != 18:
        raise FactualQaPilotError("visual claims must be 18 distinct facts")

    multi_source_cases = design.get("multi_source_cases", [])
    if len(multi_source_cases) != 18:
        raise FactualQaPilotError("source design requires 18 multi-source cases")
    boundary = design.get("boundary_cases", {})
    if {name: len(items) for name, items in boundary.items()} != {
        "no_evidence": 6,
        "ambiguous": 6,
        "cross_course_confusion": 6,
        "adversarial_integrity": 6,
    }:
        raise FactualQaPilotError("source design boundary composition drifted")
    for item in boundary["cross_course_confusion"]:
        source = source_map.get(item.get("distractor_unit_id"))
        if source is None or source["course_id"] == item.get("course_id"):
            raise FactualQaPilotError("cross-course source design is invalid")


def _expanded_corpus(
    base: dict[str, Any], *, source_design: dict[str, Any]
) -> dict[str, Any]:
    corpus = deepcopy(base)
    sources = corpus["source_units"]
    text_quotes = source_design["text_claim_evidence_quotes"]
    visual_overrides = {
        item["source_unit_id"]: item
        for item in source_design["visual_source_overrides"]
    }
    for source in sources:
        if source["modality"] == "text":
            for claim in source["claims"]:
                claim["evidence_quote"] = text_quotes[claim["claim_id"]]
        else:
            override = visual_overrides[source["source_unit_id"]]
            source["evidence_text"] = override["evidence_text"]
            source["claims"] = deepcopy(override["claims"])
    cases: list[dict[str, Any]] = []
    serial = 1

    def add_case(**values: Any) -> None:
        nonlocal serial
        cases.append({"blueprint_id": f"fqa-r{serial:03d}", **values})
        serial += 1

    for source in sources:
        for claim in source["claims"]:
            if source["modality"] == "text":
                styles = (
                    (
                        "direct-text",
                        "Ask one concise factual question directly answered by the "
                        f"target claim: {claim['text']}",
                    ),
                    (
                        "paraphrase-text",
                        "Ask a natural student question requiring the same fact "
                        f"without copying the target claim wording: {claim['text']}",
                    ),
                )
            else:
                variant = ("direct", "paraphrased", "contextual")[
                    source["claims"].index(claim)
                ]
                styles = (
                    (
                        "multimodal",
                        "Ask one factual question about the approved "
                        f"{source['modality']} fixture, grounded only in this "
                        f"distinct visual fact; formulation {variant}: "
                        f"{claim['text']}",
                    ),
                )
            for slice_name, intent in styles:
                add_case(
                    slice=slice_name,
                    course_id=source["course_id"],
                    expected_action=ANSWER_ACTION,
                    evidence_unit_ids=[source["source_unit_id"]],
                    target_claim_ids=[claim["claim_id"]],
                    question_intent=intent,
                    difficulty="medium",
                )

    for specification in source_design["multi_source_cases"]:
        add_case(
            slice="multi-evidence-text",
            course_id=specification["course_id"],
            expected_action=ANSWER_ACTION,
            evidence_unit_ids=specification["evidence_unit_ids"],
            target_claim_ids=specification["target_claim_ids"],
            question_intent=specification["question_intent"],
            difficulty="hard",
        )
    _append_boundary_cases(
        add_case,
        boundary_design=source_design["boundary_cases"],
    )
    corpus["case_blueprints"] = cases
    corpus["corpus_id"] = "factual-qa-v3-scale-rehearsal-corpus-002"
    corpus["status"] = "prospective-synthetic-rehearsal-source-reviewed"
    return corpus


def _append_boundary_cases(
    add_case: Callable[..., None],
    *,
    boundary_design: dict[str, list[dict[str, Any]]],
) -> None:
    for specification in boundary_design["no_evidence"]:
        add_case(
            slice="no-evidence",
            course_id=specification["course_id"],
            expected_action="abstain",
            evidence_unit_ids=[],
            question_intent=specification["question_intent"],
            difficulty="hard",
        )

    for specification in boundary_design["ambiguous"]:
        add_case(
            slice="ambiguous",
            course_id=specification["course_id"],
            expected_action="clarify",
            evidence_unit_ids=[],
            question_intent=specification["question_intent"],
            difficulty="hard",
        )

    for specification in boundary_design["cross_course_confusion"]:
        distractor_id = specification["distractor_unit_id"]
        target_course = specification["course_id"]
        add_case(
            slice="cross-course-confusion",
            course_id=target_course,
            expected_action="abstain",
            evidence_unit_ids=[],
            distractor_unit_ids=[distractor_id],
            question_intent=(
                f"Ask for the fact in {distractor_id} while falsely "
                f"attributing it to {target_course}."
            ),
            difficulty="hard",
        )

    for specification in boundary_design["adversarial_integrity"]:
        add_case(
            slice="adversarial-integrity",
            course_id=specification["course_id"],
            expected_action="refuse",
            evidence_unit_ids=[],
            question_intent=specification["question_intent"],
            difficulty="hard",
        )


def _validate_case_design(corpus: dict[str, Any]) -> None:
    cases = corpus["case_blueprints"]
    sources = corpus["source_units"]
    source_map = {source["source_unit_id"]: source for source in sources}
    claim_map = {
        claim["claim_id"]: (source["source_unit_id"], claim)
        for source in sources
        for claim in source["claims"]
    }
    if len(claim_map) != 48:
        raise FactualQaPilotError("rehearsal must expose 48 distinct source claims")
    for claim_id, (source_id, claim) in claim_map.items():
        quote = str(claim.get("evidence_quote", ""))
        if " ".join(quote.split()) not in " ".join(
            source_map[source_id]["evidence_text"].split()
        ):
            raise FactualQaPilotError(
                f"claim evidence anchor is not exact: {claim_id}"
            )
    if len(cases) != 120 or Counter(case["slice"] for case in cases) != EXPECTED_SLICES:
        raise FactualQaPilotError("120-case rehearsal slice composition drifted")
    ids = [case["blueprint_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise FactualQaPilotError("rehearsal blueprint IDs are not unique")
    covered_claims: set[str] = set()
    for case in cases:
        action = case["expected_action"]
        if action not in {ANSWER_ACTION, *BOUNDARY_ACTIONS}:
            raise FactualQaPilotError("rehearsal action is invalid")
        evidence = case.get("evidence_unit_ids", [])
        if any(source_id not in source_map for source_id in evidence):
            raise FactualQaPilotError("rehearsal references an unknown source")
        if any(
            source_map[source_id]["course_id"] != case["course_id"]
            for source_id in evidence
        ):
            raise FactualQaPilotError("rehearsal answer evidence crosses courses")
        target_claims = case.get("target_claim_ids", [])
        if len(target_claims) != len(set(target_claims)):
            raise FactualQaPilotError("rehearsal target claims are duplicated")
        if any(claim_id not in claim_map for claim_id in target_claims):
            raise FactualQaPilotError("rehearsal references an unknown target claim")
        if any(
            claim_map[claim_id][0] not in evidence for claim_id in target_claims
        ):
            raise FactualQaPilotError("target claim is not bound to answer evidence")
        if action == ANSWER_ACTION and not evidence:
            raise FactualQaPilotError("answer case requires evidence")
        if action in {"abstain", "refuse"} and evidence:
            raise FactualQaPilotError("abstain/refuse case cannot carry evidence")
        if case["slice"] == "multi-evidence-text":
            if len(evidence) != 2 or len(target_claims) != 2:
                raise FactualQaPilotError(
                    "multi-evidence case must bind two claims to two sources"
                )
            if {claim_map[claim_id][0] for claim_id in target_claims} != set(
                evidence
            ):
                raise FactualQaPilotError(
                    "multi-evidence claims must cover both distinct sources"
                )
        covered_claims.update(target_claims)
    source_claims = {
        claim["claim_id"] for source in sources for claim in source["claims"]
    }
    if covered_claims != source_claims:
        raise FactualQaPilotError("rehearsal does not cover every approved claim")
    multimodal_claims = [
        case["target_claim_ids"][0]
        for case in cases
        if case["slice"] == "multimodal"
    ]
    if len(multimodal_claims) != 18 or len(set(multimodal_claims)) != 18:
        raise FactualQaPilotError("multimodal cases must cover 18 distinct facts")
    course_counts = Counter(case["course_id"] for case in cases)
    if set(course_counts) != {source["course_id"] for source in sources}:
        raise FactualQaPilotError("rehearsal course coverage drifted")
    if max(course_counts.values()) - min(course_counts.values()) > 2:
        raise FactualQaPilotError("rehearsal course distribution is imbalanced")
    cross_course = [
        case for case in cases if case["slice"] == "cross-course-confusion"
    ]
    target_courses = {case["course_id"] for case in cross_course}
    distractor_courses = {
        source_map[case["distractor_unit_ids"][0]]["course_id"]
        for case in cross_course
    }
    expected_courses = set(course_counts)
    if target_courses != expected_courses or distractor_courses != expected_courses:
        raise FactualQaPilotError(
            "cross-course cases must cover every target and distractor course"
        )


def build_preflight(assets: dict[str, Any]) -> dict[str, Any]:
    instrument = assets["instrument"]
    instrument_frozen = instrument["status"] == "frozen-pending-execution"
    deepseek_ready = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    openrouter_ready = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    from scripts.run_factual_qa_v3_oracle_pilot import EMBEDDING_ROOT

    embedding_ready = EMBEDDING_ROOT.is_dir()
    working_tree_dirty = _working_tree_dirty()
    return {
        "run_type": "factual-qa-v3-scale-rehearsal-preflight",
        "instrument_id": REHEARSAL_ID,
        "status": "ready"
        if (
            deepseek_ready
            and openrouter_ready
            and embedding_ready
            and not working_tree_dirty
            and instrument_frozen
        )
        else "blocked",
        "code_revision": _code_revision(),
        "working_tree_dirty": working_tree_dirty,
        "instrument_frozen": instrument_frozen,
        "case_count": len(assets["corpus"]["case_blueprints"]),
        "deepseek_credential_present": deepseek_ready,
        "openrouter_credential_present": openrouter_ready,
        "credential_value_emitted": False,
        "embedding_model_ready": embedding_ready,
        "author_model": instrument["model_roles"]["author"]["provider_model"],
        "independent_reviewer_model": instrument["model_roles"]["independent_reviewer"][
            "provider_model"
        ],
        "external_call_enabled": False,
        "private_data_read": False,
        "private_data_emitted": False,
        "cost_stop_usd": instrument["execution"]["cost_stop_usd"],
        "scale_to_10000_authorized": False,
    }


async def _parallel_ordered(
    items: list[_T],
    *,
    concurrency: int,
    operation: Callable[[_T], Awaitable[_R]],
) -> list[_R]:
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    semaphore = asyncio.Semaphore(concurrency)

    async def run(item: _T) -> _R:
        async with semaphore:
            return await operation(item)

    return list(await asyncio.gather(*(run(item) for item in items)))


async def _provider_health_gate(
    instrument: dict[str, Any],
    *,
    author: Any,
    independent: Any,
) -> tuple[list[JsonCall], float, list[dict[str, float | str]]]:
    system = (
        "Return only the requested JSON object. This is a synthetic-public "
        "provider availability and structured-output canary."
    )
    prompt = 'Return {"status":"ok"}.'
    stages = (
        (
            "author-health",
            author,
            instrument["model_roles"]["author"],
            "factual_qa_v3_author_provider_health",
        ),
        (
            "independent-reviewer-health",
            independent,
            instrument["model_roles"]["independent_reviewer"],
            "factual_qa_v3_reviewer_provider_health",
        ),
    )
    calls: list[JsonCall] = []
    reservations: list[dict[str, float | str]] = []
    cost = 0.0
    for stage, transport, binding, task in stages:
        reserved = _maximum_batch_cost(
            binding,
            system=system,
            prompts=[prompt],
            schema=PROVIDER_HEALTH_SCHEMA,
        )
        _enforce_cost_reservation(instrument, incurred=cost, reserved=reserved)
        reservations.append(
            {"stage": stage, "maximum_reserved_cost_usd": reserved}
        )
        try:
            call = await transport.call_json(
                system=system,
                prompt=prompt,
                task=task,
                schema=PROVIDER_HEALTH_SCHEMA,
            )
            if call.value.get("status") != "ok":
                raise FactualQaPilotError("provider canary returned a non-ok status")
        except Exception as error:
            raise ProviderHealthGateError(
                stage,
                calls_attempted=len(calls) + 1,
                calls_completed=len(calls),
                approximate_cost_usd=cost,
            ) from error
        calls.append(call)
        cost += call.approximate_cost_usd
        _enforce_cost(instrument, cost)
    return calls, cost, reservations


async def execute(assets: dict[str, Any]) -> dict[str, Any]:
    instrument = assets["instrument"]
    corpus = assets["corpus"]
    source_map = {item["source_unit_id"]: item for item in corpus["source_units"]}
    execution = instrument["execution"]
    author = DeepSeekJsonTransport(instrument["model_roles"]["author"])
    independent = OpenRouterJsonTransport(
        instrument["model_roles"]["independent_reviewer"]
    )
    dispute = DeepSeekJsonTransport(instrument["model_roles"]["dispute_reviewer"])
    started = time.perf_counter()
    health_calls, external_cost, cost_reservations = await _provider_health_gate(
        instrument,
        author=author,
        independent=independent,
    )

    import tempfile

    with tempfile.TemporaryDirectory(prefix="fqa-v3-scale-rehearsal-") as name:
        chunks_by_course, page_sources, ingestion = _build_product_corpus(
            corpus, Path(name)
        )
        retrievers, embedder = _selected_retrieval(chunks_by_course)
        blueprints = corpus["case_blueprints"]
        author_system = _author_system_prompt()
        author_inputs = [
            (
                blueprint,
                _author_prompt(
                    blueprint,
                    source_context=_source_context(
                        blueprint,
                        source_map=source_map,
                    ),
                ),
            )
            for blueprint in blueprints
        ]
        author_reserved = _maximum_batch_cost(
            instrument["model_roles"]["author"],
            system=author_system,
            prompts=[prompt for _, prompt in author_inputs],
            schema=AUTHOR_SCHEMA,
        )
        _enforce_cost_reservation(
            instrument,
            incurred=external_cost,
            reserved=author_reserved,
        )
        cost_reservations.append(
            {"stage": "author", "maximum_reserved_cost_usd": author_reserved}
        )

        async def author_one(item: tuple[dict[str, Any], str]) -> JsonCall:
            _, prompt = item
            return await author.call_json(
                system=author_system,
                prompt=prompt,
                task="factual_qa_v3_scale_rehearsal_authoring",
                schema=AUTHOR_SCHEMA,
            )

        author_calls = await _parallel_ordered(
            author_inputs,
            concurrency=execution["author_concurrency"],
            operation=author_one,
        )
        external_cost += sum(call.approximate_cost_usd for call in author_calls)
        _enforce_cost(instrument, external_cost)

        results: list[dict[str, Any]] = []
        for blueprint, author_call in zip(blueprints, author_calls, strict=True):
            authored = author_call.value
            deterministic = _deterministic_record(
                blueprint, authored, source_map=source_map
            )
            retrieval = _retrieval_record(
                blueprint,
                question=str(authored.get("question", "")),
                retriever=retrievers[blueprint["course_id"]],
                page_sources=page_sources[blueprint["course_id"]],
            )
            results.append(
                {
                    "blueprint_id": blueprint["blueprint_id"],
                    "slice": blueprint["slice"],
                    "course_id": blueprint["course_id"],
                    "expected_action": blueprint["expected_action"],
                    "evidence_unit_ids": blueprint.get("evidence_unit_ids", []),
                    "distractor_unit_ids": blueprint.get("distractor_unit_ids", []),
                    "authored_case": authored,
                    "deterministic": deterministic,
                    "retrieval": retrieval,
                    "author_call": _call_record(author_call),
                }
            )

        review_system = _review_system_prompt()
        review_inputs = [
            (
                blueprint,
                _review_prompt(
                    blueprint,
                    authored=result["authored_case"],
                    source_context=_source_context(
                        blueprint,
                        source_map=source_map,
                    ),
                ),
            )
            for blueprint, result in zip(blueprints, results, strict=True)
        ]
        review_reserved = _maximum_batch_cost(
            instrument["model_roles"]["independent_reviewer"],
            system=review_system,
            prompts=[prompt for _, prompt in review_inputs],
            schema=REVIEW_SCHEMA,
        )
        _enforce_cost_reservation(
            instrument,
            incurred=external_cost,
            reserved=review_reserved,
        )
        cost_reservations.append(
            {
                "stage": "independent-case-review",
                "maximum_reserved_cost_usd": review_reserved,
            }
        )

        async def review_one(item: tuple[dict[str, Any], str]) -> JsonCall:
            _, prompt = item
            return await independent.call_json(
                system=review_system,
                prompt=prompt,
                task="factual_qa_v3_mistral_independent_review",
                schema=REVIEW_SCHEMA,
            )

        review_started = time.perf_counter()
        review_calls = await _parallel_ordered(
            review_inputs,
            concurrency=execution["independent_reviewer_concurrency"],
            operation=review_one,
        )
        external_cost += sum(call.approximate_cost_usd for call in review_calls)
        _enforce_cost(instrument, external_cost)
        for result, call in zip(results, review_calls, strict=True):
            result["independent_review"] = validate_review(call.value)
            result["independent_review_call"] = _call_record(call)
            result["dispute_review"] = None
            result["dispute_review_call"] = None
            result["retained"] = result["deterministic"]["passed"]
            result["human_audit_priority"] = (
                not result["deterministic"]["passed"]
                or result["independent_review"]["verdict"]
                != ("accept" if result["deterministic"]["passed"] else "reject")
                or result["slice"]
                in {
                    "multimodal",
                    "multi-evidence-text",
                    "adversarial-integrity",
                }
            )

        mutation_blueprints, mutation_results = _mutation_probes(
            blueprints, results, source_map=source_map, count=20
        )
        mutation_review_inputs = [
            (
                blueprint,
                _review_prompt(
                    blueprint,
                    authored=mutation["mutated_case"],
                    source_context=_source_context(
                        blueprint,
                        source_map=source_map,
                    ),
                ),
            )
            for blueprint, mutation in zip(
                mutation_blueprints, mutation_results, strict=True
            )
        ]
        mutation_reserved = _maximum_batch_cost(
            instrument["model_roles"]["independent_reviewer"],
            system=review_system,
            prompts=[prompt for _, prompt in mutation_review_inputs],
            schema=REVIEW_SCHEMA,
        )
        _enforce_cost_reservation(
            instrument,
            incurred=external_cost,
            reserved=mutation_reserved,
        )
        cost_reservations.append(
            {
                "stage": "independent-mutation-review",
                "maximum_reserved_cost_usd": mutation_reserved,
            }
        )

        async def review_mutation(
            item: tuple[dict[str, Any], str],
        ) -> JsonCall:
            _, prompt = item
            return await independent.call_json(
                system=review_system,
                prompt=prompt,
                task="factual_qa_v3_mistral_mutation_review",
                schema=REVIEW_SCHEMA,
            )

        mutation_calls = await _parallel_ordered(
            mutation_review_inputs,
            concurrency=execution["independent_reviewer_concurrency"],
            operation=review_mutation,
        )
        external_cost += sum(call.approximate_cost_usd for call in mutation_calls)
        _enforce_cost(instrument, external_cost)
        for mutation, call in zip(mutation_results, mutation_calls, strict=True):
            mutation["review"] = validate_review(call.value)
            mutation["review_call"] = _call_record(call)
        disagreement_indexes = [
            index
            for index, result in enumerate(results)
            if result["independent_review"]["verdict"]
            != ("accept" if result["deterministic"]["passed"] else "reject")
        ][: execution["dispute_reviewer_call_limit"]]
        dispute_inputs = [
            (
                index,
                _review_prompt(
                    blueprints[index],
                    authored=results[index]["authored_case"],
                    source_context=_source_context(
                        blueprints[index],
                        source_map=source_map,
                    ),
                ),
            )
            for index in disagreement_indexes
        ]
        dispute_reserved = _maximum_batch_cost(
            instrument["model_roles"]["dispute_reviewer"],
            system=review_system,
            prompts=[prompt for _, prompt in dispute_inputs],
            schema=REVIEW_SCHEMA,
        )
        _enforce_cost_reservation(
            instrument,
            incurred=external_cost,
            reserved=dispute_reserved,
        )
        cost_reservations.append(
            {
                "stage": "dispute-review",
                "maximum_reserved_cost_usd": dispute_reserved,
            }
        )

        async def dispute_one(item: tuple[int, str]) -> tuple[int, JsonCall]:
            index, prompt = item
            call = await dispute.call_json(
                system=review_system,
                prompt=prompt,
                task="factual_qa_v3_scale_rehearsal_dispute_review",
                schema=REVIEW_SCHEMA,
            )
            return index, call

        dispute_pairs = await _parallel_ordered(
            dispute_inputs,
            concurrency=execution["dispute_reviewer_concurrency"],
            operation=dispute_one,
        )
        external_cost += sum(call.approximate_cost_usd for _, call in dispute_pairs)
        _enforce_cost(instrument, external_cost)
        for index, call in dispute_pairs:
            results[index]["dispute_review"] = validate_review(call.value)
            results[index]["dispute_review_call"] = _call_record(call)

        review_elapsed = time.perf_counter() - review_started
        elapsed = time.perf_counter() - started
        call_counts = {
            "provider_health": len(health_calls),
            "author": len(author_calls),
            "independent_case": len(review_calls),
            "independent_mutation": len(mutation_calls),
            "dispute": len(dispute_pairs),
        }
        summary = _analyze(
            instrument,
            results,
            mutation_results=mutation_results,
            ingestion=ingestion,
            external_cost=external_cost,
            review_elapsed_seconds=review_elapsed,
            elapsed_seconds=elapsed,
            call_counts=call_counts,
        )
        return {
            "run_type": REHEARSAL_ID,
            "status": summary["status"],
            "code_revision": _code_revision(),
            "working_tree_dirty": _working_tree_dirty(),
            "method_version": instrument["method_version"],
        "instrument_path": str(assets["instrument_path"].relative_to(ROOT)),
        "instrument_sha256": sha256_file(assets["instrument_path"]),
        "base_corpus_path": str(assets["base_path"].relative_to(ROOT)),
        "base_corpus_sha256": assets["base_sha256"],
        "source_design_path": str(
            assets["source_design_path"].relative_to(ROOT)
        ),
        "source_design_sha256": assets["source_design_sha256"],
            "data_boundary": instrument["case_design"]["data_boundary"],
            "private_data_read": False,
            "private_data_emitted": False,
            "call_counts": call_counts,
            "provider_health_calls": [_call_record(call) for call in health_calls],
            "cost_reservations": cost_reservations,
            "ingestion": ingestion,
            "retrieval_provider": {
                "implementation": "qwen3-hybrid-v1",
                "embedding_model": embedder.model_name,
                "embedding_revision": embedder.model_revision,
                "execution": embedder.execution,
                "model_load_seconds": embedder.model_load_seconds,
                "usage": embedder.usage_snapshot().model_dump(mode="json"),
            },
            "review_stage_elapsed_seconds": review_elapsed,
            "elapsed_seconds": elapsed,
            "summary": summary,
            "results": results,
            "reviewer_mutation_probes": mutation_results,
            "human_audit_packet": _scale_audit_packet(results, sample_size=12),
        }


def _deterministic_record(
    blueprint: dict[str, Any],
    authored: dict[str, Any],
    *,
    source_map: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    record = deterministic_case_checks(blueprint, authored, source_map=source_map)
    if blueprint.get("target_claim_ids"):
        target_ok = set(authored.get("selected_claim_ids", [])) == set(
            blueprint["target_claim_ids"]
        )
        record["checks"]["target_claims_exact"] = target_ok
        citations = authored.get("citations", [])
        claim_bindings = {
            claim["claim_id"]: (source_id, claim)
            for source_id, source in source_map.items()
            for claim in source["claims"]
        }
        record["checks"]["target_claim_citations_complete"] = all(
            any(
                isinstance(citation, dict)
                and citation.get("source_unit_id") == claim_bindings[claim_id][0]
                and " ".join(
                    claim_bindings[claim_id][1]["evidence_quote"].split()
                )
                in " ".join(str(citation.get("quote", "")).split())
                for citation in citations
            )
            for claim_id in blueprint["target_claim_ids"]
            if claim_id in claim_bindings
        ) and all(
            claim_id in claim_bindings for claim_id in blueprint["target_claim_ids"]
        )
        record["passed"] = all(record["checks"].values())
    return record


def _mutation_probes(
    blueprints: list[dict[str, Any]],
    results: list[dict[str, Any]],
    *,
    source_map: dict[str, dict[str, Any]],
    count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible = [
        (blueprint, result)
        for blueprint, result in zip(blueprints, results, strict=True)
        if blueprint["expected_action"] == ANSWER_ACTION
        and result["deterministic"]["passed"]
        and result["authored_case"].get("citations")
        and result["authored_case"].get("selected_claim_ids")
    ]
    selected = _select_mutation_pairs(eligible, count=count)
    mutation_blueprints: list[dict[str, Any]] = []
    mutations: list[dict[str, Any]] = []
    for (blueprint, result), mutation_type in zip(
        selected, MUTATION_TYPES, strict=False
    ):
        mutated = deepcopy(result["authored_case"])
        if mutation_type == "truncated-citation":
            quote = str(mutated["citations"][0]["quote"])
            words = quote.split()
            if len(words) < 2:
                raise FactualQaPilotError("citation is too short to mutate")
            mutated["citations"][0]["quote"] = (
                " ".join(words[:-1]).rstrip(".,;:!?") + "…"
            )
        elif mutation_type == "missing-citation":
            mutated["citations"] = []
        elif mutation_type == "invalid-claim-binding":
            mutated["selected_claim_ids"][0] = "invalid-claim-id"
        elif mutation_type == "invalid-source-binding":
            mutated["citations"][0]["source_unit_id"] = "invalid-source-unit-id"
        else:
            raise AssertionError("unknown mutation type")
        deterministic = _deterministic_record(blueprint, mutated, source_map=source_map)
        if deterministic["passed"]:
            raise FactualQaPilotError("reviewer mutation did not create a defect")
        mutation_blueprints.append(blueprint)
        mutations.append(
            {
                "blueprint_id": blueprint["blueprint_id"],
                "mutation_type": mutation_type,
                "mutated_case": mutated,
                "deterministic": deterministic,
                "paired_clean_review": result["independent_review"],
            }
        )
    return mutation_blueprints, mutations


def _select_mutation_pairs(
    eligible: list[tuple[dict[str, Any], dict[str, Any]]], *, count: int
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    slices = ("direct-text", "paraphrase-text", "multi-evidence-text", "multimodal")
    courses = sorted({blueprint["course_id"] for blueprint, _ in eligible})
    remaining = list(eligible)
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for index in range(min(count, len(remaining))):
        desired_slice = slices[index % len(slices)]
        desired_course = courses[(index + index // len(slices)) % len(courses)]
        match = next(
            (
                pair
                for pair in remaining
                if pair[0]["slice"] == desired_slice
                and pair[0]["course_id"] == desired_course
            ),
            None,
        )
        if match is None:
            match = next(
                (pair for pair in remaining if pair[0]["slice"] == desired_slice),
                remaining[0],
            )
        selected.append(match)
        remaining.remove(match)
    return selected


def _scale_audit_packet(
    results: list[dict[str, Any]], *, sample_size: int
) -> list[dict[str, Any]]:
    def expected_verdict(item: dict[str, Any]) -> str:
        return "accept" if item["deterministic"]["passed"] else "reject"

    def unresolved(item: dict[str, Any]) -> bool:
        if item["independent_review"]["verdict"] == expected_verdict(item):
            return False
        dispute = item.get("dispute_review")
        return dispute is None or dispute["verdict"] != expected_verdict(item)

    prioritized = sorted(
        results,
        key=lambda item: (
            item["deterministic"]["passed"],
            not unresolved(item),
            item["slice"]
            not in {"multimodal", "multi-evidence-text", "adversarial-integrity"},
            item["blueprint_id"],
        ),
    )
    required = [
        item
        for item in prioritized
        if not item["deterministic"]["passed"] or unresolved(item)
    ]
    selected = required[:sample_size]
    selected_ids = {item["blueprint_id"] for item in selected}
    seen_slices = {item["slice"] for item in selected}
    for item in prioritized:
        if len(selected) == sample_size:
            break
        if (
            item["blueprint_id"] not in selected_ids
            and item["slice"] not in seen_slices
        ):
            selected.append(item)
            selected_ids.add(item["blueprint_id"])
            seen_slices.add(item["slice"])
    for item in prioritized:
        if len(selected) == sample_size:
            break
        if item["blueprint_id"] not in selected_ids:
            selected.append(item)
            selected_ids.add(item["blueprint_id"])
    return [
        {
            "blueprint_id": item["blueprint_id"],
            "slice": item["slice"],
            "question": item["authored_case"].get("question"),
            "answer": item["authored_case"].get("answer"),
            "action": item["authored_case"].get("action"),
            "citations": item["authored_case"].get("citations"),
            "deterministic": item["deterministic"],
            "retrieval": item["retrieval"],
            "independent_review": item["independent_review"],
            "dispute_review": item.get("dispute_review"),
            "requested_checks": [
                "question_clarity",
                "answer_or_action_correctness",
                "complete_claim_support",
                "citation_lineage",
                "source_page_verification",
            ],
        }
        for item in selected
    ]


def _analyze(
    instrument: dict[str, Any],
    results: list[dict[str, Any]],
    *,
    mutation_results: list[dict[str, Any]],
    ingestion: dict[str, Any],
    external_cost: float,
    review_elapsed_seconds: float,
    elapsed_seconds: float,
    call_counts: dict[str, int],
) -> dict[str, Any]:
    total = len(results)
    answerable = [item for item in results if item["expected_action"] == ANSWER_ACTION]
    boundary = [item for item in results if item["expected_action"] in BOUNDARY_ACTIONS]
    multimodal = [item for item in results if item["slice"] == "multimodal"]
    deterministic_passes = sum(item["deterministic"]["passed"] for item in results)
    boundary_passes = sum(
        item["authored_case"].get("action") == item["expected_action"]
        for item in boundary
    )
    agreements = sum(
        item["independent_review"]["verdict"]
        == ("accept" if item["deterministic"]["passed"] else "reject")
        for item in results
    )
    all3 = sum(item["retrieval"]["all_evidence_at_3"] is True for item in answerable)
    recall5 = [item["retrieval"]["evidence_recall_at_5"] for item in answerable]
    multimodal3 = sum(
        item["retrieval"]["all_evidence_at_3"] is True for item in multimodal
    )
    leakage = sum(
        bool(
            set(item.get("distractor_unit_ids", []))
            & {
                citation.get("source_unit_id")
                for citation in item["authored_case"].get("citations", [])
                if isinstance(citation, dict)
            }
        )
        for item in results
        if item["slice"] == "cross-course-confusion"
    )
    mutation_rejects = sum(
        item["review"]["verdict"] == "reject" for item in mutation_results
    )
    paired_clean_accepts = sum(
        item["paired_clean_review"]["verdict"] == "accept" for item in mutation_results
    )
    review_latencies = [
        item["independent_review_call"]["latency_ms"] for item in results
    ] + [item["review_call"]["latency_ms"] for item in mutation_results]
    questions = [
        _normalize_question(item["authored_case"].get("question")) for item in results
    ]
    duplicate_count = len(questions) - len(set(questions))
    def expected_verdict(item: dict[str, Any]) -> str:
        return "accept" if item["deterministic"]["passed"] else "reject"
    disagreements = [
        item
        for item in results
        if item["independent_review"]["verdict"] != expected_verdict(item)
    ]
    unreviewed_disagreements = [
        item for item in disagreements if item["dispute_review"] is None
    ]
    unresolved_disagreements = [
        item
        for item in disagreements
        if item["dispute_review"] is None
        or item["dispute_review"]["verdict"] != expected_verdict(item)
    ]
    human_audit_required_ids = {
        item["blueprint_id"]
        for item in results
        if not item["deterministic"]["passed"] or item in unresolved_disagreements
    }
    author_revisions = {item["author_call"]["provider_revision"] for item in results}
    dispute_calls = [
        item["dispute_review_call"]
        for item in results
        if item["dispute_review_call"] is not None
    ]
    dispute_revisions = {call["provider_revision"] for call in dispute_calls}
    model_identity_stable = (
        all(
            item["author_call"]["provider_model"] == "deepseek-v4-flash"
            and item["independent_review_call"]["provider_model"]
            == "mistralai/mistral-small-2603"
            for item in results
        )
        and None not in author_revisions
        and "" not in author_revisions
        and len(author_revisions) == 1
        and all(
            item["review_call"]["provider_model"] == "mistralai/mistral-small-2603"
            for item in mutation_results
        )
        and all(call["provider_model"] == "deepseek-v4-pro" for call in dispute_calls)
        and (
            not dispute_calls
            or (
                None not in dispute_revisions
                and "" not in dispute_revisions
                and len(dispute_revisions) == 1
            )
        )
    )
    mutation_target = instrument["reviewer_sensitivity"]["mutation_count"]
    metrics = {
        "pdf_ingestion_rate": ingestion["pdf_ingestion_rate"],
        "source_integrity_rate": 1.0,
        "author_completion_rate": sum(bool(item["authored_case"]) for item in results)
        / total,
        "deterministic_provenance_rate": deterministic_passes / total,
        "boundary_action_rate": boundary_passes / len(boundary),
        "all_evidence_at_3": all3 / len(answerable),
        "evidence_recall_at_5": statistics.fmean(recall5),
        "multimodal_all_evidence_at_3": multimodal3 / len(multimodal),
        "independent_review_completion_rate": sum(
            bool(item["independent_review"]) for item in results
        )
        / total,
        "mutation_probe_completion_rate": len(mutation_results) / mutation_target,
        "reviewer_mutation_sensitivity": mutation_rejects / mutation_target,
        "reviewer_paired_clean_specificity": paired_clean_accepts / mutation_target,
        "deterministic_independent_agreement_rate": agreements / total,
        "independent_disagreement_count": len(disagreements),
        "unreviewed_disagreement_count": len(unreviewed_disagreements),
        "unresolved_disagreement_count": len(unresolved_disagreements),
        "dispute_review_completion_rate": (
            1.0 if not disagreements else len(dispute_calls) / len(disagreements)
        ),
        "human_audit_required_case_count": len(human_audit_required_ids),
        "reviewer_malformed_response_count": 0,
        "reviewer_p95_latency_ms": _percentile(review_latencies, 0.95),
        "review_stage_elapsed_seconds": review_elapsed_seconds,
        "end_to_end_elapsed_seconds": elapsed_seconds,
        "normalized_exact_duplicate_question_rate": duplicate_count / total,
        "cross_course_leakage_count": leakage,
        "private_data_calls": 0,
        "external_cost_usd": external_cost,
        "total_provider_calls": sum(call_counts.values()),
        "model_identity_stable": model_identity_stable,
    }
    gates = instrument["quality_gates"]
    gate_results = {
        "pdf_ingestion_rate": metrics["pdf_ingestion_rate"]
        >= gates["pdf_ingestion_rate_min"],
        "source_integrity_rate": metrics["source_integrity_rate"]
        >= gates["source_integrity_rate_min"],
        "author_completion_rate": metrics["author_completion_rate"]
        >= gates["author_completion_rate_min"],
        "deterministic_provenance_rate": metrics["deterministic_provenance_rate"]
        >= gates["deterministic_provenance_rate_min"],
        "boundary_action_rate": metrics["boundary_action_rate"]
        >= gates["boundary_action_rate_min"],
        "all_evidence_at_3": metrics["all_evidence_at_3"]
        >= gates["all_evidence_at_3_min"],
        "evidence_recall_at_5": metrics["evidence_recall_at_5"]
        >= gates["evidence_recall_at_5_min"],
        "multimodal_all_evidence_at_3": metrics["multimodal_all_evidence_at_3"]
        >= gates["multimodal_all_evidence_at_3_min"],
        "independent_review_completion_rate": metrics[
            "independent_review_completion_rate"
        ]
        >= gates["independent_review_completion_rate_min"],
        "unreviewed_disagreement_count": metrics[
            "unreviewed_disagreement_count"
        ]
        <= gates["unreviewed_disagreement_count_max"],
        "unresolved_disagreement_count": metrics["unresolved_disagreement_count"]
        <= gates["unresolved_disagreement_count_max"],
        "dispute_review_completion_rate": metrics[
            "dispute_review_completion_rate"
        ]
        >= gates["dispute_review_completion_rate_min"],
        "human_audit_required_case_count": metrics[
            "human_audit_required_case_count"
        ]
        <= gates["human_audit_required_case_count_max"],
        "mutation_probe_completion_rate": metrics["mutation_probe_completion_rate"]
        >= gates["mutation_probe_completion_rate_min"],
        "reviewer_mutation_sensitivity": metrics["reviewer_mutation_sensitivity"]
        >= gates["reviewer_mutation_sensitivity_min"],
        "reviewer_paired_clean_specificity": metrics[
            "reviewer_paired_clean_specificity"
        ]
        >= gates["reviewer_paired_clean_specificity_min"],
        "reviewer_malformed_response_count": metrics[
            "reviewer_malformed_response_count"
        ]
        <= gates["reviewer_malformed_response_count_max"],
        "reviewer_p95_latency_ms": metrics["reviewer_p95_latency_ms"]
        <= gates["reviewer_p95_latency_ms_max"],
        "review_stage_elapsed_seconds": metrics["review_stage_elapsed_seconds"]
        <= gates["review_stage_elapsed_seconds_max"],
        "end_to_end_elapsed_seconds": metrics["end_to_end_elapsed_seconds"]
        <= gates["end_to_end_elapsed_seconds_max"],
        "normalized_exact_duplicate_question_rate": metrics[
            "normalized_exact_duplicate_question_rate"
        ]
        <= gates["normalized_exact_duplicate_question_rate_max"],
        "cross_course_leakage_count": metrics["cross_course_leakage_count"]
        <= gates["cross_course_leakage_count_max"],
        "private_data_calls": metrics["private_data_calls"]
        <= gates["private_data_calls_max"],
        "external_cost_usd": metrics["external_cost_usd"]
        <= gates["external_cost_usd_max"],
        "total_provider_calls": metrics["total_provider_calls"]
        <= instrument["execution"]["total_provider_call_limit"],
        "model_identity_stable": metrics["model_identity_stable"]
        is gates["model_identity_stable_required"],
    }
    passed = all(gate_results.values())
    return {
        "status": "machine-gates-passed-human-audit-required"
        if passed
        else "machine-gates-failed-refine",
        "decision": "human-audit-required" if passed else "refine-method",
        "machine_gates_passed": passed,
        "scale_to_10000_authorized": False,
        "case_count": total,
        "answerable_cases": len(answerable),
        "boundary_cases": len(boundary),
        "retained_cases": deterministic_passes,
        "quarantined_cases": total - deterministic_passes,
        "metrics": metrics,
        "gate_results": gate_results,
        "failed_gates": sorted(
            name for name, value in gate_results.items() if not value
        ),
        "slice_counts": dict(
            sorted(Counter(item["slice"] for item in results).items())
        ),
    }


def _normalize_question(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return ordered[index]


def _enforce_cost(instrument: dict[str, Any], cost: float) -> None:
    if cost > instrument["execution"]["cost_stop_usd"]:
        raise FactualQaPilotError(f"cost stop reached: USD {cost:.6f}")


def _maximum_batch_cost(
    binding: dict[str, Any],
    *,
    system: str,
    prompts: list[str],
    schema: dict[str, Any],
) -> float:
    provider_model = binding["provider_model"]
    if provider_model in DEEPSEEK_PRICES:
        prices = DEEPSEEK_PRICES[provider_model]
    else:
        prices = {
            "input": float(binding["pricing_usd_per_million_input_tokens"]),
            "output": float(binding["pricing_usd_per_million_output_tokens"]),
        }
    schema_text = json.dumps(schema, sort_keys=True)
    maximum_output_tokens = int(binding["max_output_tokens"])
    total = 0.0
    for prompt in prompts:
        request = "\n".join((prompt, "OUTPUT JSON SCHEMA:", schema_text))
        conservative_input_tokens = len(f"{system}\n{request}".encode("utf-8"))
        total += (
            conservative_input_tokens * prices["input"]
            + maximum_output_tokens * prices["output"]
        ) / 1_000_000
    return total


def _enforce_cost_reservation(
    instrument: dict[str, Any], *, incurred: float, reserved: float
) -> None:
    ceiling = incurred + reserved
    if ceiling > instrument["execution"]["cost_stop_usd"]:
        raise FactualQaPilotError(
            f"cost reservation exceeds stop: USD {ceiling:.6f}"
        )


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-deepseek", action="store_true")
    parser.add_argument("--allow-openrouter", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    if arguments.execute and not (
        arguments.allow_deepseek and arguments.allow_openrouter
    ):
        parser.error("execution requires --allow-deepseek and --allow-openrouter")
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
    preflight = build_preflight(assets)
    if not arguments.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return
    require_bounded_pilot_operation_allowed(REHEARSAL_ID)
    if preflight["status"] != "ready":
        raise FactualQaPilotError("scale rehearsal preflight is blocked")
    try:
        result = asyncio.run(execute(assets))
    except Exception as error:
        health_failure = (
            error if isinstance(error, ProviderHealthGateError) else None
        )
        _write_json_exclusive(
            output_path,
            {
                "run_type": REHEARSAL_ID,
                "status": "invalid-execution",
                "decision": "refine-method",
                "code_revision": _code_revision(),
                "working_tree_dirty": _working_tree_dirty(),
                "instrument_path": str(instrument_path.relative_to(ROOT)),
                "instrument_sha256": sha256_file(instrument_path),
                "data_boundary": "synthetic-public",
                "private_data_read": False,
                "private_data_emitted": False,
                "failure_category": type(error).__name__,
                "failure_detail": str(error),
                "failure_stage": health_failure.stage if health_failure else None,
                "provider_calls_attempted": (
                    health_failure.calls_attempted if health_failure else None
                ),
                "provider_calls_completed": (
                    health_failure.calls_completed if health_failure else None
                ),
                "approximate_cost_usd": (
                    health_failure.approximate_cost_usd if health_failure else None
                ),
                "provider_call_accounting_complete": health_failure is not None,
                "scale_to_10000_authorized": False,
            },
        )
        raise
    _write_json_exclusive(output_path, result)
    print(
        json.dumps(
            {
                "status": result["status"],
                "decision": result["summary"]["decision"],
                "machine_gates_passed": result["summary"]["machine_gates_passed"],
                "failed_gates": result["summary"]["failed_gates"],
                "metrics": result["summary"]["metrics"],
                "output": str(output_path.relative_to(ROOT)),
                "scale_to_10000_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
