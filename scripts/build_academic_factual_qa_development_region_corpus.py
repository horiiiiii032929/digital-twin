#!/usr/bin/env python3
"""Re-materialize the development corpus at the granularity its gold expects.

The committed development source package ships cluster-level spans. The
development gold cites sentence-level sub-spans inside those clusters. A
product handed the cluster cites the whole cluster, so every citation and
atomic-claim score comes back exactly zero while answer-span recall stays near
one: the system quotes the right text and is scored zero for quoting too much
of it. Multi-evidence questions fare worse still -- they need two distinct
authoritative atoms and a one-cluster-per-case corpus can only ever supply one.

Nothing new is authored here. The clusters already carry `reference_targets`
with exact `evidence_spans`, and `registered_source_chunks` is the same
registered mechanism that produced the sealed package's region corpus. This
script only applies it to the development clusters and writes the result to
ignored output.

No provider is called and no source is added.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.digital_twin.grounding.source_registration import (  # noqa: E402
    registered_source_chunks,
)
from src.digital_twin.repository_freeze import (  # noqa: E402
    require_bounded_pilot_operation_allowed,
)


INSTRUMENT_ID = "academic-factual-qa-development-region-corpus-001"
SOURCES_ENVIRONMENT_VARIABLE = "DEVELOPMENT_SOURCES_PATH"
GOLD_PATH = ROOT / (
    "research/05_evaluation/datasets/"
    "academic_factual_qa_open_10000_v1_development_gold_002.json"
)
DEFAULT_OUTPUT = (
    ROOT / "reports/generated" / INSTRUMENT_ID / "development-region-corpus.json"
)


class RegionCorpusError(RuntimeError):
    """Raised when the re-materialized corpus would not match its gold."""


def _sources_path() -> Path:
    value = os.getenv(SOURCES_ENVIRONMENT_VARIABLE)
    if not value:
        raise RegionCorpusError(
            f"export {SOURCES_ENVIRONMENT_VARIABLE} to the development source package"
        )
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise RegionCorpusError(f"development source package is missing: {path}")
    return path


def build(sources_path: Path) -> dict[str, Any]:
    """Return a region-granularity corpus in the sealed package's chunk format."""

    package = json.loads(sources_path.read_text(encoding="utf-8"))
    clusters = package.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        raise RegionCorpusError("development source package declares no clusters")
    chunks = registered_source_chunks(clusters)
    if not chunks:
        raise RegionCorpusError("no citable regions were registered")
    return {
        "schema_version": 1,
        "split": "development-retrieval-corpus",
        "derived_from": package.get("instrument_id") or "academic-factual-qa-open-10000-v1-development-002",
        "construction_method": "registered-source-chunks",
        "cluster_count": len(clusters),
        "registered_region_count": len(chunks),
        "provider_calls": 0,
        "private_data_used": False,
        "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
    }


def _gold_spans() -> set[tuple[str, int, int]]:
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))["gold"]
    spans: set[tuple[str, int, int]] = set()
    for row in gold:
        for claim in row.get("claims") or []:
            for ref in claim.get("evidence_refs") or []:
                spans.add(
                    (
                        str(ref["source_artifact_id"]),
                        int(ref["char_start"]),
                        int(ref["char_end"]),
                    )
                )
    return spans


def coverage(corpus: dict[str, Any]) -> dict[str, Any]:
    """Report how many gold evidence spans this corpus can be cited for exactly."""

    available = {
        (
            str(chunk["source_artifact_id"]),
            int(chunk["metadata"]["char_start"]),
            int(chunk["metadata"]["char_end"]),
        )
        for chunk in corpus["chunks"]
    }
    wanted = _gold_spans()
    matched = wanted & available
    return {
        "gold_evidence_spans": len(wanted),
        "exactly_citable": len(matched),
        "coverage": round(len(matched) / len(wanted), 4) if wanted else 0.0,
        "registered_regions": len(available),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.parse_args()
    require_bounded_pilot_operation_allowed(INSTRUMENT_ID, "dataset_generation")
    arguments = parser.parse_args()
    corpus = build(_sources_path())
    report = coverage(corpus)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(corpus, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "instrument_id": INSTRUMENT_ID,
                "output": str(arguments.output),
                "cluster_count": corpus["cluster_count"],
                "registered_region_count": corpus["registered_region_count"],
                "provider_calls": 0,
                **report,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
