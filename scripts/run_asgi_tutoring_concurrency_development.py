"""Bounded actual tutoring-route concurrency; in-process, not deployed capacity."""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace

from fastapi import FastAPI, Request
import httpx

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory, FINAL_PROFILE_PATH
from scripts.run_final_profile_longitudinal import CASE_CONTEXT, MODEL, ORIGIN, ROOT, RecordedRunClient, ContractFailureClient, _append
from scripts.teaching_profile_responsiveness_packet import PROFILES
from scripts.tutoring_capacity_probe import StudentProbeSession, measure_tutoring_requests
from services.api.app.dependencies import get_current_account_id, get_student_service
from services.api.app.routers.student import router
from services.llm import OpenAiResponsesClient
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.llm import LlmConfigurationError
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student.models import Account, AccountRole, CourseMembership, MembershipRole

from src.digital_twin.generation.question_specific import CANDIDATE_ID

INSTRUMENT_ID = "final-profile-asgi-tutoring-concurrency-development-001"
CARDS = (
    ConceptCardV1("load-token-lease", "token lease", "In this synthetic protocol, token lease assigns one writer a token for five steps and rejects writes after the fifth step until a new token is assigned.", "When does token lease reject a write?"),
    ConceptCardV1("load-beacon-ring", "beacon ring", "In this synthetic protocol, beacon ring sends a pulse every three steps and declares a link unavailable after three missing pulses.", "When does beacon ring declare a link unavailable?"),
)
MESSAGES = (
    "Explain when token lease rejects a write in this protocol.",
    "My attempt: token lease allows the token holder to write forever. What did I miss?",
    "Explain when beacon ring declares a link unavailable in this protocol.",
    "My attempt: beacon ring declares a link unavailable after one missing pulse. Explain the correction.",
)


def source_hashes() -> dict[str, str]:
    paths = list((ROOT / "src").rglob("*.py")) + list((ROOT / "services").rglob("*.py"))
    paths += [Path(__file__), ROOT / "scripts/final_profile_longitudinal_runtime.py",
        ROOT / "scripts/run_final_profile_longitudinal.py", ROOT / "scripts/tutoring_capacity_probe.py",
        ROOT / "scripts/teaching_profile_responsiveness_packet.py", FINAL_PROFILE_PATH]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


class AttributedClient(httpx.AsyncClient):
    def __init__(self, *args, student_index: int, ledger: Path, **kwargs):
        super().__init__(*args, **kwargs)
        self.student_index, self.ledger, self.turn_index = student_index, ledger, 0

    async def post(self, url, *args, **kwargs):
        turn = self.turn_index
        self.turn_index += 1
        case_id = f"student-{self.student_index:02d}-turn-{turn}"
        token = CASE_CONTEXT.set(case_id)
        row = {"case_id": case_id, "student_index": self.student_index, "turn": turn}
        try:
            response = await super().post(url, *args, **kwargs)
            row.update(http_status=response.status_code, response=response.json())
            return response
        except Exception as error:
            row["error"] = type(error).__name__
            raise
        finally:
            _append(self.ledger, row)
            CASE_CONTEXT.reset(token)


def validate(students: int = 25, turns: int = 4) -> dict:
    if isinstance(students, bool) or not 1 <= students <= 25 or isinstance(turns, bool) or not 1 <= turns <= 4:
        raise ValueError("students1..25 and turns1..4 required")
    return {"instrument_id": INSTRUMENT_ID, "students": students, "turns_per_student": turns,
        "planned_requests": students * turns, "cards": [asdict(c) for c in CARDS], "messages": list(MESSAGES[:turns]),
        "model": MODEL, "candidate": CANDIDATE_ID,
        "profile_context": "approved-teaching-profile-context-v1", "profile_values": PROFILES["explanatory"],
        "scope": "existing student router and factory-built service; injected synthetic identity; in-process ASGI",
        "excluded": ["production authentication/middleware", "Docker", "network sockets/TLS", "real learners", "semantic-quality scoring"]}


