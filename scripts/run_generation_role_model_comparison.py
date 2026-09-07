"""Explicit generation-only candidate comparison; semantic review required."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import platform
import time
import sys
from types import SimpleNamespace
import zipfile

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import CASE_CONTEXT
from scripts.run_operational_dialogue_development import manifest as runtime_manifest, budget_chain_snapshot
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.student.teaching_profile import new_teaching_profile
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from scripts.recorded_generation_roles import create_recorded_generation_roles
from services.llm.experimental_role_routing import ExperimentalGenerationRoleRouter

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "generation-role-model-development-001"
VERSIONS = ("v10-luna-low", "v10-luna-medium", "v10-sol-low")
AVAILABLE_VERSIONS = (*VERSIONS, "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium")
OUTPUT_CAP = 3000
RESERVATION_USD = .16
EXPECTED_IDS = {version: "question-specific-profile-grounded-v10" for version in VERSIONS}
EXPECTED_IDS["v11-luna-low"] = "question-specific-profile-grounded-v11"
EXPECTED_IDS["v12-luna-sol"] = "question-specific-profile-grounded-v12"
EXPECTED_IDS["v13-luna-sol"] = "question-specific-profile-grounded-v13"
EXPECTED_IDS["v14-luna-sol"] = "question-specific-profile-grounded-v14"
EXPECTED_IDS["v14-luna-sol-medium"] = "question-specific-profile-grounded-v14"


def append(path, row):
    with path.open("a") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")


def normalized_packet(packet):
    """Convert only public course sources and student/profile inputs for runtime use."""
    if "contexts" not in packet:
        return packet
    return {"packet_id": packet["packet_id"], "cases": [
        {"id": context["id"], "split": packet["split"], "category": context["category"],
         "target_turn_index": context["public"]["target_turn_index"],
         "profile": context["public"]["profile_values"],
         "prompts": [turn["content"] for turn in context["public"]["student_turns"]],
         "cards": [{"concept_id": source["concept_id"], "label": source["label"],
                    "description": source["text"], "objective": f"Explain the approved rule for {source['label']}."}
                   for source in packet["sources"] if source["course_id"] == context["course_id"]]}
        for context in packet["contexts"]]}


def validate_packet(packet):
    if not isinstance(packet, dict) or not packet.get("packet_id"):
        raise ValueError("versioned packet_id required")
    cases = packet.get("cases", [])
    if not cases or len(cases) > 100 or len({c["id"] for c in cases}) != len(cases):
        raise ValueError("one to100 unique cases required")
    for case in cases:
        if not case.get("split") or not case.get("profile") or not case.get("cards"):
            raise ValueError("explicit split, profile and approved synthetic cards required")
        if not 1 <= len(case.get("prompts", [])) <= 12 or any(not isinstance(x, str) or not x.strip() for x in case["prompts"]):
            raise ValueError("one to12 explicit student turns required")
        new_teaching_profile(course_id="synthetic-packet-preflight", version=1, values=case["profile"])
        for card in case["cards"]:
            ConceptCardV1(**card)
    return packet


def actual_role_router(client):
    seen = set()
    while not isinstance(client, ExperimentalGenerationRoleRouter):
        if id(client) in seen or len(seen) >= 16:
            raise RuntimeError("actual routed client chain is invalid")
        seen.add(id(client))
        client = getattr(client, "client", None)
        if client is None:
            raise RuntimeError("actual generator client has no role router")
    return client


def schedule(packet, seed, versions=VERSIONS):
    rng = random.Random(seed)
    groups = list(packet["cases"])
    rng.shuffle(groups)
    rows = []
    for index, case in enumerate(groups):
        scheduled_versions = list(versions)
        rng.shuffle(scheduled_versions)
        rows.extend({"id": f"case-{index}-{version}", "case": case,
                     "version": version, "repetition": 0} for version in scheduled_versions)
    return rows


async def run(output, packet, *, live=False, transport_factory=None, seed=7801,
              maximum_calls=500, maximum_cost_usd=100.0, packet_path=None, versions=VERSIONS):
    versions = tuple(versions)
    if not versions or len(versions) > 3 or len(set(versions)) != len(versions) or any(
            version not in AVAILABLE_VERSIONS for version in versions):
        raise ValueError("one to three distinct declared candidates required")
    arm_count = len(versions)
    if live:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("configured provider credential required")
    original_packet = packet
    input_paths = []
    input_bytes = {}
    if packet_path is not None:
        packet_path = Path(packet_path).resolve()
        original_bytes = packet_path.read_bytes()
        if json.loads(original_bytes) != original_packet:
            raise ValueError("input packet bytes do not match supplied packet data")
        input_paths = [packet_path]  # Never read sibling builders or sealed confirmation.
        input_bytes = {path.name: path.read_bytes() for path in input_paths}
        if input_bytes[packet_path.name] != original_bytes:
            raise ValueError("input packet changed during initial snapshot")
    packet = normalized_packet(packet)
    validate_packet(packet)
    if not 6 <= maximum_calls <= 500 or not 0 < maximum_cost_usd <= 100:
        raise ValueError("finite preregistered bounds exceeded")
    planned_turns = sum(len(case["prompts"]) for case in packet["cases"]) * len(versions)
    turns_per_arm = sum(len(case["prompts"]) for case in packet["cases"])
    role_configurations = {version: experimental_tutoring_configuration(version)["role_configuration"] for version in versions}
    conservative_planned_calls = turns_per_arm * sum(5 if "revision" in roles else 3
        for roles in role_configurations.values())
    if conservative_planned_calls > maximum_calls or conservative_planned_calls * RESERVATION_USD > maximum_cost_usd:
        raise ValueError("prospective call/reservation budget cannot cover complete paired packet")
    if any(2 * turns_per_arm > (maximum_calls // arm_count) // len(roles)
            for roles in role_configurations.values()):
        raise ValueError("role reservation cannot cover every planned generation, revision and repair")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    specs = schedule(packet, seed, versions)
    metadata = runtime_manifest(days=3)
    hashes = metadata["harness_sha256"]
    hashes[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    for relative in (
        "tests/test_generation_role_model_comparison.py",
        "scripts/recorded_generation_roles.py",
        "research/04_experiments/2026-09-06-v10-generation-model-comparison-plan.md",
        "research/04_experiments/2026-09-06-entity-implication-quality-plan.md",
        "research/05_evaluation/meaningful-continuation-rubric-v1.md",
        "research/04_experiments/2026-09-06-evidence-strength-generation-plan.md",
        "research/04_experiments/2026-09-06-independent-factual-revision-plan.md",
        "research/04_experiments/2026-09-06-bounded-revision-plan.md",
        "research/04_experiments/2026-09-06-conditional-revision-plan.md", "research/04_experiments/2026-09-06-conditional-revision-effort-plan.md",
    ):
        hashes[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    packet_bytes = json.dumps(original_packet, sort_keys=True, indent=2).encode()
    (output / "packet.json").write_bytes(packet_bytes)
    manifest = {"instrument_id": PROGRAM_ID, "code_revision": metadata["code_revision"], "dirty": metadata["dirty"],
        "source_hashes_start": hashes, "packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "schedule": specs, "seed": seed, "repetitions": 1, "role_configurations": {v: experimental_tutoring_configuration(v)["role_configuration"] for v in versions}, "output_cap": OUTPUT_CAP,
        "planned_turns": planned_turns, "conservative_planned_calls": conservative_planned_calls,
        "maximum_calls": maximum_calls, "maximum_reserved_usd": maximum_cost_usd, "concurrent_histories": 3,
        "host_platform": platform.platform(), "load_average_start": os.getloadavg(),
        "network_mode": "live" if live else "injected-contract", "candidate_ids": {version: EXPECTED_IDS[version] for version in versions},
        "candidate_configurations": {v: experimental_tutoring_configuration(v) for v in versions}, "invocation_argv": list(sys.argv),
        "runtime_boundary": "actual persistent StudentTutoringService; not HTTP/authentication measurement",
        "default_or_selected_profile_changed": False}
    archive_path = output / "source-snapshot.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, digest in hashes.items():
            content = (ROOT / name).read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError("source changed before archive")
            archive.writestr(name, content)
    if input_paths:
        input_directory = output / "input-artifacts"
        input_directory.mkdir()
        for name, content in input_bytes.items():
            (input_directory / name).write_bytes(content)
        manifest["input_artifact_sha256"] = {name: hashlib.sha256(content).hexdigest() for name, content in input_bytes.items()}
        manifest["original_packet_sha256"] = manifest["input_artifact_sha256"][packet_path.name]
        manifest["input_packet_normalized_equal"] = True
    manifest["source_snapshot_sha256"] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    clients, routers = {}, {}
    for version in versions:
        selection = experimental_tutoring_configuration(version)
        router = create_recorded_generation_roles(selection, output / f"provider-{version}",
            maximum_calls=maximum_calls // arm_count, maximum_cost_usd=maximum_cost_usd / arm_count,
            live=live, transport_factory=(lambda role, config, v=version: transport_factory(v, role)) if transport_factory else None)
        routers[version] = router
        clients.update({f"{version}-{role}": client for role, client in router.role_clients.items()})
    semaphore = asyncio.Semaphore(3)
    start = time.perf_counter()

    async def trajectory(spec):
        async with semaphore:
            row = {"id": spec["id"], "case_id": spec["case"]["id"], "version": spec["version"],
                   "repetition": spec["repetition"], "split": spec["case"]["split"], "completed": False,
                   "planned_turns": len(spec["case"]["prompts"]), "completed_turns": 0, "restarts": 0, "target_turn_index": spec["case"].get("target_turn_index"),
                   "category": spec["case"].get("category")}
            runtime = None
            directory = output / spec["id"]
            directory.mkdir()
            began = time.perf_counter()
            try:
                if any(client.stopped for client in clients.values()):
                    raise RuntimeError("prior ledger stop")
                kwargs = experimental_tutoring_configuration(spec["version"])["runtime_flags"]
                factory = build_final_profile_runtime_factory(directory / "runtime", "t1-v2-reactive",
                    concept_cards=tuple(ConceptCardV1(**c) for c in spec["case"]["cards"]),
                    fixture_id=packet["packet_id"], planner_client=routers[spec["version"]],
                    teaching_profile_values=spec["case"]["profile"], maximum_case_calls=40,
                    maximum_case_cost_usd=maximum_cost_usd / arm_count, **kwargs)
                runtime = factory(SimpleNamespace(case_id=spec["id"]), VirtualUtcClock(datetime(2026, 9, 22, tzinfo=UTC)))
                row["observed_generator_id"] = getattr(runtime.tutoring.generator, "implementation_id", None)
                row["observed_generation_model"] = runtime.tutoring.generator.model_id
                row["role_configuration"] = actual_role_router(runtime.tutoring.generator.client).role_configuration
                if row["observed_generation_model"] != row["role_configuration"]["generation"]["model"]:
                    raise RuntimeError("constructed generation model does not match arm")
                if row["observed_generator_id"] != EXPECTED_IDS[spec["version"]]:
                    raise RuntimeError("actual generator differs from preregistered arm")
                for index, prompt in enumerate(spec["case"]["prompts"]):
                    if any(client.stopped for client in clients.values()):
                        raise RuntimeError("ledger stopped dispatch")
                    if index == 1:
                        identity = runtime.conversation_id
                        runtime = runtime.restart_runtime(runtime)
                        if runtime.conversation_id != identity:
                            raise RuntimeError("restart changed conversation identity")
                        row["restarts"] += 1
                        if runtime.tutoring.generator.model_id != row["observed_generation_model"]:
                            raise RuntimeError("restart changed generation model")
                        row.setdefault("restarted_generation_models", []).append(runtime.tutoring.generator.model_id)
                        restarted_router = actual_role_router(runtime.tutoring.generator.client)
                        if restarted_router is not routers[spec["version"]] or restarted_router.role_configuration != row["role_configuration"]:
                            raise RuntimeError("restart changed actual routed role configuration")
                        row.setdefault("restarted_role_configurations", []).append(restarted_router.role_configuration)
                        restarted_id = getattr(runtime.tutoring.generator, "implementation_id", None)
                        row.setdefault("restarted_generator_ids", []).append(restarted_id)
                        if restarted_id != EXPECTED_IDS[spec["version"]]:
                            raise RuntimeError("restart changed actual generator arm")
                    token = CASE_CONTEXT.set(f"{spec['id']}-turn-{index}")
                    turn_start = time.perf_counter()
                    try:
                        turn = await runtime.tutoring.submit_message(runtime.student_id, runtime.conversation_id,
                            content=prompt, client_request_id=f"{spec['id']}-{index}")
                        append(directory / "turns.jsonl", {"case_id": row["case_id"], "version": spec["version"],
                            "repetition": spec["repetition"], "stage": index, "student": prompt,
                            "elapsed_ms": (time.perf_counter()-turn_start)*1000, "turn": turn.model_dump(mode="json")})
                        row["completed_turns"] += 1
                    except Exception as error:
                        append(directory / "turns.jsonl", {"stage": index, "student": prompt,
                            "error_type": type(error).__name__, "elapsed_ms": (time.perf_counter()-turn_start)*1000})
                        raise
                    finally:
                        CASE_CONTEXT.reset(token)
                row["completed"] = True
            except Exception as error:
                row["error_type"] = type(error).__name__
                row["error_message"] = str(error)[:2000]
                row["not_completed_turn_indices"] = list(range(row["completed_turns"], row["planned_turns"]))
            finally:
                row["elapsed_seconds"] = time.perf_counter()-began
                if runtime is not None:
                    try:
                        row["budget_chain"] = budget_chain_snapshot(runtime.tutoring.generator.client)
                    except Exception as error:
                        row["budget_snapshot_error"] = type(error).__name__
                        row["completed"] = False
                    try:
                        runtime.close_runtime(runtime)
                    except Exception as error:
                        row["cleanup_error"] = type(error).__name__
                        row["completed"] = False
                append(output / "histories.jsonl", row)
            return row

    histories = await asyncio.gather(*(trajectory(spec) for spec in specs))
    roles = {}
    for version, client in clients.items():
        roles[version] = {"attempts": client.attempts, "stopped": client.stopped,
            "completed_calls": sum(r["status"] == "completed" for r in client.records),
            "provider_failures": sum(r["status"] != "completed" for r in client.records),
            "unknown_cost_calls": sum((r.get("usage") or {}).get("approximate_cost_usd") is None for r in client.records),
            "ledger_reserved_usd": client.reserved_usd,
            "failure_codes": dict(Counter(r.get("failure_stage") or r.get("error_code") for r in client.records if r["status"] != "completed")),
            "reported_cost_usd": sum((r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in client.records),
            "input_tokens": sum((r.get("usage") or {}).get("input_tokens") or 0 for r in client.records),
            "output_tokens": sum((r.get("usage") or {}).get("output_tokens") or 0 for r in client.records)}
    arms = {version: {
        "roles": {role: roles[f"{version}-{role}"] for role in role_configurations[version]},
        **{metric: sum(roles[f"{version}-{role}"][metric] for role in role_configurations[version])
           for metric in ("attempts", "completed_calls", "provider_failures", "unknown_cost_calls", "reported_cost_usd", "input_tokens", "output_tokens")},
    } for version in versions}
    hash_errors = {}
    for name, digest in hashes.items():
        try:
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                hash_errors[name] = "changed"
        except OSError as error:
            hash_errors[name] = type(error).__name__
    for path in input_paths:
        try:
            if path.read_bytes() != input_bytes[path.name]:
                hash_errors[f"input-artifacts/{path.name}"] = "changed"
        except OSError as error:
            hash_errors[f"input-artifacts/{path.name}"] = type(error).__name__
    unchanged = not hash_errors
    result = {"instrument_id": PROGRAM_ID, "arms": arms, "histories": histories,
        "source_files_unchanged": unchanged, "source_hash_errors": hash_errors, "wall_seconds": time.perf_counter()-start,
        "peak_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024),
        "semantic_quality_pass": None, "decision": "invalid-source-change" if not unchanged else "independent-semantic-review-required" if live else "contract-only" if all(h["completed"] for h in histories) else "incomplete-contract",
        "artifact_sha256": {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*.jsonl")}}
    (output / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--candidates", nargs="+", choices=AVAILABLE_VERSIONS, default=VERSIONS)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--maximum-calls", type=int, default=500)
    parser.add_argument("--maximum-cost-usd", type=float, default=100)
    args = parser.parse_args()
    if args.live:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    result = asyncio.run(run(args.output_dir, json.loads(args.packet.read_text()), live=args.live,
        maximum_calls=args.maximum_calls, maximum_cost_usd=args.maximum_cost_usd, packet_path=args.packet,
        versions=args.candidates))
    print(json.dumps({"decision": result["decision"], "arms": result["arms"]}))


if __name__ == "__main__":
    main()
