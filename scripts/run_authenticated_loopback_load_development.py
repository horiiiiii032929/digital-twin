"""Finite credentialed loopback HTTPS tutoring load; no public-deployment claim."""
from __future__ import annotations

import argparse
import asyncio
from contextvars import ContextVar
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import socket
import sqlite3
import ssl
import subprocess
import sys
import time
import zipfile

import httpx
from fastapi.testclient import TestClient
import uvicorn

from scripts.run_final_profile_longitudinal import CASE_CONTEXT, MODEL, RecordedRunClient
from scripts.recorded_generation_roles import create_recorded_generation_roles
from types import SimpleNamespace
from scripts.run_mixed_source_recovery_development import SourceBoundContractClient, TEXTS, _pdf
from scripts.verify_deployable_foundation import PROFESSOR_PASSWORD, STUDENT_PASSWORD, _close_app, _settings
from services.api.app.config import AutonomyPlannerMode, EvidenceGateMode, StudentTutoringMode
from services.api.app.factory import create_app
from services.api.app.experimental import build_experimental_app
from services.llm import OpenAiResponsesClient
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.onboarding import create_session
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student import AccountRole, approved_synthetic_policy
from tests.api.test_publication_api import _teaching_profile_payload

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "authenticated-loopback-load-development-001"
ORDER = (5, 25, 25, 5, 5, 25)
QUESTIONS = ("After how many ticks does Glimmer lease expire?", "After how many steps does Lumen protocol reject a token?")
ENQUEUED = ContextVar("load_budget_enqueue", default=None)


def _append(path, row):
    with path.open("a") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
        stream.flush()


