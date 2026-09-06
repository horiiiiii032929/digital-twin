"""Fresh natural-question development baseline; no provider execution entrypoint.

Decision: can the unchanged final composition answer natural questions using
the authored synthetic source? Prediction: paraphrases expose claim-selection
gaps. Control is the current final runtime with a fake semantic client; future
live candidates must use the same public inputs and separately recorded budget.
Gold spans are development labels, pending researcher review, not human-validated
ground truth. Exact span coverage is a narrow extractive diagnostic, not an NLP
judgment of arbitrary paraphrases or full answer correctness.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

from scripts.final_profile_longitudinal_runtime import build_final_profile_runtime_factory
from scripts.run_final_profile_longitudinal import CARDS
from src.digital_twin.clock import VirtualUtcClock
from src.digital_twin.grounding.models import GenerationUsage
from src.digital_twin.llm import LlmResponse
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "research/05_evaluation/datasets/natural-course-quality-development-v1.json"
FIXTURE_ID = "natural-course-quality-development-v1"


class FakeSemanticClient:
    """Malformed output intentionally exercises fallback; never live evidence."""

    def __init__(self):
        self.calls = 0

    async def chat(self, messages, task):
        self.calls += 1
        return LlmResponse(content="{}", provider_model="gpt-5.6-luna",
            provider_revision="fake-natural-development",
            usage=GenerationUsage(input_tokens=0, output_tokens=0, total_tokens=0,
                approximate_cost_usd=0))


def load_packet(path: Path = DATASET) -> dict:
    packet = json.loads(path.read_text())
    cards = {card.concept_id: card.description for card in CARDS}
    if len({case["id"] for case in packet["cases"]}) != len(packet["cases"]):
        raise ValueError("duplicate case id")
    for source in packet["sources"]:
        if cards.get(source["concept_id"]) != source["text"]:
            raise ValueError("source card drift")
    sources = {source["concept_id"]: source for source in packet["sources"]}
    for case in packet["cases"]:
        if case["kind"] == "answerable":
            source = sources[case["concept_id"]]
            for span in case["expected_spans"]:
                if source["text"][span["start"]:span["end"]] != span["text"]:
                    raise ValueError("gold span not supported by authored source")
    return packet


def score_response(case: dict, source: dict | None, response: dict,
                   *, course_id: str, release_id: str) -> dict:
    """Check explicit extractive spans and citation identity, independently of gates."""
    citations = response["citations"]
    action = response["action"]
    if case["kind"] == "boundary":
        passed = action in case["allowed_actions"] and not citations
        return {"boundary_pass": passed, "extractive_support_pass": None,
                "failure_class": None if passed else "policy-or-boundary"}
    assert source is not None
    text = " ".join(response["text"].casefold().split())
    coverage = [" ".join(s["text"].casefold().split()) in text
                for s in case["expected_spans"]]
    checksum = hashlib.sha256(source["text"].encode()).hexdigest()
    lineage = bool(citations) and all(
        c["course_id"] == course_id and c["release_id"] == release_id
        and c["source_artifact_id"] == source["source_id"]
        and c["source_document_id"] == "document-" + source["source_id"]
        and c["source_version"] == source["source_version"]
        and c["source_checksum"] == checksum and c["locator"] == source["locator"]
        for c in citations)
    passed = action == "answer" and all(coverage) and lineage
    failure = None if passed else (
        "answer-action" if action != "answer" else
        "citation-lineage" if not lineage else "exact-span-coverage")
    return {"boundary_pass": None, "extractive_support_pass": passed,
            "span_coverage": coverage, "citation_lineage_pass": lineage,
            "failure_class": failure,
            "semantic_correctness": "not-scored-researcher-review-pending"}


async def run_packet(output_dir: Path, *, planner_client=None,
                     network_mode: str = "fake-client-no-network") -> dict:
    """Reusable baseline; external orchestration owns live authority/accounting."""
    if planner_client is None and network_mode != "fake-client-no-network":
        raise ValueError("live labeling requires explicitly supplied client")
    require_bounded_pilot_operation_allowed("natural-course-quality-development-001",
        "method_evaluation_execution")
    if network_mode != "fake-client-no-network":
        require_bounded_pilot_operation_allowed("natural-course-quality-development-001",
            "external_model_evaluation")
    packet = load_packet()
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=False)
    client = planner_client or FakeSemanticClient()
    sources = {s["concept_id"]: s for s in packet["sources"]}
    factory = build_final_profile_runtime_factory(output_dir / "runtime",
        "t1-v2-reactive", concept_cards=CARDS, fixture_id=FIXTURE_ID,
        planner_client=client)
    rows = []
    for case in packet["cases"]:
        runtime = factory(SimpleNamespace(case_id=case["id"]),
            VirtualUtcClock(datetime(2026, 9, 8, 12, tzinfo=UTC)))
        try:
            case_started = time.perf_counter()
            # Only the question enters tutoring. Gold stays in this scorer.
            turn = await runtime.tutoring.submit_message(runtime.student_id,
                runtime.conversation_id, content=case["question"],
                client_request_id=case["id"])
            response = {"text": turn.tutor_message.content,
                "action": turn.tutor_message.action,
                "citations": [c.model_dump(mode="json") for c in turn.citations]}
            row = {"case_id": case["id"], "kind": case["kind"],
                "question": case["question"], **response,
                "latency_ms": (time.perf_counter() - case_started) * 1000,
                **score_response(case, sources.get(case.get("concept_id")), response,
                    course_id=runtime.course_id, release_id=runtime.release_id)}
            rows.append(row)
            with (output_dir / "responses.jsonl").open("a") as stream:
                stream.write(json.dumps(row, sort_keys=True) + "\n")
        finally:
            runtime.close_runtime(runtime)
    summary = {"dataset_id": packet["dataset_id"], "network_mode": network_mode,
        "dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
        "duration_seconds": time.perf_counter() - started,
        "fixture_boundary": "Synthetic source installation; ingestion and browser not exercised",
        "review_status": packet["review_status"], "cases": len(rows),
        "extractive_passes": sum(r["extractive_support_pass"] is True for r in rows),
        "answerable_cases": sum(r["kind"] == "answerable" for r in rows),
        "boundary_passes": sum(r["boundary_pass"] is True for r in rows),
        "boundary_cases": sum(r["kind"] == "boundary" for r in rows),
        "fake_client_calls": client.calls if isinstance(client, FakeSemanticClient) else None,
        "interpretation": "Development extractive diagnostic; not semantic quality or live qualification."}
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if not args.validate:
        require_bounded_pilot_operation_allowed("natural-course-quality-development-001",
            "method_evaluation_execution")
    if args.validate:
        print(json.dumps({"dataset_id": load_packet()["dataset_id"], "status": "valid"}))
    elif args.output_dir:
        print(json.dumps(asyncio.run(run_packet(args.output_dir)), indent=2))
    else:
        parser.error("use --validate or --output-dir for a fake-client baseline")


if __name__ == "__main__":
    main()
