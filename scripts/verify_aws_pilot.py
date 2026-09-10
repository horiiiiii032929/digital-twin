"""Check the deployed AWS HTTPS/auth boundary without exposing credentials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

import httpx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outputs", type=Path, default=Path("infra/cdk/cdk-outputs.json"))
    args = parser.parse_args()
    outputs = json.loads(args.outputs.read_text())["DigitalTwinPilot"]
    url = outputs["AppUrlOutput"]
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".cloudfront.net"):
        raise SystemExit("Expected this stack's CloudFront HTTPS URL")
    response = subprocess.run([
        "aws", "secretsmanager", "get-secret-value", "--secret-id", outputs["RuntimeSecretArnOutput"],
        "--profile", "digital-twin", "--region", "ap-southeast-1", "--output", "json",
    ], check=True, capture_output=True, text=True)
    secret = json.loads(json.loads(response.stdout)["SecretString"])
    credentials = {"email": secret["ADMIN_EMAIL"], "password": secret["BOOTSTRAP_ADMIN_PASSWORD"]}
    checks = []

    def expect(name: str, response: httpx.Response, status: int) -> None:
        passed = response.status_code == status
        checks.append({"case": name, "status": response.status_code, "passed": passed})
        if not passed:
            print(json.dumps({"url": url, "checks": checks}, indent=2))
            raise SystemExit(f"Failed {name}; response body omitted to protect account data")

    with httpx.Client(base_url=url, timeout=65, follow_redirects=False) as client:
        expect("https-readiness", client.get("/api/health/ready"), 200)
        expect("anonymous-session-denied", client.get("/api/auth/session"), 401)
        expect("synthetic-header-denied", client.get("/api/auth/session", headers={"X-Account-ID": "admin-primary"}), 401)
        expect("cross-origin-login-denied", client.post("/api/auth/login", json=credentials, headers={"Origin": "https://invalid.example.test"}), 403)
        login = client.post("/api/auth/login", json=credentials, headers={"Origin": url})
        expect("administrator-login", login, 200)
        try:
            cookie = login.headers.get("set-cookie", "").lower()
            secure = all(flag in cookie for flag in ("secure", "httponly", "samesite=strict"))
            checks.append({"case": "secure-cookie-flags", "passed": secure})
            if not secure:
                raise SystemExit("Session cookie flags failed; values omitted")
            expect("authenticated-session", client.get("/api/auth/session"), 200)
        finally:
            expect("logout", client.post("/api/auth/logout", headers={"Origin": url}), 204)
        expect("revoked-session-denied", client.get("/api/auth/session"), 401)
    print(json.dumps({"url": url, "checks": checks, "provider_calls": 0}, indent=2))


if __name__ == "__main__":
    main()
