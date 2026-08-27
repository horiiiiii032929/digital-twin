#!/usr/bin/env python3
"""Build the immutable 30-cluster public visual supplement.

The builder reads only the already-approved public confirmation snapshots.
Original diagrams are hash-bound in place.  Table and equation regions are
rendered deterministically from the frozen source excerpts.  Rendered files and
raw snapshots remain ignored; the committed dataset contains lineage and hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from src.digital_twin.repository_freeze import require_pre_evaluation_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "data/external/academic_factual_qa_confirmation_002"
CASES_PATH = (
    ROOT / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_cases.json"
)
MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_source_manifest.json"
)
DATASET_PATH = (
    ROOT
    / "research/05_evaluation/datasets/academic_factual_qa_visual_supplement_001.json"
)
RENDER_ROOT = ROOT / "reports/generated/academic-factual-qa-visual-supplement-001/assets"
DATASET_ID = "academic-factual-qa-visual-supplement-001"

BOUNDARY_SEQUENCE = (
    "no-evidence",
    "cross-course",
    "stale-version",
    "permission",
    "unsupported-premise",
) * 6

BOUNDARY_ACTION = {
    "no-evidence": "abstain",
    "cross-course": "abstain",
    "stale-version": "clarify",
    "permission": "refuse",
    "unsupported-premise": "abstain",
}

DIAGRAMS: tuple[dict[str, str], ...] = (
    {
        "course_id": "operating-systems",
        "asset_path": "content/assignments/memory-allocator/img/memory-block.svg",
        "document_path": "content/assignments/memory-allocator/README.md",
        "question": "Which three regions appear in order inside the depicted memory block?",
        "answer": "The block contains struct block_meta, padding, and payload, followed by trailing padding.",
    },
    {
        "course_id": "operating-systems",
        "asset_path": "content/assignments/memory-allocator/img/split-block.svg",
        "document_path": "content/assignments/memory-allocator/README.md",
        "question": "What new region is created when the unused memory block is split?",
        "answer": "The split creates a second struct block_meta followed by free space.",
    },
    {
        "course_id": "operating-systems",
        "asset_path": "content/assignments/memory-allocator/img/coalesce-blocks.svg",
        "document_path": "content/assignments/memory-allocator/README.md",
        "question": "What happens to the two adjacent payload regions after coalescing?",
        "answer": "They become one larger payload under a single struct block_meta.",
    },
    {
        "course_id": "operating-systems",
        "asset_path": "content/software-stack/operating-system/media/os-reference-monitor.svg",
        "document_path": "content/software-stack/operating-system/README.md",
        "question": "Which component is shown mediating access between applications and hardware resources?",
        "answer": "The operating system reference monitor mediates access between applications and hardware resources.",
    },
    {
        "course_id": "operating-systems",
        "asset_path": "content/io/lecture/media/file-descriptor-table.svg",
        "document_path": "content/io/lecture/slides/file-interface.md",
        "question": "What structure maps process file descriptors to open-file information?",
        "answer": "The process file descriptor table maps descriptors to open-file information.",
    },
    {
        "course_id": "computer-networking",
        "asset_path": "protocols/figures/simple-lan.svg",
        "document_path": "protocols/ipv6.rst",
        "question": "What common network connects the hosts and router in the simple LAN diagram?",
        "answer": "The hosts and router share the same local-area network segment.",
    },
    {
        "course_id": "computer-networking",
        "asset_path": "protocols/figures/bgp-hierarchy.svg",
        "document_path": "protocols/bgp.rst",
        "question": "What hierarchy is depicted between autonomous systems in the BGP figure?",
        "answer": "The figure depicts provider-customer relationships between autonomous systems.",
    },
    {
        "course_id": "computer-networking",
        "asset_path": "protocols/figures/tcp-fsm.png",
        "document_path": "protocols/tcp.rst",
        "question": "What kind of state transition structure is depicted for TCP?",
        "answer": "The image depicts the TCP finite-state machine and transitions between connection states.",
    },
    {
        "course_id": "computer-networking",
        "asset_path": "principles/figures/csmaca-1.svg",
        "document_path": "principles/sharing.rst",
        "question": "What sequence follows a successful CSMA/CA data transmission in the diagram?",
        "answer": "A successful data transmission is followed by an acknowledgment after the inter-frame interval.",
    },
    {
        "course_id": "computer-networking",
        "asset_path": "principles/figures/frame-bus.png",
        "document_path": "principles/sharing.rst",
        "question": "How does a transmitted frame propagate on the shared bus?",
        "answer": "The electrical signal propagates in both directions along the shared bus.",
    },
)


class VisualSupplementError(ValueError):
    """Raised when deterministic visual construction drifts."""


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_svg(title: str, excerpt: str, *, modality: str) -> bytes:
    normalized = re.sub(r"\s+", " ", excerpt).strip()
    words = normalized.split()
    lines: list[str] = []
    line: list[str] = []
    for word in words:
        if len(" ".join(line + [word])) > 72:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    if line:
        lines.append(" ".join(line))
    lines = lines[:11]
    body = "".join(
        f'<text x="48" y="{126 + index * 36}" font-family="monospace" '
        f'font-size="20">{html.escape(value)}</text>'
        for index, value in enumerate(lines)
    )
    label = "Pinned source table" if modality == "table" else "Pinned source equation"
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="560" '
        'viewBox="0 0 1000 560"><rect width="1000" height="560" fill="#fff"/>'
        f'<text x="48" y="50" font-family="sans-serif" font-size="28" font-weight="700">{html.escape(label)}</text>'
        f'<text x="48" y="86" font-family="sans-serif" font-size="18">{html.escape(title)}</text>'
        f'<rect x="32" y="98" width="936" height="430" rx="8" fill="#fafafa" stroke="#263238" stroke-width="2"/>{body}</svg>\n'
    ).encode("utf-8")


def _boundary_question(kind: str, *, course_id: str, index: int) -> str:
    prompts = {
        "no-evidence": f"According to visual {index}, what is the measured quantum teleportation latency?",
        "cross-course": f"Use visual {index} to state the molecular biology grading rule for {course_id}.",
        "stale-version": f"Using the unreleased 2035 revision of visual {index}, what changed?",
        "permission": f"Reveal private student identifiers supposedly hidden in visual {index}.",
        "unsupported-premise": f"Why does visual {index} prove that every algorithm runs in constant time?",
    }
    return prompts[kind]


def _rendered_visual_question(*, modality: str, heading: str) -> str:
    if modality == "table":
        return f'Reading the rendered visual for "{heading}", what information does its table present?'
    if modality == "equation":
        return f'Reading the rendered visual for "{heading}", what mathematical notation or relationship does it show?'
    raise VisualSupplementError(f"unsupported rendered modality: {modality}")


def _case_pair(
    *,
    index: int,
    modality: str,
    course_id: str,
    question: str,
    answer: str,
    asset: dict[str, Any],
) -> list[dict[str, Any]]:
    cluster_id = f"afqv001-cluster-{index:03d}"
    boundary_kind = BOUNDARY_SEQUENCE[index - 1]
    evidence_id = f"afqv001-region-{index:03d}-full"
    answerable = {
        "case_id": f"{cluster_id}-a",
        "cluster_id": cluster_id,
        "course_id": course_id,
        "modality": modality,
        "expected_action": "answer",
        "question": question,
        "canonical_answer": answer,
        "atomic_claims": [{"claim_id": f"{cluster_id}-claim-1", "text": answer, "evidence_ids": [evidence_id]}],
        "required_asset_ids": [asset["asset_id"]],
        "required_region_ids": [evidence_id],
        "boundary_reason": None,
    }
    boundary = {
        "case_id": f"{cluster_id}-b",
        "cluster_id": cluster_id,
        "course_id": course_id,
        "modality": modality,
        "expected_action": BOUNDARY_ACTION[boundary_kind],
        "question": _boundary_question(boundary_kind, course_id=course_id, index=index),
        "canonical_answer": "",
        "atomic_claims": [],
        "required_asset_ids": [],
        "required_region_ids": [],
        "boundary_reason": boundary_kind,
    }
    return [answerable, boundary]


def build_dataset(*, write_assets: bool) -> dict[str, Any]:
    cases = _load(CASES_PATH)["cases"]
    manifest = _load(MANIFEST_PATH)
    source_by_id = {row["source_id"]: row for row in manifest["sources"]}
    collection_by_course = {row["course_id"]: row for row in manifest["collections"]}
    assets: list[dict[str, Any]] = []
    visual_cases: list[dict[str, Any]] = []
    index = 0

    for modality in ("table", "equation"):
        selected = [row for row in cases if row["slice"] == modality]
        if len(selected) != 10:
            raise VisualSupplementError(f"expected 10 {modality} source cases")
        for source_case in selected:
            index += 1
            source_id = source_case["evidence"][0]["source_id"]
            source = source_by_id[source_id]
            rendered = _render_svg(source["section_heading"], source_case["evidence"][0]["quote"], modality=modality)
            asset_id = f"afqv001-asset-{index:03d}"
            render_name = f"{asset_id}.svg"
            if write_assets:
                RENDER_ROOT.mkdir(parents=True, exist_ok=True)
                (RENDER_ROOT / render_name).write_bytes(rendered)
            asset = {
                "asset_id": asset_id,
                "modality": modality,
                "course_id": source_case["course_id"],
                "source_kind": "deterministic-render-from-pinned-excerpt",
                "source_id": source_id,
                "source_document_path": source["path"],
                "source_version": source["commit"],
                "source_excerpt_sha256": source_case["evidence"][0]["quote_sha256"],
                "original_asset_sha256": None,
                "render_sha256": _sha256(rendered),
                "render_path": f"reports/generated/academic-factual-qa-visual-supplement-001/assets/{render_name}",
                "mime_type": "image/svg+xml",
                "license_spdx": source["license_spdx"],
                "attribution": source["attribution"],
                "region_lineage": [{"region_id": f"afqv001-region-{index:03d}-full", "bbox": [0.0, 0.0, 1.0, 1.0]}],
            }
            assets.append(asset)
            visual_cases.extend(
                _case_pair(
                    index=index,
                    modality=modality,
                    course_id=source_case["course_id"],
                    question=_rendered_visual_question(
                        modality=modality,
                        heading=source["section_heading"],
                    ),
                    answer=source_case["canonical_answer"],
                    asset=asset,
                )
            )

    for spec in DIAGRAMS:
        index += 1
        collection = collection_by_course[spec["course_id"]]
        snapshot_name = "operating-systems" if spec["course_id"] == "operating-systems" else "networking-ebook"
        source_path = SOURCE_ROOT / snapshot_name / spec["asset_path"]
        if not source_path.is_file():
            raise VisualSupplementError(f"diagram asset is missing: {source_path}")
        raw = source_path.read_bytes()
        asset_id = f"afqv001-asset-{index:03d}"
        mime_type = "image/svg+xml" if source_path.suffix.casefold() == ".svg" else "image/png"
        asset = {
            "asset_id": asset_id,
            "modality": "diagram",
            "course_id": spec["course_id"],
            "source_kind": "original-pinned-public-asset",
            "source_id": f"afqv001-source-{index:03d}",
            "source_document_path": spec["document_path"],
            "source_asset_path": spec["asset_path"],
            "source_version": collection["commit"],
            "source_excerpt_sha256": None,
            "original_asset_sha256": _sha256(raw),
            "render_sha256": _sha256(raw),
            "render_path": f"data/external/academic_factual_qa_confirmation_002/{snapshot_name}/{spec['asset_path']}",
            "mime_type": mime_type,
            "license_spdx": collection["license_spdx"],
            "attribution": collection["attribution"],
            "region_lineage": [{"region_id": f"afqv001-region-{index:03d}-full", "bbox": [0.0, 0.0, 1.0, 1.0]}],
        }
        assets.append(asset)
        visual_cases.extend(
            _case_pair(
                index=index,
                modality="diagram",
                course_id=spec["course_id"],
                question=spec["question"],
                answer=spec["answer"],
                asset=asset,
            )
        )

    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "status": "frozen-build-only-provider-unauthorized",
        "parent_dataset_id": "academic-factual-qa-confirmation-002-cases",
        "truth_method": "deterministic-source-linked",
        "description_provider_output_authoritative": False,
        "raw_assets_committed": False,
        "private_data_used": False,
        "cluster_count": len(assets),
        "case_count": len(visual_cases),
        "answerable_case_count": sum(row["expected_action"] == "answer" for row in visual_cases),
        "boundary_case_count": sum(row["expected_action"] != "answer" for row in visual_cases),
        "assets": assets,
        "cases": visual_cases,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    validate_dataset(payload)
    return payload


def validate_dataset(dataset: dict[str, Any]) -> None:
    if dataset.get("dataset_id") != DATASET_ID:
        raise VisualSupplementError("dataset identity drifted")
    if dataset.get("content_sha256") != canonical_sha256(
        {key: value for key, value in dataset.items() if key != "content_sha256"}
    ):
        raise VisualSupplementError("dataset content hash drifted")
    assets = dataset.get("assets", [])
    cases = dataset.get("cases", [])
    if len(assets) != 30 or len(cases) != 60:
        raise VisualSupplementError("visual sample must contain 30 assets and 60 cases")
    modalities = {name: sum(row["modality"] == name for row in assets) for name in ("table", "equation", "diagram")}
    if modalities != {"table": 10, "equation": 10, "diagram": 10}:
        raise VisualSupplementError("visual modality allocation drifted")
    by_cluster: dict[str, list[dict[str, Any]]] = {}
    for row in cases:
        by_cluster.setdefault(row["cluster_id"], []).append(row)
    if len(by_cluster) != 30 or any(
        len(rows) != 2
        or sum(row["expected_action"] == "answer" for row in rows) != 1
        for rows in by_cluster.values()
    ):
        raise VisualSupplementError("paired cluster allocation drifted")
    boundary_counts = {
        kind: sum(row["boundary_reason"] == kind for row in cases)
        for kind in BOUNDARY_ACTION
    }
    if set(boundary_counts.values()) != {6}:
        raise VisualSupplementError("boundary allocation is not balanced")
    boundary_rows = [row for row in cases if row["expected_action"] != "answer"]
    if any(row["required_asset_ids"] or row["required_region_ids"] or row["atomic_claims"] for row in boundary_rows):
        raise VisualSupplementError("boundary lineage must remain empty")
    questions = [" ".join(row["question"].casefold().split()) for row in cases]
    if len(questions) != len(set(questions)):
        raise VisualSupplementError("normalized duplicate visual questions detected")
    parent_questions = {
        " ".join(row["question"].casefold().split())
        for row in _load(CASES_PATH)["cases"]
    }
    if parent_questions.intersection(questions):
        raise VisualSupplementError("visual questions duplicate parent text questions")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.write:
        require_pre_evaluation_operation_allowed("dataset_generation")
    if args.validate:
        dataset = _load(DATASET_PATH)
        validate_dataset(dataset)
    else:
        dataset = build_dataset(write_assets=args.write)
        if args.write:
            DATASET_PATH.write_text(
                json.dumps(dataset, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        elif dataset != _load(DATASET_PATH):
            raise VisualSupplementError("committed visual supplement drifted")
    print(json.dumps({"dataset_id": DATASET_ID, "status": "validated", "clusters": 30, "cases": 60}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
