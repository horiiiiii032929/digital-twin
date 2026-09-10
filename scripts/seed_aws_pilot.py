"""Provision the synthetic pack through the deployed pilot's authenticated APIs.

Defaults to a read-only local plan. Credentials/resume state stay in ignored output.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import time

import httpx

from scripts.validate_pilot_seed import PACK, ROOT, validate
from src.digital_twin.onboarding.demo import SUPERVISOR_DEMO_ANSWERS
from src.digital_twin.onboarding.interview import STEP_ORDER


def generate_demo_password() -> str:
    """Retain 160 random bits while satisfying the existing identity policy."""
    return "Aa1-" + secrets.token_urlsafe(20)


def private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with os.fdopen(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


class SeedRun:
    def __init__(self, state_path: Path, outputs: dict):
        self.path = state_path
        self.outputs = outputs
        self.url = outputs["AppUrlOutput"]
        self.manifest = json.loads((PACK / "manifest.json").read_text())
        digest = hashlib.sha256((PACK / "manifest.json").read_bytes()).hexdigest()
        self.state = json.loads(state_path.read_text()) if state_path.exists() else {
            "seed_id": self.manifest["seed_id"], "manifest_sha256": digest,
            "url": self.url, "accounts": {}, "courses": {}, "checks": [],
        }
        if self.state["manifest_sha256"] != digest or self.state["url"] != self.url:
            raise ValueError("Seed content or destination changed; do not overwrite existing seed state")
        self.clients = []

    def save(self):
        private_json(self.path, self.state)

    def client(self):
        client = httpx.Client(base_url=self.url, timeout=90, headers={"Origin": self.url}, follow_redirects=False)
        self.clients.append(client)
        return client

    def request(self, client, method, path, **kwargs):
        response = client.request(method, path, **kwargs)
        if response.status_code >= 400:
            # Never print request bodies, cookies, passwords or arbitrary response data.
            try:
                detail = response.json().get("detail", {})
                code = detail.get("code", "request_rejected") if isinstance(detail, dict) else "validation_error"
            except ValueError:
                code = "non_json_error"
            raise RuntimeError(f"{method} {path}: HTTP {response.status_code}, {code}")
        return response.json() if response.content else None

    def login(self, client, email, password):
        return self.request(client, "POST", "/api/auth/login", json={"email": email, "password": password})

    def run(self, approve_reviews: bool):
        raw = subprocess.run([
            "aws", "secretsmanager", "get-secret-value", "--secret-id", self.outputs["RuntimeSecretArnOutput"],
            "--profile", "digital-twin", "--region", "ap-southeast-1", "--output", "json",
        ], capture_output=True, text=True, check=True)
        secret = json.loads(json.loads(raw.stdout)["SecretString"])
        admin = self.client()
        self.login(admin, secret["ADMIN_EMAIL"], secret["BOOTSTRAP_ADMIN_PASSWORD"])
        accounts = self.state["accounts"]
        for item in self.manifest["accounts"]:
            key = item["id"]
            if key not in accounts:
                accounts[key] = {"email": item["email"], "role": item["role"], "password": generate_demo_password()}
                self.save()  # Credential persists before a possibly interrupted request.
            entry = accounts[key]
            if "account_id" not in entry:
                probe = self.client()
                response = probe.post("/api/auth/login", json={"email": entry["email"], "password": entry["password"]})
                if response.status_code == 200:
                    profile = response.json()
                else:
                    profile = self.request(admin, "POST", "/api/admin/accounts", json={
                        "email": entry["email"], "display_name": item["display_name"], "role": item["role"],
                        "temporary_password": entry["password"],
                    })
                entry["account_id"] = profile["account_id"]
                self.save()
        print("Eight demo identities provisioned; credential values omitted.", flush=True)
        profile = json.loads((ROOT / self.manifest["release_profile_path"]).read_text())
        for course in self.manifest["courses"]:
            cid = course["id"]
            entry = self.state["courses"].setdefault(cid, {})
            owner = accounts[course["owner_professor_id"]]
            client = self.client()
            self.login(client, owner["email"], owner["password"])
            base = f"/api/professor/courses/{cid}"
            existing = self.request(client, "GET", "/api/professor/courses")
            found = next((view for view in existing if view["course_id"] == cid), None)
            if found is None:
                self.request(client, "POST", "/api/professor/courses", json={"course_id": cid, "title": course["title"]})
            elif found["title"] != course["title"]:
                raise ValueError("Existing course conflicts with the seed")
            for membership in self.manifest["memberships"]:
                if membership["course_id"] == cid and membership["role"] == "student" and membership["active"]:
                    marker = "membership:" + membership["account_id"]
                    if not entry.get(marker):
                        self.request(client, "POST", base + "/students", json={"student_account_id": accounts[membership["account_id"]]["account_id"]})
                        entry[marker] = True
                        self.save()
            if "session_id" not in entry:
                session = self.request(client, "POST", "/api/onboarding/sessions")
                entry["session_id"] = session["session_id"]
                self.save()
            sb = "/api/onboarding/sessions/" + entry["session_id"]
            session = self.request(client, "GET", sb)
            if session.get("course_id") is None:
                session = self.request(client, "POST", base + "/onboarding-sessions/" + entry["session_id"] + "/bind")
            steps = STEP_ORDER
            while session.get("policy") is None:
                step = session["current_step"]
                if step not in steps:
                    raise RuntimeError(f"Unexpected interview step: {step}")
                session = self.request(client, "POST", sb + "/messages", json={"content": SUPERVISOR_DEMO_ANSWERS[steps.index(step)]})
            sources = [s for s in self.manifest["sources"] if s["course_id"] == cid]
            for source in sources:
                filename = Path(source["path"]).name
                if not any(s["name"] == filename for s in session["source_inventory"]):
                    session = self.request(client, "POST", sb + "/source-inventory", json={
                        "name": filename, "mime_type": source["mime_type"], "size_bytes": (PACK / source["path"]).stat().st_size,
                        "permission_status": source["permission_status"], "source_label": source["source_label"],
                        "excluded": False, "sensitive": False, "notes": source["provenance"],
                    })
                if source["permission_status"] != "approved":
                    continue
                jobs = entry.setdefault("jobs", {})
                if source["id"] not in jobs:
                    job = self.request(client, "PUT", base + "/sources/" + source["id"],
                        params={"title": filename, "display_allowed": "true", "deidentified_reviewed": "true"},
                        headers={"Content-Type": source["mime_type"], "Idempotency-Key": source["id"]},
                        content=(PACK / source["path"]).read_bytes())
                    jobs[source["id"]] = job["id"]
                    self.save()
                for _ in range(120):
                    job = self.request(client, "GET", "/api/professor/ingestion-jobs/" + jobs[source["id"]])
                    if job["status"] == "succeeded":
                        break
                    if job["status"] in ("failed", "cancelled"):
                        raise RuntimeError("Ingestion failed for " + source["id"])
                    time.sleep(2)
                else:
                    raise RuntimeError("Ingestion timed out")
            if course["target_release_status"] == "draft":
                entry["status"] = "onboarding-draft"
                self.save()
                continue
            if entry.get("status") == "published":
                self.ensure_domain(client, course, entry)
                continue
            if not entry.get("policy_prepared"):
                for field_id, value in [
                    ("knowledge_source_policy", {"source_strictness": "course_only", "preview_source_mode": "course_only", "confirmed": True}),
                    ("disallowed_private_sources", ["private student data", "consent records", "raw transcripts", "private forum exports"]),
                    ("sensitive_data_handling", "Sensitive data remains excluded; only synthetic examples are used."),
                    ("academic_integrity_policy", course["integrity_policy"]),
                ]:
                    session = self.request(client, "PATCH", sb + "/policy-fields/" + field_id, json={"value": value, "status": "resolved"})
                if not any(p["id"].startswith("custom-") for p in session["preview_cases"]):
                    session = self.request(client, "POST", sb + "/preview-cases", json={"prompt": course["objective"], "tag": "teaching_behavior"})
                entry["policy_prepared"] = True
                self.save()
            if "teaching_profile_id" not in entry:
                teaching = self.request(client, "POST", base + "/teaching-profiles", json={
                    "tone": "Patient and precise", "depth": "balanced", "explanation_structure": ["explain", "example", "check"],
                    "example_preferences": [course["objective"]], "misconception_handling": course["teaching_style"],
                    "integrity_limits": course["integrity_policy"], "help_ladder": ["question", "hint", "approved source"],
                    "outreach_policy": "No proactive outreach in this synthetic demo.",
                })
                entry["teaching_profile_id"] = teaching["profile_id"]
                self.save()
            tb = base + "/teaching-profiles/" + entry["teaching_profile_id"]
            preview = self.request(client, "GET", tb + "/preview")
            session = self.request(client, "GET", sb)
            private_json(self.path.parent / (cid + "-review.json"), {"session": session, "teaching_preview": preview})
            if not approve_reviews:
                print(cid + ": synthetic review prepared; publication pending review.", flush=True)
                continue
            if not entry.get("reviews_approved"):
                for case in session["preview_cases"]:
                    session = self.request(client, "PATCH", sb + "/preview-cases/" + case["id"] + "/decision", json={"decision": "accepted", "reason": "Synthetic workflow fixture reviewed; built-in CSRF templates are not course-specific evidence. Verify actual course behavior separately; no human evaluation claim."})
                # Final approval must follow all other review decisions.
                items = sorted(session["approval_checklist"], key=lambda item: item["id"] == "professor_release_approval")
                for item in items:
                    if item["blocks_release"]:
                        session = self.request(client, "PATCH", sb + "/approval-checklist/" + item["id"], json={"checked": True})
                if session["policy"]["release_status"] != "approved":
                    raise RuntimeError("Policy blockers remain: " + json.dumps(session["release_blockers"]))
                self.request(client, "POST", tb + "/approve", json={"preview_sha256": preview["preview_sha256"]})
                entry["reviews_approved"] = True
                self.save()
            rid = cid + "-release-1"
            existing = self.request(client, "GET", "/api/professor/courses")
            current = next(v for v in existing if v["course_id"] == cid)
            if not any(r["id"] == rid for r in current["releases"]):
                self.request(client, "POST", base + "/releases", json={
                    "session_id": entry["session_id"], "profile_id": profile["profile_id"], "profile_version": profile["profile_version"],
                    "teaching_profile_id": entry["teaching_profile_id"], "ingestion_job_ids": list(entry["jobs"].values()), "release_id": rid,
                })
            result = self.request(client, "POST", "/api/professor/releases/" + rid + "/preflight")
            entry["preflight"] = result
            self.save()
            if not result["passed"]:
                raise RuntimeError("Release preflight failed: " + cid)
            self.request(client, "POST", "/api/professor/releases/" + rid + "/publish")
            entry.update(status="published", release_id=rid)
            self.save()
            self.ensure_domain(client, course, entry)
            print(cid + ": published after deterministic preflight.", flush=True)
        if approve_reviews:
            for item in self.manifest["accounts"]:
                entry = accounts[item["id"]]
                if item["status"] == "revoked" and not entry.get("revoked"):
                    self.request(admin, "DELETE", "/api/admin/accounts/" + entry["account_id"])
                    entry["revoked"] = True
                    self.save()
        self.save()

    def ensure_domain(self, client, course, entry):
        spec_bytes = (PACK / "domain-specs.json").read_bytes()
        digest = hashlib.sha256(spec_bytes).hexdigest()
        specs = json.loads(spec_bytes)["courses"][course["id"]]
        if entry.get("domain_spec_sha256") not in (None, digest):
            raise ValueError("Domain inputs changed; use an explicit new domain version")
        base = "/api/professor/courses/" + course["id"] + "/domain-model"
        existing = self.request(client, "GET", base, params={"release_id": entry["release_id"]})
        if existing is not None:
            if entry.get("domain_spec_sha256") != digest:
                raise ValueError("Existing domain model has no matching seed checkpoint; inspect it before adopting")
            return
        chunks = []
        for job_id in entry["jobs"].values():
            job = self.request(client, "GET", "/api/professor/ingestion-jobs/" + job_id)
            chunks.extend(job["result"]["chunks"])
        concepts = []
        for spec in specs:
            matches = [chunk for chunk in chunks if spec["excerpt"] in chunk["text"]]
            if len(matches) != 1:
                raise ValueError("Concept excerpt must identify exactly one ingested chunk")
            chunk = matches[0]
            start = chunk["text"].index(spec["excerpt"])
            concepts.append({
                "concept_id": course["id"] + "-" + spec["key"], "label": spec["label"],
                "description": spec["excerpt"], "canonical_ranges": [{
                    "source_artifact_id": chunk["source_artifact_id"], "source_version": chunk["source_version"],
                    "source_sha256": chunk["source_checksum"], "locator": chunk["locator"],
                    "char_start": start, "char_end": start + len(spec["excerpt"]),
                }],
            })
        self.request(client, "POST", base, json={
            "release_id": entry["release_id"], "version": 1, "concepts": concepts,
            "objectives": [{"objective_id": course["id"] + "-objective", "statement": course["objective"],
                            "concept_ids": [c["concept_id"] for c in concepts]}],
        })
        entry["domain_spec_sha256"] = digest
        self.save()
        print(course["id"] + ": approved source-bound domain model created.", flush=True)

    def close(self):
        for client in self.clients:
            try:
                client.post("/api/auth/logout")
            finally:
                client.close()


def finalize_inactive_membership(outputs: dict) -> None:
    """The API has no inactive-membership write route; use the domain repository via SSM."""
    code = """from services.api.app.config import AppSettings
