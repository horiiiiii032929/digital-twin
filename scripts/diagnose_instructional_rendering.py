"""Read-only replay of recorded instructional proposals through local validators."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3

from src.digital_twin.generation.instructional import EvidenceLinkedInstructionalGenerator, InstructionalProposal, InstructionalSourceBindingValidator, TASK
from src.digital_twin.generation.question_specific import ELICITATION_INTENTS
from src.digital_twin.grounding.models import DocumentChunk, GenerationUsage, RetrievalHit
from src.digital_twin.student.tutoring_graph import _validation_failure


def diagnose(root: Path):
    ledger = [json.loads(line) for line in (root / "provider-v5.jsonl").read_text().splitlines()]
    requests = {row["attempt"]: row for row in ledger if row["status"] == "started"}
    generator = EvidenceLinkedInstructionalGenerator(object(), bounded_contract_enabled=True, named_referent_context_enabled=True)
    rows = []
    for response in ledger:
        if response["status"] != "completed" or response["task"] != TASK:
            continue
        request = json.loads(requests[response["attempt"]]["messages"][-1]["content"])
        case_name, stage = response["case"].rsplit("-turn-", 1)
        case_root = root / case_name
        turn = next(json.loads(line) for line in (case_root / "turns.jsonl").read_text().splitlines()
            if json.loads(line)["stage"] == int(stage))
        db_path = next((case_root / "runtime").rglob("runtime.sqlite3"))
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
            chunks = [DocumentChunk.model_validate_json(row[0]) for row in connection.execute("SELECT chunk_json FROM release_chunks WHERE release_id = (SELECT release_id FROM conversations WHERE id = ?)",
                (turn["turn"]["tutor_message"]["conversation_id"],))]
        evidence = {}
        for item in request["evidence"]:
            matches = [chunk for chunk in chunks if chunk.text == item["text"]]
            if len(matches) != 1:
                raise ValueError("recorded evidence does not identify one archived chunk")
            evidence[item["citation_id"]] = RetrievalHit(chunk=matches[0], relevance_score=1, raw_score=1)
        proposal = InstructionalProposal.model_validate_json(response["content"])
        error = None
        phase = "render"
        selected = []
        try:
            if proposal.boundary != "answerable":
                phase = "boundary"
            else:
                for aspect in proposal.aspects:
                    for span in aspect.spans:
                        hit = evidence.get(span.citation_id)
                        if hit is None or not span.text.strip() or span.text not in hit.chunk.text:
                            raise ValueError("support span is not exact approved evidence")
                        if (span.text, hit) not in selected:
                            selected.append((span.text, hit))
                answer = generator._render_proposal(proposal, question=request["question"], evidence=evidence,
                    selected=selected, initial_elicitation=(request["approved_teaching_profile"] is None
                        and request["pedagogical_intent"] in ELICITATION_INTENTS
                        and request["help_level"] == 0 and not request["application_observed_attempt"]),
                    authorized_concept_labels=tuple(request.get("approved_concept_labels", [])),
                    trace_args={"generator_id": generator.implementation_id, "provider_model": response["returned_model"],
                        "provider_revision": response["returned_revision"], "prompt_version": generator.implementation_id,
                        "started": generator.clock(), "clock": generator.clock, "usage": GenerationUsage.model_validate(response["usage"])})
                phase = "graph-validation"
                error = _validation_failure(answer, list(evidence.values()))
                if error is None and answer.trace.policy_action == "answer":
                    decision = InstructionalSourceBindingValidator().validate(answer.atomic_claims, list(evidence.values()))
                    if not decision.releasable:
                        error = decision.reason
        except (ValueError, TypeError) as exc:
            error = str(exc)
        rows.append({"case": case_name, "case_id": turn["case_id"], "stage": int(stage), "attempt": response["attempt"],
            "delivered_action": turn["turn"]["tutor_message"]["action"], "teaching_move": proposal.teaching_move,
            "phase": phase, "error": error, "question": request["question"],
            "instructional_question": proposal.instructional_question.model_dump() if proposal.instructional_question else None,
            "has_feedback": proposal.feedback is not None, "explanation_step_count": len(proposal.explanation_steps)})
    failures = [row for row in rows if row["delivered_action"] == "safe-graph-failure"]
    manifest = json.loads((root / "manifest.json").read_text())
    return {"raw_run": str(root), "external_calls": 0, "proposals": len(rows),
        "delivered_failure_count": len(failures), "causes": dict(Counter(row["error"] for row in failures)),
        "unexplained_delivered_failures": sum(row["error"] is None for row in failures),
        "source_hashes_match": all(hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
            for name, digest in manifest["source_hashes_start"].items()), "cases": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = diagnose(args.root)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
