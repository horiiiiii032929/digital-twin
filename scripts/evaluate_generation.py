"""Evaluate the deterministic grounded-generation control without paid calls."""

import argparse
import asyncio
import json
import subprocess
import tempfile
from pathlib import Path

from scripts.synthetic_course_corpus import build_retrieval_evaluation_chunks
from src.digital_twin.generation import (
    DeterministicGroundedGenerator,
    evaluate_generator,
    load_generation_evaluation_set,
)
from src.digital_twin.grounding import BM25Retriever
from src.digital_twin.tutor_policy import (
    FieldStatus,
    ReleaseStatus,
    build_initial_policy,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "research" / "05_evaluation" / "generation_v1.json"


def main() -> None:
    arguments = _arguments()
    summary = asyncio.run(_evaluate(arguments.dataset))
    payload = {
        "dataset": str(arguments.dataset.relative_to(ROOT)),
        "code_revision": _code_revision(),
        "working_tree_dirty": _working_tree_dirty(),
        "paid_provider_called": False,
        "provider_selection": "pending user provider/model and budget decision",
        "result": summary.model_dump(mode="json"),
    }
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is None:
        compact = {
            **{key: value for key, value in payload.items() if key != "result"},
            "result": summary.model_dump(mode="json", exclude={"cases"}),
        }
        print(json.dumps(compact, indent=2, sort_keys=True))
    else:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(f"{rendered}\n", encoding="utf-8")
    _check_regressions(summary)


async def _evaluate(dataset_path: Path):
    evaluation_set = load_generation_evaluation_set(dataset_path)
    with tempfile.TemporaryDirectory(prefix="digital-twin-generation-") as temp:
        chunks = build_retrieval_evaluation_chunks(Path(temp))
        retriever = BM25Retriever(chunks, k1=1.2, b=0.75)
        policy = _approved_synthetic_policy()
        return await evaluate_generator(
            "deterministic-grounded-generator-v1",
            DeterministicGroundedGenerator(),
            retriever,
            policy,
            evaluation_set,
        )


def _approved_synthetic_policy():
    policy = build_initial_policy().model_copy(deep=True)
    for field in policy.all_fields:
        if field.status == FieldStatus.BLOCKS_RELEASE:
            field.status = FieldStatus.RESOLVED
        if field.id == "knowledge_source_policy":
            field.value = {**field.value, "confirmed": True}
        if field.id in {"academic_integrity_policy", "professor_release_approval"}:
            field.status = FieldStatus.RESOLVED
        if field.id == "professor_release_approval":
            field.value = "approved"
    policy.status = ReleaseStatus.APPROVED
    policy.release_status = ReleaseStatus.APPROVED
    return policy


def _check_regressions(summary) -> None:
    failures = []
    for metric in (
        "policy_action_accuracy",
        "citation_validity",
        "graded_work_redirect_accuracy",
        "no_evidence_accuracy",
        "provider_suppression_accuracy",
    ):
        if getattr(summary, metric) < 1:
            failures.append(f"{metric} below 1.0")
    if summary.total_input_tokens or summary.total_output_tokens:
        failures.append("deterministic control used provider tokens")
    if summary.approximate_cost_usd is not None:
        failures.append("deterministic control reported provider cost")
    if failures:
        raise SystemExit("; ".join(failures))


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _code_revision() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _working_tree_dirty() -> bool:
    return bool(
        subprocess.run(
            ["git", "status", "--short"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )


if __name__ == "__main__":
    main()
