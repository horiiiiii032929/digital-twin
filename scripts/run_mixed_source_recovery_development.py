"""Credentialed mixed-source candidate contract; no external model or deployment claim."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import zipfile

import pymupdf
from fastapi.testclient import TestClient

from scripts.verify_deployable_foundation import (
    ADMIN_PASSWORD, PROFESSOR_PASSWORD, STUDENT_PASSWORD, ORIGIN,
    _close_app, _login, _provision_and_login, _settings,
)
from services.api.app.config import AutonomyPlannerMode, EvidenceGateMode, StudentTutoringMode
from services.api.app.factory import create_app
from services.operations import create_runtime_backup, restore_runtime_backup, verify_runtime_backup
from src.digital_twin.generation.question_specific import CANDIDATE_ID, TASK
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse
from src.digital_twin.onboarding import create_session
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from src.digital_twin.student import approved_synthetic_policy
from tests.api.test_publication_api import _teaching_profile_payload

ROOT = Path(__file__).resolve().parents[1]
INSTRUMENT_ID = "mixed-source-candidate-recovery-development-001"
TEXTS = {
    "lecture": "Glimmer lease expires after nine ticks.",
    "transcript": "Aster scheduler selects the ready task with the earliest deadline.",
    "forum": "Lumen protocol rejects a token after five steps.",
    "sentinel": "Glimmer lease expires after forty ticks in the sentinel course.",
}


def _hashes():
    paths = [*ROOT.glob("src/**/*.py"), *ROOT.glob("services/**/*.py"), Path(__file__),
             ROOT / "scripts/verify_deployable_foundation.py", ROOT / "tests/api/test_publication_api.py",
             ROOT / "tests/test_final_response_audit.py",
             ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
             ROOT / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


class SourceBoundContractClient:
    """Inspectable fixture proposal, never an answer-quality oracle."""
    def __init__(self, ledger, audit_model="gpt-5.6-sol"):
        self.audit_model = audit_model
        self.ledger = ledger
        self.calls = 0

    async def chat(self, messages, task):
        payload = json.loads(messages[-1].content)
        self.calls += 1
        if task == "reactive_tutoring_intent":
            content = {"schema_version": "3.0.0", "proposed_intent": "explain_concept", "reason_code": "synthetic_contract_explanation"}
        elif task == "question_specific_typed_instruction":
            keyword = next((v for v in ("lumen", "aster", "glimmer") if v in payload["question"].lower()), None)
            evidence = next((e for e in payload["evidence"] if keyword and keyword in e["text"].lower()), payload["evidence"][0])
            content = {"action": "instruction", "units": [{"kind": "explanation", "text": evidence["text"],
                "source_ids": [evidence["citation_id"]]}], "missing_details": []}
        elif task == "final_response_quality_audit_v2":
            from tests.test_final_response_audit import verdict
            content = verdict(payload, quality=True)
        elif task == "source_bound_attempt_assessment_v1":
            content = {"outcome": "not-assessed", "confidence": 0, "reason": "ambiguous-attempt", "quotations": []}
        elif task == TASK:
            question = payload["question"].lower()
            keyword = next((v for v in ("lumen", "aster", "glimmer") if v in question), None)
            evidence = next((e for e in payload["evidence"] if keyword and keyword in e["text"].lower()), payload["evidence"][0])
            content = {"boundary": "answerable", "teaching_move": "explain", "question_focus": "", "hint_span": None,
                       "aspects": [{"requirement": "synthetic source contract", "supported": True,
                                    "spans": [{"citation_id": evidence["citation_id"], "text": evidence["text"]}]}]}
        else:
            raise AssertionError(f"Unexpected contract task {task}")
        with self.ledger.open("a") as stream:
            stream.write(json.dumps({"attempt": self.calls, "task": task, "input": payload, "output": content}) + "\n")
        return LlmResponse(content=json.dumps(content), provider_model=self.audit_model if task == "final_response_quality_audit_v2" else "gpt-5.6-luna", provider_revision="injected-contract",
                           usage=GenerationUsage(approximate_cost_usd=0))


def _pdf(text):
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), text)
    content = document.tobytes(no_new_id=True)
    document.close()
    return content


def run(output: Path, *, post_report: bool = False, candidate: str = "v19-luna-sol-medium"):
    if candidate not in {"v19-luna-sol-medium", "v19-luna-luna-medium"} or (not post_report and candidate != "v19-luna-sol-medium"):
        raise ValueError("explicit post-report candidate required")
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    source_hashes = _hashes()
    runtime_flags = {"teaching_profile_context_enabled": True, "question_specific_generation_enabled": True}
    candidate_id = CANDIDATE_ID
    if post_report:
        from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
        selection = experimental_tutoring_configuration(candidate)
        candidate_id = selection["implementation_id"]
        runtime_flags = {**selection["runtime_flags"], "post_report_learning_mode": "assessed-count",
            "post_report_planner_mode": "analytic-only", "post_report_goal_recovery_enabled": True,
            "post_report_model_assessment_enabled": True, "post_report_model_assessment_version": "v2",
            "post_report_context_retrieval_enabled": True}
    base_profile = json.loads((ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json").read_text())
    manifest = {"instrument_id": INSTRUMENT_ID, "candidate_id": candidate_id,
        "post_report": post_report, "candidate_variant": candidate if post_report else None, "runtime_flags": runtime_flags,
        "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "staging_base_profile": {"profile_id": base_profile["profile_id"], "profile_version": base_profile["profile_version"]},
        "candidate_override": {"question_specific_generation": True, "approved_profile_context": True, "provider": "deterministic injected contract", "release_qualification": False},
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "source_hashes_start": source_hashes, "texts": TEXTS, "external_calls": 0,
        "scope": "Staging TestClient credentials/Origin, queued worker, injected-provider candidate, mixed sources, cohort and clean restore"}
    with zipfile.ZipFile(output / "source-snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, digest in source_hashes.items():
            content = (ROOT / name).read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError("source changed before archive")
            archive.writestr(name, content)
    manifest["source_snapshot_sha256"] = hashlib.sha256((output / "source-snapshot.zip").read_bytes()).hexdigest()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    checks = []
    result = {"manifest": manifest, "checks": checks, "failures": [], "external_calls": 0, "quality_pass": None, "deployment_qualified": False}
    provider = SourceBoundContractClient(output / "provider.jsonl", audit_model=selection["role_configuration"]["revision"]["model"] if post_report else "gpt-5.6-sol")
    if post_report:
        provider.role_configuration = selection["role_configuration"]
    started = time.perf_counter()
    client = app = None
    stage = "create-staging-app"

    def check(name, condition, detail=None):
        checks.append({"name": name, "passed": bool(condition), "detail": detail})
        if not condition:
            raise AssertionError(name)

    def request(method, url, expected=200, **kwargs):
        response = getattr(client, method)(url, **kwargs)
        check(f"{stage}:{method}:{url}", response.status_code == expected,
              {"actual": response.status_code, "expected": expected, "error": response.json() if response.status_code >= 400 else None})
        return response.json() if response.content else None

    def open_app(runtime):
        settings = replace(_settings(runtime), **{
            "student_profile_path": ROOT / "research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json",
            "t1_qualification_result_path": ROOT / "research/05_evaluation/records/governed-full-autonomy-v2-1-final-release-binding-001.json",
            "autonomy_planner_mode": AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE,
            "evidence_gate_mode": EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3,
            "student_tutoring_mode": StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH,
            "learning_gap_hmac_secret": b"synthetic-mixed-source-contract-only-key-32"})
        created = create_app(settings=settings, autonomy_planner_client=provider, **runtime_flags)
        if post_report:
            check("post-report-generator-identity", created.state.student_service.generator.implementation_id == candidate_id)
            check("post-report-assessor-identity", created.state.post_report_learning_configuration["assessment"] == "source-bound-model-assessment-v2")
            check("post-report-estimator-identity", created.state.post_report_learning_configuration["input"] == "assessed-count")
            check("post-report-planner-identity", created.state.governed_autonomy_service.graph.planner.implementation_id == "analytic-only-planner-v1")
        return created

    try:
        runtime = output / "runtime"
        app = open_app(runtime)
        client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
        accounts = _provision_and_login(client, app, checks)
        professor = accounts["professor"]
        request("post", "/api/auth/login", json={"email": "admin@foundation.example", "password": ADMIN_PASSWORD})
        students = [accounts["student"]]
        for number in range(1, 7):
            students.append(request("post", "/api/admin/accounts", expected=201,
                json={"email": f"mixed-{number}@example.test", "display_name": f"Synthetic learner {number}",
                      "role": "student", "temporary_password": STUDENT_PASSWORD}))
        check("professor-login", _login(client, professor["email"], PROFESSOR_PASSWORD).status_code == 200)
        request("post", "/api/professor/courses", expected=403, headers={"Origin": "https://untrusted.example"},
                json={"course_id": "origin-forged", "title": "Must not be created"})
        check("cross-origin-rejected-without-course", app.state.student_repository.get_course("origin-forged") is None)
        courses = {}
        jobs = {}
        profiles = {}
        for suffix in ("a", "b"):
            course_id = f"mixed-course-{suffix}"
            courses[suffix] = course_id
            request("post", "/api/professor/courses", expected=201, json={"course_id": course_id, "title": f"Synthetic mixed course {suffix}"})
            for student in (students[:6] if suffix == "a" else students[6:]):
                request("post", f"/api/professor/courses/{course_id}/students", expected=201, json={"student_account_id": student["account_id"]})
            # Approved onboarding is a disclosed synthetic setup fixture, not a UI claim.
            session = create_session(f"mixed-onboarding-{suffix}")
            session.course_id = course_id
            session.owner_account_id = professor["account_id"]
            session.current_step = "professor_approval"
            session.policy = approved_synthetic_policy()
            app.state.session_repository.save(session)
            profile = _teaching_profile_payload()
            profile["help_ladder"] = ["Explain the supported answer first", "Check understanding"]
            made = request("post", f"/api/professor/courses/{course_id}/teaching-profiles", expected=201, json=profile)
            profiles[suffix] = made["profile_id"]
            profile_url = f"/api/professor/courses/{course_id}/teaching-profiles/{made['profile_id']}"
            preview = request("get", profile_url + "/preview")
            request("post", profile_url + "/approve", json={"preview_sha256": preview["preview_sha256"]})
            jobs[suffix] = []
        stage = "mixed-source-ingestion"
        before_objects = app.state.object_store.iter_keys()
        request("put", f"/api/professor/courses/{courses['a']}/sources/unreviewed-forum", expected=422,
            headers={"Content-Type": "text/markdown", "Idempotency-Key": "reject-forum"},
            params={"title": "Anonymized forum", "display_allowed": True}, content=TEXTS["forum"].encode())
        check("unreviewed-input-writes-no-object", app.state.object_store.iter_keys() == before_objects)
        inputs = [("a", "lecture", "shared-handout", "application/pdf", _pdf(TEXTS["lecture"])),
                  ("a", "transcript", "transcript", "text/plain", TEXTS["transcript"].encode()),
                  ("a", "forum", "forum", "text/markdown", ("# Anonymized forum\n\n" + TEXTS["forum"]).encode()),
                  ("b", "sentinel", "shared-handout", "application/pdf", _pdf(TEXTS["sentinel"]))]
        source_jobs = {}
        for suffix, label, artifact, mime, content in inputs:
            job = request("put", f"/api/professor/courses/{courses[suffix]}/sources/{artifact}", expected=202,
                headers={"Content-Type": mime, "Idempotency-Key": f"mixed-{label}"},
                params={"title": f"Synthetic {label}", "display_allowed": True, "deidentified_reviewed": True}, content=content)
            completed = app.state.ingestion_job_service.process_one("mixed-contract-worker")
            check(f"worker-{label}", completed.id == job["id"] and completed.status.value == "succeeded")
            stored = request("get", f"/api/professor/ingestion-jobs/{job['id']}")
            check(f"provenance-{label}", stored["source_checksum"] == hashlib.sha256(content).hexdigest()
                  and stored["deidentified_reviewed"] and bool(stored["result"]["chunks"]))
            jobs[suffix].append(job["id"])
            source_jobs[label] = stored
        stage = "server-bound-publication"
        request("post", f"/api/professor/courses/{courses['a']}/releases", expected=404,
            json={"session_id": "mixed-onboarding-a", "profile_id": base_profile["profile_id"],
                "profile_version": base_profile["profile_version"], "release_id": "forbidden-cross-course-draft",
                "teaching_profile_id": profiles["a"], "ingestion_job_ids": jobs["b"]})
        check("cross-course-job-cannot-create-release", app.state.student_repository.get_release("forbidden-cross-course-draft") is None)
        for suffix in ("a", "b"):
            course = courses[suffix]
            release_id = f"mixed-release-{suffix}"
            request("post", f"/api/professor/courses/{course}/releases", expected=201,
                json={"session_id": f"mixed-onboarding-{suffix}", "profile_id": base_profile["profile_id"], "profile_version": base_profile["profile_version"],
                      "release_id": release_id, "teaching_profile_id": profiles[suffix], "ingestion_job_ids": jobs[suffix]})
            preflight = request("post", f"/api/professor/releases/{release_id}/preflight")
            check(f"preflight-{suffix}", preflight["passed"], preflight)
            request("post", f"/api/professor/releases/{release_id}/publish")
            selected = [job for job in source_jobs.values() if job["id"] in jobs[suffix]]
            concepts = []
            for index, job in enumerate(selected):
                chunk = job["result"]["chunks"][0]
                concepts.append({"concept_id": f"mixed-concept-{index}", "label": chunk["text"].split()[0],
                    "description": chunk["text"], "prerequisite_concept_ids": [],
                    "canonical_ranges": [{"source_artifact_id": chunk["source_artifact_id"],
                        "source_version": chunk["source_version"], "source_sha256": job["source_checksum"],
                        "locator": chunk["locator"], "char_start": 0, "char_end": len(chunk["text"])}]})
            request("post", f"/api/professor/courses/{course}/domain-model", expected=201,
                json={"release_id": release_id, "version": 1,
                    "objectives": [{"objective_id": "mixed-source-understanding", "statement": "Explain each approved synthetic source.",
                        "concept_ids": [c["concept_id"] for c in concepts]}], "concepts": concepts, "misconceptions": []})
        stage = "credentialed-dialogue-and-cohort"
        conversations = []
        gap_url = f"/api/professor/courses/{courses['a']}/learning-gaps"
        for number, student in enumerate(students[:6]):
            check(f"student-login-{number}", _login(client, student["email"], STUDENT_PASSWORD).status_code == 200)
            request("post", f"/api/student/courses/{courses['b']}/conversations", expected=403)
            conversation = request("post", f"/api/student/courses/{courses['a']}/conversations", expected=201)
            conversations.append(conversation["id"])
            content = "I am confused why Lumen protocol rejects a token after five steps." if number < 5 else "How does Aster scheduler select the ready task?"
            turn = request("post", f"/api/student/conversations/{conversation['id']}/messages", json={"content": content, "request_id": f"mixed-turn-{number}"})
            with (output / "responses.jsonl").open("a") as stream:
                stream.write(json.dumps({"learner": number, "response": turn}) + "\n")
            check(f"cited-candidate-{number}", turn["tutor_message"]["action"] == "answer" and turn["citations"]
                and all(c["release_id"] == "mixed-release-a" and c["course_id"] == courses['a'] for c in turn["citations"]), turn["tutor_message"])
            check("professor-relogin", _login(client, professor["email"], PROFESSOR_PASSWORD).status_code == 200)
            gaps = request("get", gap_url, params={"release_id": "mixed-release-a"})
            if number < 4:
                check(f"small-cohort-suppressed-{number}", not gaps["aggregation"]["visible_aggregates"] and not gaps["proposals"])
        check("exact-active-denominator", gaps["aggregation"]["active_learner_count"] == 6, gaps)
        visible = gaps["aggregation"]["visible_aggregates"]
        check("five-real-dialogue-signals", len(visible) == 1 and visible[0]["distinct_learners"] == 5 and visible[0]["source_title"] == "Synthetic forum", gaps)
        proposal_id = gaps["proposals"][0]["proposal_id"]
        request("post", gap_url + "/review", json={"release_id": "mixed-release-a", "proposal_id": proposal_id,
            "decision": "consider-for-next-release", "rationale": "Synthetic source explanation review."})
        gaps = request("get", gap_url, params={"release_id": "mixed-release-a"})
        check("review-reread", gaps["proposals"][0]["review_decision"] == "consider-for-next-release")
        request("get", gap_url, expected=422, params={"release_id": "mixed-release-b"})
        stage = "withdraw-and-backup"
        request("post", "/api/professor/releases/mixed-release-a/withdraw")
        check("student-login-after-withdraw", _login(client, students[0]["email"], STUDENT_PASSWORD).status_code == 200)
        calls = provider.calls
        request("post", f"/api/student/conversations/{conversations[0]}/messages", expected=409,
                json={"content": "Explain Lumen again.", "request_id": "withdrawn-turn"})
        check("withdraw-prevents-provider", provider.calls == calls)
        client.close()
        _close_app(app)
        client = app = None
        backup = output / "backup.zip"
        archive = create_runtime_backup(runtime / "digital-twin.sqlite3", runtime, backup)
        check("backup-manifest-checksums", verify_runtime_backup(backup) == archive)
        runtime.rename(output / "retired-runtime")
        restored = output / "restored-runtime"
        restore_runtime_backup(backup, restored / "digital-twin.sqlite3", restored)
        app = open_app(restored)
        client = TestClient(app, base_url="https://testserver", headers={"Origin": ORIGIN})
        stage = "clean-restored-application"
        check("restored-professor-login", _login(client, professor["email"], PROFESSOR_PASSWORD).status_code == 200)
        restored_gaps = request("get", gap_url, params={"release_id": "mixed-release-a"})
        check("restored-cohort-and-review", restored_gaps["aggregation"]["active_learner_count"] == 6
              and restored_gaps["proposals"][0]["review_decision"] == "consider-for-next-release")
        for label, old in source_jobs.items():
            recovered = request("get", f"/api/professor/ingestion-jobs/{old['id']}")
            check(f"restored-source-{label}", recovered["result"] == old["result"] and recovered["deidentified_reviewed"])
            content = app.state.object_store.read(recovered["source_object_key"])
            check(f"restored-bytes-{label}", hashlib.sha256(content).hexdigest() == old["source_checksum"])
        check("restored-turns", all(len(app.state.student_repository.list_messages(c)) == 2 for c in conversations))
        check("restored-withdrawn-status", app.state.student_repository.get_release("mixed-release-a").status.value == "withdrawn")
        check("restored-student-login", _login(client, students[0]["email"], STUDENT_PASSWORD).status_code == 200)
        calls = provider.calls
        request("post", f"/api/student/conversations/{conversations[0]}/messages", expected=409,
                json={"content": "Explain Lumen again.", "request_id": "restored-withdrawn-turn"})
        check("restored-withdrawal-prevents-provider", provider.calls == calls)
        check("sentinel-login", _login(client, students[6]["email"], STUDENT_PASSWORD).status_code == 200)
        request("post", f"/api/student/courses/{courses['a']}/conversations", expected=403)
        sentinel = request("post", f"/api/student/courses/{courses['b']}/conversations", expected=201)
        turn = request("post", f"/api/student/conversations/{sentinel['id']}/messages", json={"content": "When does Glimmer lease expire?", "request_id": "restored-sentinel"})
        check("restored-active-course-uses-own-source", "forty" in turn["tutor_message"]["content"] and turn["citations"]
              and all(c["release_id"] == "mixed-release-b" for c in turn["citations"]), turn)
        result["backup"] = archive.model_dump(mode="json")
        result["source_formats"] = [item[3] for item in inputs]
        result["cohort"] = {"active": 6, "gap_learners": 5, "review_restored": True}
        if post_report:
            calls = [json.loads(line) for line in (output / "provider.jsonl").read_text().splitlines()]
            check("actual-audit-dispatched", any(row["task"] == "final_response_quality_audit_v2" for row in calls))
        result["operational_gates"] = [row for row in checks if ":" not in row["name"]]
    except Exception as error:
        result["failures"].append({"stage": stage, "class": "integration-contract", "type": type(error).__name__, "message": str(error)})
    finally:
        if client is not None:
            client.close()
        if app is not None:
            _close_app(app)
    result.update(elapsed_seconds=time.perf_counter() - started, injected_provider_calls=provider.calls,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
        source_hashes_end=_hashes())
    result["source_unchanged"] = source_hashes == result["source_hashes_end"]
    result["decision"] = "invalid-source-change" if not result["source_unchanged"] else "refine" if result["failures"] else "keep-integration-contract-only"
    result["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob("*.jsonl")}
    (output / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--post-report", action="store_true", help="Explicit V19/count/analytic/V2-assessment/recovery/context contract")
    parser.add_argument("--candidate", choices=("v19-luna-sol-medium", "v19-luna-luna-medium"), default="v19-luna-sol-medium")
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "method_evaluation_execution")
    result = run(args.output_dir, post_report=args.post_report, candidate=args.candidate)
    print(json.dumps({"decision": result["decision"], "checks": len(result["checks"]), "failures": result["failures"]}))
    if result["failures"] or not result["source_unchanged"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
