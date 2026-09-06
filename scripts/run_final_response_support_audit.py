"""Finite paired final-response verification experiment; semantic scoring is external."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

from scripts.run_factual_revision_controls import public_revision_input, render_control_proposal
from scripts.run_final_profile_longitudinal import CASE_CONTEXT, RecordedRunClient, _append
from scripts.run_operational_dialogue_development import manifest as runtime_manifest
from src.digital_twin.generation.final_response_audit import (
    MODEL, QUALITY_TASK as QUALITY_TASK, REPAIR_TASK as REPAIR_TASK,
    SUPPORT_TASK as SUPPORT_TASK, QUARANTINE_TEXT,
    audit_final_response, make_final_audit_client, task_ids,
)
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "final-response-support-audit-001"
PROGRAM_IDS = {"v1": PROGRAM_ID, "v2": "final-response-support-audit-002"}
RESERVATION = .16
SOURCE_PATHS = (
    "scripts/run_final_response_support_audit.py",
    "src/digital_twin/repository_freeze.py",
    "tests/digital_twin/test_repository_freeze.py",
    "scripts/run_factual_revision_controls.py",
    "scripts/run_final_profile_longitudinal.py",
    "scripts/run_operational_dialogue_development.py",
    "tests/test_factual_revision_controls.py",
    "tests/test_conditional_revision_generation.py",
    "scripts/teaching_profile_responsiveness_packet.py",
    "tests/test_final_response_support_audit_runner.py",
    "src/digital_twin/generation/final_response_audit.py",
    "tests/test_final_response_audit.py",
    "research/04_experiments/2026-09-06-final-response-support-audit-plan.md",
    "research/04_experiments/2026-09-06-final-response-audit-contract-policy-refinement-plan.md",
)


def digest(content):
    return hashlib.sha256(content).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


class SharedAdmission:
    """Reservations never refunded; stop affects every subsequently admitted call."""

    def __init__(self, n, ledger):
        self.maximum = 4*n
        self.roles = {"audit": 3*n, "repair": n}
        self.counts = {"audit": 0, "repair": 0}
        self.calls = 0
        self.stopped = False
        self.reason = None
        self.lock = asyncio.Lock()
        self.ledger = ledger

    def stop(self, reason):
        self.stopped, self.reason = True, self.reason or reason

    async def admit(self, role, task):
        async with self.lock:
            if self.stopped or self.calls >= self.maximum or self.counts[role] >= self.roles[role]:
                self.stop("shared-admission-stop")
                _append(self.ledger, {"status": "blocked", "case": CASE_CONTEXT.get(), "role": role, "task": task, "reason": self.reason})
                raise ValueError("shared admission stopped")
            self.calls += 1
            self.counts[role] += 1
            _append(self.ledger, {"status": "admitted", "case": CASE_CONTEXT.get(), "role": role,
                                 "task": task, "attempt": self.calls, "reserved_usd": RESERVATION})


class ArmClient:
    """A single input/arm owns its sequence; role allowances cannot be borrowed."""

    def __init__(self, shared, clients, arm, case_id, variant="v1"):
        self.support_task, self.quality_task, self.repair_task = task_ids(variant)
        self.shared, self.clients, self.arm, self.case_id = shared, clients, arm, case_id
        self.tasks = []

    async def chat(self, messages, task):
        sequence = [self.support_task] if self.arm == "C1" else [self.quality_task, self.repair_task, self.quality_task]
        if len(self.tasks) >= len(sequence) or task != sequence[len(self.tasks)]:
            self.shared.stop("invalid-call-sequence")
            raise ValueError("invalid per-input call sequence")
        role = "repair" if task == self.repair_task else "audit"
        phase = "post_repair_audit" if len(self.tasks) == 2 else "repair" if role == "repair" else "initial_audit"
        token = CASE_CONTEXT.set(f"{self.case_id}/{self.arm}/{phase}/{role}")
        try:
            await self.shared.admit(role, task)
            self.tasks.append(task)
            try:
                return await self.clients[role].chat(messages, task)
            except BaseException:
                self.shared.stop("provider-or-request-failure")
                raise
        finally:
            CASE_CONTEXT.reset(token)


def rendered_text(proposal, public):
    value = render_control_proposal(proposal, public)
    if not value["completed"]:
        raise ValueError(value["error_code"])
    return value["answer"]["content"]


async def run(output, packet_path, *, bank, execute=False, injected_audit_client=None,
              injected_repair_client=None, input_provenance_paths=(), concurrency=4, expected_packet_sha256=None, variant="v1"):
    task_ids(variant)
    program_id = PROGRAM_IDS[variant]
    if bank not in {"exposed", "fresh"} or type(concurrency) is not int or not 1 <= concurrency <= 4:
        raise ValueError("explicit bank and concurrency 1 through 4 required")
    if execute:
        require_bounded_pilot_operation_allowed(program_id, "external_model_evaluation")
        if injected_audit_client is not None or injected_repair_client is not None:
            raise ValueError("injected transport cannot be labelled live")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("configured provider credential required")
    elif injected_audit_client is None or injected_repair_client is None:
        raise ValueError("both explicit injected role clients required")
    path = Path(packet_path).resolve()
    packet_bytes = path.read_bytes()
    if execute and (not expected_packet_sha256 or digest(packet_bytes) != expected_packet_sha256):
        raise ValueError("reviewed expected packet SHA256 required and must match")
    packet = json.loads(packet_bytes)
    if execute and packet.get("bank") != bank:
        raise ValueError("packet bank must match live bank selection")
    contexts = packet["contexts"]
    n, expected = len(contexts), 112 if bank == "exposed" else 128
    if not packet.get("packet_id") or not 1 <= n <= expected or (execute and n != expected) or len({r["id"] for r in contexts}) != n:
        raise ValueError("exact live bank size and unique IDs required")
    prepared = []
    for context in contexts:
        payload, draft = public_revision_input(context)
        original = rendered_text(draft, context["public"])
        if "frozen_baseline_render" in context and context["frozen_baseline_render"] != original:
            raise ValueError("frozen baseline differs from actual composed render")
        prepared.append((payload, draft, original))
    provenance = {Path(p).resolve(): Path(p).resolve().read_bytes() for p in input_provenance_paths}
    if len({p.name for p in provenance}) != len(provenance):
        raise ValueError("unique provenance basenames required")
    metadata = runtime_manifest(days=2)
    hashes = dict(metadata["harness_sha256"])
    hashes.update({p: digest((ROOT/p).read_bytes()) for p in SOURCE_PATHS})
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(output/"source-snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, expected_hash in hashes.items():
            content = (ROOT/name).read_bytes()
            if digest(content) != expected_hash:
                raise RuntimeError("source changed before snapshot")
            archive.writestr(name, content)
    (output/"packet.json").write_bytes(packet_bytes)
    if provenance:
        (output/"input-provenance").mkdir()
        for p, content in provenance.items():
            (output/"input-provenance"/p.name).write_bytes(content)
    manifest = {"instrument_id": program_id, "packet_id": packet["packet_id"], "bank": bank,
        "packet_sha256": digest(packet_bytes), "expected_packet_sha256": expected_packet_sha256, "original_packet_path": str(path),
        "source_hashes_start": hashes, "source_snapshot_sha256": digest((output/"source-snapshot.zip").read_bytes()),
        "input_provenance_sha256": {str(p): digest(v) for p, v in provenance.items()},
        "code_revision": metadata["code_revision"], "dirty": metadata["dirty"],
        "mode": "live" if execute else "injected-contract", "planned_inputs": n,
        "maximum_payload_bytes": 20000, "per_call_reservation_usd": RESERVATION,
        "maximum_calls": 4*n, "maximum_reserved_usd": RESERVATION*4*n,
        "role_maximum_calls": {"audit": 3*n, "repair": n}, "per_arm_maximum_calls": {"C1": 1, "C2": 3},
        "variant": variant, "tasks": task_ids(variant),
        "model": MODEL, "output_cap": 3000, "reasoning_effort": {"audit": "high", "repair": "medium"},
        "concurrency": concurrency, "scope": "Fixed response component comparison; no Luna generation or product integration.",
        "baseline": "Authored adequate/flawed controls" if bank == "fresh" else "Exposed fixed V16 diagnostic responses",
        "semantic_scoring": "Independent review required; verifier acceptance is not ground truth."}
    write_json(output/"manifest.json", manifest)
    shared = SharedAdmission(n, output/"admission.jsonl")
    clients = {}
    for role, injected in (("audit", injected_audit_client), ("repair", injected_repair_client)):
        serializer = make_final_audit_client(role=role)
        clients[role] = RecordedRunClient(serializer if execute else injected,
            output/f"provider-{role}.jsonl", maximum_calls=shared.roles[role],
            maximum_cost_usd=RESERVATION*shared.roles[role], reservation_usd=RESERVATION,
            max_output_tokens=3000, expected_model=MODEL, reasoning_effort=serializer.reasoning_effort,
            experimental_sol_enabled=True, network_mode=manifest["mode"])
        clients[role].serializer = serializer
    semaphore = asyncio.Semaphore(concurrency)
    started = time.perf_counter()

    async def one(context, prepared_input):
        async with semaphore:
            case_started = time.perf_counter()
            payload, draft, original = prepared_input
            row = {"id": context["id"], "public_input": context["public"],
                   "C0": {"delivered_text": original, "proposal_json": draft.model_dump_json(), "calls": 0}}
            for arm, mode in (("C1", "support"), ("C2", "quality")):
                arm_started = time.perf_counter()
                if shared.stopped:
                    row[arm] = {"outcome": "blocked", "reason": shared.reason, "calls": 0,
                                "delivered_text": QUARANTINE_TEXT, "proposal_json": None, "events": [], "elapsed_seconds": 0.0}
                    continue
                client = ArmClient(shared, clients, arm, context["id"], variant)
                result = await audit_final_response(proposal_json=draft.model_dump_json(), payload=payload,
                    render=lambda p: rendered_text(p, context["public"]), audit_client=client,
                    repair_client=client if arm == "C2" else None, mode=mode, prompt_version=variant)
                row[arm] = result.to_dict()
                row[arm]["elapsed_seconds"] = time.perf_counter()-arm_started
                if result.reason == "contract_or_provider_failure":
                    shared.stop("contract_or_provider_failure")
            row["elapsed_seconds"] = time.perf_counter()-case_started
            _append(output/"cases.jsonl", row)
            return row

    rows = await asyncio.gather(*(one(c, p) for c, p in zip(contexts, prepared, strict=True)))
    changes = {}
    watched = {ROOT/name: value for name, value in hashes.items()}
    watched.update({path: digest(packet_bytes), **{p: digest(v) for p, v in provenance.items()}})
    for p, expected_hash in watched.items():
        try:
            if digest(p.read_bytes()) != expected_hash:
                changes[str(p)] = "changed"
        except OSError as error:
            changes[str(p)] = type(error).__name__
    records = {role: client.records for role, client in clients.items()}
    all_records = [r for values in records.values() for r in values]
    summary = {"instrument_id": program_id, "cases": rows, "planned_inputs": n,
        "provider_attempts": sum(c.attempts for c in clients.values()), "admitted_calls": shared.calls,
        "reserved_usd": shared.calls*RESERVATION, "provider_stopped": shared.stopped, "stop_reason": shared.reason,
        "provider_records_by_role": records, "role_attempts": {r: c.attempts for r, c in clients.items()},
        "unknown_cost_calls": sum((r.get("usage") or {}).get("approximate_cost_usd") is None for r in all_records),
        "known_reported_cost_usd": sum((r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in all_records),
        "provider_failures": sum(r["status"] != "completed" for r in all_records),
        "source_files_unchanged": not changes, "source_hash_errors": changes,
        "wall_seconds": time.perf_counter()-started, "cases_sha256": digest((output/"cases.jsonl").read_bytes()),
        "decision": "Pending independent semantic review; source changes invalidate comparison."}
    write_json(output/"summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("v1", "v2"), default="v1")
    parser.add_argument("--bank", choices=("exposed", "fresh"), required=True)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--input-provenance", type=Path, action="append", default=[])
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--expected-packet-sha256", required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_IDS[args.variant], "external_model_evaluation")
    if not args.execute:
        parser.error("CLI requires --execute; injected contracts use run()")
    result = asyncio.run(run(args.output_dir, args.packet, bank=args.bank, execute=True,
                             input_provenance_paths=args.input_provenance, concurrency=args.concurrency,
                             expected_packet_sha256=args.expected_packet_sha256, variant=args.variant))
    print(json.dumps({k: v for k, v in result.items() if k not in {"cases", "provider_records_by_role"}}, indent=2))


if __name__ == "__main__":
    main()
