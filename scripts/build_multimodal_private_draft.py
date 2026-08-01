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

CONFIRMED_SECOND_REVIEW_FIXES = {
    "mmr1-it5003-fifo-02": "Widen the evidence region to include the complete dequeue panel.",
    "mmr1-it5003-heap-03": "Widen the evidence region to include the x = 1/2 annotation and final value.",
    "mmr1-it5007-web-01": "Extend the evidence region to include the User Device, Internet, and Server labels.",
    "mmr1-it5007-mapping-04": "Rewrite the claim so Internet and Server remain separate labels, and classify the evidence as a diagram.",
}

TAXONOMY_REVIEW_CASES = {
    "mmr1-control-datamart-01",
    "mmr1-control-enterprise-05",
    "mmr1-control-memory-03",
    "mmr1-control-packages-02",
    "mmr1-control-serialization-07",
    "mmr1-control-web-06",
    "mmr1-cs5421-dimensions-01",
    "mmr1-cs5421-indexes-02",
    "mmr1-cs5421-retail-03",
    "mmr1-integrity-permission-04",
    "mmr1-it5002-memory-01",
    "mmr1-it5004-sequence-02",
    "mmr1-it5008-email-02",
    "mmr1-it5008-faculty-01",
}


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
        "## Required decisions before case review",
        "",
        "Confirm the four direct second-review fixes in the HTML page, then confirm",
        "the label policy: modality means the minimum evidence needed to answer; a",
        "case is visual only when selectable text alone cannot answer it; and",
        "integrity-refusal cases use `not_applicable` for modality and dependency.",
        "Fourteen cases are marked for taxonomy adjudication. The export records",
        "these confirmations but does not mutate the dataset.",
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
                (
                    f"- Second-review status: confirmed fix — {CONFIRMED_SECOND_REVIEW_FIXES[case['case_id']]}"
                    if case["case_id"] in CONFIRMED_SECOND_REVIEW_FIXES
                    else "- Second-review status: taxonomy adjudication required"
                    if case["case_id"] in TAXONOMY_REVIEW_CASES
                    else "- Second-review status: no flagged disagreement"
                ),
                "- [ ] Source eligibility confirmed",
                "- [ ] Query and claims confirmed",
                "- [ ] Evidence region confirmed",
                "- [ ] Modality and visual dependency confirmed",
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
        case_class = "case"
        review_callout = ""
        if case["case_id"] in CONFIRMED_SECOND_REVIEW_FIXES:
            case_class += " confirmed-fix"
            review_callout = f"<p class=\"callout fix\"><strong>Confirmed second-review fix:</strong> {html.escape(CONFIRMED_SECOND_REVIEW_FIXES[case['case_id']])}</p>"
        elif case["case_id"] in TAXONOMY_REVIEW_CASES:
            case_class += " taxonomy-review"
            review_callout = "<p class=\"callout taxonomy\"><strong>Taxonomy decision:</strong> apply the recommended label policy above and record your judgment.</p>"
        cards.append(
            f"""
<article class="{case_class}" id="{case_id}" data-case-id="{case_id}">
  <header><h2>{case_id}</h2><span>{html.escape(asset['course_id'])} · {html.escape(case['slice'])} · {html.escape(case['modality'])}</span></header>
  <img src="{html.escape(image_path)}" alt="Private rendered source page for {case_id}">
  <section>
    {review_callout}
    <h3>Query</h3><p>{html.escape(case['query'])}</p>
    <h3>Required claims</h3><ul>{claims}</ul>
    <p><strong>Expected:</strong> {html.escape(case['expected_action'])} · <strong>Dependency:</strong> {html.escape(case['visual_dependency'])}</p>
    <fieldset class="checks"><legend>Verification checks</legend>
      <label><input type="checkbox" data-check="source"> Source is eligible for this study</label>
      <label><input type="checkbox" data-check="claims"> Query and required claims are correct</label>
      <label><input type="checkbox" data-check="region"> Evidence region is adequate</label>
      <label><input type="checkbox" data-check="taxonomy"> Modality and visual dependency are correct</label>
      <label class="confirm"><input type="checkbox" data-confirm disabled> I confirm this case</label>
      <small class="case-status" data-status>Complete all checks before confirming.</small>
    </fieldset>
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
.guide {{ background: white; border: 1px solid #cbd5e1; padding: 18px; border-radius: 12px; margin: 18px 0; }}
.guide h2, .guide h3 {{ margin-top: 0; }}
.guide ol {{ margin-bottom: 12px; }}
.guide li {{ margin: 8px 0; }}
.guide label {{ display: block; margin: 8px 0; }}
.toolbar {{ position: sticky; top: 0; background: #f4f6faee; padding: 12px 0; z-index: 2; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }}
button {{ padding: 10px 16px; border: 0; border-radius: 8px; background: #2457d6; color: white; font-weight: 700; cursor: pointer; }}
button.secondary {{ background: #475569; }}
.case {{ display: grid; grid-template-columns: minmax(420px, 1.2fr) minmax(360px, 0.8fr); gap: 18px; background: white; margin: 22px 0; padding: 18px; border-radius: 12px; box-shadow: 0 2px 12px #17203318; }}
.case.confirmed-fix {{ border: 3px solid #dc2626; }}
.case.taxonomy-review {{ border: 3px solid #d97706; }}
.case header {{ grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
.case h2 {{ margin: 0; }}
.case img {{ width: 100%; max-height: 720px; object-fit: contain; background: #eef1f6; }}
.callout {{ padding: 12px; border-radius: 8px; }}
.callout.fix {{ background: #fee2e2; border: 1px solid #f87171; }}
.callout.taxonomy {{ background: #fef3c7; border: 1px solid #f59e0b; }}
.checks {{ display: grid; gap: 8px; padding: 12px; margin: 14px 0; border: 1px solid #cbd5e1; border-radius: 8px; }}
.checks label {{ display: block; }}
.checks .confirm {{ font-weight: 700; border-top: 1px solid #cbd5e1; padding-top: 10px; }}
.checks input:disabled + * {{ opacity: .6; }}
.case-status {{ color: #475569; }}
.decision {{ display: flex; gap: 18px; margin: 18px 0; }}
textarea {{ display: block; box-sizing: border-box; width: 100%; margin-top: 6px; }}
@media (max-width: 900px) {{ .case {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body><main>
<h1>Multimodal retrieval v1 researcher review</h1>
<p class="notice">Private local artifact. Nothing is uploaded. Start with the four red cards and the policy confirmation, then confirm each case after completing all four checks. The export records your review; it does not change the benchmark automatically.</p>
<section class="guide">
  <h2>1. Confirm the four direct fixes</h2>
  <ol>
    {''.join(f'<li><label><input type="checkbox" data-fix-id="{html.escape(case_id)}"> <a href="#{html.escape(case_id)}">{html.escape(case_id)}</a>: {html.escape(description)}</label></li>' for case_id, description in CONFIRMED_SECOND_REVIEW_FIXES.items())}
  </ol>
  <h2>2. Confirm the label policy</h2>
  <p>Use the minimum evidence needed to answer. A case is visual only when selectable text alone cannot answer it. Integrity-refusal cases use <code>not_applicable</code> for modality and dependency.</p>
  <label><input type="checkbox" id="policy-confirm"> I confirm this label policy for the cases below.</label>
</section>
<div class="toolbar"><button id="export">Export confirmations</button><button class="secondary" id="reset">Clear this browser's review state</button><strong id="progress">0 / {len(dataset['cases'])} cases confirmed</strong><strong id="fix-progress">0 / 4 fixes confirmed</strong><strong id="policy-progress">Policy pending</strong></div>
{''.join(cards)}
</main>
<script>
const key = 'multimodal-review-v2';
const emptyState = {{cases: {{}}, fixes: {{}}, policyConfirmed: false}};
const state = JSON.parse(localStorage.getItem(key) || 'null') || emptyState;
state.cases = state.cases || {{}}; state.fixes = state.fixes || {{}};
function save() {{ localStorage.setItem(key, JSON.stringify(state)); update(); }}
function update() {{
  const confirmed = Object.values(state.cases).filter(x => x.confirmed).length;
  const fixes = Object.values(state.fixes).filter(Boolean).length;
  document.querySelector('#progress').textContent = `${{confirmed}} / {len(dataset['cases'])} cases confirmed`;
  document.querySelector('#fix-progress').textContent = `${{fixes}} / 4 fixes confirmed`;
  document.querySelector('#policy-progress').textContent = state.policyConfirmed ? 'Policy confirmed' : 'Policy pending';
}}
document.querySelectorAll('[data-fix-id]').forEach(box => {{
  const id = box.dataset.fixId; box.checked = Boolean(state.fixes[id]);
  box.addEventListener('change', () => {{ state.fixes[id] = box.checked; save(); }});
}});
const policy = document.querySelector('#policy-confirm');
policy.checked = Boolean(state.policyConfirmed);
policy.addEventListener('change', () => {{ state.policyConfirmed = policy.checked; save(); }});
document.querySelectorAll('.case').forEach(card => {{
  const id = card.dataset.caseId; const prior = state.cases[id] || {{}};
  if (prior.decision) {{ const radio = card.querySelector(`input[value="${{prior.decision}}"]`); if (radio) radio.checked = true; }}
  const notes = card.querySelector('textarea'); notes.value = prior.notes || '';
  const checks = card.querySelectorAll('[data-check]'); const confirm = card.querySelector('[data-confirm]'); const status = card.querySelector('[data-status]');
  checks.forEach(check => {{ check.checked = Boolean((prior.checks || {{}})[check.dataset.check]); check.addEventListener('change', () => {{
    state.cases[id] = {{...(state.cases[id] || {{}}), checks: {{...((state.cases[id] || {{}}).checks || {{}}), [check.dataset.check]: check.checked}}}};
    const ready = [...checks].every(item => item.checked); confirm.disabled = !ready;
    if (!ready) {{ confirm.checked = false; state.cases[id].confirmed = false; status.textContent = 'Complete all checks before confirming.'; }} else {{ status.textContent = 'All checks complete; confirm this case when ready.'; }}
    save();
  }}); }});
  const ready = [...checks].every(item => item.checked); confirm.disabled = !ready; confirm.checked = Boolean(prior.confirmed && ready);
  confirm.addEventListener('change', () => {{ state.cases[id] = {{...(state.cases[id] || {{}}), confirmed: confirm.checked}}; status.textContent = confirm.checked ? 'Case confirmed.' : 'Case confirmation removed.'; save(); }});
  card.querySelectorAll('input[type=radio]').forEach(r => r.addEventListener('change', () => {{ state.cases[id] = {{...(state.cases[id] || {{}}), decision: r.value}}; save(); }}));
  notes.addEventListener('input', () => {{ state.cases[id] = {{...(state.cases[id] || {{}}), notes: notes.value}}; save(); }});
}});
document.querySelector('#export').addEventListener('click', () => {{
  const blob = new Blob([JSON.stringify({{review_id:'multimodal-retrieval-v1-researcher-review-v2', policy_confirmed:state.policyConfirmed, fix_confirmations:state.fixes, decisions:state.cases}}, null, 2)], {{type:'application/json'}});
  const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = 'multimodal_retrieval_v1_review.json'; link.click(); URL.revokeObjectURL(link.href);
}});
document.querySelector('#reset').addEventListener('click', () => {{ localStorage.removeItem(key); window.location.reload(); }});
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
