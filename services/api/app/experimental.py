"""Explicit local experimental ASGI composition; the default entrypoint is unchanged."""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from services.api.app.config import AppSettings, AutonomyPlannerMode, EvidenceGateMode, GeneratorMode, RuntimeMode, StudentTutoringMode
from services.api.app.factory import create_app
from services.api.app.post_report_configuration import post_report_runtime_flags
from services.llm import OpenAiResponsesClient
from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration


WEB_DIST = Path(__file__).resolve().parents[3] / "apps/web/dist"

def validate_transport_configuration(client, expected):
    pending, seen, observed_transports = [client], set(), []
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if len(seen) > 12:
            raise ValueError("experimental transport wrapper chain is too deep")
        if isinstance(current, OpenAiResponsesClient):
            observed_config = {"model": current.model, "output_cap": current.max_output_tokens,
                "reasoning_effort": current.reasoning_effort}
            if any(observed_config[key] != expected[key] for key in observed_config):
                raise ValueError("experimental transport model or output cap differs from selector")
            observed_transports.append(observed_config)
            continue
        nested_objects = [getattr(current, name, None) for name in ("client", "transport", "serializer")]
        adapter = getattr(current, "experimental_transport_configuration", None)
        if not any(item is not None for item in nested_objects):
            if not isinstance(adapter, dict) or any(adapter.get(key) != expected[key] for key in ("model", "output_cap", "reasoning_effort")):
                raise ValueError("unknown transport capability; explicit test adapter metadata is required")
        for name in ("client", "transport", "serializer"):
            nested = getattr(current, name, None)
            if nested is not None:
                pending.append(nested)
    return observed_transports


def build_experimental_app(settings: AppSettings, candidate: str, *, transport=None, serve_web=False):
    """Use normal credential authentication and validated persistent configuration."""
    if serve_web:
        validate_web_build()
    selection = experimental_tutoring_configuration(candidate)
    if settings.mode != RuntimeMode.STAGING:
        raise ValueError("experimental application requires credential-authenticated staging settings")
    if settings.generator_mode != GeneratorMode.DETERMINISTIC:
        raise ValueError("experimental selector excludes an independently configured external generator")
    if (settings.student_tutoring_mode != StudentTutoringMode.GOVERNED_AUTONOMOUS_TUTORING_GRAPH
        or settings.autonomy_planner_mode != AutonomyPlannerMode.OPENAI_GPT_5_6_LUNA_POLICY_VALUE
        or settings.evidence_gate_mode != EvidenceGateMode.DOMINANCE_SCOPED_AMBIGUITY_SAFE_V3):
        raise ValueError("experimental application requires matching governed tutoring, Luna planner and scoped evidence modes")
    configured = settings
    roles = selection.get("role_configuration")
    if roles:
        revision_client = None
        if "revision" in roles and selection.get("final_audit_prompt_version") == "v2":
            from src.digital_twin.generation.final_response_audit import make_final_audit_client
            revision_client = make_final_audit_client(role="repair", model=roles["revision"]["model"])
        client = transport or ExperimentalGenerationRoleRouter(
            planner_client=OpenAiResponsesClient(roles["planner"]["model"], max_output_tokens=3000,
                reasoning_effort=roles["planner"]["reasoning_effort"], timeout_seconds=30),
            generation_client=OpenAiResponsesClient(roles["generation"]["model"], max_output_tokens=3000,
                reasoning_effort=roles["generation"]["reasoning_effort"], timeout_seconds=30,
                experimental_sol_enabled=roles["generation"]["model"] == "gpt-5.6-sol"),
            **({"revision_client": revision_client or OpenAiResponsesClient(roles["revision"]["model"],
                max_output_tokens=3000, reasoning_effort=roles["revision"]["reasoning_effort"],
                timeout_seconds=30, experimental_sol_enabled=True)} if "revision" in roles else {}),
            role_configuration=roles)
        if not isinstance(client, ExperimentalGenerationRoleRouter) or client.role_configuration != roles:
            raise ValueError("experimental model variant requires exact role-routing configuration")
        observed_transports = []
        for role, expected in roles.items():
            observed_transports.extend({**entry, "role": role} for entry in
                validate_transport_configuration(client.client_for_role(role), expected))
    else:
        client = transport or OpenAiResponsesClient(selection["model"], max_output_tokens=selection["output_cap"],
            reasoning_effort=selection["reasoning_effort"], timeout_seconds=30)
        observed_transports = validate_transport_configuration(client, selection)
    app = create_app(settings=configured, source_root=configured.source_root,
        region_crop_root=configured.region_crop_root, autonomy_planner_client=client,
        provider_max_concurrency=5, **selection["runtime_flags"], **post_report_runtime_flags())
    observed = app.state.student_service.generator.implementation_id
    if observed != selection["implementation_id"]:
        closed = set()
        for name in ("ingestion_job_repository", "identity_repository", "student_repository", "session_repository"):
            repository = getattr(app.state, name, None)
            close = getattr(repository, "close", None)
            if close is not None and id(repository) not in closed:
                close()
                closed.add(id(repository))
        raise RuntimeError("actual experimental application differs from selected implementation")
    app.state.experimental_tutoring_configuration = {**selection, "observed_implementation_id": observed,
        "provider_max_concurrency": 5, "observed_openai_transport_configurations": observed_transports,
        "base_qualification_is_not_candidate_semantic_qualification": True}
    if serve_web:
        @app.get("/student", include_in_schema=False)
        @app.get("/professor", include_in_schema=False)
        @app.get("/professor/setup", include_in_schema=False)
        @app.get("/professor/delivery", include_in_schema=False)
        def known_application_route():
            return FileResponse(WEB_DIST / "index.html")

        @app.api_route("/api/{unmatched_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"], include_in_schema=False)
        def unknown_api_route(unmatched_path: str):
            raise HTTPException(status_code=404, detail="Not Found")
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="experimental-web")
    return app


def validate_web_build():
    try:
        marker = json.loads((WEB_DIST / "build-configuration.json").read_text())
    except (OSError, ValueError) as error:
        raise ValueError("build the session UI with VITE_AUTH_MODE=session npm run build:web") from error
    if not (WEB_DIST / "index.html").is_file() or marker != {"schema_version": 1, "auth_mode": "session"}:
        raise ValueError("experimental UI requires a session-auth build: VITE_AUTH_MODE=session npm run build:web")


def create_experimental_app():
    """Uvicorn factory: require an explicit version and existing staging settings."""
    load_dotenv(Path(__file__).resolve().parents[3] / ".env", override=False)
    candidate = os.environ.get("APP_EXPERIMENTAL_TUTORING_CANDIDATE", "").strip()
    if not candidate:
        raise ValueError("set APP_EXPERIMENTAL_TUTORING_CANDIDATE to an explicit experimental version")
    return build_experimental_app(AppSettings.from_env(), candidate, serve_web=True)
