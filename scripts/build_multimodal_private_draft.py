#!/usr/bin/env python3
"""Build the ignored private multimodal benchmark from a reviewed page sample."""

from __future__ import annotations

import argparse
import html
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.validate_multimodal_retrieval_dataset import validate_dataset


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_QUEUE = (
    ROOT
    / "data/interim/multimodal_retrieval_v1/pdf_samples_v1/sample_queue_v1.json"
)
DEFAULT_AUTHORING = (
    ROOT / "data/interim/multimodal_retrieval_v1/case_authoring_v1.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "data/processed/multimodal_retrieval_v1/"
    "multimodal_retrieval_v1_draft.json"
)
DEFAULT_REVIEW = (
    ROOT / "data/processed/multimodal_retrieval_v1/researcher_review_v1.md"
)
DEFAULT_REVIEW_HTML = (
    ROOT / "data/processed/multimodal_retrieval_v1/researcher_review_v1.html"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-queue", type=Path, default=DEFAULT_SAMPLE_QUEUE)
    parser.add_argument("--authoring", type=Path, default=DEFAULT_AUTHORING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--review-output", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--review-html", type=Path, default=DEFAULT_REVIEW_HTML)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_dataset(
    sample_queue: dict[str, Any], authoring: dict[str, Any]
) -> dict[str, Any]:
    samples = {record["candidate_id"]: record for record in sample_queue["records"]}
    used_candidates = {case["candidate_id"] for case in authoring["cases"]}
    unknown = used_candidates - set(samples)
    if unknown:
        raise ValueError(f"authoring references unknown candidate IDs: {sorted(unknown)}")

    regions_by_candidate: dict[str, dict[str, dict[str, Any]]] = {}
    for case in authoring["cases"]:
        region = case.get("region")
        if region is not None:
            regions_by_candidate.setdefault(case["candidate_id"], {})[
                region["region_id"]
            ] = region

    assets: list[dict[str, Any]] = []
    for candidate_id in sorted(used_candidates):
        sample = samples[candidate_id]
        assets.append(
            {
                "asset_id": f"mm-asset-{candidate_id.removeprefix('mm-page-')}",
                "path": sample["render_path"],
                "sha256": sample["render_sha256"],
                "mime_type": "image/png",
                "permission": "course-approved-local-only",
                "surrounding_text": sample["page_text"],
                "source_artifact_id": sample["source_id"],
                "course_id": sample["course_id"],
                "source_document_sha256": sample["document_sha256"],
                "page": sample["page"],
                "derivation": "pdf-page-render",
                "regions": list(
                    sorted(
                        regions_by_candidate.get(candidate_id, {}).values(),
                        key=lambda region: region["region_id"],
                    )
                )
                or [
                    {
                        "region_id": f"region-{candidate_id.removeprefix('mm-page-')}-page",
                        "bbox": [0, 0, 1, 1],
                        "kind": "title",
                    }
                ],
            }
        )

    cases: list[dict[str, Any]] = []
    for case in authoring["cases"]:
        region = case.get("region")
        cases.append(
            {
                "case_id": case["case_id"],
                "split": "development",
                "slice": case["slice"],
                "modality": case["modality"],
                "asset_id": f"mm-asset-{case['candidate_id'].removeprefix('mm-page-')}",
                "query": case["query"],
                "expected_action": case["expected_action"],
                "required_claims": case["required_claims"],
                "gold_region_ids": [region["region_id"]] if region is not None else [],
                "visual_dependency": case["visual_dependency"],
                "review": {
                    "status": "pending",
                    "researcher_verified": False,
                    "notes": "Provisional assistant-authored case; researcher visual verification required.",
                },
            }
        )

    return {
        "schema_version": 1,
        "dataset_id": "multimodal-retrieval-v1-private",
        "dataset_version": "v1",
        "dataset_kind": "private_course",
        "dataset_status": "researcher_review",
        "render_policy": "rasterize-before-evaluation",
        "source_assets": assets,
        "cases": cases,
    }


def review_markdown(dataset: dict[str, Any]) -> str:
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    lines = [
        "# Multimodal retrieval v1 researcher review",
        "",
        "This file is private and ignored. Inspect the rendered page for every case.",
        "Accept only when the query is unambiguous, every required claim is correct,",
        "the region is adequate, the visual-dependency label is justified, and the",
        "source is eligible for tutoring research.",
        "",
    ]
    for case in dataset["cases"]:
        asset = assets[case["asset_id"]]
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                f"- Course: `{asset['course_id']}`",
                f"- Render: `{asset['path']}`",
                f"- Slice / modality: `{case['slice']}` / `{case['modality']}`",
                f"- Query: {case['query']}",
                "- Required claims:",
                *(
                    [f"  - {claim}" for claim in case["required_claims"]]
                    or ["  - None (boundary case)"]
                ),
                f"- Expected action: `{case['expected_action']}`",
                f"- Visual dependency: `{case['visual_dependency']}`",
                "- [ ] Source eligibility confirmed",
                "- [ ] Query and claims confirmed",
                "- [ ] Evidence region confirmed",
                "- [ ] Accept case",
                "- Reviewer notes:",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def review_html(dataset: dict[str, Any], output_path: Path) -> str:
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    cards: list[str] = []
    for case in dataset["cases"]:
        asset = assets[case["asset_id"]]
        image_path = os.path.relpath(ROOT / asset["path"], output_path.parent)
        claims = "".join(
            f"<li>{html.escape(claim)}</li>" for claim in case["required_claims"]
        ) or "<li>None - boundary case</li>"
        case_id = html.escape(case["case_id"])
        cards.append(
            f"""
<article class="case" data-case-id="{case_id}">
  <header><h2>{case_id}</h2><span>{html.escape(asset['course_id'])} · {html.escape(case['slice'])} · {html.escape(case['modality'])}</span></header>
  <img src="{html.escape(image_path)}" alt="Private rendered source page for {case_id}">
  <section>
    <h3>Query</h3><p>{html.escape(case['query'])}</p>
    <h3>Required claims</h3><ul>{claims}</ul>
    <p><strong>Expected:</strong> {html.escape(case['expected_action'])} · <strong>Dependency:</strong> {html.escape(case['visual_dependency'])}</p>
    <div class="decision">
      <label><input type="radio" name="decision-{case_id}" value="accept"> Accept</label>
      <label><input type="radio" name="decision-{case_id}" value="reject"> Reject</label>
      <label><input type="radio" name="decision-{case_id}" value="revise"> Revise</label>
    </div>
    <label>Notes<textarea rows="3" data-notes="{case_id}"></textarea></label>
  </section>
</article>"""
        )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Multimodal retrieval v1 private review</title>
<style>
:root {{ font-family: system-ui, sans-serif; color: #172033; background: #f4f6fa; }}
body {{ margin: 0; }}
main {{ max-width: 1500px; margin: auto; padding: 24px; }}
.notice {{ background: #fff3cd; border: 1px solid #e7c75e; padding: 16px; border-radius: 10px; }}
.toolbar {{ position: sticky; top: 0; background: #f4f6faee; padding: 12px 0; z-index: 2; display: flex; gap: 12px; align-items: center; }}
button {{ padding: 10px 16px; border: 0; border-radius: 8px; background: #2457d6; color: white; font-weight: 700; cursor: pointer; }}
.case {{ display: grid; grid-template-columns: minmax(420px, 1.2fr) minmax(360px, 0.8fr); gap: 18px; background: white; margin: 22px 0; padding: 18px; border-radius: 12px; box-shadow: 0 2px 12px #17203318; }}
.case header {{ grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
.case h2 {{ margin: 0; }}
.case img {{ width: 100%; max-height: 720px; object-fit: contain; background: #eef1f6; }}
.decision {{ display: flex; gap: 18px; margin: 18px 0; }}
textarea {{ display: block; box-sizing: border-box; width: 100%; margin-top: 6px; }}
@media (max-width: 900px) {{ .case {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body><main>
<h1>Multimodal retrieval v1 researcher review</h1>
<p class="notice">Private local artifact. Verify source eligibility, query and claim correctness, evidence adequacy, and visual dependency. Decisions stay in this browser until exported; nothing is uploaded.</p>
<div class="toolbar"><button id="export">Export decisions</button><strong id="progress">0 / {len(dataset['cases'])} decided</strong></div>
{''.join(cards)}
</main>
<script>
const key = 'multimodal-review-v1';
const state = JSON.parse(localStorage.getItem(key) || '{{}}');
function save() {{ localStorage.setItem(key, JSON.stringify(state)); update(); }}
function update() {{ document.querySelector('#progress').textContent = `${{Object.values(state).filter(x => x.decision).length}} / {len(dataset['cases'])} decided`; }}
document.querySelectorAll('.case').forEach(card => {{
  const id = card.dataset.caseId; const prior = state[id] || {{}};
  if (prior.decision) {{ const radio = card.querySelector(`input[value="${{prior.decision}}"]`); if (radio) radio.checked = true; }}
  const notes = card.querySelector('textarea'); notes.value = prior.notes || '';
  card.querySelectorAll('input[type=radio]').forEach(r => r.addEventListener('change', () => {{ state[id] = {{...(state[id] || {{}}), decision: r.value}}; save(); }}));
  notes.addEventListener('input', () => {{ state[id] = {{...(state[id] || {{}}), notes: notes.value}}; save(); }});
}});
document.querySelector('#export').addEventListener('click', () => {{
  const blob = new Blob([JSON.stringify({{review_id:'multimodal-retrieval-v1-researcher-review', decisions:state}}, null, 2)], {{type:'application/json'}});
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'multimodal_retrieval_v1_review.json'; link.click(); URL.revokeObjectURL(link.href);
}});
update();
</script></body></html>"""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        dataset = build_dataset(load_json(args.sample_queue), load_json(args.authoring))
        summary = validate_dataset(dataset)
        write_text(args.output, json.dumps(dataset, indent=2, sort_keys=True) + "\n")
        write_text(args.review_output, review_markdown(dataset))
        write_text(args.review_html, review_html(dataset, args.review_html))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"multimodal private draft build failed: {error}")
        return 1
    print(
        json.dumps(
            {
                "status": summary["status"],
                "assets": summary["assets"],
                "cases": summary["cases"],
                "slices": dict(sorted(Counter(case["slice"] for case in dataset["cases"]).items())),
                "modalities": dict(sorted(Counter(case["modality"] for case in dataset["cases"] if case["slice"] == "visual_answerable").items())),
                "researcher_verified": 0,
                "model_called": False,
                "private_output": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
