"""Validate that durable evaluation results are indexed and records parse."""

import json
from pathlib import Path

from src.digital_twin.evaluation import load_evaluation_record


ROOT = Path(__file__).resolve().parents[1]
EVALUATION_ROOT = ROOT / "research" / "05_evaluation"
REGISTRY = EVALUATION_ROOT / "result-registry.md"


def main() -> None:
    registry = REGISTRY.read_text(encoding="utf-8")
    errors: list[str] = []
    summaries = sorted(EVALUATION_ROOT.glob("*-results.md"))
    all_records = sorted((EVALUATION_ROOT / "records").glob("*.json"))
    supporting_summaries = [
        path for path in all_records if path.name.endswith("-summary.json")
    ]
    records = [path for path in all_records if path not in supporting_summaries]

    for summary in summaries:
        link = f"]({summary.name})"
        if link not in registry:
            errors.append(f"unregistered result summary: {summary.name}")

    run_ids: list[str] = []
    for record_path in records:
        relative_link = f"](records/{record_path.name})"
        if relative_link not in registry:
            errors.append(f"unregistered evaluation record: {record_path.name}")
        record = load_evaluation_record(record_path)
        run_ids.append(record.run_id)
        if f"`{record.run_id}`" not in registry:
            errors.append(f"registry is missing run ID: {record.run_id}")

    for summary_path in supporting_summaries:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        run = payload.get("run")
        if not isinstance(run, dict):
            errors.append(
                f"supporting summary is missing a run envelope: {summary_path.name}"
            )
            continue
        summary_run_id = run.get("run_id") or run.get("program_id")
        expected_run_id = summary_path.name.removesuffix("-summary.json")
        if summary_run_id != expected_run_id:
            errors.append(
                "supporting summary run ID does not match its filename: "
                f"{summary_path.name}"
            )
        if not (summary_path.parent / f"{expected_run_id}.json").exists():
            errors.append(
                f"supporting summary is missing its durable run record: "
                f"{summary_path.name}"
            )

    if len(run_ids) != len(set(run_ids)):
        errors.append("evaluation record run IDs must be unique")
    if errors:
        raise SystemExit("; ".join(errors))

    print(
        json.dumps(
            {
                "registry": str(REGISTRY.relative_to(ROOT)),
                "result_summaries": len(summaries),
                "machine_records": len(records),
                "supporting_summaries": len(supporting_summaries),
                "run_ids": run_ids,
                "status": "passed",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
