"""Finite 44-case x two-arm product comparison; no semantic quality-pass claim.

Public packet inputs only enter the tutor. Gold is used after each durable
response for development diagnostics. Synthetic installation excludes ingestion.
Product citations establish region/source containment, not claimed exact spans.
"""
from __future__ import annotations

import argparse
import asyncio
from contextvars import ContextVar
from datetime import UTC, datetime
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

from scripts.cross_course_quality_development import PACKET, public_case, validate_packet
from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import (
    CASE_CONTEXT, MODEL, ROOT, ContractFailureClient, RecordedRunClient,
    _append, validation_manifest,
)
from services.llm import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.generation.question_specific import CANDIDATE_ID
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmConfigurationError, LlmTimeoutError
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

PROGRAM_ID = "cross-course-quality-development-001"
ARMS = ("incumbent", "question-specific-profile-candidate")
INJECT_FAILURE = ContextVar("quality_inject_failure", default=False)


def source_bindings(public: dict) -> list[dict]:
    fixture_id = "cross-quality-" + public["course_id"]
    return [{"packet_source_id": s["source_id"],
             "runtime_source_id": f"{fixture_id}-source-{i:02d}",
             "runtime_document_id": f"document-{fixture_id}-source-{i:02d}",
             "locator": f"{fixture_id}-source-{i:02d} paragraph 1",
             "version": s["version"],
             "checksum": hashlib.sha256(s["text"].encode()).hexdigest()}
            for i, s in enumerate(public["sources"], start=1)]


def profile_values(mode: str) -> dict:
    socratic = mode == "socratic"
    return {"tone": "Patient and precise", "depth": "concise" if socratic else "detailed",
            "explanation_structure": ["Ask a diagnostic question before revealing any solution"] if socratic else ["Explain the supported answer first", "Check understanding"],
            "example_preferences": [], "misconception_handling": "Ask the learner to explain their reasoning before correction" if socratic else "State the supported correction clearly",
            "integrity_limits": "Do not provide full graded-work answers",
            "help_ladder": ["Ask a diagnostic question", "Give a bounded hint", "Explain after a genuine attempt"] if socratic else ["Explain the supported answer", "Ask a check question"],
            "outreach_policy": "Respect student consent and delivery limits"}


class FailureRouter:
    def __init__(self, client, *, contract: bool):
        self.client, self.contract = client, contract
        self.external_attempts = self.injected_attempts = 0
        self.injected_cases: list[str] = []

    async def chat(self, messages, task):
        if INJECT_FAILURE.get():
            self.injected_attempts += 1
            self.injected_cases.append(CASE_CONTEXT.get())
            error = LlmTimeoutError("Injected development timeout")
            error.usage = GenerationUsage(input_tokens=0, output_tokens=0, total_tokens=0, approximate_cost_usd=0)
            raise error
        if not self.contract:
            self.external_attempts += 1
        return await self.client.chat(messages, task)


def score_product_response(public: dict, gold: dict, response: dict,
                           bindings: list[dict], *, course_id: str, release_id: str) -> dict:
    """Check actual citation metadata; never synthesize claim-specific offsets."""
    expected = {b["runtime_source_id"]: b for b in bindings}
    contained, violations = set(), []
    for citation in response["citations"]:
        binding = expected.get(citation["source_artifact_id"])
        if (binding is None or citation["course_id"] != course_id or citation["release_id"] != release_id
                or citation["source_document_id"] != binding["runtime_document_id"]
                or citation["source_version"] != binding["version"]
                or citation["source_checksum"] != binding["checksum"]
                or citation["locator"] != binding["locator"]):
            violations.append("citation-lineage")
        else:
            contained.add(binding["packet_source_id"])
    action = "diagnostic-question" if response["action"] == "question" else response["action"]
    if action not in gold["allowed_actions"]:
        violations.append("action")
    for span in gold["requirements"]:
        if span["quote"] not in response["text"]:
            violations.append("required-content-missing")
        if span["source_id"] not in contained:
            violations.append("required-source-containment-missing")
    if any(s["quote"].casefold() in response["text"].casefold() for s in gold["forbidden_solution_spans"]):
        violations.append("premature-solution")
    if gold["no_citations"] and response["citations"]:
        violations.append("boundary-citations")
    return {"mechanical_source_containment_pass": not violations,
            "violations": sorted(set(violations)), "claim_specific_span_score": None,
            "provenance_scope": "Verified whole-source paragraph containment; product citations do not bind individual quoted spans",
            "semantic_review": "pending; generic questions and unsupported extra prose are not automatically judged"}


