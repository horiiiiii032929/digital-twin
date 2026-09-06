"""Prospective content-responsive operational dialogue; never a learning study."""
from __future__ import annotations

import asyncio
import argparse
import os
from dataclasses import asdict
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import random
import subprocess
from types import SimpleNamespace

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory, FINAL_PROFILE_PATH
from scripts.teaching_profile_responsiveness_packet import PROFILES
from scripts.run_final_profile_longitudinal import CASE_CONTEXT
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.student.models import OutreachChannel
from src.digital_twin.evaluation.learner_simulator import PERSONAS
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

INSTRUMENT_ID = "final-profile-operational-dialogue-development-001"
ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("t1-v2-reactive", "t1-v2-autonomous")
ORIGIN = datetime(2026, 9, 12, tzinfo=UTC)
CARDS = (
    ConceptCardV1("fresh-op-slot-seal", "slot seal", "In this synthetic protocol, slot seal attaches a slot number before storage and rejects an update when its slot number is older than the stored number.", "Explain how slot seal rejects an older update."),
    ConceptCardV1("fresh-op-lantern-check", "lantern check", "In this synthetic protocol, lantern check sends a probe to each station and marks a station unavailable after two consecutive unanswered probes.", "Explain when lantern check marks a station unavailable."),
    ConceptCardV1("fresh-op-ribbon-log", "ribbon log", "In this synthetic protocol, ribbon log appends an operation before acknowledging it and replays acknowledged operations in recorded order after restart.", "Explain how ribbon log preserves operation order after restart."),
    ConceptCardV1("fresh-op-parcel-window", "parcel window", "In this synthetic protocol, parcel window allows four unacknowledged parcels and resumes sending only after an acknowledgement frees a slot.", "Explain when parcel window resumes sending."),
)


def _write_line(path, value):
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()


def _draw(seed, persona, day, purpose):
    return random.Random(f"{seed}:{persona}:{day}:{purpose}").random()


def matrix(seed=6209):
    return [{"id": f"{persona.name}-{profile}-{condition}-{seed}", "persona": persona.name,
        "profile": profile, "condition": condition, "seed": seed}
        for persona in PERSONAS for profile in PROFILES for condition in CONDITIONS]


def classify_turn(action):
    if action == "question":
        return "elicitation"
    if action == "answer":
        return "factual-answer-needs-quality-review"
    if action in {"no-evidence", "abstain", "clarify", "refuse", "redirect-graded-work"}:
        return "boundary-response"
    return "operational-failure-or-other"


def manifest(*, days=30, seed=6209):
    if not 2 <= days <= 30:
        raise ValueError("days must be 2..30")
    files = [Path(__file__), FINAL_PROFILE_PATH, ROOT / "scripts/run_final_profile_longitudinal.py",
        ROOT / "scripts/governed_full_autonomy_v2_1_hidden_state_runtime.py",
        ROOT / "scripts/final_profile_longitudinal_runtime.py",
        ROOT / "src/digital_twin/generation/question_specific.py",
        ROOT / "scripts/teaching_profile_responsiveness_packet.py",
        ROOT / "services/api/app/factory.py", ROOT / "services/llm/openai_responses_client.py",
        ROOT / "src/digital_twin/student/service.py", ROOT / "src/digital_twin/student/tutoring_graph.py",
        ROOT / "src/digital_twin/student/autonomy_models.py", ROOT / "src/digital_twin/student/teaching_profile_context.py"]
    files = sorted(set(files + list((ROOT / "src").rglob("*.py")) + list((ROOT / "services").rglob("*.py"))))
    return {"instrument_id": INSTRUMENT_ID,
        "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "days": days, "seed": seed, "histories": matrix(seed),
        "candidate": "question-specific-profile-grounded-v2",
        "admission": "authorized-top5-async-answerability-admission-v1",
        "profile_context": "approved-teaching-profile-context-v1",
        "profile_sha256": hashlib.sha256(FINAL_PROFILE_PATH.read_bytes()).hexdigest(),
        "harness_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        "cards": [asdict(card) for card in CARDS], "profiles": PROFILES,
        "simulated": ["student text and attendance", "receptivity", "elapsed time"],
        "actual": ["tutoring", "persistence", "scheduled processing", "restart"],
        "mastery_or_learning_effect_measured": False,
        "content_quality_review_required": True, "intervention_utility_gap_closed": False}


