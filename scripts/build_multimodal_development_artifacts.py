#!/usr/bin/env python3
"""Build local V0-V2 representations from sealed multimodal development assets."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.validate_multimodal_retrieval_dataset import ROOT, validate_dataset
from src.digital_twin.evaluation.multimodal_benchmark import (
    load_sealed_development,
    sha256_file,
)
from src.digital_twin.evaluation.multimodal_retrieval import (
    build_candidate_records,
    group_ocr_lines,
)
from src.digital_twin.model_policy import require_model_allowed
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


SEALED_ROOT = ROOT / "data/processed/multimodal_retrieval_v1/sealed_v1"
DEFAULT_SEAL = SEALED_ROOT / "seal.json"
DEFAULT_LEDGER = SEALED_ROOT / "heldout_once_ledger.json"
DEFAULT_OUTPUT_DIR = (
    ROOT / "data/processed/multimodal_retrieval_v1/development_artifacts_v1"
)
DEFAULT_OUTPUT = DEFAULT_OUTPUT_DIR / "representations.json"
SWIFT_SOURCE = ROOT / "scripts/apple_vision_ocr.swift"
DESCRIPTION_MODEL = "gemma3:4b"
DESCRIPTION_MODEL_DIGEST = "a2af6cc3eb7f"
ANSI_ESCAPE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
DESCRIPTION_PROMPT = """Describe this study-material page for retrieval using only visible evidence.
Return one JSON object with exactly these fields:
- visual_type: short string
- description: concise factual description
- visible_labels: array of important visible labels
- relationships: array of spatial, directional, or symbol relationships
- colors_and_symbols: array of meaningful colors, marks, icons, or annotations
- table_or_diagram_structure: concise string, empty when absent
Do not answer a user question. Do not infer content that is not visible.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--skip-descriptions", action="store_true")
    return parser.parse_args()


def compile_ocr(output_dir: Path) -> Path:
    binary = output_dir / "apple_vision_ocr"
    subprocess.run(
        ["swiftc", str(SWIFT_SOURCE), "-o", str(binary)],
        check=True,
        capture_output=True,
        text=True,
    )
    return binary


def run_ocr(binary: Path, image_paths: list[Path]) -> tuple[dict[str, Any], float]:
    started = time.perf_counter()
    completed = subprocess.run(
        [str(binary), *(str(path) for path in image_paths)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout), time.perf_counter() - started


def parse_ollama_json(output: str) -> dict[str, Any]:
    cleaned = ANSI_ESCAPE.sub("", output).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("local vision response did not contain a JSON object")
    value = json.loads(cleaned[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("local vision response must be a JSON object")
    return value


def describe_image(image_path: Path) -> tuple[dict[str, Any], float]:
    require_model_allowed(DESCRIPTION_MODEL)
    started = time.perf_counter()
    environment = dict(os.environ)
    environment["OLLAMA_NOHISTORY"] = "1"
    completed = subprocess.run(
        [
            "ollama",
            "run",
            DESCRIPTION_MODEL,
            "--nowordwrap",
            "--format",
            "json",
            DESCRIPTION_PROMPT,
            str(image_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    return parse_ollama_json(completed.stdout), time.perf_counter() - started


def main() -> int:
    args = parse_args()
    require_pre_evaluation_operation_allowed("dataset_generation")
    try:
        dataset, seal = load_sealed_development(
            root=ROOT, seal_path=args.seal, ledger_path=args.ledger
        )
        validate_dataset(dataset)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        assets = sorted(dataset["source_assets"], key=lambda asset: asset["asset_id"])
        image_paths = [(ROOT / asset["path"]).resolve() for asset in assets]
        ocr_binary = compile_ocr(args.output.parent)
        ocr_payload, ocr_seconds = run_ocr(ocr_binary, image_paths)
        ocr_by_path = {record["path"]: record for record in ocr_payload["records"]}

        asset_results = []
        description_seconds = 0.0
        for index, (asset, image_path) in enumerate(
            zip(assets, image_paths, strict=True), start=1
        ):
            ocr_record = ocr_by_path[str(image_path)]
            blocks = group_ocr_lines(ocr_record["lines"])
            description = None
            elapsed = 0.0
            if not args.skip_descriptions:
                description, elapsed = describe_image(image_path)
                description_seconds += elapsed
            asset_results.append(
                {
                    "asset_id": asset["asset_id"],
                    "ocr": {
                        "width": ocr_record["width"],
                        "height": ocr_record["height"],
                        "line_count": len(ocr_record["lines"]),
                        "blocks": blocks,
                    },
                    "description": {
                        "model": DESCRIPTION_MODEL,
                        "model_digest": DESCRIPTION_MODEL_DIGEST,
                        "review_status": "unreviewed-ranking-metadata",
                        "content": description,
                        "elapsed_seconds": elapsed,
                    }
                    if description is not None
                    else None,
                    "records": build_candidate_records(
                        asset, ocr_blocks=blocks, description=description
                    ),
                }
            )
            print(f"multimodal preprocessing asset={index}/{len(assets)} complete=true")

        output = {
            "schema_version": 1,
            "artifact_id": "multimodal-retrieval-v1-development-representations",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "seal_id": seal["seal_id"],
            "development_sha256": seal["development_sha256"],
            "heldout_status": seal["heldout_status"],
            "heldout_read": False,
            "candidate_versions": {
                "V0": "selectable-page-text-bm25@v1",
                "V1": "apple-vision-ocr-block-bm25@v1",
                "V2": "apple-layout-plus-local-gemma3-description-bm25@v1",
            },
            "providers": {
                "ocr": {
                    "implementation": "Apple Vision VNRecognizeTextRequest",
                    "recognition_level": ocr_payload["recognitionLevel"],
                    "uses_language_correction": ocr_payload[
                        "usesLanguageCorrection"
                    ],
                    "platform": platform.platform(),
                    "external_calls": 0,
                },
                "description": {
                    "implementation": "local Ollama",
                    "model": DESCRIPTION_MODEL,
                    "model_digest": DESCRIPTION_MODEL_DIGEST,
                    "external_calls": 0,
                    "authoritative": False,
                    "review_status": "unreviewed-ranking-metadata",
                    "enabled": not args.skip_descriptions,
                },
            },
            "operational": {
                "asset_count": len(assets),
                "ocr_total_seconds": ocr_seconds,
                "ocr_seconds_per_asset": ocr_seconds / len(assets),
                "description_total_seconds": description_seconds,
                "description_seconds_per_asset": description_seconds / len(assets),
                "paid_provider_called": False,
                "external_provider_called": False,
            },
            "assets": asset_results,
        }
        args.output.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "assets": len(assets),
                    "output": str(args.output),
                    "output_sha256": sha256_file(args.output),
                    "heldout_read": False,
                    "paid_provider_called": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"multimodal development preprocessing failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
