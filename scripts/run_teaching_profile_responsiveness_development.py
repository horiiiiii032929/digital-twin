"""Bounded fresh profile comparison; synthetic responsiveness, not professor fidelity."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
import zipfile
from types import SimpleNamespace

from services.llm import OpenAiResponsesClient
from services.llm.budget import BudgetedLlmClient
from scripts.recorded_generation_roles import create_recorded_generation_roles
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.llm import LlmConfigurationError
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import (
    CARDS, CASE_CONTEXT, MODEL, ORIGIN, ROOT, ContractFailureClient,
    RecordedRunClient, _append, _digest, validation_manifest,
)
from scripts.teaching_profile_responsiveness_packet import (
    CASES, PROFILES, packet_manifest, score_style_choice,
)
from src.digital_twin.evaluation.experimental_tutoring_candidate import (
    GENERATION_VARIANTS, experimental_tutoring_configuration,
)

PROGRAM_ID = "teaching-profile-responsiveness-development-001"
CONDITIONS = ("context-off", "approved-teaching-profile-context-v1")


def manifest() -> dict:
    binding = validation_manifest()
    return {"program_id": PROGRAM_ID, "packet": packet_manifest(),
        "packet_sha256": _digest(packet_manifest()), "profile_sha256": binding["profile_sha256"],
        "cards_sha256": _digest([c.__dict__ for c in CARDS]), "model": MODEL,
        "case_count": len(PROFILES) * len(CONDITIONS) * len(CASES),
        "scope": "development responsiveness; no real-professor fidelity claim",
        "setup": "synthetic approved fixtures, not ingestion/publication acceptance"}


def summarize(rows: list[dict], *, contract: bool) -> dict:
    adherence = {}
    for condition in CONDITIONS:
        eligible = [r for r in rows if r["condition"] == condition and r["kind"] == "style"]
        adherence[condition] = {"eligible": len(eligible),
            "matches": sum(r.get("style_match") is True for r in eligible),
            "errors": sum("error" in r for r in eligible)}
    differentiation = {}
    for condition in CONDITIONS:
        pairs = []
        for case in CASES:
            if case["kind"] != "style":
                continue
            arms = [r for r in rows if r["condition"] == condition and r["case_id"] == case["id"]]
            valid = len(arms) == 2 and all("response" in r for r in arms)
            pairs.append({"case_id": case["id"], "complete": valid,
                "intent_differs": valid and arms[0]["intent"] != arms[1]["intent"],
                "content_differs": valid and arms[0]["response"]["tutor_message"]["content"] != arms[1]["response"]["tutor_message"]["content"]})
        differentiation[condition] = pairs
    return {"decision": "contract-only-not-live-evidence" if contract else
        "development-pending-content-and-boundary-review",
        "style_intent_adherence": adherence, "matched_profile_differentiation": differentiation,
        "case_errors": sum("error" in r for r in rows),
        "delivered_action_counts": dict(Counter(r["response"]["tutor_message"]["action"]
            for r in rows if "response" in r)),
        "safe_action_count": sum(r.get("response", {}).get("tutor_message", {}).get("action", "").startswith("safe-")
            for r in rows),
        "provider_failure_cases": sum(r.get("provider_failure_count", 0) > 0 for r in rows),
        "boundary_violations": None,
        "boundary_review": "Manual review of delivered responses required; no automatic safety-pass claim.",
        "failure_coverage": "Withdrawn/hash-mismatch and explicit provider/malformed perturbations require separate contract tests.",
        "release_qualified": False}


async def run(output_dir: Path, *, contract: bool, injected_client=None,
              concurrency: int = 2, maximum_calls: int = 100,
              maximum_cost_usd: float = 1.0, candidate: str | None = None) -> dict:
    if not 1 <= concurrency <= 4 or maximum_calls < 1 or not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0:
        raise ValueError("Positive finite bounds and concurrency 1..4 required")
    if injected_client is not None and not contract:
        raise ValueError("Injected clients require explicit contract mode")
    if candidate not in {None, "v10", *GENERATION_VARIANTS}:
        raise ValueError("explicit responsiveness candidate must be V10 or a declared generation variant")
    selection = experimental_tutoring_configuration(candidate) if candidate else None
    roles = selection.get("role_configuration") if selection else None
    if roles and "revision" in roles and (maximum_calls != 150 or not 24 <= maximum_cost_usd <= 30):
        raise ValueError("three-role full24-case comparison requires150 calls and USD24..30")
    if roles and "revision" not in roles and (maximum_calls != 100 or not 16 <= maximum_cost_usd <= 20):
        raise ValueError("role-separated full24-case comparison requires100 calls and USD16..20")
    if selection and not roles and (not 72 <= maximum_calls <= 100 or not 1.8 <= maximum_cost_usd <= 3):
        raise ValueError("V10 full24-case comparison requires72..100 calls and USD1.8..3")
    if not contract:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise LlmConfigurationError("Live execution requires an OpenAI credential")
    metadata = manifest()
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata.update(mode="contract" if contract else "live-development",
        code_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        code_dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        tracked_diff_sha256=hashlib.sha256(subprocess.check_output(["git", "diff", "HEAD"], cwd=ROOT)).hexdigest(),
        concurrency=concurrency, maximum_calls=maximum_calls, maximum_cost_usd=maximum_cost_usd)
    metadata["harness_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__), ROOT / "scripts/teaching_profile_responsiveness_packet.py",
            ROOT / "scripts/final_profile_longitudinal_runtime.py", ROOT / "scripts/run_final_profile_longitudinal.py")}
    if selection:
        from scripts.run_operational_dialogue_development import manifest as runtime_manifest
        metadata["harness_sha256"].update(runtime_manifest()["harness_sha256"])
        plan = ROOT / "research/04_experiments/2026-09-06-v10-profile-responsiveness-plan.md"
        metadata["harness_sha256"][str(plan.relative_to(ROOT))] = hashlib.sha256(plan.read_bytes()).hexdigest()
        if roles:
            for relative in ("scripts/recorded_generation_roles.py", "tests/test_teaching_profile_responsiveness_runner.py",
                    "research/04_experiments/2026-09-06-v10-generation-model-comparison-plan.md",
                    "research/04_experiments/2026-09-06-evidence-strength-generation-plan.md",
                    "research/04_experiments/2026-09-06-independent-factual-revision-plan.md",
                    "research/04_experiments/2026-09-06-bounded-revision-plan.md",
                    "research/04_experiments/2026-09-06-conditional-revision-plan.md", "research/04_experiments/2026-09-06-conditional-revision-effort-plan.md"):
                metadata["harness_sha256"][relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            metadata.update(model=roles["generation"]["model"], planner_model=roles["planner"]["model"],
                role_configuration=roles, role_call_allocations={role: maximum_calls // len(roles) for role in roles},
                role_cost_allocations={role: maximum_cost_usd / len(roles) for role in roles},
                shared_outer_budget=True, per_role_reservation_usd=.16)
        metadata.update(candidate_configuration=selection, output_cap=3000,
            intervention="approved-context handling, including conditional advisory-field omission",
            legacy_intent_scores_are_diagnostic_only=True)
        with zipfile.ZipFile(output_dir / "source-snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, digest in metadata["harness_sha256"].items():
                content = (ROOT / name).read_bytes()
                if hashlib.sha256(content).hexdigest() != digest:
                    raise RuntimeError("source changed before profile comparison archive")
                archive.writestr(name, content)
        metadata["source_snapshot_sha256"] = hashlib.sha256((output_dir / "source-snapshot.zip").read_bytes()).hexdigest()
    metadata["manifest_sha256"] = _digest(metadata)
    (output_dir / "manifest.json").write_text(json.dumps(metadata, indent=2))
    if roles:
        transport_factory = (lambda role, _config: injected_client[role]
            if isinstance(injected_client, dict) else injected_client) if injected_client is not None else None
        client = create_recorded_generation_roles(selection, output_dir / "provider",
            maximum_calls=maximum_calls, maximum_cost_usd=maximum_cost_usd, live=not contract,
            transport_factory=transport_factory)
        runtime_client = BudgetedLlmClient(client, max_calls=maximum_calls,
            max_cost_usd=maximum_cost_usd, max_concurrency=concurrency)
        generation_ledger = client.ledger_paths["generation"]
    else:
        transport = injected_client or (ContractFailureClient() if contract else
            OpenAiResponsesClient(MODEL, max_output_tokens=3000 if selection else 500, reasoning_effort="low",
                **({"timeout_seconds": 30} if selection else {})))
        client = RecordedRunClient(transport, output_dir / "provider.jsonl", maximum_calls=maximum_calls,
            maximum_cost_usd=maximum_cost_usd, network_mode=metadata["mode"],
            **({"max_output_tokens": 3000, "reservation_usd": .025} if selection else {}))
        runtime_client = client
        generation_ledger = output_dir / "provider.jsonl"
    semaphore = asyncio.Semaphore(concurrency)

    async def one(profile_name, values, condition, case):
        async with semaphore:
            case_id = f"{profile_name}-{condition}-{case['id']}"
            row = {"id": case_id, "case_id": case["id"], "profile": profile_name,
                "profile_values_sha256": _digest(values), "condition": condition, "kind": case["kind"],
                "message": case["message"]}
            runtime = None
            token = CASE_CONTEXT.set(case_id)
            started = time.perf_counter()
            try:
                flags = dict(selection["runtime_flags"]) if selection else {}
                flags["teaching_profile_context_enabled"] = condition != "context-off"
                if selection:
                    row["effective_runtime_flags"] = flags
                factory = build_final_profile_runtime_factory(output_dir / "runtimes" / case_id,
                    "t1-v2-reactive", concept_cards=CARDS, fixture_id=PROGRAM_ID,
                    planner_client=runtime_client, teaching_profile_values=values,
                    maximum_case_calls=maximum_calls, maximum_case_cost_usd=maximum_cost_usd,
                    **flags)
                runtime = factory(SimpleNamespace(case_id=case_id), VirtualUtcClock(ORIGIN))
                if selection:
                    row["observed_generator_id"] = runtime.tutoring.generator.implementation_id
                    if row["observed_generator_id"] != selection["implementation_id"]:
                        raise RuntimeError("actual profile-comparison generator differs from selection")
                    if roles:
                        row["observed_generation_model_id"] = runtime.tutoring.generator.model_id
                        if row["observed_generation_model_id"] != roles["generation"]["model"]:
                            raise RuntimeError("actual profile-comparison generation model differs from selection")
                response = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
                    content=case["message"], client_request_id=case_id)
                row.update(response=response.model_dump(mode="json"), intent=response.tutoring_intent,
                    style_match=score_style_choice(profile_name, response.tutoring_intent or "")
                    if case["kind"] == "style" else None,
                    operational_metrics=(await runtime.collect_metrics(runtime)).model_dump(mode="json"))
            except Exception as error:
                row.update(error=type(error).__name__, error_code=getattr(error, "code", None))
            finally:
                if runtime is not None:
                    try:
                        runtime.close_runtime(runtime)
                    except Exception as error:
                        row["close_error"] = type(error).__name__
                CASE_CONTEXT.reset(token)
            row["latency_ms"] = (time.perf_counter() - started) * 1000
            calls = [r for r in client.records if r["case"] == case_id]
            row["provider_task_status"] = dict(Counter(f"{c['task']}:{c['status']}" for c in calls))
            row["provider_failure_count"] = sum(c["status"] != "completed" for c in calls)
            _append(output_dir / "cases.jsonl", row)
            return row

    rows = await asyncio.gather(*(one(name, values, condition, case)
        for name, values in PROFILES.items() for condition in CONDITIONS for case in CASES))
    result = {**summarize(rows, contract=contract), "program_id": PROGRAM_ID, "manifest": metadata,
        "cases": rows, "provider_attempts": client.attempts, "reserved_usd": client.reserved_usd,
        "provider_stopped": client.stopped,
        "reported_provider_cost_usd": sum(c.get("usage", {}).get("approximate_cost_usd") or 0 for c in client.records),
        "provider_latency_ms": sum(c.get("latency_ms", 0) for c in client.records),
        "live_model_successes": 0 if contract else sum(c["status"] == "completed" for c in client.records)}
    if selection:
        result["profile_request_binding"] = inspect_profile_binding(generation_ledger, rows)
        if roles and "revision" in roles:
            result["revision_profile_request_binding"] = inspect_profile_binding(
                client.ledger_paths["revision"], rows, task=("question_specific_factual_revision", "question_specific_bounded_revision", "question_specific_conditional_revision"))
        result["source_hash_errors"] = {name: "changed-or-missing" for name, digest in metadata["harness_sha256"].items()
            if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest}
        result["source_files_unchanged"] = not result["source_hash_errors"]
    if roles:
        result["shared_outer_budget"] = runtime_client.snapshot()
        result["role_attempts"] = {role: recorded.attempts for role, recorded in client.role_clients.items()}
        result["role_ledger_paths"] = {role: path.name for role, path in client.ledger_paths.items()}
    result["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output_dir.glob("*.jsonl")}
    (output_dir / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def inspect_profile_binding(provider_path: Path, rows: list[dict], *,
                            task: str | tuple[str, ...] = "question_specific_typed_instruction") -> dict:
    """Inspect actual dispatched generation payloads; uncalled cases are untested."""
    requests = [json.loads(line) for line in provider_path.read_text().splitlines()] if provider_path.exists() else []
    checked = []
    for row in rows:
        matching = [request for request in requests if request.get("status") == "started"
            and request.get("case") == row["id"] and request.get("task") in ((task,) if isinstance(task, str) else task)]
        outcomes = []
        for request in matching:
            payload = json.loads(next(message["content"] for message in request["messages"] if message["role"] == "user"))
            profile = payload.get("approved_teaching_profile")
            on = row["condition"] != "context-off"
            matches = (profile is None) if not on else (
                isinstance(profile, dict) and profile.get("preferences") == PROFILES[row["profile"]])
            advisory = [key for key in ("pedagogical_intent", "help_level", "application_observed_attempt") if key in payload]
            outcomes.append({"request_sha256": request["request_sha256"], "profile_binding_matches": matches,
                "advisory_fields": advisory, "conditional_advisory_binding_matches": not advisory if on else len(advisory) == 3})
        checked.append({"id": row["id"], "generation_requests": len(outcomes), "checked_requests": outcomes,
            "status": "untested-no-generation-request" if not outcomes else "checked"})
    eligible = [item for row in checked for item in row["checked_requests"]]
    return {"cases": checked, "eligible_requests": len(eligible),
        "all_dispatched_bindings_match": bool(eligible) and all(item["profile_binding_matches"] and item["conditional_advisory_binding_matches"] for item in eligible)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--contract-smoke", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--maximum-calls", type=int, default=100)
    parser.add_argument("--maximum-cost-usd", type=float, default=1.0)
    parser.add_argument("--candidate", choices=("v10", *GENERATION_VARIANTS))
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    if args.validate:
        print(json.dumps(manifest(), indent=2))
        return
    if args.output_dir is None:
        parser.error("--output-dir required; existing runs are never overwritten")
    result = asyncio.run(run(args.output_dir, contract=args.contract_smoke,
        concurrency=args.concurrency, maximum_calls=args.maximum_calls, maximum_cost_usd=args.maximum_cost_usd,
        candidate=args.candidate))
    print(json.dumps({k: result[k] for k in ("decision", "provider_attempts", "live_model_successes", "case_errors")}))
    if result["case_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
