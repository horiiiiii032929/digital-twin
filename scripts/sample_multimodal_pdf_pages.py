#!/usr/bin/env python3
"""Select and render private PDF pages for multimodal benchmark authoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf
from PIL import Image, ImageDraw, ImageFont

from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_ROOT = Path.home() / "Documents" / "academia_vault"
DEFAULT_INVENTORY = (
    ROOT / "data/interim/multimodal_retrieval_v1/source_inventory_v1.json"
)
DEFAULT_OUTPUT_ROOT = ROOT / "data/interim/multimodal_retrieval_v1/pdf_samples_v1"
ACTIVE_MANIFEST = ROOT / "research/05_evaluation/cross_course_portfolio_v2.manifest.json"

TABLE_PATTERN = re.compile(r"\b(table|row|column|matrix|schema|relation)\b", re.IGNORECASE)
CHART_PATTERN = re.compile(r"\b(chart|graph|plot|axis|latency|throughput|distribution)\b", re.IGNORECASE)
EQUATION_PATTERN = re.compile(r"(?:[=∑Σ∫√]|\b(?:equation|probability|formula|derive)\b)", re.IGNORECASE)
FLOW_PATTERN = re.compile(r"\b(flow|pipeline|architecture|process|sequence|state|network)\b", re.IGNORECASE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--per-course", type=int, default=4)
    parser.add_argument("--render-dpi", type=int, default=120)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def active_manifest_paths() -> set[str]:
    manifest = load_json(ACTIVE_MANIFEST)
    return {
        (Path(course["relative_root"]) / document["filename"]).as_posix()
        for course in manifest["courses"]
        for document in course["documents"]
    }


def page_diagnostic(page: pymupdf.Page) -> dict[str, Any]:
    text = page.get_text("text").strip()
    image_count = len(page.get_images(full=True))
    try:
        drawing_count = len(page.get_drawings())
    except RuntimeError:
        drawing_count = 0
    blocks = page.get_text("blocks")
    keyword_flags = {
        "table": bool(TABLE_PATTERN.search(text)),
        "chart": bool(CHART_PATTERN.search(text)),
        "equation": bool(EQUATION_PATTERN.search(text)),
        "flow": bool(FLOW_PATTERN.search(text)),
    }
    score = (
        min(image_count, 8) * 5.0
        + min(drawing_count, 80) * 0.15
        + min(len(blocks), 20) * 0.1
        + sum(2.0 for value in keyword_flags.values() if value)
    )
    if image_count and len(text) < 80:
        score += 4.0
    if len(text) < 5 and not image_count and drawing_count < 3:
        score -= 10.0
    modalities: list[str] = []
    if image_count:
        modalities.extend(["screenshot_or_photo", "scanned_page"])
    if drawing_count >= 5 or keyword_flags["flow"]:
        modalities.append("diagram")
    for modality in ("table", "chart", "equation"):
        if keyword_flags[modality]:
            modalities.append(modality)
    if not modalities:
        modalities.append("text_control")
    return {
        "score": round(score, 4),
        "text_characters": len(text),
        "text_blocks": len(blocks),
        "image_objects": image_count,
        "drawing_objects": drawing_count,
        "suggested_modalities": sorted(set(modalities)),
        "page_text": text[:4000],
    }


def analyze_sources(
    inventory: dict[str, Any], source_root: Path
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    approved_paths = active_manifest_paths()
    diagnostics: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for source in inventory["sources"]:
        if source["format_group"] != "pdf":
            continue
        if source["eligibility"] != "eligible_candidate" and source["relative_path"] not in approved_paths:
            continue
        path = source_root / source["relative_path"]
        try:
            with pymupdf.open(path) as document:
                for page_index, page in enumerate(document):
                    diagnostic = page_diagnostic(page)
                    diagnostics.append(
                        {
                            "course_id": source["course_id"],
                            "source_id": source["source_id"],
                            "relative_path": source["relative_path"],
                            "document_sha256": source["sha256"],
                            "page": page_index + 1,
                            "page_count": document.page_count,
                            **diagnostic,
                        }
                    )
        except (OSError, RuntimeError, ValueError) as error:
            failures.append(
                {
                    "source_id": source["source_id"],
                    "failure": type(error).__name__,
                }
            )
    return diagnostics, failures


def select_pages(
    diagnostics: list[dict[str, Any]], *, per_course: int
) -> list[dict[str, Any]]:
    if per_course < 1:
        raise ValueError("per-course sample size must be positive")
    by_course: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for diagnostic in diagnostics:
        if diagnostic["course_id"] != "unassigned":
            by_course[diagnostic["course_id"]].append(diagnostic)

    selected: list[dict[str, Any]] = []
    for course, candidates in sorted(by_course.items()):
        ranked = sorted(
            candidates,
            key=lambda item: (
                -item["score"],
                item["source_id"],
                item["page"],
            ),
        )
        source_counts: Counter[str] = Counter()
        course_selection: list[dict[str, Any]] = []
        for candidate in ranked:
            if source_counts[candidate["source_id"]] >= 2:
                continue
            course_selection.append(candidate)
            source_counts[candidate["source_id"]] += 1
            if len(course_selection) == per_course:
                break
        if len(course_selection) < per_course:
            for candidate in ranked:
                if candidate in course_selection:
                    continue
                course_selection.append(candidate)
                if len(course_selection) == per_course:
                    break
        selected.extend(course_selection)
    return selected


def render_page(
    source_path: Path,
    page: int,
    output_path: Path,
    *,
    dpi: int,
    renderer: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = output_path.with_suffix("")
    subprocess.run(
        [
            renderer,
            "-f",
            str(page),
            "-l",
            str(page),
            "-singlefile",
            "-r",
            str(dpi),
            "-png",
            str(source_path),
            str(prefix),
        ],
        check=True,
        capture_output=True,
    )


def build_contact_sheets(records: list[dict[str, Any]], output_root: Path) -> list[str]:
    sheets: list[str] = []
    font = ImageFont.load_default()
    for index in range(0, len(records), 12):
        batch = records[index : index + 12]
        canvas = Image.new("RGB", (1600, 1200), "white")
        draw = ImageDraw.Draw(canvas)
        for cell, record in enumerate(batch):
            row, column = divmod(cell, 4)
            image = Image.open(ROOT / record["render_path"]).convert("RGB")
            image.thumbnail((370, 330))
            x = column * 400 + 15
            y = row * 400 + 35
            canvas.paste(image, (x + (370 - image.width) // 2, y))
            draw.text(
                (x, y - 22),
                f"{record['candidate_id']} | {record['course_id']} | p{record['page']}",
                fill="black",
                font=font,
            )
        sheet_path = output_root / f"contact-sheet-{index // 12 + 1:02d}.jpg"
        canvas.save(sheet_path, quality=88)
        sheets.append(sheet_path.relative_to(ROOT).as_posix())
    return sheets


def materialize_sample(
    selected: list[dict[str, Any]],
    *,
    source_root: Path,
    output_root: Path,
    dpi: int,
) -> dict[str, Any]:
    renderer = shutil.which("pdftoppm")
    if renderer is None:
        raise ValueError("pdftoppm is required to render PDF samples")
    render_root = output_root / "renders"
    records: list[dict[str, Any]] = []
    for item in selected:
        candidate_digest = hashlib.sha256(
            f"{item['source_id']}:{item['page']}".encode("utf-8")
        ).hexdigest()[:16]
        candidate_id = f"mm-page-{candidate_digest}"
        render_path = render_root / f"{candidate_id}.png"
        render_page(
            source_root / item["relative_path"],
            item["page"],
            render_path,
            dpi=dpi,
            renderer=renderer,
        )
        records.append(
            {
                "candidate_id": candidate_id,
                **item,
                "render_path": render_path.relative_to(ROOT).as_posix(),
                "render_sha256": hashlib.sha256(render_path.read_bytes()).hexdigest(),
                "review": {
                    "status": "pending_visual_review",
                    "observed_modality": None,
                    "eligible_for_benchmark": None,
                    "notes": "",
                },
            }
        )
    output_root.mkdir(parents=True, exist_ok=True)
    sheets = build_contact_sheets(records, output_root)
    return {
        "sample_id": "academic-vault-multimodal-pdf-sample-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "render_dpi": dpi,
        "records": records,
        "contact_sheets": sheets,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    require_pre_evaluation_operation_allowed("dataset_generation")
    try:
        inventory = load_json(args.inventory)
        diagnostics, failures = analyze_sources(inventory, args.source_root)
        selected = select_pages(diagnostics, per_course=args.per_course)
        sample = materialize_sample(
            selected,
            source_root=args.source_root,
            output_root=args.output_root,
            dpi=args.render_dpi,
        )
        sample["source_failures"] = failures
        sample["analyzed_pages"] = len(diagnostics)
        write_json(args.output_root / "sample_queue_v1.json", sample)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"multimodal PDF sampling failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "status": "passed",
                "analyzed_pages": len(diagnostics),
                "selected_pages": len(selected),
                "courses": dict(sorted(Counter(item["course_id"] for item in selected).items())),
                "source_failures": len(failures),
                "contact_sheets": len(sample["contact_sheets"]),
                "contains_source_text": False,
                "private_output": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