def budget_chain_snapshot(client):
    """Observe existing budget wrappers without inferring unexposed state."""
    from services.llm.budget import BudgetedLlmClient
    snapshots = []
    visited = set()
    while isinstance(client, BudgetedLlmClient) and id(client) not in visited:
        visited.add(id(client))
        snapshots.append(client.snapshot())
        client = client.client
    return {"observable": bool(snapshots), "wrappers": snapshots,
        "any_cost_reporting_failed": any(row["cost_reporting_failed"] for row in snapshots) if snapshots else None}


def durable_lineage_audit(runtime):
    repository = runtime.repository
    conversation = repository.get_conversation(runtime.conversation_id)
    messages = repository.list_messages(runtime.conversation_id)
    outreach = repository.list_proactive_messages(runtime.student_id, course_id=runtime.course_id)
    citations = [citation for message in messages for citation in repository.list_citations(message.id)]
    citations += [citation for message in outreach for citation in repository.list_proactive_citations(message.id)]
    expected = (runtime.student_id, runtime.course_id, runtime.release_id)
    identity_matches = conversation is not None and (conversation.student_id, conversation.course_id, conversation.release_id) == expected
    violations = sum(message.conversation_id != runtime.conversation_id for message in messages)
    violations += sum((message.student_id, message.course_id, message.release_id) != expected for message in outreach)
    violations += sum((citation.course_id, citation.release_id) != (runtime.course_id, runtime.release_id) for citation in citations)
    return {"persisted_conversation_identity_matches": identity_matches,
        "message_count": len(messages), "outreach_count": len(outreach), "citation_count": len(citations),
        "lineage_violations": violations, "passed": identity_matches and violations == 0,
        "source_entailment_verified": False}


def durable_restart_snapshot(runtime):
    """Read stored domain records; compare actual content rather than closure IDs."""
    repository = runtime.repository
    values = {
        "messages": repository.list_messages(runtime.conversation_id),
        "learner_state": repository.get_learner_state(runtime.conversation_id),
        "learner_belief_state": repository.get_learner_belief_state_v2(runtime.conversation_id),
        "outreach_preferences": repository.list_outreach_preferences(runtime.student_id, runtime.course_id),
        "autonomous_actions": repository.list_autonomous_actions(runtime.course_id, student_id=runtime.student_id),
        "proactive_messages": repository.list_proactive_messages(runtime.student_id, course_id=runtime.course_id),
    }
    result = {}
    for name, value in values.items():
        serialized = ([item.model_dump(mode="json") for item in value] if isinstance(value, list)
            else value.model_dump(mode="json") if value is not None else None)
        result[name] = {"sha256": hashlib.sha256(json.dumps(serialized, sort_keys=True).encode()).hexdigest(),
            "count": len(value) if isinstance(value, list) else int(value is not None)}
    return result


def operational_generation_configuration(runtime, selection):
    """Inspect the actual generator and its reachable role transport after restart."""
    from services.llm.budget import BudgetedLlmClient
    from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
    generator = runtime.tutoring.generator
    observed = {"model": getattr(generator, "model_id", None), "implementation_id": generator.implementation_id}
    if selection and selection.get("role_configuration"):
        client, seen = generator.client, set()
        while isinstance(client, BudgetedLlmClient) and id(client) not in seen:
            seen.add(id(client))
            client = client.client
        if not isinstance(client, ExperimentalGenerationRoleRouter) or client.role_configuration != selection["role_configuration"]:
            raise RuntimeError("actual operational role configuration differs from selector")
        if observed["model"] != selection["role_configuration"]["generation"]["model"]:
            raise RuntimeError("actual operational generation model differs from selector")
        observed["role_configuration"] = client.role_configuration
    return observed


