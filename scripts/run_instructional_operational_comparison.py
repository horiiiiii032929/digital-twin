"""Eight matched operating histories; synthetic elapsed time, not a learning study."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path

from scripts.run_operational_dialogue_development import CONDITIONS, ROOT, manifest, run_history
from scripts.run_final_profile_longitudinal import CASE_CONTEXT
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

INSTRUMENT_ID = "instructional-eight-history-operational-development-001"
ROLE_VARIANTS = ("v10-luna-low", "v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium")

def candidate_operating_specs(candidate, seed=6209):
    if candidate not in {"v9", "v10", *ROLE_VARIANTS}:
        raise ValueError("this prospective comparison requires an explicit preregistered candidate against V4")
    experimental_tutoring_configuration(candidate)
    return [{"id": f"{version}-{persona}-socratic-{condition}-{seed}", "version": version,
        "persona": persona, "profile": "socratic", "condition": condition, "seed": seed}
        for persona in ("fast-learner", "low-receptivity") for condition in CONDITIONS
        for version in ("v4", candidate)]


async def run_candidate_operating_matrix(root, *, candidate, contract=True, transport_factory=None):
    """Exactly eight matched histories; no cohort-size or qualification inference."""
    import time
    import zipfile
    from collections import Counter
    from scripts.run_final_profile_longitudinal import RecordedRunClient, ContractFailureClient, MODEL
    from services.llm import OpenAiResponsesClient
    specs = candidate_operating_specs(candidate)
    variant = candidate in ROLE_VARIANTS
    role_count = len(experimental_tutoring_configuration(candidate).get("role_configuration", {})) or 1
    arm_calls, arm_cost = (4800, 768.0) if variant else (2500, 62.5)
    if not contract:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("configured provider credential required")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    mode = "contract" if contract else "provider-backed"
    design = manifest(days=30, seed=6209)
    plan = ROOT / "research/04_experiments/2026-09-06-final-candidate-eight-history-operational-plan.md"
    design["harness_sha256"][str(plan.relative_to(ROOT))] = hashlib.sha256(plan.read_bytes()).hexdigest()
    design.update(instrument_id=INSTRUMENT_ID, histories=specs, candidate=candidate, executed_history_count=8,
        expected_restarts=8, expected_consent_changes=16, days=30, seed=6209,
        profiles={"socratic": design["profiles"]["socratic"]},
        candidate_configurations={v: experimental_tutoring_configuration(v) for v in ("v4", candidate)},
        network_mode=mode, concurrency=2, maximum_provider_calls=arm_calls * 2, maximum_reserved_usd=arm_cost * 2,
        per_arm_maximum_calls=arm_calls, per_arm_maximum_reserved_usd=arm_cost,
        effective_inner_history_maximum_calls=8 * 600,
        role_budget_partitions=({"calls": arm_calls // role_count, "usd": arm_cost / role_count, "reservation_usd": .16} if variant else None),
        consent_disabled_days=[10, 19], consent_reenabled_day=20,
        expected_learning_effect=None, per_history_call_cap=600, per_history_cost_cap_usd=100,
        aggregate_arm_cost_cap_dominates_history_cost_cap=True)
    for extra in [Path(__file__), ROOT / "research/04_experiments/2026-09-06-independent-factual-revision-plan.md", ROOT / "research/04_experiments/2026-09-06-bounded-revision-plan.md", ROOT / "research/04_experiments/2026-09-06-conditional-revision-plan.md", ROOT / "research/04_experiments/2026-09-06-conditional-revision-effort-plan.md", ROOT / "research/04_experiments/2026-09-06-evidence-strength-generation-plan.md", ROOT / "src/digital_twin/evaluation/experimental_tutoring_candidate.py", ROOT / "scripts/recorded_generation_roles.py", ROOT / "scripts/autonomous_tutoring_worker.py", ROOT / "tests/test_instructional_operational_comparison.py", ROOT / "tests/test_autonomous_worker_composition.py", ROOT / "research/04_experiments/2026-09-06-experimental-worker-composition-plan.md"]:
        design["harness_sha256"][str(extra.relative_to(ROOT))] = hashlib.sha256(extra.read_bytes()).hexdigest()
    with zipfile.ZipFile(root / "source-snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, digest in design["harness_sha256"].items():
            content = (ROOT / name).read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError("source changed before cohort archive")
            archive.writestr(name, content)
    design["source_snapshot_sha256"] = hashlib.sha256((root / "source-snapshot.zip").read_bytes()).hexdigest()
    (root / "manifest.json").write_text(json.dumps(design, indent=2, sort_keys=True))
    clients = {}
    for version in ("v4", candidate):
        selection = experimental_tutoring_configuration(version)
        if selection.get("role_configuration"):
            from scripts.recorded_generation_roles import create_recorded_generation_roles
            clients[version] = create_recorded_generation_roles(selection, root / f"provider-{version}",
                maximum_calls=arm_calls, maximum_cost_usd=arm_cost, live=not contract,
                transport_factory=(lambda role, config: transport_factory(version, role, config)) if transport_factory else None)
            continue
        transport = (transport_factory(version) if transport_factory else ContractFailureClient() if contract
            else OpenAiResponsesClient(MODEL, timeout_seconds=30, max_output_tokens=3000, reasoning_effort="low"))
        clients[version] = RecordedRunClient(transport, root / f"provider-{version}.jsonl",
            maximum_calls=arm_calls, maximum_cost_usd=arm_cost, reservation_usd=.025,
            max_output_tokens=3000, network_mode=mode)
    semaphore = asyncio.Semaphore(2)
    started = time.perf_counter()
    async def history(spec):
        async with semaphore:
            token = CASE_CONTEXT.set(spec["id"])
            try:
                if any(client.stopped for client in clients.values()):
                    raise RuntimeError("prior provider ledger stop")
                return await run_history(root / spec["id"], spec, planner_client=clients[spec["version"]],
                    days=30, network_mode=mode, candidate=spec["version"],
                    execution_metadata=design, verify_restart=True)
            except Exception as error:
                result_path = root / spec["id"] / "result.jsonl"
                retained = json.loads(result_path.read_text().splitlines()[-1]) if result_path.exists() else {}
                return {**retained, "history": spec, "decision": "failed-operational-history", "error_type": type(error).__name__}
            finally:
                CASE_CONTEXT.reset(token)
    histories = await asyncio.gather(*(history(spec) for spec in specs))
    arms = {}
    for version, client in clients.items():
        arms[version] = {"attempts": client.attempts, "stopped": client.stopped,
            "completed_calls": sum(row["status"] == "completed" for row in client.records),
            "provider_failures": sum(row["status"] != "completed" for row in client.records),
            "failure_codes": dict(Counter(row.get("failure_stage") or row.get("error_code") for row in client.records if row["status"] != "completed")),
            "unknown_cost_calls": sum((row.get("usage") or {}).get("approximate_cost_usd") is None for row in client.records),
            "reported_cost_usd": sum((row.get("usage") or {}).get("approximate_cost_usd") or 0 for row in client.records),
            "input_tokens": sum((row.get("usage") or {}).get("input_tokens") or 0 for row in client.records),
            "output_tokens": sum((row.get("usage") or {}).get("output_tokens") or 0 for row in client.records)}
    hash_errors = {}
    for name, digest in design["harness_sha256"].items():
        try:
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                hash_errors[name] = "changed"
        except OSError as error:
            hash_errors[name] = type(error).__name__
    counters = Counter()
    for row in histories:
        counters.update(row.get("counters", {}))
    completed = sum(row["decision"] != "failed-operational-history" for row in histories)
    valid = (completed == 8 and not hash_errors and counters["consent_violations"] == 0
        and counters["restart_count"] == 8 and counters["consent_changes"] == 16
        and all(row.get("restart_checks") and all(check["equal"] for check in row["restart_checks"])
            and row.get("observed_generator_ids") == [experimental_tutoring_configuration(row["history"]["version"])["implementation_id"]] * 2
            and row.get("durable_lineage_audit", {}).get("passed")
            and row.get("budget_chain", {}).get("observable")
            and row.get("budget_chain", {}).get("any_cost_reporting_failed") is False for row in histories)
        and all(not a["stopped"] and a["unknown_cost_calls"] == 0 for a in arms.values()))
    result = {"instrument_id": INSTRUMENT_ID, "manifest": design, "histories": histories,
        "executed_history_count": len(histories), "completed": completed, "arms": arms,
        "operational_counters": dict(counters), "source_files_unchanged": not hash_errors,
        "source_hash_errors": hash_errors, "wall_seconds": time.perf_counter()-started,
        "decision": ("contract-only" if contract else "pending-independent-content-and-utility-review") if valid else "incomplete-operational-cohort",
        "provider_attempts": sum(a["attempts"] for a in arms.values()),
        "provider_failures": sum(a["provider_failures"] for a in arms.values()),
        "learning_effect_measured": False, "intervention_utility_gap_closed": False, "release_qualified": False,
        "artifact_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in root.rglob("*.jsonl")}}
    result["history_output_audits"] = [audit_history_output(root / spec["id"], spec) for spec in specs]
    if any(not audit["observed_invariants_pass"] for audit in result["history_output_audits"]):
        result["decision"] = "incomplete-operational-cohort"
    (root / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result




def audit_history_output(root, spec):
    from collections import Counter
    def rows(name):
        path = root / name
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    turns = rows("turns.jsonl")
    days_complete = [row["day"] for row in rows("days.jsonl")] == list(range(1, 31))
    proactive = rows("proactive.jsonl")
    student = [row["turn"]["student_message"] for row in turns]
    tutor = [row["turn"]["tutor_message"] for row in turns]
    ids = [message["id"] for message in [*student, *tutor]]
    requests = [message["client_request_id"] for message in student]
    conversations = {message["conversation_id"] for message in [*student, *tutor]}
    linked = all(t["response_to_message_id"] == s["id"] for s, t in zip(student, tutor, strict=True))
    delivered_ids = {row["message"]["id"] for row in proactive if row["message"]["status"] == "delivered"}
    outreach_replies = [row for row in turns if row["reason"] == "proactive-reply"]
    outreach_linked = all(row.get("responding_to_delivered_message_id") in delivered_ids for row in outreach_replies)
    seen_tutor_questions = set()
    reactive_links = True
    for row in turns:
        if row["reason"] == "question-reply":
            reactive_links = reactive_links and row.get("responding_to_delivered_message_id") in seen_tutor_questions
        if row["turn"]["tutor_message"]["action"] == "question":
            seen_tutor_questions.add(row["turn"]["tutor_message"]["id"])
    unique = len(ids) == len(set(ids)) and len(requests) == len(set(requests))
    return {"history_id": spec["id"], "turn_count": len(turns), "days_1_through_30_recorded": days_complete,
        "reactive_replies_link_actual_prior_question": reactive_links,
        "tutor_action_counts": dict(Counter(message["action"] for message in tutor)),
        "proactive_records": len(proactive), "delivered_outreach": len(delivered_ids),
        "outreach_reply_count": len(outreach_replies), "outreach_replies_link_delivered_message": outreach_linked,
        "observed_unique_message_and_request_ids": unique, "duplicate_post_idempotency_tested": False,
        "tutor_replies_link_student_messages": linked, "single_conversation": len(conversations) == 1,
        "cross_course_semantic_retrieval_tested": False,
        "observed_invariants_pass": bool(turns) and days_complete and reactive_links and unique and linked and outreach_linked and len(conversations) == 1}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--candidate", choices=("v9", "v10", *ROLE_VARIANTS), default="v9")
    args = parser.parse_args()
    if args.live:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    result = asyncio.run(run_candidate_operating_matrix(args.output, candidate=args.candidate, contract=not args.live))
    print(json.dumps({"decision": result["decision"], "completed": result["completed"],
        "provider_attempts": result["provider_attempts"]}))


if __name__ == "__main__":
    main()
