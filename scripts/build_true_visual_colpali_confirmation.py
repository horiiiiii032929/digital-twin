#!/usr/bin/env python3
"""Build the fresh region-authoritative ColPali-style visual confirmation.

The package is intentionally independent from visual supplement 001/003.  It
contains ten tables, ten equations, and ten diagrams from pinned public source
snapshots.  Each visual has one answerable and one boundary case.  Gold refers
to original source artifacts and normalized image regions, never provider text
or runtime chunk identifiers.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
from typing import Any

from scripts.build_academic_factual_qa_confirmation_v2 import canonical_sha256
from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "data/external/academic_factual_qa_confirmation_002"
MANIFEST_PATH = (
    ROOT
    / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_source_manifest.json"
)
DATASET_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_colpali_confirmation_001.json"
)
RENDER_ROOT = ROOT / "reports/generated/true-visual-colpali-confirmation-001/assets"
DATASET_ID = "true-visual-colpali-confirmation-001"

BOUNDARY_KINDS = (
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


class VisualConfirmationBuildError(ValueError):
    """Raised when a source, render, or immutable contract drifts."""


@dataclass(frozen=True)
class RenderedSpec:
    course_id: str
    snapshot: str
    source_path: str
    title: str
    rows: tuple[tuple[str, ...], ...]
    question: str
    canonical_answer: str
    start_marker: str
    end_marker: str


@dataclass(frozen=True)
class EquationSpec:
    source_path: str
    title: str
    display: str
    question: str
    canonical_answer: str
    start_marker: str
    end_marker: str


@dataclass(frozen=True)
class DiagramSpec:
    source_path: str
    asset_path: str
    title: str
    question: str
    canonical_answer: str
    start_marker: str
    end_marker: str


TABLES: tuple[RenderedSpec, ...] = (
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/software-stack/operating-system/slides/operating-system.md",
        "User mode and kernel mode",
        (("Mode", "Privilege", "Typical code"), ("User", "unprivileged", "applications / processes"), ("Kernel", "privileged", "kernel, drivers")),
        "In the table, which mode is privileged and what code typically runs there?",
        "Kernel mode is privileged and typically runs kernel code and drivers.",
        "| User Mode",
        "| flexible, diverse",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/software-stack/operating-system/slides/operating-system.md",
        "Library calls and system calls",
        (("Call type", "Provider", "Invocation"), ("Library", "libraries", "typical function call"), ("System", "operating system", "typically causes mode switch")),
        "Which call type typically causes a mode switch?",
        "A system call typically causes a mode switch.",
        "| Library calls",
        "| generally portable",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/software-stack/overview/slides/software-stack.md",
        "Hardware and software",
        (("Hardware", "Software"), ("efficient", "featureful"), ("unmodifiable", "configurable"), ("physical", "virtual, easy to duplicate")),
        "According to the table, which side is configurable?",
        "Software is configurable, while hardware is unmodifiable.",
        "| Hardware",
        "| monolithic",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/software-stack/software-types/slides/types-of-software.md",
        "Applications and libraries",
        (("Applications", "Libraries"), ("entry point", "exposed interface (API)"), ("usable", "reusable"), ("load-time", "link-time and load-time")),
        "What interface characteristic distinguishes a library from an application?",
        "A library exposes an interface or API, while an application has an entry point.",
        "| Applications",
        "| used by system and user",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/io/lab/content/file-descriptors.md",
        "libc and syscall file operations",
        (("libc", "syscall"), ("fopen()", "open()"), ("fread()", "read()"), ("fwrite()", "write()"), ("fseek()", "lseek()"), ("fclose()", "close()")),
        "Which system call corresponds to fread()?",
        "The read() system call corresponds to fread().",
        "|    libc",
        "| `fclose()`",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/io/lab/content/file-descriptors.md",
        "fopen modes and open flags",
        (("fopen() mode", "open() flag"), ("r", "O_RDONLY"), ("w", "O_WRONLY | O_CREAT | O_TRUNC"), ("a", "O_WRONLY | O_CREAT | O_APPEND"), ("r+", "O_RDWR"), ("w+", "O_RDWR | O_CREAT | O_TRUNC"), ("a+", "O_RDWR | O_CREAT | O_APPEND")),
        "Which open() flags correspond to fopen() mode a+?",
        "Mode a+ corresponds to O_RDWR, O_CREAT, and O_APPEND.",
        "| `fopen()` mode",
        "|     `\"a+\"`",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/compute/lecture/slides/scheduling-algorithms.md",
        "Process running times",
        (("Process", "Running time"), ("P1", "4"), ("P2", "3"), ("P3", "5")),
        "What running time is listed for process P3?",
        "Process P3 has a running time of 5.",
        "| Process | Running time |",
        "| P3      | 5",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/compute/lab/content/threads.md",
        "Processes and threads",
        (("Process", "Thread"), ("independent", "part of a process"), ("isolated VAS", "shares VAS with other threads"), ("slower creation", "faster creation")),
        "Which execution unit shares a virtual address space with peers?",
        "A thread shares the virtual address space with other threads.",
        "| PROCESS",
        "| ending means ending all threads",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/app-interact/lab/content/os-cloud.md",
        "Virtual machine record",
        (("id", "name", "mem_size", "state"), ("1", "my_vm", "2147483648", "0")),
        "What memory size is recorded for my_vm?",
        "The recorded memory size for my_vm is 2147483648 bytes.",
        "| id | name  | disk_id",
        "|  1 | my_vm",
    ),
    RenderedSpec(
        "operating-systems",
        "operating-systems",
        "content/app-interact/lab/content/os-cloud.md",
        "Virtual disk record",
        (("id", "size", "template_name"), ("1", "10737418240", "ubuntu_22.04")),
        "Which template and size are listed for disk 1?",
        "Disk 1 uses template ubuntu_22.04 and has size 10737418240 bytes.",
        "| id | size        | template_name |",
        "|  1 | 10737418240 | ubuntu_22.04",
    ),
)

EQUATIONS: tuple[EquationSpec, ...] = (
    EquationSpec("latex/rebuilding.tex", "ScapegoatTree size invariant", "n <= q <= 2n", "What bounds relate n and q in the displayed invariant?", "The invariant is n <= q <= 2n.", "\\[  #n# \\le #q# \\le 2#n#", "\\enspace . \\]"),
    EquationSpec("latex/rebuilding.tex", "ScapegoatTree height invariant", "height <= log_(3/2)(q)", "What upper bound on height is shown?", "Height is at most log base 3/2 of q.", "\\mbox{height} \\le", "\\log_{3/2} q"),
    EquationSpec("latex/intro.tex", "Euler's constant", "e = lim n->infinity (1 + 1/n)^n", "How is Euler's constant defined in the display?", "e is the limit as n approaches infinity of (1 + 1/n)^n.", "e = \\lim_{n\\rightarrow\\infty}", "\\approx  2.71828"),
    EquationSpec("latex/intro.tex", "Removing a logarithm from an exponent", "b^(log_b k) = k", "What identity removes the logarithm from the exponent?", "The identity is b raised to log base b of k equals k.", "b^{\\log_b k} = k", "b^{\\log_b k} = k"),
    EquationSpec("latex/intro.tex", "Changing logarithm base", "log_b(k) = log_a(k) / log_a(b)", "What change-of-base identity is displayed?", "log base b of k equals log base a of k divided by log base a of b.", "\\log_b k = \\frac{\\log_a k}{\\log_a b}", "\\enspace ."),
    EquationSpec("latex/intro.tex", "Binomial coefficient", "C(n,k) = n! / (k!(n-k)!)", "How is n choose k expressed using factorials?", "n choose k equals n factorial divided by k factorial times (n-k) factorial.", "\\binom{n}{k} = \\frac{n!}{k!(n-k)!}", "\\enspace ."),
    EquationSpec("latex/rbs.tex", "Harmonic number", "H_k = 1 + 1/2 + ... + 1/k", "How is the kth harmonic number defined?", "H_k is 1 + 1/2 + 1/3 + ... + 1/k.", "H_k = 1 + 1/2", "1/k \\enspace ."),
    EquationSpec("latex/heaps.tex", "BinaryHeap child indices", "left(i)=2i+1; right(i)=2i+2", "What are the array indices of a node's left and right children?", "The left child is at 2i+1 and the right child is at 2i+2.", "#left(i)#=2#i#+1", "#right(i)#=2#i#+2"),
    EquationSpec("latex/redblack.tex", "2-4 tree leaf lower bound", "n >= 2^h", "What lower bound connects the number of leaves n and height h?", "A 2-4 tree of height h has at least 2^h leaves, so n >= 2^h.", "#n# \\ge 2^h", "#n# \\ge 2^h"),
    EquationSpec("latex/scapegoat.tex", "Scapegoat imbalance", "size(w.child) / size(w) > 2/3", "Which ratio identifies the scapegoat node?", "The ratio size(w.child) / size(w) is greater than 2/3.", "\\frac{#size(w.child)#}{#size(w)#}", "\\frac{2}{3}"),
)

DIAGRAMS: tuple[DiagramSpec, ...] = (
    DiagramSpec("principles/sharing.rst", "principles/figures/fullmesh.png", "Full-mesh network", "How many hosts are shown in the full-mesh diagram?", "The full-mesh diagram shows five hosts.", "Consider for example a network with five hosts.", "A first organization for this LAN is the full-mesh."),
    DiagramSpec("principles/sharing.rst", "principles/figures/star.png", "Star topology", "Where does each host's physical link terminate in the star diagram?", "Each host has one physical link to the center of the star.", "A third organization of a computer network is a star topology.", "one physical link between each host and the center of the star."),
    DiagramSpec("principles/sharing.rst", "principles/figures/ring.png", "Ring topology", "How are the hosts arranged in this topology?", "The hosts are attached to a ring.", "A fourth physical organization of a network is the ring topology.", "each host has a single physical interface connecting it to the ring."),
    DiagramSpec("principles/sharing.rst", "principles/figures/tree.png", "Tree topology", "Which host is the parent of H4 and H5 in the diagram?", "H3 is the parent of H4 and H5.", "\\node [host] {H1}", "child { node [host] {H5} }"),
    DiagramSpec("principles/referencemodels.rst", "principles/figures/ref-model-osi.png", "OSI reference model", "How many layers are shown in the OSI reference model?", "The OSI reference model has seven layers.", "The OSI reference model", "is divided in seven layers."),
    DiagramSpec("protocols/udp.rst", "protocols/figures/udp-ports.png", "UDP port usage", "For the client request, what are the source and destination ports?", "The request uses source port 1234 and destination port 5678.", "The figure below shows a typical usage of the UDP port numbers.", "destined to port number `5678` on the server host."),
    DiagramSpec("principles/sharing.rst", "principles/figures/csmaca-hidden.png", "Hidden station problem", "What communication limitation is depicted between the two separated devices?", "The two devices cannot receive each other's signal even though both can receive the third host.", "Another problem faced by wireless networks is often called the `hidden station problem`.", "both be receiving the signal produced by a third host."),
    DiagramSpec("principles/transport.rst", "principles/figures/transport-dwin.png", "Dynamic receiving window", "Which two window sizes bound the number of unacknowledged segments?", "The bound is the minimum of swin and rwin.", "the sender maintains two state variables", "\\min(swin,rwin)"),
    DiagramSpec("protocols/bgp.rst", "protocols/figures/bgp-peering.png", "BGP peering", "What relationship is shown between R1 and R2?", "R1 and R2 are directly connected BGP peers.", "BGP routers exchange routes over BGP sessions.", "The two endpoints of a BGP session are called `BGP peers`."),
    DiagramSpec("protocols/bgp.rst", "protocols/figures/bgp-nexthop.png", "BGP nexthop", "Which routers have BGP sessions with R2 in the diagram?", "R2 has BGP sessions with R1 and R3.", "This network contains three routers : `R1`, `R2` and `R3`.", "the second between `R2` and `R3`."),
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VisualConfirmationBuildError(f"JSON root must be an object: {path.name}")
    return value


def _source_span(path: Path, start_marker: str, end_marker: str) -> tuple[str, int, int]:
    text = path.read_text(encoding="utf-8")
    start = text.find(start_marker)
    if start < 0:
        raise VisualConfirmationBuildError(f"start marker drifted in {path.name}: {start_marker!r}")
    end_start = text.find(end_marker, start)
    if end_start < 0:
        raise VisualConfirmationBuildError(f"end marker drifted in {path.name}: {end_marker!r}")
    end = end_start + len(end_marker)
    return text[start:end], start, end


def _render_table_svg(spec: RenderedSpec) -> bytes:
    columns = len(spec.rows[0])
    if columns < 2 or any(len(row) != columns for row in spec.rows):
        raise VisualConfirmationBuildError("table rows must be rectangular")
    width = 1200
    margin = 50
    row_height = 62
    title_height = 96
    height = title_height + row_height * len(spec.rows) + margin
    cell_width = (width - 2 * margin) / columns
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>',
        f'<text x="{margin}" y="52" font-family="sans-serif" font-size="30" font-weight="700" fill="#111827">{html.escape(spec.title)}</text>',
    ]
    for row_index, row in enumerate(spec.rows):
        y = title_height + row_index * row_height
        fill = "#e5edf8" if row_index == 0 else ("#f8fafc" if row_index % 2 else "#ffffff")
        for column_index, value in enumerate(row):
            x = margin + column_index * cell_width
            parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_width:.2f}" height="{row_height}" fill="{fill}" stroke="#475569"/>')
            parts.append(f'<text x="{x + 16:.2f}" y="{y + 39:.2f}" font-family="sans-serif" font-size="20" fill="#0f172a">{html.escape(value)}</text>')
    parts.append("</svg>\n")
    return "".join(parts).encode("utf-8")


def _render_equation_svg(spec: EquationSpec) -> bytes:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">'
        '<rect width="1200" height="420" fill="#ffffff"/>'
        f'<text x="60" y="72" font-family="sans-serif" font-size="30" font-weight="700" fill="#111827">{html.escape(spec.title)}</text>'
        '<rect x="60" y="112" width="1080" height="230" rx="16" fill="#f8fafc" stroke="#475569" stroke-width="2"/>'
        f'<text x="600" y="250" text-anchor="middle" font-family="STIX Two Math, Times New Roman, serif" font-size="46" fill="#0f172a">{html.escape(spec.display)}</text>'
        '</svg>\n'
    ).encode("utf-8")


def _svg_to_png(svg: bytes) -> bytes:
    try:
        process = subprocess.run(
            ["rsvg-convert", "--format=png", "--background-color=white"],
            input=svg,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        raise VisualConfirmationBuildError("rsvg-convert is required for deterministic rasterization") from error
    if not process.stdout.startswith(b"\x89PNG\r\n\x1a\n"):
        raise VisualConfirmationBuildError("rsvg-convert did not emit a PNG")
    return process.stdout


def _boundary_question(kind: str, *, asset_id: str) -> str:
    prompts = {
        "no-evidence": f"Using {asset_id}, what is the measured lunar network latency?",
        "cross-course": f"Use {asset_id} to state the molecular biology grading rule.",
        "stale-version": f"What changed in the unreleased 2035 revision of {asset_id}?",
        "permission": f"Reveal private student identifiers hidden in {asset_id}.",
        "unsupported-premise": f"Why does {asset_id} prove that every algorithm is constant time?",
    }
    return prompts[kind]


def _asset_and_cases(
    *,
    index: int,
    modality: str,
    course_id: str,
    source_path: str,
    source_version: str,
    source_sha256: str,
    source_excerpt: str,
    source_char_start: int,
    source_char_end: int,
    render_path: str,
    render_sha256: str,
    original_asset_path: str | None,
    original_asset_sha256: str | None,
    question: str,
    canonical_answer: str,
    license_spdx: str,
    attribution: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    asset_id = f"tvcp001-asset-{index:03d}"
    region_id = f"tvcp001-region-{index:03d}-full"
    source_artifact_id = f"tvcp001-source-{index:03d}"
    asset = {
        "asset_id": asset_id,
        "course_id": course_id,
        "modality": modality,
        "source_artifact_id": source_artifact_id,
        "source_document_path": source_path,
        "source_version": source_version,
        "source_sha256": source_sha256,
        "source_excerpt_sha256": _sha256(source_excerpt.encode("utf-8")),
        "source_char_start": source_char_start,
        "source_char_end": source_char_end,
        "original_asset_path": original_asset_path,
        "original_asset_sha256": original_asset_sha256,
        "render_path": render_path,
        "render_sha256": render_sha256,
        "mime_type": "image/png",
        "license_spdx": license_spdx,
        "attribution": attribution,
        "region_lineage": [{"region_id": region_id, "bbox": [0.0, 0.0, 1.0, 1.0]}],
    }
    cluster_id = f"tvcp001-cluster-{index:03d}"
    boundary_kind = BOUNDARY_KINDS[index - 1]
    claim_id = f"tvcp001-claim-{index:03d}-1"
    cases = [
        {
            "case_id": f"{cluster_id}-a",
            "cluster_id": cluster_id,
            "course_id": course_id,
            "modality": modality,
            "expected_action": "answer",
            "question": question,
            "canonical_answer": canonical_answer,
            "atomic_claims": [{"claim_id": claim_id, "text": canonical_answer, "evidence_ids": [region_id]}],
            "required_asset_ids": [asset_id],
            "required_region_ids": [region_id],
            "boundary_reason": None,
        },
        {
            "case_id": f"{cluster_id}-b",
            "cluster_id": cluster_id,
            "course_id": course_id,
            "modality": modality,
            "expected_action": BOUNDARY_ACTION[boundary_kind],
            "question": _boundary_question(boundary_kind, asset_id=asset_id),
            "canonical_answer": "",
            "atomic_claims": [],
            "required_asset_ids": [],
            "required_region_ids": [],
            "boundary_reason": boundary_kind,
        },
    ]
    return asset, cases


def build_dataset(*, write_assets: bool) -> dict[str, Any]:
    manifest = _load(MANIFEST_PATH)
    collections = {row["course_id"]: row for row in manifest["collections"]}
    assets: list[dict[str, Any]] = []
    cases: list[dict[str, Any]] = []
    index = 0

    for spec in TABLES:
        index += 1
        path = SOURCE_ROOT / spec.snapshot / spec.source_path
        raw = path.read_bytes()
        excerpt, start, end = _source_span(path, spec.start_marker, spec.end_marker)
        png = _svg_to_png(_render_table_svg(spec))
        render_name = f"tvcp001-asset-{index:03d}.png"
        if write_assets:
            RENDER_ROOT.mkdir(parents=True, exist_ok=True)
            (RENDER_ROOT / render_name).write_bytes(png)
        collection = collections[spec.course_id]
        asset, pair = _asset_and_cases(
            index=index,
            modality="table",
            course_id=spec.course_id,
            source_path=spec.source_path,
            source_version=collection["commit"],
            source_sha256=_sha256(raw),
            source_excerpt=excerpt,
            source_char_start=start,
            source_char_end=end,
            render_path=f"reports/generated/true-visual-colpali-confirmation-001/assets/{render_name}",
            render_sha256=_sha256(png),
            original_asset_path=None,
            original_asset_sha256=None,
            question=spec.question,
            canonical_answer=spec.canonical_answer,
            license_spdx=collection["license_spdx"],
            attribution=collection["attribution"],
        )
        assets.append(asset)
        cases.extend(pair)

    collection = collections["data-structures"]
    for spec in EQUATIONS:
        index += 1
        path = SOURCE_ROOT / "open-data-structures" / spec.source_path
        raw = path.read_bytes()
        excerpt, start, end = _source_span(path, spec.start_marker, spec.end_marker)
        png = _svg_to_png(_render_equation_svg(spec))
        render_name = f"tvcp001-asset-{index:03d}.png"
        if write_assets:
            RENDER_ROOT.mkdir(parents=True, exist_ok=True)
            (RENDER_ROOT / render_name).write_bytes(png)
        asset, pair = _asset_and_cases(
            index=index,
            modality="equation",
            course_id="data-structures",
            source_path=spec.source_path,
            source_version=collection["commit"],
            source_sha256=_sha256(raw),
            source_excerpt=excerpt,
            source_char_start=start,
            source_char_end=end,
            render_path=f"reports/generated/true-visual-colpali-confirmation-001/assets/{render_name}",
            render_sha256=_sha256(png),
            original_asset_path=None,
            original_asset_sha256=None,
            question=spec.question,
            canonical_answer=spec.canonical_answer,
            license_spdx=collection["license_spdx"],
            attribution=collection["attribution"],
        )
        assets.append(asset)
        cases.extend(pair)

    collection = collections["computer-networking"]
    for spec in DIAGRAMS:
        index += 1
        document_path = SOURCE_ROOT / "networking-ebook" / spec.source_path
        asset_path = SOURCE_ROOT / "networking-ebook" / spec.asset_path
        source_raw = document_path.read_bytes()
        image_raw = asset_path.read_bytes()
        excerpt, start, end = _source_span(document_path, spec.start_marker, spec.end_marker)
        asset, pair = _asset_and_cases(
            index=index,
            modality="diagram",
            course_id="computer-networking",
            source_path=spec.source_path,
            source_version=collection["commit"],
            source_sha256=_sha256(source_raw),
            source_excerpt=excerpt,
            source_char_start=start,
            source_char_end=end,
            render_path=f"data/external/academic_factual_qa_confirmation_002/networking-ebook/{spec.asset_path}",
            render_sha256=_sha256(image_raw),
            original_asset_path=spec.asset_path,
            original_asset_sha256=_sha256(image_raw),
            question=spec.question,
            canonical_answer=spec.canonical_answer,
            license_spdx=collection["license_spdx"],
            attribution=collection["attribution"],
        )
        assets.append(asset)
        cases.extend(pair)

    payload: dict[str, Any] = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "status": "frozen-build-only-provider-unauthorized",
        "supersedes_method_result": "true-visual-supplement-003",
        "method_family": "colpali-style-multivector-late-interaction",
        "truth_method": "deterministic-original-region-lineage",
        "source_section_disjoint_from_visual_supplement_001": True,
        "provider_embeddings_authoritative": False,
        "raw_assets_committed": False,
        "private_data_used": False,
        "cluster_count": len(assets),
        "case_count": len(cases),
        "answerable_case_count": sum(row["expected_action"] == "answer" for row in cases),
        "boundary_case_count": sum(row["expected_action"] != "answer" for row in cases),
        "assets": assets,
        "cases": cases,
    }
    payload["content_sha256"] = canonical_sha256(payload)
    validate_dataset(payload)
    return payload


def validate_dataset(dataset: dict[str, Any]) -> None:
    if dataset.get("dataset_id") != DATASET_ID:
        raise VisualConfirmationBuildError("dataset identity drifted")
    expected_hash = canonical_sha256({key: value for key, value in dataset.items() if key != "content_sha256"})
    if dataset.get("content_sha256") != expected_hash:
        raise VisualConfirmationBuildError("dataset content hash drifted")
    assets = dataset.get("assets")
    cases = dataset.get("cases")
    if not isinstance(assets, list) or not isinstance(cases, list) or len(assets) != 30 or len(cases) != 60:
        raise VisualConfirmationBuildError("dataset must contain 30 assets and 60 cases")
    modalities = {name: sum(row.get("modality") == name for row in assets) for name in ("table", "equation", "diagram")}
    if modalities != {"table": 10, "equation": 10, "diagram": 10}:
        raise VisualConfirmationBuildError("modality allocation drifted")
    asset_ids = [row["asset_id"] for row in assets]
    if len(asset_ids) != len(set(asset_ids)):
        raise VisualConfirmationBuildError("asset IDs must be unique")
    by_cluster: dict[str, list[dict[str, Any]]] = {}
    for case in cases:
        by_cluster.setdefault(case["cluster_id"], []).append(case)
    if len(by_cluster) != 30 or any(len(rows) != 2 or sum(row["expected_action"] == "answer" for row in rows) != 1 for rows in by_cluster.values()):
        raise VisualConfirmationBuildError("case pairing drifted")
    boundary_counts = {kind: sum(row.get("boundary_reason") == kind for row in cases) for kind in BOUNDARY_ACTION}
    if set(boundary_counts.values()) != {6}:
        raise VisualConfirmationBuildError("boundary allocation must be balanced")
    boundary_rows = [row for row in cases if row["expected_action"] != "answer"]
    if any(row["required_asset_ids"] or row["required_region_ids"] or row["atomic_claims"] for row in boundary_rows):
        raise VisualConfirmationBuildError("boundary cases must have empty evidence lineage")
    normalized_questions = [re.sub(r"\s+", " ", row["question"].casefold()).strip() for row in cases]
    if len(normalized_questions) != len(set(normalized_questions)):
        raise VisualConfirmationBuildError("visual questions must be unique")
    old = _load(ROOT / "research/05_evaluation/datasets/academic_factual_qa_visual_supplement_001.json")
    old_documents = {row["source_document_path"] for row in old["assets"]}
    new_ranges = {(row["source_document_path"], row["source_char_start"], row["source_char_end"]) for row in assets}
    if len(new_ranges) != 30:
        raise VisualConfirmationBuildError("source sections must be unique")
    for row in assets:
        if row["source_document_path"] in old_documents:
            old_same = [item for item in old["assets"] if item["source_document_path"] == row["source_document_path"]]
            for item in old_same:
                old_start = item.get("source_char_start")
                old_end = item.get("source_char_end")
                if isinstance(old_start, int) and isinstance(old_end, int):
                    overlaps = max(old_start, row["source_char_start"]) < min(
                        old_end, row["source_char_end"]
                    )
                    if overlaps:
                        raise VisualConfirmationBuildError(
                            "fresh visual source range overlaps supplement 001"
                        )
                elif item.get("source_excerpt_sha256") == row["source_excerpt_sha256"]:
                    raise VisualConfirmationBuildError(
                        "fresh visual source section overlaps supplement 001"
                    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    if args.write:
        require_bounded_pilot_operation_allowed(DATASET_ID, "dataset_generation")
    if args.validate:
        validate_dataset(_load(DATASET_PATH))
        dataset = _load(DATASET_PATH)
    else:
        dataset = build_dataset(write_assets=args.write)
        if args.write:
            DATASET_PATH.write_text(json.dumps(dataset, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        elif dataset != _load(DATASET_PATH):
            raise VisualConfirmationBuildError("committed visual confirmation drifted")
    print(json.dumps({"dataset_id": DATASET_ID, "clusters": 30, "cases": 60, "status": "validated"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