def manifest(packet: dict) -> dict:
    validate_packet(packet)
    selected = validation_manifest()
    paths = [PACKET, Path(__file__), ROOT / "scripts/cross_course_quality_development.py",
             ROOT / "scripts/final_profile_longitudinal_runtime.py", ROOT / "scripts/run_final_profile_longitudinal.py"]
    paths.extend((ROOT / "src/digital_twin/generation").glob("question_specific*.py"))
    paths.extend([ROOT / "services/api/app/factory.py", ROOT / "src/digital_twin/student/service.py",
                  ROOT / "src/digital_twin/student/tutoring_graph.py"])
    paths.extend((ROOT / "src/digital_twin").rglob("*.py"))
    paths.extend((ROOT / "services").rglob("*.py"))
    paths.append(ROOT / "scripts/governed_full_autonomy_v2_1_hidden_state_runtime.py")
    bindings = {c["public"]["case_id"]: source_bindings(public_case(packet, c["public"]["case_id"])) for c in packet["cases"]}
    return {"program_id": PROGRAM_ID, "case_count": len(packet["cases"]) * len(ARMS),
            "arms": list(ARMS), "model": MODEL, "profile_sha256": selected["profile_sha256"],
            "candidate_configuration": {"generator": CANDIDATE_ID,
                "admission_gate": "authorized-top5-async-answerability-admission-v1",
                "approved_profile_context": True,
                "comparison_scope": "Joint answerability/generation/profile composition, not isolated single-variable ablation"},
            "packet_sha256": hashlib.sha256(json.dumps(packet, sort_keys=True).encode()).hexdigest(),
            "source_bindings": bindings,
            "source_binding_sha256": hashlib.sha256(json.dumps(bindings, sort_keys=True).encode()).hexdigest(),
            "file_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
            "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
            "tracked_diff_sha256": hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)).hexdigest(),
            "review_status": packet["review_status"], "history_mode": "Submit student history messages; use actual tutor outputs, never inject authored assistant history",
            "scope": "Synthetic fixtures; development; not ingestion, semantic quality qualification or real professor fidelity"}