from src.digital_twin.identity import SQLiteIdentityRepository
from src.digital_twin.student import SQLiteStudentRepository
from src.digital_twin.student.models import CourseMembership, MembershipRole
settings=AppSettings.from_env(require_provider_credentials=False)
identities=SQLiteIdentityRepository(settings.database_path)
repo=SQLiteStudentRepository(settings.database_path)
credential=identities.get_credential_by_email('eli.student@example.test')
if credential is None:
 raise RuntimeError('Expected demo identity missing')
cid='demo-pilot-v1-systems'
existing=repo.get_membership(credential.account_id,cid)
if existing is not None and existing.active:
 raise RuntimeError('Refusing to overwrite an active membership')
repo.save_membership(CourseMembership(account_id=credential.account_id,course_id=cid,role=MembershipRole.STUDENT,active=False))
identities.close()
repo.close()
print('Inactive synthetic membership verified')
"""
    def aws(*arguments):
        result = subprocess.run(["aws", *arguments, "--profile", "digital-twin", "--region", "ap-southeast-1", "--output", "json"], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    command = "set -eu\ndocker exec -i digital-twin-api python - <<'PY'\n" + code + "\nPY\n"
    sent = aws("ssm", "send-command", "--instance-ids", outputs["InstanceIdOutput"], "--document-name", "AWS-RunShellScript",
               "--parameters", json.dumps({"commands": [command]}))
    command_id = sent["Command"]["CommandId"]
    for _ in range(60):
        time.sleep(2)
        result = aws("ssm", "get-command-invocation", "--command-id", command_id, "--instance-id", outputs["InstanceIdOutput"])
        if result["Status"] == "Success":
            print("Inactive synthetic membership verified through SSM.")
            return
        if result["Status"] not in {"Pending", "InProgress", "Delayed"}:
            raise RuntimeError("Inactive membership finalization failed; inspect SSM command " + command_id)
    raise RuntimeError("SSM finalization pending; inspect " + command_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--approve-demo-reviews", action="store_true")
    parser.add_argument("--state", type=Path, default=ROOT / "output/aws-pilot-seed/state.json")
    args = parser.parse_args()
    print(json.dumps(validate()))
    if not args.apply:
        print("Read-only plan; pass --apply to provision demo data.")
        return
    output = json.loads((ROOT / "infra/cdk/cdk-outputs.json").read_text())["DigitalTwinPilot"]
    if output["AppUrlOutput"] != "https://d3cccbyk2qjxd6.cloudfront.net":
        raise ValueError("Unexpected deployment destination")
    args.state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(args.state.parent, 0o700)
    with (args.state.parent / ".seed.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run = SeedRun(args.state, output)
        try:
            run.run(args.approve_demo_reviews)
            if args.approve_demo_reviews:
                finalize_inactive_membership(output)
        finally:
            run.close()


if __name__ == "__main__":
    main()
