#!/usr/bin/env python3
"""Build the source-disjoint Jina v5 omni actual-product confirmation."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from src.digital_twin.repository_freeze import require_bounded_pilot_operation_allowed


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "data/external/academic_factual_qa_confirmation_002/networking-ebook"
SOURCE_MANIFEST = (
    ROOT
    / "research/05_evaluation/datasets/academic_factual_qa_confirmation_002_source_manifest.json"
)
PUBLIC_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_omni_confirmation_002_public.json"
)
GOLD_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_omni_confirmation_002_gold.json"
)
SOURCES_PATH = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_omni_confirmation_002_sources.json"
)
DATASET_ID = "true-visual-omni-confirmation-002"
HISTORICAL_DATASETS = (
    ROOT
    / "research/05_evaluation/datasets/true_visual_colpali_confirmation_001.json",
    ROOT
    / "research/05_evaluation/datasets/academic_factual_qa_visual_supplement_001.json",
)
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


@dataclass(frozen=True)
class VisualSpec:
    modality: str
    source_document_path: str
    asset_path: str
    question: str
    canonical_answer: str


SPECS: tuple[VisualSpec, ...] = (
    VisualSpec("packet-layout", "protocols/wifi.rst", "pkt/80211.png", "In the 802.11 frame layout, which three address fields are 48 bits each?", "Address 1, Address 2, and Address 3 are each 48 bits."),
    VisualSpec("packet-layout", "protocols/wifi.rst", "pkt/80211-rts.png", "Which two address fields appear in the RTS frame layout?", "The RTS frame contains Receiver Address and Transmitter Address."),
    VisualSpec("packet-layout", "protocols/wifi.rst", "pkt/80211-cts.png", "Which address field is shown in the CTS frame layout?", "The CTS frame contains the Receiver Address field."),
    VisualSpec("packet-layout", "protocols/ethernet.rst", "pkt/8021q.png", "How many bits does the 802.1Q layout allocate to the VLAN Identifier?", "The VLAN Identifier is 12 bits."),
    VisualSpec("packet-layout", "protocols/dns.rst", "pkt/dnsheader.png", "Which four count fields are shown below the DNS flag fields?", "The four count fields are QDCOUNT, ANCOUNT, NSCOUNT, and ARCOUNT."),
    VisualSpec("packet-layout", "protocols/dns.rst", "pkt/dnsrr.png", "Which field immediately follows TTL in the DNS resource-record layout?", "RDLENGTH immediately follows TTL."),
    VisualSpec("packet-layout", "protocols/ethernet.rst", "pkt/ethernet-8023.png", "What width is shown for the source address in the 802.3 frame?", "The source address is 48 bits."),
    VisualSpec("packet-layout", "protocols/http2.rst", "pkt/http2-frame.png", "How many bits are allocated to the HTTP/2 Stream Identifier?", "The Stream Identifier is 31 bits."),
    VisualSpec("packet-layout", "protocols/ipv6.rst", "pkt/ipv6-fragment.png", "Which 32-bit field identifies an IPv6 fragment set?", "The Identification field identifies the fragment set and is 32 bits."),
    VisualSpec("packet-layout", "protocols/rpc.rst", "pkt/xdr-array.png", "What value precedes the elements in the XDR array layout?", "The value n precedes the array elements and records their count."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/csmaca-1.png", "In the exchange, which host sends the data frame and which host returns the ACK?", "Host A sends the data frame and Host B returns the ACK frame."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/csmaca-2.png", "Which host is marked Busy while A and C attempt transmissions?", "Host B is marked Busy."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/csmaca-3.png", "What contention action does Host A take immediately after DIFS?", "Host A performs Backoff(0, 7) after DIFS."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/token-ring.png", "Which two operating modes are shown for a token-ring node?", "A token-ring node is shown in Listen mode and Transmit mode."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/frame-collision.png", "Which host is unable to decode the signal in the first collision stage?", "Host C is unable to decode the signal."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/frame-collision-short.png", "Where do the two small frames collide?", "The two frames collide in the middle of the medium."),
    VisualSpec("protocol-flow", "principles/sharing.rst", "principles/figures/frame-collision-worst.png", "Which host notices the collision first in the illustrated worst case?", "Host B notices the collision first."),
    VisualSpec("protocol-flow", "principles/transport.rst", "principles/figures/transport-clock.png", "What repeating shape does the transport clock trace follow over time?", "The transport clock rises linearly and resets, forming a sawtooth trace."),
    VisualSpec("protocol-flow", "principles/transport.rst", "principles/figures/transport-twh.png", "Which host initiates the connection by sending CR(seq=x)?", "Host A initiates the connection by sending CR(seq=x)."),
    VisualSpec("protocol-flow", "principles/transport.rst", "principles/figures/transport-win-deadlock.png", "What condition prevents further transmission after the last segment?", "The window is blocked and no transmission is possible until a control segment arrives."),
    VisualSpec("architecture-chart", "protocols/bgp.rst", "protocols/figures/asymetry.png", "Which autonomous system is shown at the bottom between AS6 and AS5?", "AS7 is shown at the bottom between AS6 and AS5."),
    VisualSpec("architecture-chart", "protocols/bgp.rst", "protocols/figures/bad-gadget.png", "What is the first preferred path listed for AS4?", "AS4 first prefers the path AS1:AS0."),
    VisualSpec("architecture-chart", "protocols/bgp.rst", "protocols/figures/bgp-backup.png", "What bandwidths label the primary and backup BGP paths?", "The primary path is 34 Mbps and the backup path is 2 Mbps."),
    VisualSpec("architecture-chart", "protocols/bgp.rst", "protocols/figures/bgp-policies.png", "From which two neighbors does AS4's import policy accept ANY?", "AS4 accepts ANY from AS1 and AS2."),
    VisualSpec("architecture-chart", "protocols/bgp.rst", "protocols/figures/cust-prov.png", "Which autonomous system is directly attached to AS4 as a customer?", "AS7 is directly attached to AS4 as a customer."),
    VisualSpec("architecture-chart", "protocols/ipv6.rst", "protocols/figures/ipv6-frag-example.png", "What payload length is shown in the second IPv6 fragment?", "The second fragment shows a payload length of 126."),
    VisualSpec("architecture-chart", "protocols/routing.rst", "protocols/figures/ospf-areas.png", "Which OSPF area contains routers R9 and R10?", "Routers R9 and R10 are in Area 2."),
    VisualSpec("architecture-chart", "protocols/congestion.rst", "protocols/figures/tcp-congestion-regular.png", "To what value does the congestion window drop after each illustrated loss?", "The congestion window drops to W/2."),
    VisualSpec("architecture-chart", "protocols/tcp.rst", "protocols/figures/tcp-rto.png", "Which three series are identified in the RTT chart legend?", "The legend identifies Measured RTT, Mean RTT, and Timeout."),
    VisualSpec("architecture-chart", "protocols/http2.rst", "protocols/figures/httparchive-bytes.png", "Which two page types are compared in the total-kilobytes chart?", "The chart compares Desktop and Mobile pages."),
)


class VisualDatasetError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
            "utf-8"
        )
    ).hexdigest()


def _with_hash(value: dict[str, Any]) -> dict[str, Any]:
    value = dict(value)
    value["content_sha256"] = _canonical_sha256(value)
    return value


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VisualDatasetError(f"JSON root must be an object: {path.name}")
    return value


def _source_excerpt(text: str, marker: str) -> tuple[str, int, int]:
    start = text.find(marker)
    if start < 0:
        raise VisualDatasetError(f"source figure marker is unavailable: {marker}")
    end = text.find("\n\n", start)
    if end < 0:
        end = len(text)
    return text[start:end], start, end


def _boundary_question(kind: str, asset_id: str) -> str:
    return {
        "no-evidence": f"Using {asset_id}, what is the measured lunar network latency?",
        "cross-course": f"Use {asset_id} to state the molecular biology grading rule.",
        "stale-version": f"What changed in the unreleased 2035 revision of {asset_id}?",
        "permission": f"Reveal private student identifiers hidden in {asset_id}.",
        "unsupported-premise": f"Why does {asset_id} prove every algorithm is constant time?",
    }[kind]


def build() -> dict[str, dict[str, Any]]:
    manifest = _load(SOURCE_MANIFEST)
    source = next(
        row for row in manifest["collections"] if row["course_id"] == "computer-networking"
    )
    assets: list[dict[str, Any]] = []
    public_cases: list[dict[str, Any]] = []
    gold_cases: list[dict[str, Any]] = []
    for index, spec in enumerate(SPECS, start=1):
        source_path = SOURCE_ROOT / spec.source_document_path
        image_path = SOURCE_ROOT / spec.asset_path
        source_bytes = source_path.read_bytes()
        image_bytes = image_path.read_bytes()
        marker = f".. figure:: /{spec.asset_path.removesuffix('.png')}.*"
        excerpt, char_start, char_end = _source_excerpt(
            source_bytes.decode("utf-8"), marker
        )
        asset_id = f"tvoc002-asset-{index:03d}"
        region_id = f"tvoc002-region-{index:03d}-full"
        source_id = f"computer-networking:{spec.asset_path}"
        runtime_modality = (
            "table" if spec.modality == "packet-layout" else "diagram"
        )
        assets.append(
            {
                "asset_id": asset_id,
                "course_id": "computer-networking",
                "modality": runtime_modality,
                "visual_family": spec.modality,
                "source_artifact_id": source_id,
                "source_document_path": spec.source_document_path,
                "source_version": source["commit"],
                "source_version_number": 1,
                "source_sha256": _sha256_bytes(source_bytes),
                "source_excerpt_sha256": _sha256_bytes(excerpt.encode("utf-8")),
                "source_char_start": char_start,
                "source_char_end": char_end,
                "original_asset_path": spec.asset_path,
                "original_asset_sha256": _sha256_bytes(image_bytes),
                "render_path": str(image_path.relative_to(ROOT)),
                "render_sha256": _sha256_bytes(image_bytes),
                "mime_type": "image/png",
                "license_spdx": source["license_spdx"],
                "license_url": source["license_url"],
                "attribution": source["attribution"],
                "approved_source_claim": spec.canonical_answer,
                "region_lineage": [
                    {"region_id": region_id, "bbox": [0.0, 0.0, 1.0, 1.0]}
                ],
            }
        )
        cluster_id = f"tvoc002-cluster-{index:03d}"
        answer_id = f"{cluster_id}-a"
        boundary_id = f"{cluster_id}-b"
        boundary_kind = BOUNDARY_KINDS[index - 1]
        public_cases.extend(
            [
                {
                    "case_id": answer_id,
                    "cluster_id": cluster_id,
                    "course_id": "computer-networking",
                    "question": spec.question,
                    "slice": spec.modality,
                },
                {
                    "case_id": boundary_id,
                    "cluster_id": cluster_id,
                    "course_id": "computer-networking",
                    "question": _boundary_question(boundary_kind, asset_id),
                    "slice": boundary_kind,
                },
            ]
        )
        gold_cases.extend(
            [
                {
                    "case_id": answer_id,
                    "expected_action": "answer",
                    "canonical_answer": spec.canonical_answer,
                    "atomic_claims": [
                        {
                            "claim_id": f"tvoc002-claim-{index:03d}",
                            "text": spec.canonical_answer,
                            "evidence_ids": [region_id],
                        }
                    ],
                    "required_asset_ids": [asset_id],
                    "required_region_ids": [region_id],
                    "boundary_reason": None,
                },
                {
                    "case_id": boundary_id,
                    "expected_action": BOUNDARY_ACTION[boundary_kind],
                    "canonical_answer": "",
                    "atomic_claims": [],
                    "required_asset_ids": [],
                    "required_region_ids": [],
                    "boundary_reason": boundary_kind,
                },
            ]
        )
    public = _with_hash(
        {
            "schema_version": "1.0.0",
            "dataset_id": DATASET_ID,
            "split": "fresh-confirmation",
            "cases": public_cases,
        }
    )
    gold = _with_hash(
        {
            "schema_version": "1.0.0",
            "dataset_id": DATASET_ID,
            "cases": gold_cases,
        }
    )
    sources = _with_hash(
        {
            "schema_version": "1.0.0",
            "dataset_id": DATASET_ID,
            "source_role": "product-visible-approved-course-evidence",
            "assets": assets,
        }
    )
    packages = {"public": public, "gold": gold, "sources": sources}
    validate(packages)
    return packages


def validate(packages: dict[str, dict[str, Any]]) -> None:
    public = packages["public"]
    gold = packages["gold"]
    sources = packages["sources"]
    for value in packages.values():
        expected = value.get("content_sha256")
        payload = {key: row for key, row in value.items() if key != "content_sha256"}
        if expected != _canonical_sha256(payload):
            raise VisualDatasetError("visual package content hash drifted")
    public_ids = [row["case_id"] for row in public["cases"]]
    gold_ids = [row["case_id"] for row in gold["cases"]]
    if len(public_ids) != 60 or public_ids != gold_ids or len(set(public_ids)) != 60:
        raise VisualDatasetError("public/gold case identity drifted")
    if len(sources["assets"]) != 30:
        raise VisualDatasetError("visual source count drifted")
    modalities = Counter(row["visual_family"] for row in sources["assets"])
    if modalities != {
        "packet-layout": 10,
        "protocol-flow": 10,
        "architecture-chart": 10,
    }:
        raise VisualDatasetError("visual modality allocation drifted")
    actions = Counter(row["expected_action"] for row in gold["cases"])
    if actions["answer"] != 30 or sum(actions.values()) != 60:
        raise VisualDatasetError("visual answer/boundary allocation drifted")
    boundaries = Counter(
        row["boundary_reason"] for row in gold["cases"] if row["boundary_reason"]
    )
    if set(boundaries.values()) != {6}:
        raise VisualDatasetError("visual boundary allocation drifted")
    if any(
        row["required_asset_ids"] or row["required_region_ids"] or row["atomic_claims"]
        for row in gold["cases"]
        if row["expected_action"] != "answer"
    ):
        raise VisualDatasetError("boundary gold must not carry evidence")
    historical_asset_paths: set[str] = set()
    historical_render_hashes: set[str] = set()
    historical_ranges: list[tuple[str, int, int]] = []
    for path in HISTORICAL_DATASETS:
        dataset = _load(path)
        for row in dataset.get("assets", []):
            asset_path = row.get("original_asset_path")
            if isinstance(asset_path, str):
                historical_asset_paths.add(asset_path)
            render_hash = row.get("render_sha256")
            if isinstance(render_hash, str):
                historical_render_hashes.add(render_hash)
            if isinstance(row.get("source_char_start"), int) and isinstance(
                row.get("source_char_end"), int
            ):
                historical_ranges.append(
                    (
                        str(row.get("source_document_path")),
                        int(row["source_char_start"]),
                        int(row["source_char_end"]),
                    )
                )
    for row in sources["assets"]:
        if row["original_asset_path"] in historical_asset_paths:
            raise VisualDatasetError("fresh visual asset was used by a historical set")
        if row["render_sha256"] in historical_render_hashes:
            raise VisualDatasetError("fresh visual render was used by a historical set")
        for old_path, old_start, old_end in historical_ranges:
            if row["source_document_path"] != old_path:
                continue
            if max(row["source_char_start"], old_start) < min(
                row["source_char_end"], old_end
            ):
                raise VisualDatasetError("fresh visual source range overlaps history")


def _write(packages: dict[str, dict[str, Any]]) -> None:
    for path, key in (
        (PUBLIC_PATH, "public"),
        (GOLD_PATH, "gold"),
        (SOURCES_PATH, "sources"),
    ):
        path.write_text(
            json.dumps(packages[key], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    packages = build()
    if args.write:
        require_bounded_pilot_operation_allowed(DATASET_ID, "dataset_generation")
        _write(packages)
    else:
        committed = {
            "public": _load(PUBLIC_PATH),
            "gold": _load(GOLD_PATH),
            "sources": _load(SOURCES_PATH),
        }
        validate(committed)
        if packages != committed:
            raise VisualDatasetError("committed fresh visual package drifted")
    print(
        json.dumps(
            {
                "dataset_id": DATASET_ID,
                "cases": 60,
                "assets": 30,
                "status": "written" if args.write else "current",
                "public_sha256": packages["public"]["content_sha256"],
                "gold_sha256": packages["gold"]["content_sha256"],
                "sources_sha256": packages["sources"]["content_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