def _hashes():
    paths = [*ROOT.glob("src/**/*.py"), *ROOT.glob("services/**/*.py"), Path(__file__),
        ROOT / "scripts/run_final_profile_longitudinal.py", ROOT / "scripts/recorded_generation_roles.py",
        ROOT / "research/04_experiments/2026-09-06-v10-generation-model-comparison-plan.md", ROOT / "research/04_experiments/2026-09-06-evidence-strength-generation-plan.md", ROOT / "research/04_experiments/2026-09-06-independent-factual-revision-plan.md", ROOT / "research/04_experiments/2026-09-06-bounded-revision-plan.md", ROOT / "research/04_experiments/2026-09-06-conditional-revision-plan.md", ROOT / "research/04_experiments/2026-09-06-conditional-revision-effort-plan.md", ROOT / "scripts/run_mixed_source_recovery_development.py",
        ROOT / "scripts/verify_deployable_foundation.py", ROOT / "tests/api/test_publication_api.py",
        ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
        ROOT / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


class CompactContractClient(SourceBoundContractClient):
    async def chat(self, messages, task):
        if task not in {"question_specific_compact_instruction", "question_specific_profile_authority", "question_specific_typed_instruction", "question_specific_factual_revision", "question_specific_bounded_revision", "question_specific_conditional_revision"}:
            return await super().chat(messages, task)
        from src.digital_twin.llm import LlmResponse
        from src.digital_twin.grounding.models import GenerationUsage
        payload = json.loads(messages[-1].content)
        source = payload["evidence"][0]
        content = {"action": "instruction", "units": [{"kind": "explanation",
            "text": "The approved source supplies the requested condition.",
            "source_ids": [source["citation_id"]]}], "missing_details": []}
        self.calls += 1
        _append(self.ledger, {"attempt": self.calls, "task": task, "input": payload, "output": content})
        if task == "question_specific_conditional_revision":
            content = {"disposition": "repair", "fault": "missing_requested_answer", "proposed_move": "instructional",
                "target_concept": "synthetic governing condition", "diagnosis": "Synthetic conditional repair contract.",
                "replacement": content}
        return LlmResponse(content=json.dumps(content), provider_model=getattr(self, "provider_model", MODEL),
            provider_revision="injected-contract", usage=GenerationUsage(approximate_cost_usd=0))


class AdmissionObservedTransport:
    def __init__(self, transport, output, state=None):
        self.transport, self.output = transport, output
        self.state = state if state is not None else SimpleNamespace(active=0, peak=0)

    @property
    def peak(self):
        return self.state.peak

    async def chat(self, messages, task):
        self.state.active += 1
        self.state.peak = max(self.state.peak, self.state.active)
        stamp = time.perf_counter()
        queued = ENQUEUED.get()
        row = {"case": CASE_CONTEXT.get(), "task": task, "event": "start", "inflight": self.state.active,
               "budget_and_ledger_admission_wait_ms": (stamp - queued) * 1000 if queued is not None else None}
        _append(self.output / "provider-timing.jsonl", row)
        try:
            return await self.transport.chat(messages, task)
        finally:
            self.state.active -= 1
            _append(self.output / "provider-timing.jsonl", {"case": CASE_CONTEXT.get(), "task": task,
                "event": "end", "inflight": self.state.active, "provider_wall_ms": (time.perf_counter() - stamp) * 1000})


class CaseAttributionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        case = headers.get(b"x-evaluation-case", b"setup").decode("ascii", errors="replace")[:100]
        token = CASE_CONTEXT.set(case)
        try:
            await self.app(scope, receive, send)
        finally:
            CASE_CONTEXT.reset(token)


def _bootstrap(app, config):
    """Synthetic accounts/policy are fixtures; sources/profile/domain use real APIs."""
    output = Path(config["output"])
    origin = config["origin"]
    identity = app.state.identity_service
    professor = identity.provision_account(account_id="loopback-professor", email="professor@load.example",
        display_name="Synthetic load professor", role=AccountRole.PROFESSOR, password=PROFESSOR_PASSWORD)
    accounts = []
    for group, count in enumerate(config["order"]):
        for index in range(count):
            account = identity.provision_account(account_id=f"load-{group}-{index}", email=f"load-{group}-{index}@example.test",
                display_name="Synthetic load learner", role=AccountRole.STUDENT, password=STUDENT_PASSWORD)
            accounts.append({"id": account.account_id, "email": account.email, "group": group, "index": index})
    def expect(response, code=200):
        if response.status_code != code:
            raise AssertionError(f"setup HTTP{response.status_code}, expected{code}: {response.text}")
        return response.json() if response.content else None
    course = "loopback-mixed-course"
    with TestClient(app, base_url=origin, headers={"Origin": origin}) as client:
        expect(client.post("/api/auth/login", json={"email": professor.email, "password": PROFESSOR_PASSWORD}))
        expect(client.post("/api/professor/courses", json={"course_id": course, "title": "Synthetic mixed-source load course"}), 201)
        for account in accounts:
            expect(client.post(f"/api/professor/courses/{course}/students", json={"student_account_id": account["id"]}), 201)
        session = create_session("loopback-onboarding")
        session.course_id, session.owner_account_id = course, professor.account_id
        session.current_step, session.policy = "professor_approval", approved_synthetic_policy()
        app.state.session_repository.save(session)
        profile = _teaching_profile_payload()
        profile["help_ladder"] = ["Explain the supported answer first", "Check understanding"]
        p = expect(client.post(f"/api/professor/courses/{course}/teaching-profiles", json=profile), 201)
        endpoint = f"/api/professor/courses/{course}/teaching-profiles/{p['profile_id']}"
        preview = expect(client.get(endpoint + "/preview"))
        expect(client.post(endpoint + "/approve", json={"preview_sha256": preview["preview_sha256"]}))
        jobs = []
        for label, mime, content in [("lecture", "application/pdf", _pdf(TEXTS["lecture"])),
                ("transcript", "text/plain", TEXTS["transcript"].encode()),
                ("forum", "text/markdown", ("# Anonymized forum\n\n" + TEXTS["forum"]).encode())]:
            job = expect(client.put(f"/api/professor/courses/{course}/sources/{label}",
                headers={"Content-Type": mime, "Idempotency-Key": f"loopback-{label}"},
                params={"title": f"Synthetic {label}", "display_allowed": True, "deidentified_reviewed": True}, content=content), 202)
            finished = app.state.ingestion_job_service.process_one("loopback-worker")
            if finished.id != job["id"] or finished.status.value != "succeeded":
                raise AssertionError("queued ingestion did not succeed")
            jobs.append(finished)
        base = json.loads((ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json").read_text())
        release = "loopback-release"
        expect(client.post(f"/api/professor/courses/{course}/releases", json={"session_id": session.session_id,
            "profile_id": base["profile_id"], "profile_version": base["profile_version"], "release_id": release,
            "teaching_profile_id": p["profile_id"], "ingestion_job_ids": [j.id for j in jobs]}), 201)
        if not expect(client.post(f"/api/professor/releases/{release}/preflight"))["passed"]:
            raise AssertionError("publication preflight failed")
        expect(client.post(f"/api/professor/releases/{release}/publish"))
        concepts = []
        for index, job in enumerate(jobs):
            chunk = job.result.chunks[0]
            concepts.append({"concept_id": f"load-concept-{index}", "label": chunk.text.split()[0], "description": chunk.text,
                "prerequisite_concept_ids": [], "canonical_ranges": [{"source_artifact_id": chunk.source_artifact_id,
                "source_version": chunk.source_version, "source_sha256": job.source_checksum, "locator": chunk.locator,
                "char_start": 0, "char_end": len(chunk.text)}]})
        expect(client.post(f"/api/professor/courses/{course}/domain-model", json={"release_id": release, "version": 1,
            "objectives": [{"objective_id": "source-facts", "statement": "Explain approved synthetic facts.", "concept_ids": [c['concept_id'] for c in concepts]}],
            "concepts": concepts, "misconceptions": []}), 201)
    (output / "setup.json").write_text(json.dumps({"accounts": accounts, "course_id": course, "release_id": release,
        "profile_id": p["profile_id"], "source_checksums": [j.source_checksum for j in jobs]}, indent=2))


def serve(config_path):
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    config = json.loads(Path(config_path).read_text())
    output = Path(config["output"])
    selection = experimental_tutoring_configuration(config["candidate"]) if config.get("candidate") else None
    roles = selection.get("role_configuration") if selection else None
    call_ceiling, cost_ceiling = (1200, 192) if roles and "revision" in roles else (800, 128) if roles else (300, 10)
    maximum_calls = config.get("maximum_calls", call_ceiling)
    maximum_cost = config.get("maximum_cost_usd", cost_ceiling)
    reservation = config.get("reservation_usd", .16 if roles else .03)
    if (isinstance(maximum_calls, bool) or not isinstance(maximum_calls, int) or not 1 <= maximum_calls <= call_ceiling
        or not isinstance(maximum_cost, (int, float)) or isinstance(maximum_cost, bool)
        or not math.isfinite(maximum_cost) or not 0 < maximum_cost <= cost_ceiling
        or not isinstance(reservation, (int, float)) or not math.isfinite(reservation)
        or (reservation != .16 if roles else not .025 <= reservation <= .03)):
        raise ValueError("isolated server limits must remain within the preregistered caps")
    output_cap = selection["output_cap"] if selection else 1500
    fixture = CompactContractClient if selection and selection["runtime_flags"].get("instructional_compact_response_enabled") else SourceBoundContractClient
    if roles:
        state = SimpleNamespace(active=0, peak=0)
        def role_transport(role, configuration):
            transport = fixture(output / "fixture-calls.jsonl") if config["contract"] else OpenAiResponsesClient(
                configuration["model"], max_output_tokens=output_cap, reasoning_effort=configuration["reasoning_effort"],
                timeout_seconds=30, experimental_sol_enabled=configuration["model"] == "gpt-5.6-sol")
            if config["contract"]:
                transport.experimental_transport_configuration = dict(configuration)
                transport.provider_model = configuration["model"]
            return AdmissionObservedTransport(transport, output, state=state)
        recorded = create_recorded_generation_roles(selection, output / "provider",
            maximum_calls=maximum_calls, maximum_cost_usd=maximum_cost, live=not config["contract"],
            transport_factory=role_transport)
        observed = state
    else:
        transport = fixture(output / "fixture-calls.jsonl") if config["contract"] else OpenAiResponsesClient(
            MODEL, max_output_tokens=output_cap, reasoning_effort="low", timeout_seconds=30)
        if config["contract"] and selection:
            transport.experimental_transport_configuration = {key: selection[key] for key in ("model", "output_cap", "reasoning_effort")}
        observed = AdmissionObservedTransport(transport, output)
        recorded = RecordedRunClient(observed, output / "provider.jsonl", maximum_calls=maximum_calls, maximum_cost_usd=maximum_cost,
            reservation_usd=reservation, network_mode="injected-contract" if config["contract"] else "live-loopback",
            max_output_tokens=output_cap)
    settings = replace(_settings(output / "runtime"), allowed_origins=(config["origin"],),
        login_attempts_per_minute=1000, authenticated_requests_per_minute=10000,
        student_profile_path=ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
        t1_qualification_result_path=ROOT / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json",
        autonomy_planner_mode=AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
        evidence_gate_mode=EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
        student_tutoring_mode=StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
        learning_gap_hmac_secret=b"synthetic-loopback-load-only-secret-key-32", provider_max_calls_per_process=maximum_calls, provider_cost_cap_usd=maximum_cost)
    flags = selection["runtime_flags"] if selection else {"teaching_profile_context_enabled": True,
        "question_specific_generation_enabled": True, "bounded_generation_contract_enabled": config["bounded_contract"]}
    app = (build_experimental_app(settings, config["candidate"], transport=recorded, serve_web=config.get("serve_web", False)) if selection
        else create_app(settings=settings, autonomy_planner_client=recorded, provider_max_concurrency=5, **flags))
    actual_id = app.state.student_service.generator.implementation_id
    if selection and actual_id != selection["implementation_id"]:
        _close_app(app)
        raise RuntimeError("actual authenticated generator differs from explicit candidate")
    (output / "candidate-observed.json").write_text(json.dumps({"selection": selection, "implementation_id": actual_id}))
    original = app.state.autonomy_planner_budget.chat
    async def admission_clock(messages, task):
        token = ENQUEUED.set(time.perf_counter())
        try:
            return await original(messages, task)
        finally:
            ENQUEUED.reset(token)
    app.state.autonomy_planner_budget.chat = admission_clock
    app.add_middleware(CaseAttributionMiddleware)
    try:
        _bootstrap(app, config)
        # Uvicorn re-raises captured SIGTERM after graceful shutdown. Preserve a
        # benign original handler so the enclosing finally can persist evidence.
        signal.signal(signal.SIGTERM, lambda *_: None)
        server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=config["port"],
            ssl_keyfile=str(output / "localhost.key"), ssl_certfile=str(output / "localhost.crt"),
            access_log=False, log_level="warning", timeout_graceful_shutdown=30))
        sock = socket.socket(fileno=config["socket_fd"])
        server.run(sockets=[sock])
    finally:
        (output / "server-budget.json").write_text(json.dumps({"budget": app.state.autonomy_planner_budget.snapshot(),
            "provider_attempts": recorded.attempts, "provider_records": recorded.records,
            "reserved_usd": recorded.reserved_usd, "maximum_provider_overlap": observed.peak}, indent=2))
        _close_app(app)


def _percentile(values, fraction=0.95):
    import math
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else None


async def run(output, *, contract=False, bounded_contract=False, candidate=None):
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    if candidate not in {None, "v4", "v8", "v9", "v10", "v10-luna-low", "v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"}:
        raise ValueError("authenticated candidate must be v4, v8, v9 or v10")
    selection = experimental_tutoring_configuration(candidate) if candidate else None
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    if not contract and not os.environ.get("OPENAI_API_KEY", "").strip():
        raise ValueError("Configured provider credential required")
    hashes = _hashes()
    order = (2,) if contract else ORDER
    manifest = {"instrument_id": INSTRUMENT_ID, "contract": contract, "order": order, "questions": QUESTIONS,
        "bounded_contract": bounded_contract, "candidate_configuration": selection, "model": selection["model"] if selection else MODEL, "output_cap": selection["output_cap"] if selection else 1500, "provider_concurrency": 5,
        "maximum_calls": 1200 if candidate in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"} else 800 if selection and selection.get("role_configuration") else 300, "maximum_reserved_usd": 192 if candidate in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"} else 128 if selection and selection.get("role_configuration") else 10, "route_p95_gate_ms": 15000,
        "host": {"platform": platform.platform(), "machine": platform.machine(), "logical_cpus": os.cpu_count(),
                 "python": platform.python_version()},
        "source_hashes_start": hashes, "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "co_resident_processes": subprocess.check_output(["ps", "-A", "-o", "pid,pcpu,comm"], text=True)}
    archive_path = output / "source-snapshot.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative, digest in hashes.items():
            content = (ROOT / relative).read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError("Source changed before dispatch archive completed")
            archive.writestr(relative, content)
    manifest["source_snapshot_sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    cert_config = output / "localhost.cnf"
    cert_config.write_text("[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=localhost\n[ext]\nsubjectAltName=IP:127.0.0.1,DNS:localhost\nbasicConstraints=critical,CA:TRUE\n")
    subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-config", str(cert_config),
        "-keyout", str(output / "localhost.key"), "-out", str(output / "localhost.crt")], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.chmod(output / "localhost.key", 0o600)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    origin = f"https://127.0.0.1:{port}"
    config = {"output": str(output), "contract": contract, "order": order, "origin": origin, "port": port,
              "socket_fd": sock.fileno(), "bounded_contract": bounded_contract, "candidate": candidate}
    config_path = output / "server-config.json"
    config_path.write_text(json.dumps(config, indent=2))
    server_log = (output / "server.log").open("w")
    process = subprocess.Popen([sys.executable, "-m", "scripts.run_authenticated_loopback_load_development", "--serve", str(config_path)],
        cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT, pass_fds=(sock.fileno(),))
    sock.close()
    context = ssl.create_default_context(cafile=str(output / "localhost.crt"))
    clients = []
    result = {"manifest": manifest, "repetitions": [], "failures": [], "quality_pass": None, "deployment_qualified": False}
    identities = []
    sampling = True
    async def sample_rss():
        while sampling and process.poll() is None:
            child = await asyncio.create_subprocess_exec("ps", "-o", "rss=", "-p", str(process.pid), stdout=asyncio.subprocess.PIPE)
            data, _ = await child.communicate()
            if data.strip():
                _append(output / "server-rss.jsonl", {"time": time.time(), "rss_bytes": int(data.strip()) * 1024})
            await asyncio.sleep(0.25)
    sampler = asyncio.create_task(sample_rss())
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(base_url=origin, verify=context, timeout=2) as health:
            deadline = time.monotonic() + 120
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Isolated server exited during setup; inspect retained server.log")
                try:
                    response = await health.get("/api/health")
                    if response.status_code < 500:
                        break
                except httpx.HTTPError:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError("server readiness deadline")
                await asyncio.sleep(0.1)
        setup = json.loads((output / "setup.json").read_text())
        async with asyncio.timeout(600):
            for group, count in enumerate(order):
                group_clients = []
                for account in [a for a in setup["accounts"] if a["group"] == group]:
                    client = httpx.AsyncClient(base_url=origin, verify=context, timeout=120, headers={"Origin": origin})
                    clients.append(client)
                    begin = time.perf_counter()
                    response = await client.post("/api/auth/login", json={"email": account["email"], "password": STUDENT_PASSWORD})
                    _append(output / "authentication.jsonl", {"group": group, "index": account["index"], "status": response.status_code,
                        "latency_ms": (time.perf_counter() - begin) * 1000})
                    response.raise_for_status()
                    rejected = await client.get("/api/student/courses", headers={"X-Account-ID": account["id"]})
                    if rejected.status_code != 401:
                        raise AssertionError("Synthetic identity override was not rejected")
                    response = await client.post(f"/api/student/courses/{setup['course_id']}/conversations")
                    response.raise_for_status()
                    conversation = response.json()["id"]
                    identities.append(conversation)
                    group_clients.append((client, conversation, account["index"]))
                gate = asyncio.Event()
                async def learner(client, conversation, index):
                    await gate.wait()
                    rows = []
                    for turn, question in enumerate(QUESTIONS):
                        row = {"group": group, "burst_clients": count, "index": index, "turn": turn,
                            "case_id": f"group-{group}-student-{index}-turn-{turn}", "conversation_id": conversation}
                        begin = time.perf_counter()
                        try:
                            response = await client.post(f"/api/student/conversations/{conversation}/messages",
                                headers={"X-Evaluation-Case": row["case_id"]}, json={"content": question, "request_id": row["case_id"]})
                            row["status"] = response.status_code
                            data = response.json()
                            row["response"] = data
                            response.raise_for_status()
                            tutor, citations = data["tutor_message"], data["citations"]
                            row["action"] = tutor["action"]
                            row["lineage_pass"] = bool(citations) and tutor["conversation_id"] == conversation and all(
                                c["course_id"] == setup["course_id"] and c["release_id"] == setup["release_id"] for c in citations)
                        except Exception as error:
                            row["error_type"] = type(error).__name__
                        row["latency_ms"] = (time.perf_counter() - begin) * 1000
                        _append(output / "responses.jsonl", row)
                        rows.append(row)
                    return rows
                tasks = [asyncio.create_task(learner(*item)) for item in group_clients]
                begin = time.perf_counter()
                gate.set()
                all_rows = [row for values in await asyncio.gather(*tasks) for row in values]
                metrics = {"group": group, "burst_clients": count, "planned_requests": count * 2, "observed_requests": len(all_rows),
                    "elapsed_seconds": time.perf_counter() - begin, "all_request_p95_ms": _percentile([r["latency_ms"] for r in all_rows]),
                    "http_failures": sum(bool(r.get("error_type")) for r in all_rows),
                    "lineage_failures": sum(not r.get("lineage_pass", False) for r in all_rows),
                    "non_answer_actions": sum(r.get("action") != "answer" for r in all_rows)}
                metrics["gates_pass"] = metrics["all_request_p95_ms"] <= 15000 and not any(metrics[k] for k in ("http_failures", "lineage_failures", "non_answer_actions"))
                result["repetitions"].append(metrics)
                _append(output / "repetitions.jsonl", metrics)
    except Exception as error:
        result["failures"].append({"type": type(error).__name__, "message": str(error)})
    finally:
        for client in clients:
            await client.aclose()
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=40)
            except TimeoutError:
                process.kill()
                await asyncio.to_thread(process.wait)
        sampling = False
        await sampler
        server_log.close()
    result["elapsed_seconds"] = time.perf_counter() - started
    result["server_exit_code"] = process.returncode
    budget_path = output / "server-budget.json"
    result["provider"] = json.loads(budget_path.read_text()) if budget_path.exists() else None
    result["source_hashes_end"] = _hashes()
    result["source_unchanged"] = hashes == result["source_hashes_end"]
    rss_path = output / "server-rss.jsonl"
    result["peak_sampled_server_rss_bytes"] = max((json.loads(line)["rss_bytes"] for line in rss_path.read_text().splitlines()), default=None) if rss_path.exists() else None
    db = output / "runtime/digital-twin.sqlite3"
    if db.exists():
        connection = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        result["saved_message_counts"] = [connection.execute("SELECT COUNT(*) FROM messages WHERE conversation_id=?", (c,)).fetchone()[0] for c in identities]
        connection.close()
    result["persistence_pass"] = result.get("saved_message_counts") == [4] * sum(order)
    provider_data = result["provider"]
    result["provider_evidence_pass"] = bool(provider_data) and (
        provider_data["provider_attempts"] == len(provider_data["provider_records"])
        and all(r["status"] == "completed" for r in provider_data["provider_records"])
        and not provider_data["budget"]["cost_reporting_failed"])
    all_passed = (not result["failures"] and result["persistence_pass"] and result["provider_evidence_pass"]
        and result["server_exit_code"] == 0 and len(result["repetitions"]) == len(order)
        and all(r["gates_pass"] for r in result["repetitions"]))
    result["decision"] = ("invalid-source-change" if not result["source_unchanged"] else
        "contract-only" if contract and all_passed else
        "keep-bounded-loopback-development-only" if all_passed else "refine")
    result["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.jsonl")}
    (output / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--serve", type=Path)
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--contract", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--bounded-contract", action="store_true")
    parser.add_argument("--candidate", choices=("v4", "v8", "v9", "v10", "v10-luna-low", "v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"))
    args = parser.parse_args()
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "external_model_evaluation")
    if args.serve:
        serve(args.serve)
        return
    if args.output_dir is None:
        parser.error("exclusive --output-dir required")
    result = asyncio.run(run(args.output_dir, contract=args.contract, bounded_contract=args.bounded_contract, candidate=args.candidate))
    print(json.dumps({"decision": result["decision"], "failures": result["failures"], "repetitions": result["repetitions"]}))
    if result["failures"] or not result["source_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
