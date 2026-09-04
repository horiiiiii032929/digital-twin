#!/usr/bin/env python3
"""Materialize one release-bound visual index from the qualified component ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from services.api.app.config import ROOT
from src.digital_twin.grounding import VisualIndexStoreV1
from src.digital_twin.student import SQLiteStudentRepository


DEFAULT_DATABASE = ROOT / "data/interim/runtime/digital-twin.sqlite3"
DEFAULT_SOURCE_LEDGER = (
    ROOT
    / "reports/generated/true-visual-colpali-confirmation-001/provider-ledger.sqlite3"
)
DEFAULT_DATASET = (
    ROOT / "research/05_evaluation/datasets/true_visual_colpali_confirmation_001.json"
)
DEFAULT_OUTPUT_ROOT = ROOT / "data/interim/runtime/derived/visual-indexes"


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--source-ledger", type=Path, default=DEFAULT_SOURCE_LEDGER)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def _materialize(args: argparse.Namespace, *, output_root: Path) -> dict[str, object]:
    for path, label in (
        (args.database, "student database"),
        (args.source_ledger, "qualified visual component ledger"),
        (args.dataset, "visual dataset"),
    ):
        if not path.is_file():
            raise SystemExit(f"{label} is unavailable: {path}")
    repository = SQLiteStudentRepository(args.database)
    release = repository.get_release(args.release_id)
    if release is None:
        raise SystemExit(f"release is unavailable: {args.release_id}")
    store = VisualIndexStoreV1(output_root)
    manifest = store.materialize_from_component_ledger(
        source_ledger_path=args.source_ledger,
        dataset_path=args.dataset,
        course_id=release.course_id,
        release_id=release.id,
        profile_id=release.profile_id,
        profile_version=release.profile_version,
        chunks=release.chunks,
    )
    store.load_bound(
        course_id=release.course_id,
        release_id=release.id,
        profile_id=release.profile_id,
        profile_version=release.profile_version,
        source_ledger_sha256=manifest.source_ledger_sha256,
        chunks=release.chunks,
    )
    return {
        "status": "ready",
        "mode": "jina-v4-late-interaction",
        "release_id": release.id,
        "course_id": release.course_id,
        "artifact_id": manifest.artifact_id,
        "record_count": manifest.record_count,
        "source_set_sha256": manifest.source_set_sha256,
        "dataset_sha256": manifest.dataset_sha256,
        "source_ledger_sha256": manifest.source_ledger_sha256,
        "output": str(store.path_for(release.id)),
    }


def main() -> int:
    args = _arguments()
    if args.preflight:
        with tempfile.TemporaryDirectory(prefix="visual-index-preflight-") as directory:
            result = _materialize(args, output_root=Path(directory))
            result["preflight_only"] = True
    else:
        result = _materialize(args, output_root=args.output_root)
        result["preflight_only"] = False
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
