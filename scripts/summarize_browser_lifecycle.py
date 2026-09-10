"""Summarize saved, synthetic browser-run histories without generating new turns."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics


STARTS = {
    "typical-engaged": "I understand member_id identifies a member. Why can team_id repeat",
    "fast-learner": "My understanding is that member_id uniquely identifies",
    "slow-learner": "I am new to these tables. What does one row mean",
    "high-forgetting": "I keep forgetting which key identifies a member.",
    "misconception-prone": "I think a foreign key must be unique, so the Members table is wrong",
    "answer-seeking": "This is my graded Data Systems assignment. Write the complete submission",
    "low-receptivity": "I only want a brief explanation: what is the difference",
}


def summarize(histories: dict) -> dict:
    cases = []
    excluded = []
    for persona, start in STARTS.items():
        matches = [
            view for view in histories[persona]
            if view["messages"] and view["messages"][0]["content"].startswith(start)
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one recorded QA history for {persona}")
        messages = matches[0]["messages"]
        if len(messages) < 24:
            raise ValueError(f"Incomplete twelve-turn journey: {persona}")
        for index in range(12):
            student, tutor = messages[index * 2:index * 2 + 2]
            if student["role"] != "student" or tutor["role"] != "tutor":
                raise ValueError(f"Invalid message ordering: {persona}/{index + 1}")
            trace = tutor.get("trace") or {}
            cases.append({
                "case_id": f"{persona}-v{index // 4 + 1}-t{index % 4 + 1}",
                "persona": persona,
                "visit": index // 4 + 1,
                "prompt": student["content"],
                "reply": tutor["content"],
                "action": tutor.get("action"),
                "created_at": tutor["created_at"],
                "provider_model": trace.get("provider_model"),
                "latency_ms": trace.get("latency_ms"),
                "usage": trace.get("usage"),
                "validation_scope": trace.get("validation_scope"),
            })
        if len(messages) > 24:
            excluded.append({"persona": persona, "additional_messages": len(messages) - 24,
                             "reason": "Browser return-login form retained another account; extra QA turn excluded."})
    actions = Counter(case["action"] for case in cases)
    latencies = [case["latency_ms"] for case in cases if case["latency_ms"] is not None]
    usage = [case["usage"] for case in cases if case["usage"] is not None]
    failures = [case for case in cases if case["action"] == "safe-graph-failure"]
    return {
        "run_id": "aws-browser-lifecycle-001",
        "dataset_version": "aws-browser-lifecycle-v1",
        "permission": "Repository-authored synthetic course data and synthetic persona roleplay only.",
        "scope": "Coding fixes only; existing architecture, prompts, models, policies and feature flags retained.",
        "core_student_turns": len(cases),
        "action_counts": dict(actions),
        "safe_failure_fraction": len(failures) / len(cases),
        "all_safe_failures_preserve_nonzero_usage": all(
            case["provider_model"] not in {None, "not-called"}
            and (case["usage"] or {}).get("total_tokens", 0) > 0 for case in failures
        ),
        "recorded_generation_latency_ms": {
            "n": len(latencies), "median": statistics.median(latencies), "max": max(latencies),
            "scope": "Recorded generation trace; not end-to-end browser latency or total request cost.",
        },
        "recorded_generation_usage": {
            "total_tokens": sum(item.get("total_tokens", 0) for item in usage),
            "approximate_cost_usd": sum(item.get("approximate_cost_usd") or 0 for item in usage),
            "unknown_cost_entries": sum(item.get("approximate_cost_usd") is None for item in usage),
            "scope": "Generation traces include bounded draft/audit usage where recorded; not a billing reconciliation or all planning calls.",
        },
        "persona_actions": {persona: dict(Counter(case["action"] for case in cases if case["persona"] == persona)) for persona in STARTS},
        "excluded_additional_history": excluded,
        "limitations": [
            "Actions are outcomes, not a semantic correctness score.",
            "One compressed browser run; no independent repeats or human learning measurements.",
            "Fresh-course publication, real check-in delivery/reply, v2 release and isolated recovery remain blocked/unrun.",
            "Cross-course operator mistake is outside these Data Systems histories and excluded from the 84-turn core.",
        ],
        "decision": "Keep bounded coding fixes; Refine demo readiness. No architecture selection or bug-free claim.",
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata", type=Path)
    args = parser.parse_args()
    result = summarize(json.loads(args.input.read_text()))
    if args.metadata:
        result["release_metadata"] = json.loads(args.metadata.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"cases", "persona_actions"}}, indent=2))


if __name__ == "__main__":
    main()
