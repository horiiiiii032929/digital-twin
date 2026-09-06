"""Versioned paired persistent-runtime pedagogy comparison; semantic review required."""
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
import time
import sys
from types import SimpleNamespace
import zipfile

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import CASE_CONTEXT, MODEL, RecordedRunClient, ContractFailureClient
from scripts.run_operational_dialogue_development import manifest as runtime_manifest, budget_chain_snapshot
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.evaluation.experimental_tutoring_candidate import experimental_tutoring_configuration
from src.digital_twin.student.teaching_profile import new_teaching_profile
from src.digital_twin.evaluation.simulated_learner_v1 import ConceptCardV1
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed
from services.llm import OpenAiResponsesClient
from scripts.recorded_generation_roles import create_recorded_generation_roles

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "paired-pedagogy-development-001"
VERSIONS = ("v4", "v5")
OUTPUT_CAP = 3000
EXPECTED_IDS = {v: f"question-specific-profile-grounded-{v}" for v in ("v4", "v5", "v6", "v7", "v8", "v9", "v10")}
ROLE_VARIANTS = ("v10-luna-low", "v10-luna-medium", "v10-sol-low", "v11-luna-low", "v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium")
EXPECTED_IDS.update({version: "question-specific-profile-grounded-" + version.split("-")[0] for version in ROLE_VARIANTS})


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


def schedule(packet, seed, repetitions, candidate="v5"):
    if candidate not in {"v5", "v6", "v7", "v8", "v9", "v10", *ROLE_VARIANTS}:
        raise ValueError("candidate must be v5, v6, v7, v8, v9 or v10")
    arms = ("v4", candidate)
    rows = []
    for repetition in range(repetitions):
        groups = list(packet["cases"])
        random.Random(seed + repetition).shuffle(groups)
        for index, case in enumerate(groups):
            versions = arms if (index + repetition) % 2 == 0 else tuple(reversed(arms))
            rows.extend({"id": f"case-{index}-repeat-{repetition}-{version}", "case": case,
                         "version": version, "repetition": repetition} for version in versions)
    return rows