async def run_history(root, spec, *, planner_client, days=30, network_mode="contract", candidate=None,
                      execution_metadata=None, verify_restart=False):
    """One bounded history. Caller owns a recorded, finite run-level transport."""
    if network_mode not in {"contract", "provider-backed"}:
        raise ValueError("explicit contract/provider-backed mode required")
    if network_mode == "provider-backed":
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    if not 2 <= days <= 30:
        raise ValueError("days must be 2..30")
    selection = experimental_tutoring_configuration(candidate) if candidate else None
    if selection and selection.get("role_configuration"):
        from services.api.app.experimental import validate_transport_configuration
        from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
        if not isinstance(planner_client, ExperimentalGenerationRoleRouter) or planner_client.role_configuration != selection["role_configuration"]:
            raise ValueError("explicit candidate requires exact recorded role configuration")
        for role, expected in selection["role_configuration"].items():
            validate_transport_configuration(planner_client.client_for_role(role), expected)
    elif selection and (getattr(getattr(planner_client, "serializer", None), "max_output_tokens", None) != selection["output_cap"]
        or getattr(planner_client, "expected_model", None) != selection["model"]):
        raise ValueError("explicit candidate requires the matching recorded model and output cap")
    persona = next(item for item in PERSONAS if item.name == spec["persona"])
    root.mkdir(parents=True, exist_ok=False)
    _write_line(root / "configuration.jsonl", {**manifest(days=days, seed=spec["seed"]),
        **(execution_metadata or {}),
        "history": spec, "network_mode": network_mode, "candidate_configuration": selection,
        "candidate": selection["implementation_id"] if selection else "question-specific-profile-grounded-v2"})
    clock = VirtualUtcClock(ORIGIN)
    factory = build_final_profile_runtime_factory(root / "runtime", spec["condition"],
        concept_cards=CARDS, fixture_id="fresh-operational-dialogue-001", planner_client=planner_client,
        teaching_profile_values=PROFILES[spec["profile"]], maximum_case_calls=600, maximum_case_cost_usd=100,
        **(selection["runtime_flags"] if selection else {"teaching_profile_context_enabled": True, "question_specific_generation_enabled": True}))
    runtime = factory(SimpleNamespace(case_id=spec["id"]), clock)
    if selection and runtime.tutoring.generator.implementation_id != selection["implementation_id"]:
        runtime.close_runtime(runtime)
        raise RuntimeError("actual operational generator differs from explicit candidate")
    counters = {"turns": 0, "questions": 0, "question_replies": 0, "proactive_seen": 0,
        "proactive_replies": 0, "unmapped_proactive": 0, "restart_count": 0, "consent_changes": 0, "consent_violations": 0}
    observed_generator_ids = [runtime.tutoring.generator.implementation_id]
    observed_generation_configurations = [operational_generation_configuration(runtime, selection)]
    restart_checks = []
    seen = set()
    restart_day = min(15, max(1, days // 2))

    def attempt(card, day, purpose):
        correct = _draw(spec["seed"], persona.name, day, purpose) >= persona.misconception_probability
        text = card.description if correct else "I think it skips every check and accepts all values."
        return f"My attempt for {card.label}: {text}"

    async def submit(text, day, reason, responding_to=None, responding_to_tutor=None):
        counters["turns"] += 1
        turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
            content=text, client_request_id=f"{spec['id']}-{counters['turns']}",
            responding_to_outreach_message_id=responding_to)
        _write_line(root / "turns.jsonl", {"day": day, "reason": reason, "student": text,
            "classification": classify_turn(turn.tutor_message.action),
            "responding_to_delivered_message_id": responding_to or responding_to_tutor,
            "turn": turn.model_dump(mode="json")})
        if turn.tutor_message.action == "question":
            counters["questions"] += 1
        return turn

    try:
        for day in range(1, days + 1):
            if getattr(planner_client, "stopped", False):
                raise RuntimeError("recorded provider ledger stopped dispatch")
            target = ORIGIN.timestamp() + day * 86400 + 12 * 3600
            clock.advance_by(int(target - clock.now().timestamp()))
            if day == restart_day:
                original_conversation = runtime.conversation_id
                before_restart = durable_restart_snapshot(runtime) if verify_restart else None
                runtime = runtime.restart_runtime(runtime)
                observed_generator_ids.append(runtime.tutoring.generator.implementation_id)
                observed_generation_configurations.append(operational_generation_configuration(runtime, selection))
                if verify_restart:
                    after_restart = durable_restart_snapshot(runtime)
                    check = {"day": day, "before": before_restart, "after": after_restart, "equal": before_restart == after_restart}
                    restart_checks.append(check)
                    _write_line(root / "restart-checks.jsonl", check)
                    if not check["equal"]:
                        raise RuntimeError("durable state changed across restart")
                if selection and runtime.tutoring.generator.implementation_id != selection["implementation_id"]:
                    raise RuntimeError("restart changed the explicit candidate")
                if runtime.conversation_id != original_conversation:
                    raise RuntimeError("restart changed conversation identity")
                counters["restart_count"] += 1
            if days == 30 and day in {10, 20}:
                preference = runtime.autonomy.outreach.update_preference(runtime.student_id, runtime.course_id,
                    channel=OutreachChannel.IN_APP, enabled=day == 20, timezone="UTC",
                    quiet_hours_start="23:00", quiet_hours_end="02:00", max_messages_per_7_days=3)
                counters["consent_changes"] += 1
                _write_line(root / "consent.jsonl", {"day": day, "preference": preference.model_dump(mode="json")})
            if spec["condition"] == "t1-v2-autonomous":
                await runtime.autonomy.process_due(worker_id="operational-development", now=clock.now(), limit=10)
                replied_proactively_today = False
                for message in runtime.repository.list_proactive_messages(runtime.student_id, course_id=runtime.course_id):
                    if message.id in seen:
                        continue
                    seen.add(message.id)
                    counters["proactive_seen"] += 1
                    created = datetime.fromisoformat(message.created_at.replace("Z", "+00:00"))
                    if days == 30 and message.status.value == "delivered" and (
                        ORIGIN.timestamp() + 10 * 86400 + 12 * 3600 <= created.timestamp()
                        < ORIGIN.timestamp() + 20 * 86400 + 12 * 3600):
                        counters["consent_violations"] += 1
                    _write_line(root / "proactive.jsonl", {"day": day, "message": message.model_dump(mode="json"),
                        "citations": [item.model_dump(mode="json") for item in runtime.repository.list_proactive_citations(message.id)]})
                    matching = [card for card in CARDS if card.label.casefold() in message.content.casefold()]
                    if len(matching) != 1:
                        counters["unmapped_proactive"] += 1
                        continue
                    if not replied_proactively_today and message.status.value == "delivered" and _draw(spec["seed"], persona.name, day, "proactive") < persona.receptivity_probability:
                        await submit(attempt(matching[0], day, "proactive-attempt"), day, "proactive-reply", message.id)
                        counters["proactive_replies"] += 1
                        replied_proactively_today = True
            if day == 1 or _draw(spec["seed"], persona.name, day, "attendance") < persona.activity_probability_per_day:
                card = CARDS[(day - 1) % len(CARDS)]
                turn = await submit(f"How does {card.label} work in this course protocol?", day, "scheduled-question")
                if turn.tutor_message.action == "question" and _draw(spec["seed"], persona.name, day, "reactive-reply") < persona.receptivity_probability:
                    await submit(attempt(card, day, "reactive-attempt"), day, "question-reply",
                        responding_to_tutor=turn.tutor_message.id)
                    counters["question_replies"] += 1
            _write_line(root / "days.jsonl", {"day": day, "counters": dict(counters)})
        for action in runtime.repository.list_autonomous_actions(runtime.course_id):
            _write_line(root / "autonomous-actions.jsonl", action.model_dump(mode="json"))
        result = {"history": spec, "days": days, "network_mode": network_mode, "candidate_configuration": selection, "counters": counters,
            "metrics": (await runtime.collect_metrics(runtime)).model_dump(mode="json"),
            "decision": ("contract-operational-history-only" if network_mode == "contract"
                else "completed-operational-history-pending-content-review"),
            "learning_effect_measured": False, "intervention_utility_gap_closed": False}
    except Exception as error:
        result = {"history": spec, "network_mode": network_mode, "counters": counters,
            "decision": "failed-operational-history", "error_type": type(error).__name__}
        raise
    finally:
        try:
            if "result" in locals():
                result["observed_generator_ids"] = observed_generator_ids
                result["observed_generation_configurations"] = observed_generation_configurations
                result["restart_checks"] = restart_checks
                try:
                    if verify_restart:
                        result["durable_lineage_audit"] = durable_lineage_audit(runtime)
                    result["budget_chain"] = budget_chain_snapshot(runtime.tutoring.generator.client)
                except Exception as diagnostic_error:
                    result["diagnostic_error_type"] = type(diagnostic_error).__name__
                    result["decision"] = "failed-operational-history"
        finally:
            try:
                runtime.close_runtime(runtime)
            finally:
                if "result" in locals():
                    _write_line(root / "result.jsonl", result)
    return result


async def run_matrix(root, *, planner_client, days=30, seed=6209, network_mode="contract", concurrency=2, execution_metadata=None):
    """Run all preregistered cells; no individual failure silently disappears."""
    if not 1 <= concurrency <= 6:
        raise ValueError("concurrency must be 1..6")
    if network_mode not in {"contract", "provider-backed"}:
        raise ValueError("explicit execution mode required")
    if network_mode == "provider-backed":
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    design = {**manifest(days=days, seed=seed), **(execution_metadata or {})}
    root.mkdir(parents=True, exist_ok=False)
    (root / "manifest.json").write_text(json.dumps({**design, "network_mode": network_mode}, indent=2))
    semaphore = asyncio.Semaphore(concurrency)
    fatal = asyncio.Event()

    async def history(spec):
        async with semaphore:
            if fatal.is_set() or getattr(planner_client, "stopped", False):
                return {"history": spec, "decision": "failed-operational-history", "error_type": "prior-fatal-or-ledger-stop"}
            token = CASE_CONTEXT.set(spec["id"])
            try:
                return await run_history(root / spec["id"], spec, planner_client=planner_client,
                    days=days, network_mode=network_mode)
            except Exception as error:
                fatal.set()
                return {"history": spec, "decision": "failed-operational-history", "error_type": type(error).__name__}
            finally:
                CASE_CONTEXT.reset(token)

    results = await asyncio.gather(*(history(spec) for spec in matrix(seed)))
    summary = {"instrument_id": INSTRUMENT_ID, "network_mode": network_mode, "histories": results,
        "decision": "pending-independent-content-and-utility-review",
        "completed": sum(row["decision"] != "failed-operational-history" for row in results),
        "learning_effect_measured": False, "release_qualified": False}
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


async def run_pilot(root, *, contract=True, transport=None):
    """Two matched three-day histories, globally limited to 80 model calls."""
    from scripts.run_final_profile_longitudinal import RecordedRunClient, ContractFailureClient, MODEL
    from services.llm import OpenAiResponsesClient
    mode = "contract" if contract else "provider-backed"
    if not contract:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("provider-backed pilot requires the configured credential")
    root.mkdir(parents=True, exist_ok=False)
    if transport is None:
        transport = ContractFailureClient() if contract else OpenAiResponsesClient(
            MODEL, timeout_seconds=30, max_output_tokens=500, reasoning_effort="low")
    client = RecordedRunClient(transport, root / "provider.jsonl", maximum_calls=80,
        maximum_cost_usd=100.0, network_mode=mode)
    specs = [row for row in matrix() if row["persona"] == "fast-learner" and row["profile"] == "socratic"]
    design = {**manifest(days=3), "histories": specs, "network_mode": mode,
        "maximum_provider_calls": 80, "per_call_timeout_seconds": 30, "concurrency": 2,
        "stage": "two-history-operational-pilot"}
    (root / "manifest.json").write_text(json.dumps(design, indent=2))

    async def history(spec):
        token = CASE_CONTEXT.set(spec["id"])
        try:
            return await run_history(root / spec["id"], spec, planner_client=client, days=3, network_mode=mode)
        except Exception as error:
            return {"history": spec, "decision": "failed-operational-history", "error_type": type(error).__name__}
        finally:
            CASE_CONTEXT.reset(token)

    results = await asyncio.gather(*(history(spec) for spec in specs))
    summary = {"instrument_id": INSTRUMENT_ID, "network_mode": mode, "histories": results,
        "provider_attempts": client.attempts, "provider_successes": sum(row["status"] == "completed" for row in client.records),
        "provider_failures": sum(row["status"] != "completed" for row in client.records),
        "provider_stopped": client.stopped, "reserved_usd": client.reserved_usd,
        "reported_cost_usd": sum((row.get("usage") or {}).get("approximate_cost_usd", 0) or 0 for row in client.records),
        "decision": "contract-only" if contract else "operational-pilot-pending-content-review",
        "learning_effect_measured": False, "release_qualified": False,
        "artifact_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*.jsonl")}}
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def progression_specs():
    """Fixed synthetic stimuli, independent of provider-produced answers."""
    never = dict(PROFILES["socratic"])
    never.update(help_ladder=["diagnostic question", "one partial hint", "never reveal a direct answer"],
        explanation_structure=["ask a diagnostic question", "offer partial guidance only"],
        integrity_limits="Never reveal a complete direct answer, including ungraded questions.")
    return [{"id": name, "profile": profile, "correct_attempt": correct}
        for name, profile, correct in [
            ("socratic-correct", PROFILES["socratic"], True),
            ("socratic-incorrect", PROFILES["socratic"], False),
            ("explanatory-correct", PROFILES["explanatory"], True),
            ("never-answer-incorrect", never, False)]]


