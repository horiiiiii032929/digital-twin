"""One-pass revision controls; semantic review remains external to the model."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import time
import zipfile

from scripts.run_final_profile_longitudinal import CASE_CONTEXT, RecordedRunClient
from scripts.run_operational_dialogue_development import manifest as runtime_manifest
from services.llm import OpenAiResponsesClient
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ID = "independent-factual-revision-controls-001"
TASK = "question_specific_factual_revision"
MODEL = "gpt-5.6-sol"


def public_revision_input(context):
    """Whitelist public fields; never pass family, adequacy or gold labels."""
    from src.digital_twin.generation.typed_instruction import TypedInstructionProposal
    from src.digital_twin.student.teaching_profile import new_teaching_profile

    public = context["public"]
    question = public["question"]
    if not isinstance(question, str) or not question.strip():
        raise ValueError("nonempty public question required")
    values = public["profile_values"]
    profile = new_teaching_profile(course_id="synthetic-revision-control", version=1, values=values)
    from src.digital_twin.student.teaching_profile_context import CANDIDATE_ID, PROFILE_FIELDS
    history = public["history"]
    if any(set(row) != {"role", "content"} or row["role"] not in {"user", "assistant"}
           or not isinstance(row["content"], str) for row in history):
        raise ValueError("explicit public user/assistant history required")
    sources = public["sources"]
    if not sources or len({row["id"] for row in sources}) != len(sources):
        raise ValueError("unique explicit public sources required")
    if any(not all(isinstance(row.get(key), str) and row[key].strip()
                   for key in ("id", "label", "text")) for row in sources):
        raise ValueError("public source ID, label and text required")
    draft = TypedInstructionProposal.model_validate(public["draft"])
    payload = {"question": question, "learner_history": [dict(row) for row in history],
        "approved_teaching_profile": {"configuration_id": CANDIDATE_ID,
            "content_sha256": profile.content_sha256,
            "preferences": {name: getattr(profile, name) for name in PROFILE_FIELDS},
            "authority": "Preferences apply only within existing policy, evidence, consent, and allowed actions."},
        "approved_concept_labels": [row["label"] for row in sources],
        "evidence": [{"citation_id": row["id"], "text": row["text"]} for row in sources]}
    return payload, draft


def render_control_proposal(proposal, public, *, response=None):
    """Use the actual shared V11/V12 composer; no fabricated draft-call usage."""
    from src.digital_twin.generation.evidence_strength import EvidenceStrengthInstructionalGenerator
    from src.digital_twin.grounding.models import DocumentChunk, RetrievalHit, GenerationUsage

    generator = EvidenceStrengthInstructionalGenerator(None, model_id="gpt-5.6-luna",
        named_referent_context_enabled=True, bounded_contract_enabled=True)
    evidence = {source["id"]: RetrievalHit(chunk=DocumentChunk(
        id=f"revision-control-{source['id']}", document_id=f"synthetic-{source['id']}",
        text=source["text"], ordinal=index, source_version=1, locator=f"control source {index+1}",
        source_checksum=hashlib.sha256(source["text"].encode()).hexdigest(),
        retrieval_allowed=True, display_allowed=True, metadata={"title": source["label"]}),
        relevance_score=1, raw_score=1) for index, source in enumerate(public["sources"])}
    try:
        answer = generator._compose(proposal, evidence=evidence, trace_args={
            "generator_id": "factual-revision-control-composer", "prompt_version": "revision-only-component-control",
            "provider_model": response.provider_model if response else "researcher-authored-no-provider",
            "provider_revision": response.provider_revision if response else None,
            "started": generator.clock(), "clock": generator.clock,
            "usage": response.usage if response else GenerationUsage(approximate_cost_usd=0)})
        return {"completed": True, "answer": answer.model_dump(mode="json"),
            "scope": "Actual shared composer on authored approved synthetic hits; revision-only usage, no draft call."}
    except ValueError as error:
        return {"completed": False, "error_type": type(error).__name__, "error_code": str(error)}


async def run(output, packet_path, *, execute=False, injected_client=None, input_provenance_paths=(), candidate="v12"):
    from src.digital_twin.generation.factual_revision import revise_instructional_proposal
    from src.digital_twin.generation.typed_instruction import TypedInstructionProposal

    if candidate not in {"v12", "v13", "v14", "v14-medium", "v15"}:
        raise ValueError("explicit v12, v13 or v14 revision candidate required")
    maximum_calls, maximum_cost = (112, 17.92) if candidate in {"v14", "v14-medium", "v15"} else (80, 12.80) if candidate == "v13" else (64, 10.24)
    effort = "medium" if candidate in {"v14-medium", "v15"} else "low"
    revision_helper = revise_instructional_proposal
    if candidate == "v13":
        from src.digital_twin.generation.bounded_revision import revise_bounded_instructional_proposal
        revision_helper = revise_bounded_instructional_proposal
    if candidate in {"v14", "v14-medium", "v15"}:
        from src.digital_twin.generation.conditional_revision import conditionally_revise_instructional_proposal
        revision_helper = conditionally_revise_instructional_proposal
    if candidate == "v15":
        from src.digital_twin.generation.global_support_revision import globally_assess_instructional_proposal
        revision_helper = globally_assess_instructional_proposal
    if execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
        if injected_client is not None:
            raise ValueError("injected transport cannot be labelled live")
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            raise ValueError("configured provider credential required")
    elif injected_client is None:
        raise ValueError("contract requires an explicit injected transport")
    path = Path(packet_path).resolve()
    packet_bytes = path.read_bytes()
    provenance = {Path(item).resolve(): Path(item).resolve().read_bytes() for item in input_provenance_paths}
    if len({item.name for item in provenance}) != len(provenance):
        raise ValueError("provenance basenames must be unique")
    packet = json.loads(packet_bytes)
    contexts = packet["contexts"]
    if not packet.get("packet_id") or not 1 <= len(contexts) <= maximum_calls or (
        execute and len(contexts) != maximum_calls
    ) or len({row["id"] for row in contexts}) != len(contexts):
        raise ValueError("exact candidate-sized unique live controls or bounded injected packet required")
    prepared = [public_revision_input(row) for row in contexts]
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    metadata = runtime_manifest(days=2)
    hashes = metadata["harness_sha256"]
    for name in (str(Path(__file__).relative_to(ROOT)), "tests/test_factual_revision_controls.py",
                 "research/04_experiments/2026-09-06-independent-factual-revision-plan.md",
                 "research/04_experiments/2026-09-06-bounded-revision-plan.md",
                 "research/04_experiments/2026-09-06-conditional-revision-plan.md",
                 "research/04_experiments/2026-09-06-conditional-revision-effort-plan.md",
                 "research/04_experiments/2026-09-06-global-support-assessment-plan.md"):
        hashes[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    with zipfile.ZipFile(output / "source-snapshot.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, digest in hashes.items():
            content = (ROOT / name).read_bytes()
            if hashlib.sha256(content).hexdigest() != digest:
                raise RuntimeError("source changed before snapshot")
            archive.writestr(name, content)
    (output / "packet.json").write_bytes(packet_bytes)
    if provenance:
        (output / "input-provenance").mkdir()
        for item, content in provenance.items():
            (output / "input-provenance" / item.name).write_bytes(content)
    manifest = {"instrument_id": PROGRAM_ID, "packet_id": packet["packet_id"],
        "packet_sha256": hashlib.sha256(packet_bytes).hexdigest(), "original_packet_path": str(path),
        "input_provenance_sha256": {str(item): hashlib.sha256(content).hexdigest() for item, content in provenance.items()},
        "profile_authority_scope": "Product-shaped validated synthetic profile fixture; no human professor approval asserted.",
        "code_revision": metadata["code_revision"], "dirty": metadata["dirty"],
        "source_hashes_start": hashes, "source_snapshot_sha256": hashlib.sha256((output / "source-snapshot.zip").read_bytes()).hexdigest(),
        "mode": "live" if execute else "injected-contract", "model": MODEL,
        "output_cap": 3000, "reasoning_effort": effort, "task": "question_specific_conditional_revision" if candidate in {"v14", "v14-medium", "v15"} else TASK if candidate == "v12" else "draft-dependent bounded or unrestricted revision",
        "candidate": candidate, "candidate_alias": "v15-luna-sol-medium" if candidate == "v15" else "v14-luna-sol-medium" if candidate == "v14-medium" else f"{candidate}-luna-sol",
        "revision_selection": "one conditional keep/repair wrapper; draft action is not authority" if candidate in {"v14", "v14-medium", "v15"} else "unrestricted" if candidate == "v12" else "bounded for restricted draft actions, otherwise unchanged V12 helper",
        "maximum_calls": maximum_calls, "maximum_reserved_usd": maximum_cost, "per_call_reservation_usd": .16,
        "concurrency": 1, "planned_controls": len(contexts), "revisions_per_control": 1,
        "semantic_scoring": "Independent assistant review; no model self-rating or automatic pass.",
        "scope": "Actual product revision helper, injected authored draft; not the integrated generation/runtime path."}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    client = RecordedRunClient(injected_client if not execute else OpenAiResponsesClient(
        MODEL, max_output_tokens=3000, reasoning_effort=effort, timeout_seconds=30,
        experimental_sol_enabled=True), output / "provider-revision.jsonl", maximum_calls=maximum_calls,
        maximum_cost_usd=maximum_cost, reservation_usd=.16, max_output_tokens=3000,
        expected_model=MODEL, reasoning_effort=effort, experimental_sol_enabled=True,
        network_mode="live" if execute else "injected-contract")
    rows = []
    started = time.perf_counter()
    for context, (payload, draft) in zip(contexts, prepared, strict=True):
        row = {"id": context["id"], "public_input": context["public"], "completed": False,
            "original_render": render_control_proposal(draft, context["public"])}
        stamp = time.perf_counter()
        token = CASE_CONTEXT.set(context["id"])
        before = client.attempts
        try:
            result = await revision_helper(client, payload=payload, draft=draft)
            if candidate in {"v14", "v14-medium", "v15"}:
                response, proposal = result.response, result.proposal
                kept = result.decision.disposition == "keep"
                row.update(conditional_assessment=result.decision.model_dump(mode="json"),
                    assessment_input_sha256=result.input_sha256, assessed_draft_sha256=result.draft_sha256,
                    final_content_origin="researcher-authored-kept" if kept else "sol-replacement",
                    original_proposal_preserved=proposal.model_dump(mode="json") == draft.model_dump(mode="json"))
                rendered = render_control_proposal(proposal, context["public"], response=None if kept else response)
            else:
                response = result
                proposal = TypedInstructionProposal.model_validate_json(response.content)
                rendered = render_control_proposal(proposal, context["public"], response=response)
            row.update(completed=rendered["completed"], revised_render=rendered, revised_proposal=proposal.model_dump(mode="json"),
                response=response.model_dump(mode="json"), source_ids_resolve=all(
                    source in {item["citation_id"] for item in payload["evidence"]}
                    for unit in proposal.units for source in unit.source_ids))
        except Exception as error:
            row.update(error_type=type(error).__name__, error_code=getattr(error, "code", None))
        finally:
            CASE_CONTEXT.reset(token)
            row.update(elapsed_seconds=time.perf_counter()-stamp, provider_attempts=client.attempts-before)
            rows.append(row)
            with (output / "cases.jsonl").open("a") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
    changes = {}
    for name, digest in hashes.items():
        try:
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != digest:
                changes[name] = "changed"
        except OSError as error:
            changes[name] = type(error).__name__
    try:
        if path.read_bytes() != packet_bytes:
            changes["original_packet"] = "changed"
    except OSError as error:
        changes["original_packet"] = type(error).__name__
    for item, content in provenance.items():
        try:
            if item.read_bytes() != content:
                changes[str(item)] = "changed"
        except OSError as error:
            changes[str(item)] = type(error).__name__
    summary = {"instrument_id": PROGRAM_ID, "cases": rows, "completed": sum(r["completed"] for r in rows),
        "provider_attempts": client.attempts, "provider_stopped": client.stopped,
        "provider_failures": sum(r["status"] != "completed" for r in client.records),
        "unknown_cost_calls": sum((r.get("usage") or {}).get("approximate_cost_usd") is None for r in client.records),
        "known_reported_cost_usd": sum((r.get("usage") or {}).get("approximate_cost_usd") or 0 for r in client.records),
        "provider_records": client.records, "source_files_unchanged": not changes,
        "source_hash_errors": changes, "wall_seconds": time.perf_counter()-started,
        "cases_sha256": hashlib.sha256((output / "cases.jsonl").read_bytes()).hexdigest(),
        "decision": "Refine pending independent semantic review; no Stage B authorization from structural success."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--candidate", choices=("v12", "v13", "v14", "v14-medium", "v15"), default="v12")
    parser.add_argument("--input-provenance", type=Path, action="append", default=[])
    args = parser.parse_args()
    if args.execute:
        require_bounded_pilot_operation_allowed(PROGRAM_ID, "external_model_evaluation")
    if not args.execute:
        parser.error("CLI requires --execute; injected contracts use the Python run interface")
    print(json.dumps(asyncio.run(run(args.output_dir, args.packet, execute=True, input_provenance_paths=args.input_provenance, candidate=args.candidate)), indent=2))


if __name__ == "__main__":
    main()