async def run(output: Path, *, contract: bool, students: int = 25, turns: int = 4,
              maximum_calls: int = 500, maximum_cost_usd: float = 5, injected_client=None, provider_max_concurrency: int = 1) -> dict:
    manifest = validate(students, turns)
    if provider_max_concurrency not in (1, 5) or isinstance(provider_max_concurrency, bool):
        raise ValueError("provider_max_concurrency must be serial1 or candidate5")
    manifest["provider_max_concurrency"] = provider_max_concurrency
    if isinstance(maximum_calls, bool) or maximum_calls < 1 or not math.isfinite(maximum_cost_usd) or maximum_cost_usd <= 0:
        raise ValueError("finite positive call and dollar caps required")
    if injected_client is not None and not contract:
        raise ValueError("injected clients require contract mode")
    if not contract:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise LlmConfigurationError("Live run requires provider credentials")
    output.mkdir(parents=True, exist_ok=False)
    hashes = source_hashes()
    manifest.update(mode="contract" if contract else "provider-backed", source_hashes_start=hashes,
        maximum_calls=maximum_calls, maximum_cost_usd=maximum_cost_usd,
        code_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        dirty=bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)))
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    transport = injected_client or (ContractFailureClient() if contract else OpenAiResponsesClient(MODEL, max_output_tokens=500, reasoning_effort="low"))
    provider = RecordedRunClient(transport, output / "provider.jsonl", maximum_calls=maximum_calls,
        maximum_cost_usd=maximum_cost_usd, network_mode=manifest["mode"])
    runtime = None
    clients = []
    result = {"instrument_id": INSTRUMENT_ID, "manifest": manifest, "quality_pass": None, "deployment_qualified": False}
    try:
        factory = build_final_profile_runtime_factory(output / "runtime", "t1-v2-reactive",
            concept_cards=CARDS, fixture_id=INSTRUMENT_ID, planner_client=provider,
            teaching_profile_values=PROFILES["explanatory"], teaching_profile_context_enabled=True,
            question_specific_generation_enabled=True, maximum_case_calls=maximum_calls,
            maximum_case_cost_usd=maximum_cost_usd, provider_max_concurrency=provider_max_concurrency)
        runtime = factory(SimpleNamespace(case_id="shared-load-runtime"), VirtualUtcClock(ORIGIN))
        app = FastAPI()
        app.include_router(router, prefix="/api")
        async def synthetic_identity(request: Request):
            return request.headers["X-Account-ID"]
        app.dependency_overrides[get_current_account_id] = synthetic_identity
        app.dependency_overrides[get_student_service] = lambda: runtime.tutoring
        sessions = []
        for index in range(students):
            student_id = f"load-synthetic-{index:02d}"
            runtime.repository.save_account(Account(id=student_id, role=AccountRole.STUDENT))
            runtime.repository.save_membership(CourseMembership(account_id=student_id,
                course_id=runtime.course_id, role=MembershipRole.STUDENT))
            conversation = runtime.tutoring.create_conversation(student_id, runtime.course_id)
            client = AttributedClient(transport=httpx.ASGITransport(app=app), base_url="http://asgi-load",
                headers={"X-Account-ID": student_id}, student_index=index, ledger=output / "responses.jsonl")
            clients.append(client)
            sessions.append(StudentProbeSession(client, conversation.id, runtime.course_id, runtime.release_id))
        result["probe"] = await measure_tutoring_requests(sessions, list(MESSAGES[:turns]))
        result["saved_message_counts"] = [len(runtime.repository.list_messages(s.conversation_id)) for s in sessions]
    except Exception as error:
        result["error"] = type(error).__name__
    finally:
        close_errors = []
        for client in clients:
            try:
                await client.aclose()
            except Exception as error:
                close_errors.append(type(error).__name__)
        if runtime is not None:
            try:
                runtime.close_runtime(runtime)
            except Exception as error:
                close_errors.append(type(error).__name__)
        result["close_errors"] = close_errors
    end_hashes = source_hashes()
    result.update(source_hashes_end=end_hashes, source_unchanged=hashes == end_hashes,
        provider_attempts=provider.attempts, reserved_usd=provider.reserved_usd,
        provider_failures=sum(c["status"] != "completed" for c in provider.records),
        reported_cost_usd=sum(c.get("usage", {}).get("approximate_cost_usd") or 0 for c in provider.records),
        input_tokens=sum(c.get("usage", {}).get("input_tokens", 0) for c in provider.records),
        output_tokens=sum(c.get("usage", {}).get("output_tokens", 0) for c in provider.records),
        provider_task_status=dict(Counter(f"{c['task']}:{c['status']}" for c in provider.records)),
        provider_records=provider.records,
        covered_students=sorted({int(c["case"].split("-")[1]) for c in provider.records if c["case"].startswith("student-") and c["status"] == "completed"}))
    active_provider_calls = peak_provider_calls = 0
    ledger_path = output / "provider.jsonl"
    if ledger_path.exists():
        for line in ledger_path.read_text().splitlines():
            event = json.loads(line)
            if event["status"] == "started":
                active_provider_calls += 1
                peak_provider_calls = max(peak_provider_calls, active_provider_calls)
            elif event["status"] in {"completed", "failed"}:
                active_provider_calls -= 1
    result["maximum_provider_calls_in_flight"] = peak_provider_calls
    result["delivered_action_counts"] = dict(Counter(r.get("action", "request-failed") for r in result.get("probe", {}).get("requests", [])))
    result["persistence_counts_pass"] = result.get("saved_message_counts") == [turns * 2] * students
    result["decision"] = ("invalid-source-change" if not result["source_unchanged"] else
        "contract-only-not-capacity-evidence" if contract else
        "refine-operational-errors" if result.get("error") or result["close_errors"] or result["provider_failures"] or provider.stopped or not result["persistence_counts_pass"] or result.get("probe", {}).get("failure_count", 1) else
        "incomplete-provider-coverage" if len(result["covered_students"]) != students else
        "go-deeper-deployed-load-and-quality-required")
    result["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.jsonl")}
    (output / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--contract-smoke", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--students", type=int, default=25)
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--provider-max-concurrency", type=int, choices=(1, 5), default=1)
    parser.add_argument("--maximum-calls", type=int, default=500)
    parser.add_argument("--maximum-cost-usd", type=float, default=5)
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    if args.validate:
        print(json.dumps(validate(args.students, args.turns), indent=2))
        return
    if args.output_dir is None:
        parser.error("exclusive --output-dir required")
    result = asyncio.run(run(args.output_dir, contract=args.contract_smoke, students=args.students,
        turns=args.turns, maximum_calls=args.maximum_calls, maximum_cost_usd=args.maximum_cost_usd,
        provider_max_concurrency=args.provider_max_concurrency))
    print(json.dumps({k:result[k] for k in ("decision", "provider_attempts", "source_unchanged")}))
    if result.get("error"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