async def run_progression_pilot(root, *, contract=True, transport=None, model_id="gpt-5.6-luna"):
    """Sixteen fixed turns; external execution is exact-scope and call bounded."""
    from scripts.run_final_profile_longitudinal import RecordedRunClient, ContractFailureClient
    from services.llm import OpenAiResponsesClient
    if model_id not in {"gpt-5.6-luna", "gpt-5.6-terra"}:
        raise ValueError("unknown explicit model comparator")
    mode = "contract" if contract else "provider-backed"
    if not contract:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("provider-backed progression pilot requires configured credential")
    root.mkdir(parents=True, exist_ok=False)
    if transport is None:
        transport = ContractFailureClient() if contract else OpenAiResponsesClient(
            model_id, timeout_seconds=30, max_output_tokens=500, reasoning_effort="low")
    client = RecordedRunClient(transport, root / "provider.jsonl", maximum_calls=100,
        maximum_cost_usd=2.0, network_mode=mode, expected_model=model_id,
        reservation_usd=0.06 if model_id == "gpt-5.6-terra" else 0.01)
    design = {**manifest(days=3), "histories": progression_specs(), "network_mode": mode,
        "stage": "four-history-v2-progression-pilot", "maximum_provider_calls": 100,
        "maximum_reserved_usd": 2.0, "requested_model": model_id,
        "comparison_scope": "reactive generation and semantic planning only; selected profile unchanged", "per_call_timeout_seconds": 30, "concurrency": 2}
    (root / "manifest.json").write_text(json.dumps(design, indent=2))
    semaphore = asyncio.Semaphore(2)

    async def history(spec):
        async with semaphore:
            token = CASE_CONTEXT.set(spec["id"])
            runtime = None
            output = root / spec["id"]
            output.mkdir()
            try:
                factory = build_final_profile_runtime_factory(output / "runtime", "t1-v2-reactive",
                    concept_cards=CARDS, fixture_id="operational-progression-v2-fresh",
                    planner_client=client, teaching_profile_context_enabled=True,
                    question_specific_generation_enabled=True, teaching_profile_values=spec["profile"],
                    experimental_planner_model_id=model_id,
                    maximum_case_cost_usd=2.0, maximum_case_calls=100)
                runtime = factory(SimpleNamespace(case_id=spec["id"]), VirtualUtcClock(ORIGIN))
                attempt_text = ("My attempt for slot seal: " + CARDS[0].description if spec["correct_attempt"]
                    else "My attempt for slot seal: I think an older update should overwrite the stored value.")
                prompts = ["How does slot seal work in this course protocol?", attempt_text,
                    "I am still unsure about slot seal. Please help me apply its rule to an older update.",
                    "Now I have a different question: how does lantern check work in this course protocol?"]
                for index, prompt in enumerate(prompts):
                    if index == 3:
                        conversation_id = runtime.conversation_id
                        runtime = runtime.restart_runtime(runtime)
                        if runtime.conversation_id != conversation_id:
                            raise RuntimeError("restart changed conversation identity")
                    turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
                        content=prompt, client_request_id=f"{spec['id']}-turn-{index}")
                    _write_line(output / "turns.jsonl", {"stage": index, "student": prompt,
                        "turn": turn.model_dump(mode="json"), "classification": classify_turn(turn.tutor_message.action)})
                return {"id": spec["id"], "turns": 4, "restarts": 1, "completed": True}
            except Exception as error:
                return {"id": spec["id"], "completed": False, "error_type": type(error).__name__}
            finally:
                if runtime is not None:
                    runtime.close_runtime(runtime)
                CASE_CONTEXT.reset(token)

    results = await asyncio.gather(*(history(spec) for spec in progression_specs()))
    summary = {"instrument_id": INSTRUMENT_ID, "stage": design["stage"], "network_mode": mode,
        "histories": results, "provider_attempts": client.attempts,
        "provider_successes": sum(row["status"] == "completed" for row in client.records),
        "provider_failures": sum(row["status"] != "completed" for row in client.records),
        "reported_cost_usd": sum((row.get("usage") or {}).get("approximate_cost_usd", 0) or 0 for row in client.records),
        "source_files_unchanged": all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
            for path, digest in design["harness_sha256"].items()),
        "decision": "contract-only" if contract else "pending-independent-progression-review",
        "release_qualified": False, "learning_effect_measured": False,
        "artifact_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*.jsonl")}}
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


