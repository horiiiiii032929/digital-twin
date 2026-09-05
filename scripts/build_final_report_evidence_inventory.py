"""Build a safe, reproducible inventory for the final project report.

The inventory lists tracked and ordinary untracked repository artifacts, parses
the evaluation result registry, validates linked machine records, and records
aggregate metadata for ignored local evidence directories. It deliberately does
not expose filenames or hashes from ignored raw/generated directories.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


INVENTORY_ROOTS = (
    ".github",
    "README.md",
    "PRODUCT.md",
    "apps",
    "compose.staging.yml",
    "deploy",
    "docs",
    "experiments",
    "package-lock.json",
    "package.json",
    "pyproject.toml",
    "reports",
    "research",
    "scripts",
    "services",
    "src",
    "tests",
    "uv.lock",
)

LOCAL_AGGREGATE_DIRECTORIES = (
    "data/raw",
    "data/interim",
    "data/processed",
    "data/external",
    "experiments/runs",
    "reports/generated",
)

OUTPUT_FILENAMES = {
    "evidence-file-inventory.csv",
    "evaluation-result-inventory.csv",
    "local-evidence-aggregates.csv",
    "evidence-inventory-summary.json",
}

MARKDOWN_LINK_PATTERN = re.compile(r"\[[^]]+\]\(([^)]+)\)")


@dataclass(frozen=True)
class RegistryRow:
    result_id: str
    date: str
    component: str
    dataset_or_corpus: str
    status: str
    decision: str
    summary_cell: str
    machine_record_cell: str
    reproduction: str
    line_number: int


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_path(path: str) -> str:
    if path == "research/05_evaluation/result-registry.md":
        return "evaluation-registry"
    if path.startswith("research/05_evaluation/records/"):
        return "machine-result-record"
    if path.startswith("research/05_evaluation/datasets/"):
        return "committed-evaluation-dataset"
    if path.startswith("research/05_evaluation/instruments/"):
        return "evaluation-instrument"
    if path.startswith("research/05_evaluation/profiles/"):
        return "component-or-release-profile"
    if path.startswith("research/05_evaluation/"):
        return "evaluation-summary-or-rubric"
    if path.startswith("research/04_experiments/"):
        return "experiment-plan-or-learning-log"
    if path.startswith("research/03_data/"):
        return "data-governance-or-schema"
    if path.startswith("research/02_requirements/"):
        return "requirement-or-user-research"
    if path.startswith("research/01_literature/"):
        return "literature-note"
    if path.startswith("research/00_admin/"):
        return "scope-or-decision-history"
    if path.startswith("research/06_reports/") or path.startswith("reports/"):
        return "report-or-figure"
    if path.startswith("docs/"):
        return "architecture-or-operations-documentation"
    if path.startswith("tests/"):
        return "automated-or-manual-verification"
    if path.startswith("scripts/") or path.startswith("experiments/"):
        return "reproduction-or-analysis-tool"
    if path.startswith("src/") or path.startswith("services/"):
        return "backend-implementation"
    if path.startswith("apps/"):
        return "frontend-implementation"
    if path.startswith("deploy/") or path == "compose.staging.yml":
        return "deployment-configuration"
    if path.startswith(".github/"):
        return "project-governance-or-ci"
    return "repository-configuration"


def repository_files(root: Path, output_directory: Path) -> list[tuple[str, str]]:
    tracked = set(
        run_git(root, "ls-files", "--", *INVENTORY_ROOTS).splitlines()
    )
    ordinary_untracked = set(
        run_git(
            root,
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            *INVENTORY_ROOTS,
        ).splitlines()
    )
    output_rel = output_directory.resolve().relative_to(root.resolve()).as_posix()
    excluded_outputs = {f"{output_rel}/{name}" for name in OUTPUT_FILENAMES}
    rows = [(path, "tracked") for path in tracked - excluded_outputs]
    rows.extend(
        (path, "untracked")
        for path in ordinary_untracked - tracked - excluded_outputs
    )
    return sorted(rows)


def parse_registry(path: Path) -> list[RegistryRow]:
    rows: list[RegistryRow] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 9:
            raise ValueError(
                f"{path}:{line_number}: expected 9 table cells, found {len(cells)}"
            )
        rows.append(
            RegistryRow(
                result_id=cells[0].strip("`"),
                date=cells[1],
                component=cells[2],
                dataset_or_corpus=cells[3],
                status=cells[4],
                decision=cells[5],
                summary_cell=cells[6],
                machine_record_cell=cells[7],
                reproduction=cells[8],
                line_number=line_number,
            )
        )
    result_ids = [row.result_id for row in rows]
    duplicates = sorted(
        result_id for result_id, count in Counter(result_ids).items() if count > 1
    )
    if duplicates:
        raise ValueError(f"duplicate result IDs: {', '.join(duplicates)}")
    return rows


def markdown_link_targets(cell: str) -> list[str]:
    return MARKDOWN_LINK_PATTERN.findall(cell)


def decision_class(status: str, decision: str) -> str:
    normalized_status = re.sub(r"[`*_]", "", status).strip().lower()
    normalized_decision = re.sub(r"[`*_]", "", decision).strip().lower()
    combined = f"{normalized_status} {normalized_decision}"
    if re.search(r"\bno[ -]release\b", combined):
        return "no-release"

    # The status cell is the authoritative result label.  Restrict matching to
    # its leading label so diagnostic phrases such as ``invalid citation`` do
    # not turn a completed Keep result into an invalid execution.  Only fall
    # back to the decision cell for older rows without a structured status.
    status_patterns = (
        (r"^(?:completed\s+)?invalid(?:[ -]execution)?\b", "invalid"),
        (r"^(?:completed\s+)?keep\b", "keep"),
        (r"^(?:completed\s+)?refine\b", "refine"),
        (r"^(?:completed\s+)?drop\b", "drop"),
        (r"^(?:completed\s+)?go[ -]deeper\b", "go-deeper"),
    )
    for pattern, classification in status_patterns:
        if re.search(pattern, normalized_status):
            return classification

    decision_patterns = (
        (r"^(?:decision:\s*)?invalid(?:[ -]execution)?\b", "invalid"),
        (r"^(?:decision:\s*)?keep\b", "keep"),
        (r"^(?:decision:\s*)?refine\b", "refine"),
        (r"^(?:decision:\s*)?drop\b", "drop"),
        (r"^(?:decision:\s*)?go[ -]deeper\b", "go-deeper"),
    )
    for pattern, classification in decision_patterns:
        if re.search(pattern, normalized_decision):
            return classification
    return "other"


def write_csv(path: Path, fieldnames: Iterable[str], rows: Iterable[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(fieldnames),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def build_inventory(root: Path, output_directory: Path) -> dict[str, object]:
    output_directory.mkdir(parents=True, exist_ok=True)

    file_rows: list[dict[str, object]] = []
    category_counts: Counter[str] = Counter()
    git_state_counts: Counter[str] = Counter()
    for relative_path, git_state in repository_files(root, output_directory):
        absolute_path = root / relative_path
        if not absolute_path.is_file():
            continue
        category = classify_path(relative_path)
        file_rows.append(
            {
                "path": relative_path,
                "category": category,
                "git_state": git_state,
                "bytes": absolute_path.stat().st_size,
                "sha256": sha256_file(absolute_path),
            }
        )
        category_counts[category] += 1
        git_state_counts[git_state] += 1
    write_csv(
        output_directory / "evidence-file-inventory.csv",
        ("path", "category", "git_state", "bytes", "sha256"),
        file_rows,
    )

    registry_path = root / "research/05_evaluation/result-registry.md"
    registry_rows = parse_registry(registry_path)
    result_rows: list[dict[str, object]] = []
    decision_counts: Counter[str] = Counter()
    machine_record_count = 0
    missing_links: list[str] = []
    for row in registry_rows:
        summary_targets = markdown_link_targets(row.summary_cell)
        machine_targets = markdown_link_targets(row.machine_record_cell)
        summary_target = next(
            (target for target in summary_targets if target.endswith(".md")),
            summary_targets[0] if summary_targets else "",
        )
        machine_target = next(
            (target for target in machine_targets if target.startswith("records/") and target.endswith(".json")),
            "",
        )
        summary_path = (
            f"research/05_evaluation/{summary_target}" if summary_target else ""
        )
        machine_path = (
            f"research/05_evaluation/{machine_target}" if machine_target else ""
        )
        summary_present = bool(summary_path and (root / summary_path).is_file())
        machine_present = bool(machine_path and (root / machine_path).is_file())
        linked_paths = [
            f"research/05_evaluation/{target}"
            for target in summary_targets + machine_targets
            if "://" not in target and not target.startswith("#")
        ]
        missing_links.extend(
            path for path in linked_paths if not (root / path).is_file()
        )
        if machine_present:
            json.loads((root / machine_path).read_text())
            machine_record_count += 1
        classification = decision_class(row.status, row.decision)
        decision_counts[classification] += 1
        result_rows.append(
            {
                "result_id": row.result_id,
                "date": row.date,
                "component": row.component,
                "dataset_or_corpus": row.dataset_or_corpus,
                "status": row.status,
                "decision": row.decision,
                "decision_class": classification,
                "summary_path": summary_path,
                "summary_present": summary_present,
                "machine_record_path": machine_path,
                "machine_record_present": machine_present,
                "all_linked_evidence_paths": ";".join(linked_paths),
                "reproduction": row.reproduction,
                "registry_line": row.line_number,
            }
        )
    if missing_links:
        raise ValueError(f"missing registry links: {', '.join(sorted(missing_links))}")
    write_csv(
        output_directory / "evaluation-result-inventory.csv",
        (
            "result_id",
            "date",
            "component",
            "dataset_or_corpus",
            "status",
            "decision",
            "decision_class",
            "summary_path",
            "summary_present",
            "machine_record_path",
            "machine_record_present",
            "all_linked_evidence_paths",
            "reproduction",
            "registry_line",
        ),
        result_rows,
    )

    local_rows: list[dict[str, object]] = []
    for relative_directory in LOCAL_AGGREGATE_DIRECTORIES:
        directory = root / relative_directory
        files = sorted(
            path
            for path in directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        ) if directory.is_dir() else []
        local_rows.append(
            {
                "directory": relative_directory,
                "file_count": len(files),
                "total_bytes": sum(path.stat().st_size for path in files),
                "inventory_boundary": (
                    "aggregate-only; ignored local contents and filenames are not copied"
                ),
            }
        )
    write_csv(
        output_directory / "local-evidence-aggregates.csv",
        ("directory", "file_count", "total_bytes", "inventory_boundary"),
        local_rows,
    )

    json_groups = {
        "machine-result-record": root / "research/05_evaluation/records",
        "committed-evaluation-dataset": root / "research/05_evaluation/datasets",
        "evaluation-instrument": root / "research/05_evaluation/instruments",
        "component-or-release-profile": root / "research/05_evaluation/profiles",
    }
    json_validation: dict[str, dict[str, int]] = {}
    record_join_quality: dict[str, object] = {}
    for label, directory in json_groups.items():
        paths = sorted(directory.glob("*.json"))
        valid = 0
        run_id_filename_mismatches: list[dict[str, str]] = []
        missing_component = 0
        missing_dataset_id = 0
        missing_corpus_id = 0
        for path in paths:
            payload = json.loads(path.read_text())
            valid += 1
            if label == "machine-result-record":
                if payload.get("run_id") != path.stem:
                    run_id_filename_mismatches.append(
                        {
                            "file": path.relative_to(root).as_posix(),
                            "run_id": str(payload.get("run_id", "")),
                        }
                    )
                missing_component += int("component" not in payload)
                missing_dataset_id += int("dataset_id" not in payload)
                missing_corpus_id += int("corpus_id" not in payload)
        json_validation[label] = {"files": len(paths), "valid_json": valid}
        if label == "machine-result-record":
            record_join_quality = {
                "run_id_filename_mismatch_count": len(run_id_filename_mismatches),
                "run_id_filename_mismatches": run_id_filename_mismatches,
                "without_component_count": missing_component,
                "without_dataset_id_count": missing_dataset_id,
                "without_corpus_id_count": missing_corpus_id,
                "interpretation": (
                    "Use the registry link and record run_id rather than assuming "
                    "the filename is the result ID. Missing optional fields reflect "
                    "legacy/program schemas and require result-summary context."
                ),
            }

    summary: dict[str, object] = {
        "schema_version": 1,
        "code_revision": run_git(root, "rev-parse", "HEAD").strip(),
        "inventory_boundary": {
            "listed_individually": "tracked and ordinary untracked report-relevant repository files",
            "aggregate_only": list(LOCAL_AGGREGATE_DIRECTORIES),
            "excluded_from_local_aggregate_detail": "ignored filenames, hashes, and contents",
        },
        "repository_files": {
            "count": len(file_rows),
            "by_category": dict(sorted(category_counts.items())),
            "by_git_state": dict(sorted(git_state_counts.items())),
        },
        "evaluation_registry": {
            "result_count": len(registry_rows),
            "decision_classes": dict(sorted(decision_counts.items())),
            "machine_record_count": machine_record_count,
            "without_machine_record_count": len(registry_rows) - machine_record_count,
            "broken_local_link_count": 0,
        },
        "json_validation": json_validation,
        "record_join_quality": record_join_quality,
        "local_evidence_aggregates": local_rows,
    }
    (output_directory / "evidence-inventory-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("research/06_reports/final/evidence-inventory"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output_directory = args.output_directory
    if not output_directory.is_absolute():
        output_directory = root / output_directory
    summary = build_inventory(root, output_directory.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
