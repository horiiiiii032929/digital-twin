"""Rehearse real recording APIs, or prepare fresh published courses for retakes.

The default verifies in an isolated temporary runtime. --published writes only
to the fixed recording API port; it refuses to replace existing courses.
"""
import argparse
import json
from pathlib import Path
import tempfile

import httpx
from fastapi.testclient import TestClient

from scripts.recording_app import ACTORS, make_recording_app
from scripts.recording_safety import require_recording_runtime
from src.digital_twin.onboarding.demo import SUPERVISOR_DEMO_ANSWERS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "reports/presentation/recording"
OUT = ROOT / "reports/generated/recording-workspace"


def prepare(client, *, include_turns=False, session_a_id=None, session_b_id=None, publish_releases=True):
    require_recording_runtime(client)
    records = []
    for index, (title, slug) in enumerate((("Systems", "systems-notes"),
                                         ("Release governance", "release-governance-notes"))):
        professor = ACTORS[index][1]
        course_id = ("course-a-recording", "course-b-recording")[index]
        headers = {"X-Account-ID": professor}
        def call(method, path, expected=200, **kwargs):
            response = client.request(method, path, headers={**headers, **kwargs.pop("headers", {})}, **kwargs)
            if response.status_code != expected:
                raise RuntimeError(f"{method} {path}: {response.status_code}: {response.text[:1000]}")
            return response.json()
        course = call("POST", "/api/professor/courses", 201, json={"title": title, "course_id": course_id})
        existing_session = (session_a_id, session_b_id)[index]
        session = (call("GET", f"/api/onboarding/sessions/{existing_session}")
                   if existing_session else call("POST", "/api/onboarding/sessions", 201))
        base = f"/api/onboarding/sessions/{session['session_id']}"
        if not existing_session:
            for answer in SUPERVISOR_DEMO_ANSWERS:
                session = call("POST", base + "/messages", json={"content": answer})
        pdf = ASSETS / f"{slug}.pdf"
        session = call("POST", base + "/source-inventory", json={
            "name": pdf.name, "mime_type": "application/pdf", "size_bytes": pdf.stat().st_size,
            "permission_status": "approved", "source_label": "course-approved",
            "excluded": False, "sensitive": False, "notes": "Synthetic recording material; all demo uses allowed."})
        session = call("POST", f"/api/professor/courses/{course_id}/onboarding-sessions/{session['session_id']}/bind")
        for item in session["approval_checklist"]:
            if item["id"].startswith("preview_") or item["id"] == "professor_release_approval":
                continue
            session = call("PATCH", base + "/approval-checklist/" + item["id"], json={"checked": True})
        for preview in session["preview_cases"]:
            session = call("PATCH", base + f"/preview-cases/{preview['id']}/decision",
                           json={"decision": "accepted", "reason": "Synthetic recording rehearsal."})
        session = call("POST", base + "/preview-cases", json={"prompt": "Ask what I have tried before giving a hint.", "tag": "teaching_behavior"})
        custom = session["preview_cases"][-1]
        session = call("PATCH", base + f"/preview-cases/{custom['id']}/decision",
                       json={"decision": "accepted", "reason": "Synthetic recording rehearsal."})
        session = call("PATCH", base + "/approval-checklist/professor_release_approval", json={"checked": True})
        profile_base = f"/api/professor/courses/{course_id}/teaching-profiles"
        profile = call("POST", profile_base, 201, json={
            "tone": "Patient and precise", "depth": "balanced", "explanation_structure": ["Explain", "Check"],
            "example_preferences": [title], "misconception_handling": "Check the explanation against approved sources.",
            "integrity_limits": "Require an attempt on assessed work.", "help_ladder": ["Question", "Hint", "Approved source"],
            "outreach_policy": "Private in-app practice with student consent."})
        preview = call("GET", profile_base + f"/{profile['profile_id']}/preview")
        assert len(preview["cases"]) == 10
        profile = call("POST", profile_base + f"/{profile['profile_id']}/approve", json={"preview_sha256": preview["preview_sha256"]})
        ingested = call("PUT", f"/api/professor/courses/{course_id}/sources/{slug}", 201,
                        params={"title": title + " teaching notes", "display_allowed": True},
                        headers={"Content-Type": "application/pdf"}, content=pdf.read_bytes())
        assert ingested["chunks"], "Real PDF ingestion must return evidence chunks."
        release = call("POST", f"/api/professor/courses/{course_id}/releases", 201, json={
            "session_id": session["session_id"], "profile_id": "student-tutor", "profile_version": "v1",
            "teaching_profile_id": profile["profile_id"], "release_id": f"recording-{index}-v1", "chunks": ingested["chunks"]})
        preflight = call("POST", f"/api/professor/releases/{release['id']}/preflight")
        assert preflight["passed"], preflight
        if publish_releases:
            release = call("POST", f"/api/professor/releases/{release['id']}/publish")
        for actor in ACTORS[2 + index * 2:4 + index * 2]:
            call("POST", f"/api/professor/courses/{course_id}/students", 201, json={"student_account_id": actor[1]})
        records.append({"course_id": course["id"], "professor_id": professor, "session_id": session["session_id"],
                        "release_id": release["id"], "source_checksum": ingested["source_checksum"],
                        "chunk_count": len(ingested["chunks"]), "teaching_preview_cases": len(preview["cases"]),
                        "preflight": preflight})
    if include_turns:
        configured = client.post("/__recording/configure", headers={"X-Recording-Control": "local-synthetic-only"})
        assert configured.status_code == 200, configured.text
        questions = ("What is cache coherence?", "What is virtual memory?", "What does a release policy define?",
                     "What are approval and withdrawal controls in a release policy?")
        facts = ("replicated processor data consistent", "process addresses to physical memory pages",
                 "approval and withdrawal controls", "approval and withdrawal controls")
        for index, (actor, question) in enumerate(zip(ACTORS[2:], questions, strict=True)):
            headers = {"X-Account-ID": actor[1]}
            course_id = records[index // 2]["course_id"]
            response = client.post(f"/api/student/courses/{course_id}/conversations", headers=headers)
            assert response.status_code == 201, response.text
            conversation = response.json()
            response = client.post(f"/api/student/conversations/{conversation['id']}/messages", headers=headers,
                json={"content": question, "request_id": f"recording-check-{index}"})
            assert response.status_code == 200, response.text
            turn = response.json()
            if turn.get("pending_clarification"):
                response = client.post(f"/api/student/conversations/{conversation['id']}/messages", headers=headers,
                    json={"content": "1", "request_id": f"recording-check-{index}-clarification"})
                assert response.status_code == 200, response.text
                turn = response.json()
            assert turn["citations"], turn
            assert all(c["course_id"] == course_id for c in turn["citations"])
            assert facts[index] in turn["tutor_message"]["content"], turn
            records[index // 2].setdefault("verified_turns", []).append(turn)
    return {"mode": "Synthetic deterministic demo; synchronous PDF ingestion", "courses": records,
            "scope": "Recording preparation, not release qualification or model/learning evaluation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published", action="store_true", help="Prepare fresh courses on recording API 8018 for later-scene retakes.")
    args = parser.parse_args()
    if args.published:
        with httpx.Client(base_url="http://127.0.0.1:8018", trust_env=False, timeout=60) as client:
            for actor in ACTORS[:2]:
                response = client.get("/api/professor/courses", headers={"X-Account-ID": actor[1]})
                response.raise_for_status()
                if response.json():
                    raise SystemExit("Recording courses already exist. Restart the recording workspace for a fresh retake.")
            result = prepare(client)
        name = "published-checkpoint.json"
    else:
        with tempfile.TemporaryDirectory(prefix="recording-check-") as directory:
            with TestClient(make_recording_app(Path(directory))) as client:
                result = prepare(client, include_turns=True)
        name = "verification.json"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(result, indent=2) + "\n")
    print(f"Prepared and checked two PDF-backed published courses: {OUT / name}")


if __name__ == "__main__":
    main()