async def run_full_operating_matrix(root, *, contract=True, transport=None):
    """24×30 actual operating histories; no teaching-quality qualification."""
    import time
    from collections import Counter
    from scripts.run_final_profile_longitudinal import RecordedRunClient, ContractFailureClient, MODEL
    from services.llm import OpenAiResponsesClient
    mode = "contract" if contract else "provider-backed"
    if not contract:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("full provider-backed matrix requires configured credential")
    if transport is None:
        transport = ContractFailureClient() if contract else OpenAiResponsesClient(
            MODEL, timeout_seconds=30, max_output_tokens=500, reasoning_effort="low")
    client = RecordedRunClient(transport, root / "provider.jsonl", maximum_calls=5000,
        maximum_cost_usd=50.0, network_mode=mode)
    started = time.perf_counter()
    summary = await run_matrix(root, planner_client=client, days=30, network_mode=mode, concurrency=6,
        execution_metadata={"stage": "24-history-30-virtual-day-operating-development",
            "maximum_provider_calls": 5000, "maximum_reserved_usd": 50.0, "requested_model": MODEL,
            "per_call_timeout_seconds": 30, "concurrency": 6,
            "consent_disabled_days": [10, 19], "consent_reenabled_day": 20})
    design = json.loads((root / "manifest.json").read_text())
    actions = Counter()
    roles = Counter()
    for path in root.glob("*/turns.jsonl"):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            actions[row["turn"]["tutor_message"]["action"]] += 1
            roles[row["turn"]["student_message"]["role"]] += 1
            roles[row["turn"]["tutor_message"]["role"]] += 1
    latencies = sorted(row["latency_ms"] for row in client.records)
    counters = Counter()
    for row in summary["histories"]:
        counters.update(row.get("counters", {}))
    summary.update(provider_attempts=client.attempts,
        provider_successes=sum(row["status"] == "completed" for row in client.records),
        provider_failures=sum(row["status"] != "completed" for row in client.records),
        provider_stopped=client.stopped, reserved_usd=client.reserved_usd,
        reported_cost_usd=sum((row.get("usage") or {}).get("approximate_cost_usd", 0) or 0 for row in client.records),
        total_tokens=sum((row.get("usage") or {}).get("total_tokens", 0) or 0 for row in client.records),
        input_tokens=sum((row.get("usage") or {}).get("input_tokens", 0) or 0 for row in client.records),
        output_tokens=sum((row.get("usage") or {}).get("output_tokens", 0) or 0 for row in client.records),
        provider_task_counts=dict(Counter(row["task"] for row in client.records)),
        provider_failure_codes=dict(Counter(row.get("error_code", "unknown") for row in client.records if row["status"] != "completed")),
        provider_latency_p95_ms=latencies[min(len(latencies)-1, int(len(latencies)*.95))] if latencies else None,
        wall_seconds=time.perf_counter()-started, tutor_action_counts=dict(actions), role_counts=dict(roles),
        operational_counters=dict(counters),
        source_files_unchanged=all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
            for path, digest in design["harness_sha256"].items()),
        artifact_sha256={str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in root.rglob("*.jsonl")})
    fatal = (summary["completed"] != 24 or client.stopped or counters["consent_violations"]
        or not summary["source_files_unchanged"])
    summary["decision"] = ("contract-only" if contract else
        "refine-operational-failures" if fatal else "completed-operational-development-quality-remains-refine")
    (root / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pilot-contract", action="store_true")
    mode.add_argument("--pilot-live", action="store_true")
    mode.add_argument("--progression-contract", action="store_true")
    mode.add_argument("--progression-live", action="store_true")
    mode.add_argument("--full-live", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--progression-model", choices=["gpt-5.6-luna", "gpt-5.6-terra"], default="gpt-5.6-luna")
    args = parser.parse_args()
    if args.progression_model != "gpt-5.6-luna" and not (args.progression_contract or args.progression_live):
        parser.error("--progression-model is limited to the explicit reactive progression comparison")
    if args.pilot_live or args.progression_live or args.full_live:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    if not (args.pilot_contract or args.pilot_live or args.progression_contract or args.progression_live or args.full_live):
        print(json.dumps(manifest(), indent=2))
    else:
        if args.output_dir is None:
            parser.error("--output-dir is required")
        if args.full_live:
            result = asyncio.run(run_full_operating_matrix(args.output_dir, contract=False))
        elif args.progression_contract or args.progression_live:
            result = asyncio.run(run_progression_pilot(args.output_dir, contract=args.progression_contract, model_id=args.progression_model))
        else:
            result = asyncio.run(run_pilot(args.output_dir, contract=args.pilot_contract))
        print(json.dumps({"decision": result["decision"], "provider_attempts": result["provider_attempts"],
            "provider_failures": result["provider_failures"]}))
        if any(row.get("decision") == "failed-operational-history" or row.get("completed") is False for row in result["histories"]):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
