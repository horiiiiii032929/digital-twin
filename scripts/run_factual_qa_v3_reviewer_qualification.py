"""Qualify the strict factual-QA reviewer on deterministic paired defects."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import subprocess
import time
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from services.llm import LiteLlmClient
from src.digital_twin.llm import LlmMessage
from src.digital_twin.model_policy import require_registered_current_model
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

from scripts.run_factual_qa_quality_pilot import REVIEW_SCHEMA, validate_review
from scripts.run_factual_qa_v3_scale_rehearsal import (
    PROVIDER_HEALTH_SCHEMA,
    _strict_review_prompt,
    _strict_review_system_prompt,
)


ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_PATH = ROOT / "research/05_evaluation/instruments/factual_qa_v3_reviewer_qualification_006.json"
DEFAULT_OUTPUT = ROOT / "reports/generated/factual-qa-v3-reviewer-qualification-006.json"
QUALIFICATION_ID = "factual-qa-v3-reviewer-qualification-006"
QUALIFICATION_CONFIGS = {
    QUALIFICATION_ID: {
        "namespace": "rq006",
        "value_offset": 0,
        "provider_model": "mistralai/mistral-small-2603",
        "provider_routing": {
            "order": ["Mistral"],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "allow",
            "zdr": False,
        },
        "cost_stop_usd": 0.5,
        "output": DEFAULT_OUTPUT,
    },
    "factual-qa-v3-reviewer-qualification-007": {
        "namespace": "rq007",
        "value_offset": 700,
        "provider_model": "qwen/qwen3.7-plus",
        "provider_routing": {
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "allow",
            "zdr": False,
        },
        "cost_stop_usd": 0.1,
        "output": ROOT
        / "reports/generated/factual-qa-v3-reviewer-qualification-007.json",
    },
}
MUTATION_TYPES = (
    *(["missing-citation"] * 4),
    *(["truncated-citation"] * 4),
    *(["paraphrased-citation"] * 4),
    *(["extra-supported-claim"] * 4),
    *(["invalid-claim-binding"] * 4),
    *(["invalid-source-binding"] * 4),
)


class ReviewerQualificationError(ValueError):
    """Raised when the bounded reviewer-qualification contract drifts."""


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReviewerQualificationError(f"expected JSON object: {path}")
    return value


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, check=True,
        capture_output=True, text=True,
    ).stdout.strip())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_instrument(path: Path = INSTRUMENT_PATH) -> dict[str, Any]:
    instrument = _load_json(path)
    qualification_id = instrument.get("instrument_id")
    if qualification_id not in QUALIFICATION_CONFIGS:
        raise ReviewerQualificationError("unexpected reviewer qualification ID")
    config = QUALIFICATION_CONFIGS[qualification_id]
    if instrument.get("status") not in {
        "reviewed-pending-execution-authorization", "frozen-pending-execution"
    }:
        raise ReviewerQualificationError("invalid reviewer qualification status")
    if instrument.get("model_leaderboard") is not False:
        raise ReviewerQualificationError("qualification cannot be a leaderboard")
    fixture = instrument.get("fixture", {})
    if fixture.get("pair_count") != 24 or fixture.get("mutation_types") != dict(Counter(MUTATION_TYPES)):
        raise ReviewerQualificationError("paired fixture design drifted")
    if fixture.get("namespace", "rq006") != config["namespace"]:
        raise ReviewerQualificationError("paired fixture namespace drifted")
    if fixture.get("value_offset", 0) != config["value_offset"]:
        raise ReviewerQualificationError("paired fixture value offset drifted")
    execution = instrument.get("execution", {})
    if execution != {
        "provider_health_call_limit": 1, "clean_review_call_limit": 24,
        "mutation_review_call_limit": 24, "total_provider_call_limit": 49,
        "batch_size": 8, "retry_attempts": 0,
        "cost_stop_usd": config["cost_stop_usd"],
        "clean_worktree_required": True, "checkpoint_after_each_batch": True,
        "output_overwrite_allowed": False,
    }:
        raise ReviewerQualificationError("execution limits drifted")
    binding = instrument.get("model_role", {})
    require_registered_current_model(str(binding.get("provider_model", "")))
    if binding.get("provider_model") != config["provider_model"]:
        raise ReviewerQualificationError("reviewer model drifted")
    if binding.get("provider_routing") != config["provider_routing"]:
        raise ReviewerQualificationError("provider routing drifted")
    return instrument


def build_pairs(qualification_id: str = QUALIFICATION_ID) -> list[dict[str, Any]]:
    if qualification_id not in QUALIFICATION_CONFIGS:
        raise ReviewerQualificationError("unsupported reviewer qualification ID")
    config = QUALIFICATION_CONFIGS[qualification_id]
    namespace = str(config["namespace"])
    value_offset = int(config["value_offset"])
    pairs: list[dict[str, Any]] = []
    modalities = ("text", "code", "table", "diagram")
    for index, mutation_type in enumerate(MUTATION_TYPES, start=1):
        course_id = f"synthetic-course-{((index - 1) % 4) + 1}"
        source_id = f"{namespace}-source-{index:02d}"
        distractor_id = f"{namespace}-distractor-{index:02d}"
        marker, auxiliary = f"M{index:02d}", f"A{index:02d}"
        if qualification_id == QUALIFICATION_ID:
            target_quote = f"Marker {marker} uses threshold {100 + index} units."
            extra_quote = f"Marker {auxiliary} uses threshold {200 + index} units."
            question = f"What threshold does marker {marker} use?"
        else:
            value = value_offset + index
            target_templates = (
                f"Rule {marker} sets a limit of {value} credits.",
                f"Mapping {marker} links node N{value} to node P{value + 3}.",
                f"Sequence {marker} places phase S{index} before phase T{index}.",
                f"Exception {marker} applies only when flag F{value % 17} is active.",
            )
            target_quote = target_templates[(index - 1) % len(target_templates)]
            extra_quote = (
                f"Auxiliary rule {auxiliary} reserves {value + 100} credits."
            )
            question = f"What fact is specified by rule {marker}?"
        source = {
            "source_unit_id": source_id, "course_id": course_id,
            "modality": modalities[(index - 1) % len(modalities)],
            "source_truth": f"{target_quote} {extra_quote}",
            "claims": [
                {"claim_id": f"{namespace}-claim-{index:02d}", "text": target_quote, "evidence_quote": target_quote},
                {"claim_id": f"{namespace}-extra-{index:02d}", "text": extra_quote, "evidence_quote": extra_quote},
            ],
        }
        if qualification_id == QUALIFICATION_ID:
            distractor_quote = (
                f"Distractor D{index:02d} uses threshold {300 + index} units."
            )
        else:
            distractor_quote = (
                f"Distractor D{index:02d} uses value {value_offset + 300 + index}."
            )
        distractor = {
            "source_unit_id": distractor_id,
            "course_id": f"synthetic-course-{(index % 4) + 1}", "modality": "text",
            "source_truth": distractor_quote,
            "claims": [{"claim_id": f"{namespace}-distractor-claim-{index:02d}", "text": distractor_quote, "evidence_quote": distractor_quote}],
        }
        target_claim_id = source["claims"][0]["claim_id"]
        blueprint = {
            "blueprint_id": f"{namespace}-pair-{index:02d}", "slice": source["modality"],
            "course_id": course_id, "expected_action": "answer",
            "target_claim_ids": [target_claim_id], "evidence_unit_ids": [source_id],
            "distractor_unit_ids": [distractor_id],
            "intent": f"Ask for the threshold used by marker {marker}.",
        }
        clean = {
            "question": question,
            "answer": target_quote, "action": "answer",
            "selected_claim_ids": [target_claim_id],
            "citations": [{"source_unit_id": source_id, "quote": target_quote}],
        }
        mutated = deepcopy(clean)
        if mutation_type == "missing-citation":
            mutated["citations"] = []
        elif mutation_type == "truncated-citation":
            mutated["citations"][0]["quote"] = target_quote.rsplit(" ", 1)[0]
        elif mutation_type == "paraphrased-citation":
            if qualification_id == QUALIFICATION_ID:
                mutated["citations"][0]["quote"] = (
                    f"The threshold for {marker} is {100 + index}."
                )
            else:
                mutated["citations"][0]["quote"] = (
                    f"Rule {marker} conveys the same fact without an exact quotation."
                )
        elif mutation_type == "extra-supported-claim":
            mutated["selected_claim_ids"].append(source["claims"][1]["claim_id"])
            mutated["citations"].append({"source_unit_id": source_id, "quote": extra_quote})
        elif mutation_type == "invalid-claim-binding":
            invalid_namespace = "" if qualification_id == QUALIFICATION_ID else f"{namespace}-"
            mutated["selected_claim_ids"][0] = (
                f"{invalid_namespace}invalid-claim-{index:02d}"
            )
        elif mutation_type == "invalid-source-binding":
            mutated["citations"][0] = {"source_unit_id": distractor_id, "quote": distractor_quote}
        pairs.append({
            "pair_id": blueprint["blueprint_id"], "mutation_type": mutation_type,
            "blueprint": blueprint, "source": source, "distractor": distractor,
            "clean_case": clean, "mutated_case": mutated,
        })
    return pairs


def deterministic_valid(pair: dict[str, Any], authored: dict[str, Any]) -> bool:
    blueprint = pair["blueprint"]
    sources = {pair["source"]["source_unit_id"]: pair["source"], pair["distractor"]["source_unit_id"]: pair["distractor"]}
    if set(authored.get("selected_claim_ids", [])) != set(blueprint["target_claim_ids"]):
        return False
    citations = authored.get("citations", [])
    for claim_id in blueprint["target_claim_ids"]:
        claim = next(item for item in pair["source"]["claims"] if item["claim_id"] == claim_id)
        if not any(
            citation.get("source_unit_id") == pair["source"]["source_unit_id"]
            and " ".join(claim["evidence_quote"].split()) in " ".join(citation.get("quote", "").split())
            for citation in citations
        ):
            return False
    return all(
        citation.get("source_unit_id") in sources
        and " ".join(citation.get("quote", "").split()) in " ".join(sources[citation["source_unit_id"]]["source_truth"].split())
        for citation in citations
    )


def build_preflight(instrument: dict[str, Any], output_path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    qualification_id = str(instrument["instrument_id"])
    frozen = instrument["status"] == "frozen-pending-execution"
    credential_name = str(
        instrument["model_role"]["credential_environment_variable"]
    )
    credential = bool(os.getenv(credential_name, "").strip())
    dirty = _working_tree_dirty()
    available = not output_path.exists()
    return {
        "run_type": "factual-qa-v3-reviewer-qualification-preflight",
        "instrument_id": qualification_id,
        "status": "ready" if frozen and credential and not dirty and available else "blocked",
        "code_revision": _code_revision(), "instrument_frozen": frozen,
        "working_tree_dirty": dirty, "credential_present": credential,
        "output_available": available, "pair_count": 24,
        "provider_call_limit": instrument["execution"]["total_provider_call_limit"],
        "cost_stop_usd": instrument["execution"]["cost_stop_usd"],
        "external_call_enabled": False, "private_data_read": False,
        "scale_to_10000_authorized": False,
    }


class DurableReviewerTransport:
    def __init__(self, binding: dict[str, Any]) -> None:
        self.binding = binding
        self.client = LiteLlmClient(
            binding["litellm_model"], timeout_seconds=binding["timeout_seconds"],
            max_output_tokens=binding["max_output_tokens"], temperature=binding["temperature"],
            response_format={"type": "json_object"},
            provider_options={"extra_body": {"provider": deepcopy(binding["provider_routing"])}},
            expected_provider_model=binding["provider_model"],
        )

    async def call(self, *, system: str, prompt: str, schema: dict[str, Any], task: str) -> dict[str, Any]:
        request = "\n".join((prompt, "OUTPUT JSON SCHEMA:", json.dumps(schema, sort_keys=True)))
        started = time.perf_counter()
        try:
            response = await self.client.chat(
                [LlmMessage(role="system", content=system), LlmMessage(role="user", content=request)], task=task,
            )
        except Exception as error:
            return {"status": "provider-error", "error_type": type(error).__name__, "latency_ms": (time.perf_counter() - started) * 1000, "provider_response_received": False, "review": None, "call": None}
        latency_ms = (time.perf_counter() - started) * 1000
        usage = response.usage
        cost = (usage.input_tokens * float(self.binding["pricing_usd_per_million_input_tokens"]) + usage.output_tokens * float(self.binding["pricing_usd_per_million_output_tokens"])) / 1_000_000
        call = {"provider_model": response.provider_model, "provider_revision": response.provider_revision, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "approximate_cost_usd": cost, "latency_ms": latency_ms}
        try:
            value = json.loads(response.content)
            review = value if schema is PROVIDER_HEALTH_SCHEMA else validate_review(value)
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            return {"status": "malformed-review", "error_type": type(error).__name__, "content_sha256": hashlib.sha256(response.content.encode("utf-8")).hexdigest(), "latency_ms": latency_ms, "provider_response_received": True, "review": None, "call": call}
        return {"status": "complete", "error_type": None, "latency_ms": latency_ms, "provider_response_received": True, "review": review, "call": call}


def _write_initial(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _write_checkpoint(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists():
        raise ReviewerQualificationError("stale checkpoint temporary exists")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _maximum_reserved_cost(
    binding: dict[str, Any], *, system: str, prompts: list[str]
) -> float:
    input_tokens = sum(
        (len(system) + len(prompt) + 1023) // 4 + 256 for prompt in prompts
    )
    output_tokens = len(prompts) * int(binding["max_output_tokens"])
    return (
        input_tokens * float(binding["pricing_usd_per_million_input_tokens"])
        + output_tokens * float(binding["pricing_usd_per_million_output_tokens"])
    ) / 1_000_000


async def execute(
    instrument: dict[str, Any],
    *,
    instrument_path: Path = INSTRUMENT_PATH,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    qualification_id = str(instrument["instrument_id"])
    pairs = build_pairs(qualification_id)
    if not all(deterministic_valid(pair, pair["clean_case"]) and not deterministic_valid(pair, pair["mutated_case"]) for pair in pairs):
        raise ReviewerQualificationError("deterministic pair validity drifted")
    system = _strict_review_system_prompt()
    work: list[dict[str, Any]] = []
    for pair in pairs:
        context = {"approved_sources": [pair["source"]], "distractors": [pair["distractor"]]}
        for condition in ("clean", "mutated"):
            authored = pair[f"{condition}_case"]
            work.append({"pair_id": pair["pair_id"], "condition": condition, "mutation_type": pair["mutation_type"], "prompt": _strict_review_prompt(pair["blueprint"], authored=authored, source_context=context)})
    maximum_reserved_cost = _maximum_reserved_cost(
        instrument["model_role"],
        system=system,
        prompts=["Provider readiness canary.", *(item["prompt"] for item in work)],
    )
    if maximum_reserved_cost > instrument["execution"]["cost_stop_usd"]:
        raise ReviewerQualificationError("maximum call reservation exceeds cost stop")
    state: dict[str, Any] = {
        "run_type": qualification_id, "status": "running", "code_revision": _code_revision(),
        "instrument_sha256": _sha256(instrument_path), "data_boundary": "synthetic-public",
        "private_data_read": False, "private_data_emitted": False,
        "scale_to_10000_authorized": False,
        "maximum_reserved_cost_usd": maximum_reserved_cost,
        "calls_attempted": 0,
        "calls_with_provider_response": 0, "results": [],
    }
    _write_initial(output_path, state)
    transport = DurableReviewerTransport(instrument["model_role"])
    canary = await transport.call(
        system="Return JSON with status ok only.",
        prompt="Provider readiness canary.",
        schema=PROVIDER_HEALTH_SCHEMA,
        task=f"{qualification_id}_canary",
    )
    state["calls_attempted"] = 1
    state["calls_with_provider_response"] = int(canary["provider_response_received"])
    state["canary"] = canary
    if canary["status"] != "complete" or canary["review"] != {"status": "ok"}:
        state.update({
            "status": "invalid-execution",
            "decision": instrument["decision_rule"]["any_gate_fails"],
        })
        _write_checkpoint(output_path, state)
        return state
    _write_checkpoint(output_path, state)
    started = time.perf_counter()
    batch_size = instrument["execution"]["batch_size"]
    for offset in range(0, len(work), batch_size):
        batch = work[offset:offset + batch_size]
        outcomes = await asyncio.gather(
            *(
                transport.call(
                    system=system,
                    prompt=item["prompt"],
                    schema=REVIEW_SCHEMA,
                    task=f"{qualification_id}_review",
                )
                for item in batch
            )
        )
        for item, outcome in zip(batch, outcomes, strict=True):
            state["results"].append({key: value for key, value in item.items() if key != "prompt"} | {"outcome": outcome})
        state["calls_attempted"] += len(batch)
        state["calls_with_provider_response"] += sum(bool(outcome["provider_response_received"]) for outcome in outcomes)
        state["completed_review_records"] = len(state["results"])
        _write_checkpoint(output_path, state)
    results = state["results"]
    clean = [item for item in results if item["condition"] == "clean"]
    mutated = [item for item in results if item["condition"] == "mutated"]
    errors = [item for item in results if item["outcome"]["status"] != "complete"]
    clean_accepts = sum(item["outcome"]["status"] == "complete" and item["outcome"]["review"]["verdict"] == "accept" for item in clean)
    mutation_rejects = sum(item["outcome"]["status"] == "complete" and item["outcome"]["review"]["verdict"] == "reject" for item in mutated)
    type_sensitivity = {kind: sum(item["outcome"]["status"] == "complete" and item["outcome"]["review"]["verdict"] == "reject" for item in mutated if item["mutation_type"] == kind) / 4 for kind in sorted(set(MUTATION_TYPES))}
    calls = [item["outcome"]["call"] for item in results if item["outcome"]["call"] is not None]
    if canary["call"] is not None:
        calls.append(canary["call"])
    latencies = [float(call["latency_ms"]) for call in calls]
    revisions = {
        call["provider_revision"]
        for call in calls
        if call["provider_revision"] not in {None, ""}
    }
    model_stable = (
        bool(calls)
        and all(
            call["provider_model"] == instrument["model_role"]["provider_model"]
            for call in calls
        )
        and len(revisions) <= 1
    )
    cost = sum(float(call["approximate_cost_usd"]) for call in calls)
    metrics = {
        "review_completion_rate": (len(results) - len(errors)) / 48,
        "clean_specificity": clean_accepts / 24, "mutation_sensitivity": mutation_rejects / 24,
        "per_mutation_type_sensitivity": type_sensitivity,
        "malformed_or_provider_error_count": len(errors),
        "reviewer_p95_latency_ms": statistics.quantiles(latencies, n=100, method="inclusive")[94],
        "model_identity_stable": model_stable, "external_cost_usd": cost,
        "private_data_calls": 0, "provider_calls": state["calls_attempted"],
        "elapsed_seconds": time.perf_counter() - started,
    }
    gates = instrument["quality_gates"]
    gate_results = {
        "review_completion_rate": metrics["review_completion_rate"] >= gates["review_completion_rate_min"],
        "clean_specificity": metrics["clean_specificity"] >= gates["clean_specificity_min"],
        "mutation_sensitivity": metrics["mutation_sensitivity"] >= gates["mutation_sensitivity_min"],
        "per_mutation_type_sensitivity": min(type_sensitivity.values()) >= gates["per_mutation_type_sensitivity_min"],
        "malformed_or_provider_error_count": len(errors) <= gates["malformed_or_provider_error_count_max"],
        "reviewer_p95_latency_ms": metrics["reviewer_p95_latency_ms"] <= gates["reviewer_p95_latency_ms_max"],
        "model_identity_stable": model_stable,
        "external_cost_usd": cost <= gates["external_cost_usd_max"],
        "private_data_calls": metrics["private_data_calls"] <= gates["private_data_calls_max"],
    }
    decision_rule = instrument["decision_rule"]
    state.update({
        "status": "completed",
        "decision": (
            decision_rule["all_gates_pass"]
            if all(gate_results.values())
            else decision_rule["any_gate_fails"]
        ),
        "metrics": metrics,
        "gate_results": gate_results,
        "failed_gates": [
            name for name, passed in gate_results.items() if not passed
        ],
    })
    _write_checkpoint(output_path, state)
    return state


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", type=Path, default=INSTRUMENT_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--allow-openrouter", action="store_true")
    arguments = parser.parse_args()
    if arguments.execute and not arguments.allow_openrouter:
        parser.error("execution requires --allow-openrouter")
    return arguments


def main() -> None:
    arguments = _arguments()
    instrument_path = arguments.instrument if arguments.instrument.is_absolute() else ROOT / arguments.instrument
    if arguments.output is None:
        instrument_preview = _load_json(instrument_path)
        config = QUALIFICATION_CONFIGS.get(instrument_preview.get("instrument_id"))
        if config is None:
            raise ReviewerQualificationError("unexpected reviewer qualification ID")
        output_path = Path(config["output"])
    else:
        output_path = (
            arguments.output if arguments.output.is_absolute()
            else ROOT / arguments.output
        )
    load_dotenv(ROOT / ".env", override=False)
    instrument = validate_instrument(instrument_path)
    preflight = build_preflight(instrument, output_path)
    if not arguments.execute:
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return
    qualification_id = str(instrument["instrument_id"])
    require_bounded_pilot_operation_allowed(qualification_id)
    if preflight["status"] != "ready":
        raise ReviewerQualificationError("reviewer qualification preflight blocked")
    result = asyncio.run(
        execute(
            instrument,
            instrument_path=instrument_path,
            output_path=output_path,
        )
    )
    print(json.dumps({"run_type": result["run_type"], "status": result["status"], "decision": result["decision"], "metrics": result.get("metrics"), "failed_gates": result.get("failed_gates")}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
