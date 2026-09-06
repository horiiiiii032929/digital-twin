"""Fresh development trajectories through the production application factory.

Contract smoke deliberately injects malformed model output; it is never live
evidence. Paid execution requires a separately recorded bounded authorization.
Synthetic course setup is injected: this is not an ingestion/UI acceptance run.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from contextvars import ContextVar
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

from services.llm import OpenAiResponsesClient
from src.digital_twin.evaluation.autonomy_contract import AutonomySystemManifestV1
from src.digital_twin.evaluation.autonomy_learner_driver import (
    DriverScheduleV1, run_hidden_state_learner_case,
)
from src.digital_twin.evaluation.autonomy_learning_scoring import (
    score_hidden_state_case,
)
from src.digital_twin.evaluation.autonomy_product_adapter import StudentProductAutonomyAdapterV1
from src.digital_twin.evaluation.learner_simulator import PERSONAS, SimulatorFamily
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1, TextRealisingLearnerV1
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import (
    LlmBudgetExceededError, LlmClient, LlmConfigurationError, LlmIdentityDriftError,
    LlmMalformedResponseError, LlmMessage, LlmResponse,
)
from src.digital_twin.model_policy import OPENAI_MODEL_PRICING_USD_PER_MILLION
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from scripts.run_governed_full_autonomy_v2_1_hidden_state_learner_014 import build_case

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "final-profile-live-longitudinal-development-001"
PROFILE = ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json"
MODEL = "gpt-5.6-luna"
EXPECTED_PROFILE_SHA256 = "7a2465951fecb0c1ad20cc9daad14d92499f7838ba13c50dddd6acc2f8a8aea3"
CONDITIONS = ("t1-v2-reactive", "t1-v2-autonomous")
ORIGIN = datetime(2026, 9, 7, tzinfo=UTC)
CASE_CONTEXT: ContextVar[str] = ContextVar("longitudinal_case", default="unassigned")

# New development-only synthetic facts, not a reused sealed confirmation set.
CARDS = (
    ConceptCardV1("concept-checksum-audit", "checksum audit",
        "Checksum audit computes a digest before archival, stores the digest separately, and compares a newly computed digest during retrieval to detect altered bytes.",
        "Explain how checksum audit detects altered archived bytes."),
    ConceptCardV1("concept-calendar-sharding", "calendar sharding",
        "Calendar sharding partitions event records by month, routes each event to its month partition, and searches all intersecting month partitions for a date interval.",
        "Explain how calendar sharding searches a date interval."),
    ConceptCardV1("concept-escrow-counter", "escrow counter",
        "An escrow counter assigns each replica a spending allowance, rejects decrements above the local allowance, and transfers allowance between replicas without changing the global total.",
        "Explain how an escrow counter prevents excess decrements."),
    ConceptCardV1("concept-prefix-compression", "prefix compression",
        "Prefix compression stores the common beginning of sorted keys once, records the remaining suffix for each key, and reconstructs each key by joining its prefix and suffix.",
        "Explain how prefix compression reconstructs a key."),
)


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


class RecordedRunClient:
    """Durable attempt ledger and conservative process-wide reservation cap.

