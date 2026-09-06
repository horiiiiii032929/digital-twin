"""Paired, network-free goal-scope regression on the actual product adapter.

Run each arm from its corresponding source snapshot; never relabel candidate code
as the baseline. Archives include code/configuration only, never local data or env.
"""

from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import datetime
from hashlib import sha256
import importlib.metadata
import json
from pathlib import Path
import resource
import socket
import sqlite3
import sys
from unittest.mock import patch
from zipfile import ZipFile, ZIP_DEFLATED

from scripts.run_governed_full_autonomy_v2_1_hidden_state_learner_014 import run_program
from scripts.run_governed_full_autonomy_v2_1_multi_concept_confirmation_025 import (
    CONCEPT_CARDS, CONDITIONS, CONTRASTS, _decision,
)
from src.digital_twin.evaluation.learner_simulator import PERSONAS, SimulatorFamily
from src.digital_twin.student.autonomy_control import DeterministicAutonomousGoalManager

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "goal-completion-scope-development-001"
SEEDS = (9101, 9102, 9103)


def target_ready(targets: list[str], snapshot: dict[str, dict]) -> bool:
    """Independent operational contract; do not call the goal manager as oracle."""
    return bool(targets) and all(
        (item := snapshot.get(concept)) is not None
        and item["correct_evidence_count"] >= 2
        and item["incorrect_evidence_count"] == 0
        and item["attribution_confidence"] >= 0.5
        for concept in targets
    )


def audit_completions(runtime_root: Path) -> dict:
    records = []
    statuses: Counter = Counter()
    databases = sorted(runtime_root.rglob("*.sqlite3"))
    for db in databases:
        wal = Path(str(db) + "-wal")
        if wal.exists() and wal.stat().st_size:
            raise ValueError(f"database is not checkpointed: {db}")
        connection = sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            statuses.update(dict(connection.execute(
                "SELECT status, COUNT(*) FROM autonomous_goals GROUP BY status"
            )))
            for (encoded,) in connection.execute(
                "SELECT goal_json FROM autonomous_goals WHERE status='completed'"
            ):
                goal = json.loads(encoded)
                row = connection.execute(
                    "SELECT model_json FROM course_domain_models WHERE release_id=?",
                    (goal["release_id"],),
                ).fetchone()
                domain = json.loads(row[0]) if row else {}
                objectives = [o for o in domain.get("objectives", [])
                              if o["statement"] == goal["approved_course_objective"]]
                targets = objectives[0]["concept_ids"] if len(objectives) == 1 else []
                cutoff = datetime.fromisoformat(goal["updated_at"])
                # Attribution rows are complete snapshots at committed revisions.
                # Use observation time: persistence timestamps use the wall clock.
                latest = {}
                for conv, revision, observation in connection.execute(
                    "SELECT d.conversation_id, d.next_revision, o.observation_json "
                    "FROM learner_state_deltas_v2 d "
                    "JOIN learner_observations_v2 o ON o.observation_id=d.observation_id "
                    "JOIN conversations c ON c.id=d.conversation_id "
                    "WHERE c.student_id=? AND o.course_id=? AND o.release_id=? "
                    "ORDER BY d.next_revision",
                    (goal["student_id"], goal["course_id"], goal["release_id"]),
                ):
                    if datetime.fromisoformat(json.loads(observation)["observed_at"]) <= cutoff:
                        latest[conv] = revision
                snapshots = []
                for conv, revision in latest.items():
                    snapshot = dict(
                        (concept, json.loads(attribution))
                        for concept, attribution in connection.execute(
                            "SELECT concept_id, attribution_json FROM learner_concept_attributions_v2 "
                            "WHERE conversation_id=? AND revision=?", (conv, revision),
                        )
                    )
                    snapshots.append({"conversation_id": conv, "revision": revision,
                                      "attributions": snapshot,
                                      "target_ready": target_ready(targets, snapshot)})
                records.append({
                    "database": str(db.relative_to(runtime_root)),
                    "database_sha256": sha256(db.read_bytes()).hexdigest(),
                    "goal_id": goal["goal_id"], "objective": goal["approved_course_objective"],
                    "completed_at": goal["updated_at"], "targets": targets,
                    "snapshots": snapshots,
                    "supported": any(s["target_ready"] for s in snapshots),
                })
        finally:
            connection.close()
    unsupported = [r for r in records if not r["supported"]]
    return {
        "database_count": len(databases), "goal_status_counts": dict(statuses),
        "completed": len(records), "supported": len(records) - len(unsupported),
        "unsupported": len(unsupported),
        "affected_histories": len({r["database"] for r in unsupported}),
        "unmapped": sum(not r["targets"] for r in records), "records": records,
        "limitations": [
            "Final database audit cannot disambiguate commits with identical virtual timestamps.",
            "A completion is supported if one same-student/course/release conversation has eligible evidence; conversations are never pooled.",
            "Operational evidence eligibility is not human mastery or a pedagogical quality score.",
        ],
    }


