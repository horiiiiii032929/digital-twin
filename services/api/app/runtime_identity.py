"""Public composition identity and local worker heartbeats; never settings dumps."""

import hashlib
import json
import os
import math
from datetime import UTC, datetime
from pathlib import Path


def runtime_identity(app) -> dict:
    generator = app.state.student_service.generator
    graph = app.state.governed_autonomy_service.graph
    settings = app.state.settings
    selected = getattr(app.state, "experimental_tutoring_configuration", None)
    if selected is not None:
        selected = {key: selected[key] for key in (
            "version", "implementation_id", "model", "output_cap", "reasoning_effort",
            "runtime_flags", "role_configuration", "observed_openai_transport_configurations",
        ) if key in selected}
    database_path = getattr(app.state.student_repository, "path", None)
    learning = getattr(app.state, "post_report_learning_configuration", None)
    if learning is not None:
        learning = {key: learning[key] for key in (
            "input", "estimator", "planner", "goal_completion", "status", "assessment", "retrieval_context",
            "assessment_model",
        ) if key in learning}
    database_comparable = isinstance(database_path, str) and database_path != ":memory:"
    identity = {
        "schema_version": 1,
        "source_sha256": app.state.implementation_source_sha256,
        "generator_implementation": getattr(generator, "implementation_id", type(generator).__name__),
        "generator_model": getattr(generator, "model_id", None),
        "planner_implementation": type(graph.planner).__name__,
        "planner_model": getattr(graph.planner, "model_id", None),
        "learning_configuration": learning,
        "server_tutoring_mode": settings.student_tutoring_mode.value,
        "evidence_gate_mode": settings.evidence_gate_mode.value,
        "experimental_version": selected.get("version") if selected else None,
        "experimental_configuration": selected,
        "database_binding_comparable": database_comparable,
        "database_binding_sha256": hashlib.sha256(str(Path(database_path).resolve()).encode()).hexdigest() if database_comparable else None,
    }
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {**identity, "composition_sha256": digest,
        "scope": "Observed composition fields and database binding; equality is not semantic quality qualification or a full deployment verification."}


def write_worker_heartbeat(app, *, worker_id: str, status: str, poll_seconds: float, error_type: str | None = None):
    directory = app.state.settings.data_root / "worker-status"
    directory.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(worker_id.encode()).hexdigest()
    destination = directory / f"{key}.json"
    temporary = directory / f"{key}.{os.getpid()}.tmp"
    payload = {"worker_key": key, "status": status, "updated_at": datetime.now(UTC).isoformat(),
        "poll_seconds": poll_seconds, "composition_sha256": runtime_identity(app)["composition_sha256"],
        "error_type": error_type}
    temporary.write_text(json.dumps(payload, sort_keys=True) + "\n")
    temporary.replace(destination)


def worker_status(app, identity: dict) -> list[dict]:
    now = datetime.now(UTC)
    rows = []
    for path in sorted((app.state.settings.data_root / "worker-status").glob("*.json"))[:100]:
        try:
            if path.stat().st_size > 16384:
                continue
            row = json.loads(path.read_text())
            updated = datetime.fromisoformat(row["updated_at"])
            age = (now - updated).total_seconds()
            interval = float(row["poll_seconds"])
            if not math.isfinite(interval) or interval <= 0:
                raise ValueError("invalid heartbeat interval")
            stale = age < 0 or age > max(120, interval * 3)
            rows.append({"worker_key": row["worker_key"], "status": row["status"],
                "updated_at": row["updated_at"], "stale": stale,
                "composition_matches_api": identity["database_binding_comparable"] and row["composition_sha256"] == identity["composition_sha256"],
                "error_type": row.get("error_type")})
        except (OSError, ValueError, KeyError, TypeError):
            rows.append({"worker_key": path.stem, "status": "unreadable", "stale": True,
                "composition_matches_api": False, "updated_at": None, "error_type": None})
    return rows