The bound charges every admitted call its full reserved allowance, even when
reported cost is lower or absent. Concurrent histories cannot overspend the
configured allowance, and app restarts do not reset it. No run-level resume.
"""

    def __init__(self, client: LlmClient, ledger: Path, *, maximum_calls: int,
                 maximum_cost_usd: float, network_mode: str,
                 reservation_usd: float = 0.01, maximum_payload_bytes: int = 20_000, expected_model: str = MODEL, max_output_tokens: int = 500, reasoning_effort: str = "low", experimental_sol_enabled: bool = False):
        if (isinstance(maximum_calls, bool) or maximum_calls < 1
                or not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0
                or not math.isfinite(reservation_usd) or reservation_usd <= 0):
            raise ValueError("Positive finite call/cost limits are required")
        self.client, self.ledger = client, ledger
        self.expected_model = expected_model
        if isinstance(client, OpenAiResponsesClient) and (client.max_output_tokens != max_output_tokens
                or client.model != expected_model or client.reasoning_effort != reasoning_effort):
            raise ValueError("recorded serializer and provider output caps must match; model and reasoning must also match")
        self.maximum_calls, self.maximum_cost_usd = maximum_calls, maximum_cost_usd
        self.reservation_usd, self.maximum_payload_bytes = reservation_usd, maximum_payload_bytes
        self.network_mode = network_mode
        self.lock = asyncio.Lock()
        self.attempts = 0
        self.reserved_usd = 0.0
        self.records: list[dict] = []
        self.stopped = False
        # This serializer includes the response schema as well as messages.
        self.serializer = OpenAiResponsesClient(expected_model, max_output_tokens=max_output_tokens, reasoning_effort=reasoning_effort, experimental_sol_enabled=experimental_sol_enabled)
        input_price, output_price = OPENAI_MODEL_PRICING_USD_PER_MILLION[expected_model]
        # One token per UTF-8 byte plus explicit framing headroom. Fail before
        # calls if the frozen price/size assumptions exceed the reservation.
        bound = ((maximum_payload_bytes + 4096) * input_price + max_output_tokens * output_price) / 1_000_000
        if bound > reservation_usd:
            raise ValueError("Reservation is below the conservative request cost bound")

    def conservative_request_cost_usd(self, messages: list[LlmMessage], task: str) -> float:
        return self.serializer.conservative_request_cost_usd(messages, task)

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        payload = self.serializer._payload(messages, task)
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        async with self.lock:
            if (self.stopped or self.attempts >= self.maximum_calls
                    or self.reserved_usd + self.reservation_usd > self.maximum_cost_usd + 1e-12
                    or len(encoded) > self.maximum_payload_bytes):
                self.stopped = True
                _append(self.ledger, {"status": "blocked-before-call", "case": CASE_CONTEXT.get(),
                    "task": task, "reason": "budget-or-payload-bound", "payload_bytes": len(encoded)})
                raise LlmBudgetExceededError()
            self.attempts += 1
            self.reserved_usd += self.reservation_usd
            row = {"attempt": self.attempts, "case": CASE_CONTEXT.get(), "task": task,
                "requested_model": self.expected_model, "network_mode": self.network_mode,
                "requested_reasoning_effort": self.serializer.reasoning_effort, "requested_output_cap": self.serializer.max_output_tokens,
                "request_sha256": hashlib.sha256(encoded).hexdigest(),
                "reserved_usd": self.reservation_usd}
            _append(self.ledger, {**row, "status": "started", "messages": [m.model_dump() for m in messages]})
        started = time.perf_counter()
        try:
            response = await self.client.chat(messages, task)
            # Retain billed evidence even when identity or cost checks reject
            # this response. Rejection must not erase the provider's usage.
            row.update(returned_model=response.provider_model,
                returned_revision=response.provider_revision, usage=response.usage.model_dump(),
                content=response.content)
            if response.provider_model != self.expected_model:
                raise LlmIdentityDriftError(provider_model=response.provider_model,
                    provider_revision=response.provider_revision)
            cost = response.usage.approximate_cost_usd
            if cost is None or not math.isfinite(cost) or cost < 0 or cost > self.reservation_usd:
                self.stopped = True
                raise ValueError("Reported cost violates reservation contract")
            row.update(status="completed", returned_model=response.provider_model,
                returned_revision=response.provider_revision, usage=response.usage.model_dump(),
                content=response.content)
            return response
        except BaseException as error:
            row.update(status="failed", error_code=getattr(error, "code", type(error).__name__),
                returned_model=getattr(error, "provider_model", None) or row.get("returned_model"),
                returned_revision=getattr(error, "provider_revision", None) or row.get("returned_revision"))
            row["failure_stage"] = getattr(error, "stage", None)
            row["failure_diagnostics"] = getattr(error, "diagnostics", None)
            usage = getattr(error, "usage", None)
            if usage is not None:
                row["usage"] = usage.model_dump()
            # Stop after an unpriced/unknown failure; reserved allowance is retained.
            if (usage is None or usage.approximate_cost_usd is None
                    or not math.isfinite(usage.approximate_cost_usd)
                    or usage.approximate_cost_usd > self.reservation_usd):
                self.stopped = True
            raise
        finally:
            row["latency_ms"] = (time.perf_counter() - started) * 1000
            self.records.append(row)
            _append(self.ledger, row)


class ContractFailureClient:
    """Explicitly test provider-failure handling, not model capability."""

    async def chat(self, messages: list[LlmMessage], task: str) -> LlmResponse:
        raise LlmMalformedResponseError(stage="injected-contract-smoke", provider_model=MODEL,
            usage=GenerationUsage(input_tokens=0, output_tokens=0, approximate_cost_usd=0))


def validation_manifest() -> dict:
    if hashlib.sha256(PROFILE.read_bytes()).hexdigest() != EXPECTED_PROFILE_SHA256:
        raise ValueError("Selected profile changed; review and version this development binding")
    profile = json.loads(PROFILE.read_text())
    return {"program_id": PROGRAM_ID, "stage": "development-only", "profile_id": profile["profile_id"],
        "profile_sha256": hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
        "dataset_sha256": _digest([c.__dict__ for c in CARDS]), "model": MODEL,
        "conditions": list(CONDITIONS), "seed": 4107,
        "setup_boundary": "synthetic release fixture; not ingestion or UI qualification",
        "live_authorized": False, "remaining": ["fresh profile-adherence comparison",
            "independent factual scoring", "actual ingestion/dashboard journey", "30-day live confirmation"]}


def run_decision(rows: list[dict], client: RecordedRunClient, *, contract: bool) -> str:
    if contract:
        return "contract-smoke-only-not-live-evidence"
    if not rows:
        return "insufficient-live-coverage"
    if client.stopped or any(row.get("error") for row in rows):
        return "incomplete-or-failed-development"
    for row in rows:
        calls = [r for r in client.records if r["case"] == row["id"]]
        if not calls or not any(r["status"] == "completed" for r in calls):
            return "insufficient-live-coverage"
        if any(r["status"] != "completed" for r in calls):
            return "refine-provider-failures"
    # Scoring is diagnostic; no independent answer/profile rubric yet.
    return "development-complete-pending-quality-review"


async def run(output_dir: Path, *, contract: bool, days: int = 7,
              concurrency: int = 2, maximum_calls: int = 200,
              maximum_cost_usd: float = 2.0) -> dict:
    if days < 2 or days > 30 or concurrency < 1 or concurrency > 4:
        raise ValueError("Days must be 2..30 and concurrency 1..4")
    if not contract:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise LlmConfigurationError("Live execution requires an OpenAI credential")
    from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata = validation_manifest()
    metadata["code_revision"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)
    metadata.update(code_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        tracked_diff_sha256=hashlib.sha256(diff).hexdigest(), days=days, concurrency=concurrency,
        maximum_calls=maximum_calls, maximum_cost_usd=maximum_cost_usd,
        mode="contract-smoke" if contract else "live-development",
        live_authorized=not contract)
    # Include hashes for uncommitted new runner/adapter, which git diff omits.
    metadata["harness_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), ROOT / "scripts/final_profile_longitudinal_runtime.py")}
    (output_dir / "manifest.json").write_text(json.dumps(metadata, indent=2))
    transport = ContractFailureClient() if contract else OpenAiResponsesClient(
        MODEL, max_output_tokens=500, reasoning_effort="low")
    client = RecordedRunClient(transport, output_dir / "provider.jsonl", maximum_calls=maximum_calls,
        maximum_cost_usd=maximum_cost_usd, network_mode=metadata["mode"])
    semaphore = asyncio.Semaphore(concurrency)

    async def history(condition, persona):
        async with semaphore:
            case = build_case(persona=persona, family=SimulatorFamily.BKT_LIKE, seed=4107, days=days)
            case = case.model_copy(update={"case_id": "fresh-final-" + case.case_id})
            case_id = f"{condition}-{case.case_id}"
            token = CASE_CONTEXT.set(case_id)
            adapter = None
            try:
                manifest = AutonomySystemManifestV1(system_id=f"final:{condition}",
                    flow_id="final-profile-longitudinal-v1", adapter_version="1.0.0",
                    code_revision=metadata["code_revision"], graph_version="production-create-app",
                    release_profile_sha256=metadata["profile_sha256"], policy_version=1,
                    model_bindings={"planner": MODEL, "factual": "deterministic/evidence-set-v2"},
                    network_free=contract)
                adapter = StudentProductAutonomyAdapterV1(condition=condition, manifest=manifest,
                    runtime_factory=build_final_profile_runtime_factory(output_dir / "runtime" / case_id,
                        condition, concept_cards=CARDS, fixture_id="final-live-development-001",
                        planner_client=client, maximum_case_cost_usd=maximum_cost_usd,
                        maximum_case_calls=maximum_calls), clock_origin=ORIGIN)
                result = await run_hidden_state_learner_case(adapter, case,
                    TextRealisingLearnerV1(persona=persona, family=SimulatorFamily.BKT_LIKE,
                        seed=4107, cards=CARDS),
                    schedule=DriverScheduleV1(days=days, restart_day=min(15, max(1, days // 2))),
                    clock_origin=ORIGIN)
                score = score_hidden_state_case(condition=condition, truth=result.truth,
                    response=result.response, evidence=result.learner_evidence)
                row = {"id": case_id, "condition": condition, "score": score.model_dump(mode="json")}
                _append(output_dir / "truth.jsonl", {"id": case_id, **result.truth.to_dict()})
                _append(output_dir / "responses.jsonl", {"id": case_id, **result.response.model_dump(mode="json")})
                _append(output_dir / "learner-evidence.jsonl", {"id": case_id,
                    "evidence": result.learner_evidence.model_dump(mode="json")})
            except Exception as error:
                row = {"id": case_id, "condition": condition, "error": type(error).__name__}
            finally:
                if adapter is not None:
                    adapter.close()
                CASE_CONTEXT.reset(token)
            _append(output_dir / "cases.jsonl", row)
            return row

    rows = await asyncio.gather(*(history(condition, persona)
        for condition in CONDITIONS for persona in PERSONAS[:2]))
    summary = {"program_id": PROGRAM_ID, "decision": run_decision(rows, client, contract=contract),
        "cases": rows, "provider_attempts": client.attempts, "reserved_usd": client.reserved_usd,
        "live_model_successes": 0 if contract else sum(r["status"] == "completed" for r in client.records),
        "release_qualified": False, "manifest": metadata}
    summary["task_coverage"] = {
        row["id"]: dict(Counter(f"{call['task']}:{call['status']}" for call in client.records
            if call["case"] == row["id"])) for row in rows
    }
    summary["quality_review_required"] = [
        "Confirm complex planning and proactive wording paths actually executed; simple fast paths are separate.",
        "Review source-grounded answer quality and professor-profile adherence independently.",
        "This tutoring fixture does not establish ingestion, UI, or real student learning.",
    ]
    summary["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in output_dir.glob("*.jsonl")}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--contract-smoke", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--maximum-calls", type=int, default=200)
    parser.add_argument("--maximum-cost-usd", type=float, default=2.0)
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    if args.validate:
        print(json.dumps(validation_manifest(), indent=2))
        return
    if args.output_dir is None:
        parser.error("--output-dir is required; existing runs are never overwritten")
    result = asyncio.run(run(args.output_dir, contract=args.contract_smoke, days=args.days,
        concurrency=args.concurrency, maximum_calls=args.maximum_calls, maximum_cost_usd=args.maximum_cost_usd))
    print(json.dumps({"decision": result["decision"], "provider_attempts": result["provider_attempts"],
        "live_model_successes": result["live_model_successes"]}, indent=2))
    if any(row.get("error") for row in result["cases"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
