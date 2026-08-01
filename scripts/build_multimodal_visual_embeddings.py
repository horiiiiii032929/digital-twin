#!/usr/bin/env python3
"""Build sealed-development V3 image vectors without reading held-out."""

from __future__ import annotations

import argparse
import json
import os
import platform
import resource
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

from scripts.validate_multimodal_retrieval_dataset import ROOT, validate_dataset
from src.digital_twin.evaluation.multimodal_benchmark import (
    load_sealed_development,
    sha256_file,
)
from src.digital_twin.evaluation.multimodal_retrieval import (
    contextual_crop_bbox,
    normalized_crop_pixels,
)


SEALED_ROOT = ROOT / "data/processed/multimodal_retrieval_v1/sealed_v1"
DEFAULT_SEAL = SEALED_ROOT / "seal.json"
DEFAULT_LEDGER = SEALED_ROOT / "heldout_once_ledger.json"
DEFAULT_REPRESENTATIONS = (
    ROOT
    / "data/processed/multimodal_retrieval_v1/"
    "development_artifacts_v1/representations.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "data/processed/multimodal_retrieval_v1/"
    "development_artifacts_v1/visual_embeddings.json"
)
MODEL_NAME = "ViT-B-32-quickgelu"
PRETRAINED_TAG = "openai"
MODEL_REPOSITORY = "timm/vit_base_patch32_clip_224.openai"
MODEL_FILENAME = "open_clip_model.safetensors"
MODEL_WEIGHT_SHA256 = (
    "e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seal", type=Path, default=DEFAULT_SEAL)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument(
        "--representations", type=Path, default=DEFAULT_REPRESENTATIONS
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--device", choices=("cpu", "mps"), default="mps")
    return parser.parse_args()


def verified_weight_path() -> Path:
    from huggingface_hub import try_to_load_from_cache

    cached = try_to_load_from_cache(MODEL_REPOSITORY, MODEL_FILENAME)
    if not isinstance(cached, str):
        raise ValueError("frozen OpenCLIP weights are absent from the local cache")
    path = Path(cached)
    if sha256_file(path) != MODEL_WEIGHT_SHA256:
        raise ValueError("frozen OpenCLIP weight hash mismatch")
    return path


def source_image_by_asset(dataset: dict[str, Any]) -> dict[str, Path]:
    return {
        asset["asset_id"]: (ROOT / asset["path"]).resolve()
        for asset in dataset["source_assets"]
    }


def visual_inputs(
    image: Image.Image, records: list[dict[str, Any]]
) -> tuple[list[Image.Image], list[dict[str, Any]]]:
    images: list[Image.Image] = []
    metadata: list[dict[str, Any]] = []
    for record in records:
        bbox = tuple(float(value) for value in record["bbox"])
        if record["kind"] == "page_text":
            crop_bbox = (0.0, 0.0, 1.0, 1.0)
            crop = image.copy()
            kind = "visual_page"
        elif record["kind"] == "ocr_block":
            crop_bbox = contextual_crop_bbox(bbox)
            crop = image.crop(
                normalized_crop_pixels(
                    crop_bbox, image_width=image.width, image_height=image.height
                )
            )
            kind = "visual_crop"
        else:
            continue
        images.append(crop)
        metadata.append(
            {
                "record_id": record["record_id"],
                "asset_id": record["asset_id"],
                "course_id": record["course_id"],
                "source_artifact_id": record["source_artifact_id"],
                "render_sha256": record["render_sha256"],
                "page": record["page"],
                "permission": record["permission"],
                "kind": kind,
                "bbox": list(bbox),
                "crop_bbox": list(crop_bbox),
            }
        )
    return images, metadata


def main() -> int:
    args = parse_args()
    try:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        weight_path = verified_weight_path()
        dataset, seal = load_sealed_development(
            root=ROOT, seal_path=args.seal, ledger_path=args.ledger
        )
        validate_dataset(dataset)
        representations = json.loads(args.representations.read_text(encoding="utf-8"))
        if representations["seal_id"] != seal["seal_id"]:
            raise ValueError("representation seal ID mismatch")
        if representations["development_sha256"] != seal["development_sha256"]:
            raise ValueError("representation development hash mismatch")
        if representations.get("heldout_read") is not False:
            raise ValueError("representation does not preserve held-out closure")

        import open_clip
        import torch

        if args.device == "mps" and not torch.backends.mps.is_available():
            raise ValueError("MPS was requested but is unavailable")
        load_started = time.perf_counter()
        model, _, preprocess = open_clip.create_model_and_transforms(
            MODEL_NAME, pretrained=PRETRAINED_TAG, device=args.device
        )
        model.eval()
        model_load_seconds = time.perf_counter() - load_started
        images_by_asset = source_image_by_asset(dataset)
        vectors: list[dict[str, Any]] = []
        embedding_started = time.perf_counter()
        for index, asset in enumerate(representations["assets"], start=1):
            with Image.open(images_by_asset[asset["asset_id"]]) as opened:
                image = opened.convert("RGB")
                crops, metadata = visual_inputs(image, asset["records"]["V1"])
            batch = torch.stack([preprocess(crop) for crop in crops]).to(args.device)
            with torch.inference_mode():
                encoded = model.encode_image(batch)
                encoded = encoded / encoded.norm(dim=-1, keepdim=True)
            for record, vector in zip(
                metadata, encoded.detach().cpu().float().tolist(), strict=True
            ):
                vectors.append({**record, "embedding": vector})
            print(
                f"multimodal visual embedding asset={index}/"
                f"{len(representations['assets'])} complete=true"
            )
        embedding_seconds = time.perf_counter() - embedding_started
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        output = {
            "schema_version": 1,
            "artifact_id": "multimodal-retrieval-v1-development-visual-embeddings",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat(),
            "seal_id": seal["seal_id"],
            "development_sha256": seal["development_sha256"],
            "representations_sha256": sha256_file(args.representations),
            "heldout_status": seal["heldout_status"],
            "heldout_read": False,
            "candidate_version": "openclip-vit-b-32-quickgelu-openai-rrf@v1",
            "provider": {
                "implementation": "open-clip-torch",
                "version": open_clip.__version__,
                "model": MODEL_NAME,
                "pretrained_tag": PRETRAINED_TAG,
                "weight_sha256": MODEL_WEIGHT_SHA256,
                "weight_path": str(weight_path),
                "external_calls": 0,
                "paid_cost_usd": 0,
            },
            "configuration": {
                "dimension": len(vectors[0]["embedding"]),
                "normalized": True,
                "crop_padding": 0.03,
                "minimum_crop_width": 0.25,
                "minimum_crop_height": 0.20,
                "rank_fusion": "reciprocal-rank-fusion",
                "rank_constant": 60,
                "candidate_depth": 20,
                "query_prefix": "study material relevant to:",
            },
            "operational": {
                "device": args.device,
                "platform": platform.platform(),
                "model_parameters": sum(parameter.numel() for parameter in model.parameters()),
                "model_load_seconds": model_load_seconds,
                "embedding_seconds": embedding_seconds,
                "embedding_seconds_per_region": embedding_seconds / len(vectors),
                "vector_count": len(vectors),
                "peak_rss_bytes": peak_rss,
                "external_provider_called": False,
                "paid_provider_called": False,
            },
            "vectors": vectors,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "vectors": len(vectors),
                    "dimension": output["configuration"]["dimension"],
                    "output": str(args.output),
                    "output_sha256": sha256_file(args.output),
                    "heldout_read": False,
                    "external_provider_called": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal visual embedding build failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