def source_files() -> list[Path]:
    return sorted({
        *(p for folder in ("src", "services", "scripts") for p in (ROOT / folder).rglob("*.py")),
        *(ROOT / "research/05_evaluation/profiles").glob("*.json"),
        ROOT / "pyproject.toml", ROOT / "uv.lock",
    })


async def run(arm: str, output: Path) -> None:
    expected = f"deterministic-autonomous-goal-manager-{'v1' if arm == 'baseline' else 'v2'}"
    if DeterministicAutonomousGoalManager.implementation_id != expected:
        raise ValueError(f"{arm} requires {expected}; use the matching archived source")
    output.mkdir(parents=True, exist_ok=False)
    files = source_files()
    hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in files}
    with ZipFile(output / "source.zip", "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, str(path.relative_to(ROOT)))
    manifest = {
        "run_id": f"{PROGRAM_ID}-{arm}", "arm": arm, "source_sha256": hashes,
        "python": sys.version, "packages": {
            name: importlib.metadata.version(name)
            for name in ("pydantic", "langgraph", "langgraph-checkpoint-sqlite")
        },
        "dataset": {"version": "goal-scope-histories-v1", "seeds": SEEDS,
                    "concept_source": "multi-concept-confirmation-025", "days": 30},
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    original_connect = socket.socket.connect

    def deny_network(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("external network forbidden for goal-scope evaluation")
        return original_connect(sock, address)

    with patch.object(socket.socket, "connect", deny_network):
        summary = await run_program(
            output_dir=output, conditions=CONDITIONS, personas=PERSONAS,
            families=tuple(SimulatorFamily), seeds=SEEDS, days=30,
            provider_backed=False, resamples=1000, program_id=manifest["run_id"],
            concept_cards=CONCEPT_CARDS, fixture_id="goal-scope-histories-v1",
            contrasts=CONTRASTS,
        )
    if any(sha256(p.read_bytes()).hexdigest() != hashes[str(p.relative_to(ROOT))] for p in files):
        raise RuntimeError("source changed during the run; retain output as invalid")
    audit = audit_completions(output / "runtime")
    (output / "goal-audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    _, gates = _decision(summary)
    gates["target-scoped-completions"] = {"pass": audit["unsupported"] == 0, "observed": audit["unsupported"], "threshold": 0}
    gates["positive-completions"] = {"pass": audit["supported"] > 0, "observed": audit["supported"], "threshold": 1}
    responses = [json.loads(line) for line in (output / "responses.jsonl").read_text().splitlines()]
    gates["restart-consistency"] = {"pass": all(
        r["final_state"]["restart_count"] == 1
        and len(checks := r["diagnostic_trace"]["independent_evidence_v2"]["restart_checks"]) == 1
        and all(c["before_sha256"] == c["after_sha256"] for c in checks)
        for r in responses
    )}
    gates["completed-histories"] = {"pass": all(r["operational_status"] == "completed" for r in responses)}
    gates["database-coverage"] = {"pass": audit["database_count"] == summary["run"]["cases"]}
    result = {
        "run_id": manifest["run_id"], "gates": gates,
        "decision": "keep" if all(g["pass"] for g in gates.values()) else "refine",
        "peak_memory_native_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "peak_memory_unit": "bytes" if sys.platform == "darwin" else "KiB",
        "responses": len(responses), "summary": summary,
        "goal_audit": {k: v for k, v in audit.items() if k != "records"},
    }
    (output / "decision.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("gates", "summary")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.arm, args.output_dir))


if __name__ == "__main__":
    main()