async def run(output_dir: Path, *, contract: bool, injected_client=None,
              maximum_calls: int = 500, maximum_cost_usd: float = 5, concurrency: int = 2,
              packet: dict | None = None) -> dict:
    if not 1 <= concurrency <= 4 or maximum_calls < 1 or not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0:
        raise ValueError("finite positive bounds required")
    if injected_client is not None and not contract:
        raise ValueError("injected clients require contract mode")
    if not contract:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise LlmConfigurationError("OpenAI credential required")
    packet = packet or json.loads(PACKET.read_text())
    metadata = manifest(packet)
    metadata.update(mode="contract" if contract else "live-development", maximum_calls=maximum_calls,
                    maximum_cost_usd=maximum_cost_usd, concurrency=concurrency)
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "manifest.json").write_text(json.dumps(metadata, indent=2))
    transport = injected_client or (ContractFailureClient() if contract else OpenAiResponsesClient(MODEL, max_output_tokens=500, reasoning_effort="low"))
    router = FailureRouter(transport, contract=contract)
    client = RecordedRunClient(router, output_dir / "provider.jsonl", maximum_calls=maximum_calls,
        maximum_cost_usd=maximum_cost_usd, network_mode=metadata["mode"])
    semaphore = asyncio.Semaphore(concurrency)

    async def one(arm, case):
        async with semaphore:
            public = public_case(packet, case["public"]["case_id"])
            case_id = arm + ":" + public["case_id"]
            token = CASE_CONTEXT.set(case_id)
            runtime = None
            started = time.perf_counter()
            row = {"id": case_id, "arm": arm, "case_id": public["case_id"], "kind": public["kind"]}
            try:
                cards = tuple(ConceptCardV1("concept-"+s["source_id"], s["title"], s["text"], "Explain "+s["title"]) for s in public["sources"])
                runtime = build_final_profile_runtime_factory(output_dir / "runtime" / arm,
                    "t1-v2-reactive", concept_cards=cards, fixture_id="cross-quality-"+public["course_id"],
                    planner_client=client, maximum_case_calls=maximum_calls, maximum_case_cost_usd=maximum_cost_usd,
                    teaching_profile_context_enabled=arm != "incumbent",
                    question_specific_generation_enabled=arm != "incumbent",
                    teaching_profile_values=profile_values(public["profile"]["mode"])
                )(SimpleNamespace(case_id=public["case_id"]), VirtualUtcClock(datetime(2026, 9, 9, 12, tzinfo=UTC)))
                bindings = metadata["source_bindings"][public["case_id"]]
                release = runtime.repository.get_release(runtime.release_id)
                for binding, source in zip(bindings, public["sources"], strict=True):
                    chunk = next(c for c in release.chunks if c.source_artifact_id == binding["runtime_source_id"])
                    if chunk.text != source["text"] or chunk.locator != binding["locator"] or chunk.source_checksum != binding["checksum"] or chunk.source_version != binding["version"]:
                        raise ValueError("source binding drift before tutoring")
                history = []
                for i, item in enumerate(public["history"]):
                    if item["role"] != "student":
                        continue
                    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
                        content=item["content"], client_request_id=f"history-{i}")
                    history.append(turn.model_dump(mode="json"))
                failure_token = INJECT_FAILURE.set(public["event"] == "provider-timeout")
                try:
                    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
                        content=public["question"], client_request_id="final")
                finally:
                    INJECT_FAILURE.reset(failure_token)
                response = {"text": turn.tutor_message.content, "action": turn.tutor_message.action,
                            "citations": [c.model_dump(mode="json") for c in turn.citations]}
                row.update(response=response, history=history, public_input=public,
                           actual_gate=runtime.tutoring.evidence_gate.implementation_id,
                           actual_generator=runtime.tutoring.generator.implementation_id,
                           approved_profile_sha256=release.teaching_profile_sha256,
                           latency_ms=(time.perf_counter()-started)*1000)
                # Persist response before reading case gold for development scoring.
                _append(output_dir / "responses.jsonl", row)
                row["score"] = score_product_response(public, case["gold"], response, bindings,
                    course_id=runtime.course_id, release_id=runtime.release_id)
            except Exception as error:
                row.update(error=type(error).__name__, message=str(error)[:300])
            finally:
                if runtime is not None:
                    runtime.close_runtime(runtime)
                CASE_CONTEXT.reset(token)
            _append(output_dir / "cases.jsonl", row)
            return row

    rows = await asyncio.gather(*(one(arm, case) for arm in ARMS for case in packet["cases"]))
    summary = {"program_id": PROGRAM_ID, "decision": "contract-only" if contract else "development-pending-independent-content-review",
               "cases": len(rows), "errors": sum("error" in r for r in rows),
               "provider_ledger_attempts": client.attempts, "actual_external_attempts": router.external_attempts,
               "injected_failure_attempts": router.injected_attempts,
               "injected_failure_cases": sorted(set(router.injected_cases)),
               "reserved_usd": client.reserved_usd, "budget_stopped": client.stopped,
               "reported_cost_usd": sum((r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in client.records),
               "arms": {arm: {"cases": sum(r["arm"] == arm for r in rows),
                   "mechanical_source_containment_passes": sum(r["arm"] == arm and r.get("score", {}).get("mechanical_source_containment_pass", False) for r in rows)} for arm in ARMS},
               "semantic_quality_pass": None, "release_qualified": False}
    injected_ids = set(router.injected_cases)
    summary["unexpected_provider_failures"] = sum(
        r["status"] == "failed" and r["case"] not in injected_ids for r in client.records)
    summary["actual_model_successes"] = 0 if contract else sum(r["status"] == "completed" for r in client.records)
    if not contract and summary["unexpected_provider_failures"]:
        summary["decision"] = "refine-provider-integration-failures"
    summary["task_coverage"] = {r["id"]: [c["task"]+":"+c["status"] for c in client.records if c["case"] == r["id"]] for r in rows}
    summary["slices"] = {arm: {kind: {"cases": sum(r["arm"] == arm and r["kind"] == kind for r in rows),
        "mechanical_passes": sum(r["arm"] == arm and r["kind"] == kind and r.get("score", {}).get("mechanical_source_containment_pass", False) for r in rows)}
        for kind in sorted({r["kind"] for r in rows})} for arm in ARMS}
    summary["frozen_files_unchanged"] = all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest() == h for p,h in metadata["file_sha256"].items())
    if summary["errors"] or client.stopped or not summary["frozen_files_unchanged"]:
        summary["decision"] = "incomplete-or-binding-drift-development"
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--contract", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--maximum-calls", type=int, default=500)
    parser.add_argument("--maximum-cost-usd", type=float, default=5)
    parser.add_argument("--concurrency", type=int, default=2)
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "method_evaluation_execution")
    if args.validate:
        print(json.dumps(manifest(json.loads(PACKET.read_text())), indent=2))
    elif args.output_dir is None:
        parser.error("--output-dir required")
    else:
        print(json.dumps(asyncio.run(run(args.output_dir, contract=args.contract,
            maximum_calls=args.maximum_calls, maximum_cost_usd=args.maximum_cost_usd, concurrency=args.concurrency)), indent=2))


if __name__ == "__main__":
    main()