async def run(output, packet, *, live=False, transport_factory=None, seed=7801,
              repetitions=1, maximum_calls=800, maximum_cost_usd=20.0, candidate="v5", packet_path=None, input_provenance_paths=()):
    if candidate not in {"v5", "v6", "v7", "v8", "v9", "v10", *ROLE_VARIANTS}:
        raise ValueError("candidate must be v5, v6, v7, v8, v9 or v10")
    versions = ("v4", candidate)
    role_variant = candidate in ROLE_VARIANTS
    revision_variant = candidate in {"v12-luna-sol", "v13-luna-sol", "v14-luna-sol", "v14-luna-sol-medium"}
    role_count = 3 if revision_variant else 2
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
        input_paths = [packet_path, *(Path(path).resolve() for path in input_provenance_paths)]
        if len({path.name for path in input_paths}) != len(input_paths):
            raise ValueError("input artifact basenames must be unique")
        input_bytes = {path.name: path.read_bytes() for path in input_paths}
        if input_bytes[packet_path.name] != original_bytes:
            raise ValueError("input packet changed during initial snapshot")
    packet = normalized_packet(packet)
    validate_packet(packet)
    if not 1 <= repetitions <= 3 or not 2 <= maximum_calls <= (1200 if revision_variant else 800) or not 0 < maximum_cost_usd <= (192 if revision_variant else 128 if role_variant else 20):
        raise ValueError("finite preregistered bounds exceeded")
    planned_turns = sum(len(case["prompts"]) for case in packet["cases"]) * len(versions) * repetitions
    conservative_planned_calls = planned_turns * (5 if revision_variant else 3)
    if conservative_planned_calls > maximum_calls or conservative_planned_calls * (.16 if role_variant else .025) > maximum_cost_usd:
        raise ValueError("prospective call/reservation budget cannot cover complete paired packet")
    if role_variant and 2 * sum(len(case["prompts"]) for case in packet["cases"]) * repetitions > (maximum_calls // 2) // role_count:
        raise ValueError("candidate role partition cannot cover every planned generation and repair")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    specs = schedule(packet, seed, repetitions, candidate)
    metadata = runtime_manifest(days=3)
    hashes = metadata["harness_sha256"]
    hashes[str(Path(__file__).relative_to(ROOT))] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    test_path = ROOT / "tests/test_paired_pedagogy_development.py"
    hashes[str(test_path.relative_to(ROOT))] = hashlib.sha256(test_path.read_bytes()).hexdigest()
    plan_path = ROOT / "research/04_experiments/2026-09-06-paired-pedagogy-runner-plan.md"
    hashes[str(plan_path.relative_to(ROOT))] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    rubric_path = ROOT / "research/05_evaluation/meaningful-continuation-rubric-v1.md"
    if rubric_path.exists():
        hashes[str(rubric_path.relative_to(ROOT))] = hashlib.sha256(rubric_path.read_bytes()).hexdigest()
    sidecar_plan = ROOT / "research/04_experiments/2026-09-06-boundary-classification-sidecar-plan.md"
    if sidecar_plan.exists():
        hashes[str(sidecar_plan.relative_to(ROOT))] = hashlib.sha256(sidecar_plan.read_bytes()).hexdigest()
    stage_plan = ROOT / "research/04_experiments/2026-09-06-mixed-evidence-stage-sidecar-plan.md"
    if stage_plan.exists():
        hashes[str(stage_plan.relative_to(ROOT))] = hashlib.sha256(stage_plan.read_bytes()).hexdigest()
    v9_plan = ROOT / "research/04_experiments/2026-09-06-profile-authority-runner-integration-plan.md"
    hashes[str(v9_plan.relative_to(ROOT))] = hashlib.sha256(v9_plan.read_bytes()).hexdigest()
    v10_plan = ROOT / "research/04_experiments/2026-09-06-typed-compact-v10-runner-plan.md"
    hashes[str(v10_plan.relative_to(ROOT))] = hashlib.sha256(v10_plan.read_bytes()).hexdigest()
    for relative in ("scripts/recorded_generation_roles.py", "research/04_experiments/2026-09-06-v10-generation-model-comparison-plan.md", "research/04_experiments/2026-09-06-evidence-strength-generation-plan.md", "research/04_experiments/2026-09-06-independent-factual-revision-plan.md", "research/04_experiments/2026-09-06-bounded-revision-plan.md", "research/04_experiments/2026-09-06-conditional-revision-plan.md", "research/04_experiments/2026-09-06-conditional-revision-effort-plan.md"):
        hashes[relative] = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    packet_bytes = json.dumps(original_packet, sort_keys=True, indent=2).encode()
    (output / "packet.json").write_bytes(packet_bytes)
    manifest = {"instrument_id": PROGRAM_ID, "code_revision": metadata["code_revision"], "dirty": metadata["dirty"],
        "source_hashes_start": hashes, "packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "schedule": specs, "seed": seed, "repetitions": repetitions, "model": MODEL, "output_cap": OUTPUT_CAP,
        "planned_turns": planned_turns, "conservative_planned_calls": conservative_planned_calls,
        "maximum_calls": maximum_calls, "maximum_reserved_usd": maximum_cost_usd, "concurrent_histories": 4,
        "network_mode": "live" if live else "injected-contract", "candidate_ids": {version: EXPECTED_IDS[version] for version in versions},
        "candidate": candidate, "candidate_configuration": experimental_tutoring_configuration(candidate), "invocation_argv": list(sys.argv),
        "runtime_boundary": "actual persistent StudentTutoringService; not HTTP/authentication measurement",
        "default_or_selected_profile_changed": False}
    if role_variant:
        manifest.pop("model")
        manifest["provider_roles"] = {"v4": {"model": MODEL, "output_cap": OUTPUT_CAP, "reasoning_effort": "low"},
            candidate: experimental_tutoring_configuration(candidate)["role_configuration"]}
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
    clients = {}
    for version in versions:
        selection = experimental_tutoring_configuration(version)
        if selection.get("role_configuration"):
            clients[version] = create_recorded_generation_roles(selection, output / f"provider-{version}",
                maximum_calls=maximum_calls // 2, maximum_cost_usd=maximum_cost_usd / 2, live=live,
                transport_factory=(lambda role, config, v=version: transport_factory(v, role)) if transport_factory else None)
            continue
        transport = transport_factory(version) if transport_factory else (OpenAiResponsesClient(
            MODEL, max_output_tokens=OUTPUT_CAP, timeout_seconds=30, reasoning_effort="low") if live else ContractFailureClient())
        clients[version] = RecordedRunClient(transport, output / f"provider-{version}.jsonl",
            maximum_calls=maximum_calls // 2, maximum_cost_usd=maximum_cost_usd / 2,
            reservation_usd=.025, max_output_tokens=OUTPUT_CAP, network_mode=manifest["network_mode"])
    semaphore = asyncio.Semaphore(4)
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
                    fixture_id=packet["packet_id"], planner_client=clients[spec["version"]],
                    teaching_profile_values=spec["case"]["profile"], maximum_case_calls=40,
                    maximum_case_cost_usd=maximum_cost_usd / 2, **kwargs)
                runtime = factory(SimpleNamespace(case_id=spec["id"]), VirtualUtcClock(datetime(2026, 9, 22, tzinfo=UTC)))
                row["observed_generator_id"] = getattr(runtime.tutoring.generator, "implementation_id", None)
                if spec["version"] in ROLE_VARIANTS:
                    row["observed_generation_model"] = runtime.tutoring.generator.model_id
                    row["role_configuration"] = clients[spec["version"]].role_configuration
                    if row["observed_generation_model"] != row["role_configuration"]["generation"]["model"]:
                        raise RuntimeError("actual generation model differs from candidate")
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
                        if spec["version"] in ROLE_VARIANTS:
                            actual_client = runtime.tutoring.generator.client
                            for _ in range(16):
                                if actual_client is clients[spec["version"]]:
                                    break
                                actual_client = getattr(actual_client, "client", None)
                            if actual_client is not clients[spec["version"]] or runtime.tutoring.generator.model_id != row["observed_generation_model"]:
                                raise RuntimeError("restart changed role routing or model")
                            row.setdefault("restarted_role_configurations", []).append(actual_client.role_configuration)
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
    arms = {}
    for version, client in clients.items():
        arms[version] = {"attempts": client.attempts, "stopped": client.stopped,
            "completed_calls": sum(r["status"] == "completed" for r in client.records),
            "provider_failures": sum(r["status"] != "completed" for r in client.records),
            "unknown_cost_calls": sum((r.get("usage") or {}).get("approximate_cost_usd") is None for r in client.records),
            "ledger_reserved_usd": client.reserved_usd,
            "failure_codes": dict(Counter(r.get("failure_stage") or r.get("error_code") for r in client.records if r["status"] != "completed")),
            "reported_cost_usd": sum((r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in client.records),
            "input_tokens": sum((r.get("usage") or {}).get("input_tokens") or 0 for r in client.records),
            "output_tokens": sum((r.get("usage") or {}).get("output_tokens") or 0 for r in client.records)}
    for version, client in clients.items():
        if version in ROLE_VARIANTS:
            arms[version]["role_ledger_paths"] = {role: str(path.relative_to(output)) for role, path in client.ledger_paths.items()}
            arms[version]["role_attempts"] = {role: child.attempts for role, child in client.role_clients.items()}
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
        "semantic_quality_pass": None, "decision": "invalid-source-change" if not unchanged else "independent-semantic-review-required" if live else "contract-only" if all(h["completed"] for h in histories) else "incomplete-contract",
        "artifact_sha256": {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest() for p in output.rglob("*.jsonl")}}
    (output / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--candidate", choices=("v5", "v6", "v7", "v8", "v9", "v10", *ROLE_VARIANTS), default="v5")
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--input-provenance", type=Path, action="append", default=[])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--maximum-calls", type=int, default=800)
    parser.add_argument("--maximum-cost-usd", type=float, default=20)
    args = parser.parse_args()
    if args.live:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    result = asyncio.run(run(args.output_dir, json.loads(args.packet.read_text()), live=args.live, repetitions=args.repetitions, candidate=args.candidate,
        maximum_calls=args.maximum_calls, maximum_cost_usd=args.maximum_cost_usd, packet_path=args.packet, input_provenance_paths=args.input_provenance))
    print(json.dumps({"decision": result["decision"], "arms": result["arms"]}))


if __name__ == "__main__":
    main()
