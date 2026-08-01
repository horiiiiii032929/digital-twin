#!/usr/bin/env python3
"""Build the ignored private multimodal benchmark from a reviewed page sample."""

from __future__ import annotations

import argparse
import copy
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
    "mmr1-it5007-mapping-04": "Rewrite the claim so Internet and Server remain separate labels; retain the screenshot source modality because the page contains an embedded UI screenshot.",
}

AUTO_ADJUDICATIONS = {
    "mmr1-control-datamart-01": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-fifo-04": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-chatbot-08": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-enterprise-05": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-memory-03": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-packages-02": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-serialization-07": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-control-web-06": "Keep source modality=mixed; visual_dependency=text_sufficient is the authoritative answerability label.",
    "mmr1-integrity-permission-04": "Keep the source modality; the refusal action is authoritative and no modality choice is needed.",
    "mmr1-integrity-crosscourse-01": "Keep the source modality; the refusal action is authoritative and no modality choice is needed.",
    "mmr1-integrity-solution-02": "Keep the source modality; the refusal action is authoritative and no modality choice is needed.",
    "mmr1-integrity-provider-03": "Keep the source modality; the refusal action is authoritative and no modality choice is needed.",
}

FRESH_REVIEW_CASES = {
    "mmr1-cs5421-dimensions-01",
    "mmr1-cs5421-indexes-02",
    "mmr1-cs5421-retail-03",
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


def _case_review_signature(case: dict[str, Any]) -> tuple[Any, ...]:
    """Return the evidence-bearing fields that make a prior review reusable."""
    return (
        case["slice"],
        case["modality"],
        case["asset_id"],
        case["query"],
        tuple(case["required_claims"]),
        case["expected_action"],
        tuple(case["gold_region_ids"]),
        case["visual_dependency"],
    )


def preserve_unchanged_reviews(
    dataset: dict[str, Any], prior_dataset: dict[str, Any]
) -> dict[str, Any]:
    """Carry forward verified reviews only when the complete case evidence matches."""
    prior_cases = {case["case_id"]: case for case in prior_dataset.get("cases", [])}
    for case in dataset["cases"]:
        prior = prior_cases.get(case["case_id"])
        if (
            prior is not None
            and prior.get("review", {}).get("researcher_verified") is True
            and _case_review_signature(prior) == _case_review_signature(case)
        ):
            case["review"] = copy.deepcopy(prior["review"])
    return dataset


def review_markdown(dataset: dict[str, Any]) -> str:
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    lines = [
        "# Multimodal retrieval v1 researcher review",
        "",
        "This file is private and ignored. Inspect the rendered page for every case.",
        "Accept only when the query is unambiguous, every required claim is correct,",
        "the region is adequate, and the source is eligible for tutoring research.",
        "",
        "## Required decisions before case review",
        "",
        "Confirm the four direct second-review fixes in the HTML page. The label",
        "policy is already adjudicated: modality names the source page's primary",
        "representation; visual dependency determines whether selectable text",
        "alone can answer; and refusal cases are judged by action rather than",
        "evidence modality. Your review is limited to source eligibility,",
        "query/claims, evidence regions, and an accept/reject/revise disposition;",
        "the export records your confirmations but does not mutate the dataset.",
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
                    else f"- Second-review status: Codex adjudication — {AUTO_ADJUDICATIONS[case['case_id']]}"
                    if case["case_id"] in AUTO_ADJUDICATIONS
                    else "- Second-review status: no flagged disagreement"
                ),
                "- [ ] Source eligibility confirmed",
                "- [ ] Query and claims confirmed",
                "- [ ] Evidence region confirmed",
                "- Taxonomy: pre-adjudicated by Codex (displayed for context)",
                "- [ ] Record disposition: accept, reject, or revise",
                "- Reviewer notes:",
                "",
            ]
        )
    return "\n".join(lines) + "\n"


def review_html(dataset: dict[str, Any], output_path: Path) -> str:
    assets = {asset["asset_id"]: asset for asset in dataset["source_assets"]}
    initial_cases: dict[str, Any] = {}
    for case in dataset["cases"]:
        if case["review"]["researcher_verified"]:
            initial_cases[case["case_id"]] = {
                "checks": {
                    "source": True,
                    "claims": True,
                    "region": True,
                    "taxonomy": True,
                },
                "decision": "accept",
                "confirmed": True,
                "notes": case["review"]["notes"],
            }
    initial_state = {
        "cases": initial_cases,
        "fixes": {
            case_id: case_id in initial_cases
            for case_id in CONFIRMED_SECOND_REVIEW_FIXES
        },
        "policyConfirmed": True,
    }
    initial_state_json = json.dumps(initial_state, sort_keys=True).replace("</", "<\\/")
    verified_count = len(initial_cases)
    pending_count = len(dataset["cases"]) - verified_count
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
        if case["review"]["researcher_verified"]:
            case_class += " preverified"
            review_callout = '<p class="callout verified"><strong>Prior review retained:</strong> this unchanged case is already researcher-verified.</p>'
        elif case["case_id"] in FRESH_REVIEW_CASES:
            case_class += " fresh-review"
            review_callout = '<p class="callout fresh"><strong>New visual replacement:</strong> confirm that the question truly requires the marked visual evidence.</p>'
        elif case["case_id"] in CONFIRMED_SECOND_REVIEW_FIXES:
            case_class += " confirmed-fix"
            review_callout = f"<p class=\"callout fix\"><strong>Confirmed second-review fix:</strong> {html.escape(CONFIRMED_SECOND_REVIEW_FIXES[case['case_id']])}</p>"
        elif case["case_id"] in AUTO_ADJUDICATIONS:
            case_class += " auto-adjudicated"
            review_callout = f"<p class=\"callout adjudicated\"><strong>Codex adjudication:</strong> {html.escape(AUTO_ADJUDICATIONS[case['case_id']])}</p>"
        taxonomy_check = (
            '<label><input type="checkbox" data-check="taxonomy" checked disabled> Modality and visual dependency pre-adjudicated</label>'
            if case["case_id"] in AUTO_ADJUDICATIONS
            else '<label><input type="checkbox" data-check="taxonomy"> Modality and visual dependency are correct</label>'
        )
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
      {taxonomy_check}
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
.case.auto-adjudicated {{ border: 3px solid #2563eb; }}
.case.fresh-review {{ border: 3px solid #7c3aed; }}
.case.preverified {{ display: none; opacity: .8; }}
body.show-preverified .case.preverified {{ display: grid; }}
.case header {{ grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: baseline; gap: 16px; }}
.case h2 {{ margin: 0; }}
.case img {{ width: 100%; max-height: 720px; object-fit: contain; background: #eef1f6; }}
.callout {{ padding: 12px; border-radius: 8px; }}
.callout.fix {{ background: #fee2e2; border: 1px solid #f87171; }}
.callout.taxonomy {{ background: #fef3c7; border: 1px solid #f59e0b; }}
.callout.adjudicated {{ background: #dbeafe; border: 1px solid #60a5fa; }}
.callout.fresh {{ background: #ede9fe; border: 1px solid #8b5cf6; }}
.callout.verified {{ background: #dcfce7; border: 1px solid #4ade80; }}
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
<p class="notice">Private local artifact. Nothing is uploaded. Only {pending_count} new visual replacements need review; {verified_count} unchanged reviews were retained. Complete the checks, choose Accept / Reject / Revise, and confirm each purple card.</p>
<section class="guide">
  <h2>1. Confirm the four direct fixes</h2>
  <ol>
    {''.join(f'<li><label><input type="checkbox" data-fix-id="{html.escape(case_id)}"> <a href="#{html.escape(case_id)}">{html.escape(case_id)}</a>: {html.escape(description)}</label></li>' for case_id, description in CONFIRMED_SECOND_REVIEW_FIXES.items())}
  </ol>
  <h2>2. Taxonomy is pre-adjudicated</h2>
  <p>Codex applied the benchmark taxonomy: modality names the source page's primary representation, while visual dependency determines whether selectable text alone can answer. Cases answerable from linear extracted text are held out of the visual denominator. Blue cards show these decisions; you do not need to choose them again.</p>
  <label><input type="checkbox" id="policy-confirm" checked disabled> Taxonomy policy applied.</label>
</section>
<div class="toolbar"><button id="export">Export confirmations</button><button class="secondary" id="reset">Clear this browser's review state</button><label><input type="checkbox" id="show-preverified"> Show {verified_count} completed cases</label><strong id="progress">{verified_count} / {len(dataset['cases'])} cases confirmed</strong><strong id="fix-progress">4 / 4 fixes confirmed</strong><strong id="policy-progress">Taxonomy pre-adjudicated</strong></div>
{''.join(cards)}
</main>
<script>
const key = 'multimodal-review-v3';
const initialState = {initial_state_json};
const state = JSON.parse(localStorage.getItem(key) || 'null') || initialState;
state.cases = state.cases || {{}}; state.fixes = state.fixes || {{}};
state.policyConfirmed = true;
function save() {{ localStorage.setItem(key, JSON.stringify(state)); update(); }}
function update() {{
  const confirmed = Object.values(state.cases).filter(x => x.confirmed).length;
  const fixes = Object.values(state.fixes).filter(Boolean).length;
  document.querySelector('#progress').textContent = `${{confirmed}} / {len(dataset['cases'])} cases confirmed`;
  document.querySelector('#fix-progress').textContent = `${{fixes}} / 4 fixes confirmed`;
  document.querySelector('#policy-progress').textContent = 'Taxonomy pre-adjudicated';
}}
document.querySelectorAll('[data-fix-id]').forEach(box => {{
  const id = box.dataset.fixId; box.checked = Boolean(state.fixes[id]);
  box.addEventListener('change', () => {{ state.fixes[id] = box.checked; save(); }});
}});
document.querySelector('#show-preverified').addEventListener('change', event => {{
  document.body.classList.toggle('show-preverified', event.target.checked);
}});
document.querySelectorAll('.case').forEach(card => {{
  const id = card.dataset.caseId; const prior = state.cases[id] || {{}};
  if (prior.decision) {{ const radio = card.querySelector(`input[value="${{prior.decision}}"]`); if (radio) radio.checked = true; }}
  const notes = card.querySelector('textarea'); notes.value = prior.notes || '';
  const checks = card.querySelectorAll('[data-check]'); const decisions = card.querySelectorAll('input[type=radio]'); const confirm = card.querySelector('[data-confirm]'); const status = card.querySelector('[data-status]');
  function refreshCase() {{
    const checksReady = [...checks].every(item => item.checked); const decisionReady = [...decisions].some(item => item.checked); const ready = checksReady && decisionReady;
    confirm.disabled = !ready;
    if (!ready && confirm.checked) {{ confirm.checked = false; state.cases[id] = {{...(state.cases[id] || {{}}), confirmed: false}}; }}
    status.textContent = !checksReady ? 'Complete the three active checks.' : !decisionReady ? 'Choose Accept, Reject, or Revise before confirming.' : confirm.checked ? 'Case confirmed.' : 'All checks complete; confirm this case when ready.';
  }}
  checks.forEach(check => {{ check.checked = check.disabled || Boolean((prior.checks || {{}})[check.dataset.check]); check.addEventListener('change', () => {{
    state.cases[id] = {{...(state.cases[id] || {{}}), checks: {{...((state.cases[id] || {{}}).checks || {{}}), [check.dataset.check]: check.checked}}}};
    refreshCase();
    save();
  }}); }});
  const ready = [...checks].every(item => item.checked) && [...decisions].some(item => item.checked); confirm.checked = Boolean(prior.confirmed && ready); refreshCase();
  confirm.addEventListener('change', () => {{ state.cases[id] = {{...(state.cases[id] || {{}}), confirmed: confirm.checked}}; status.textContent = confirm.checked ? 'Case confirmed.' : 'Case confirmation removed.'; save(); }});
  decisions.forEach(r => r.addEventListener('change', () => {{ state.cases[id] = {{...(state.cases[id] || {{}}), decision: r.value}}; refreshCase(); save(); }}));
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
        prior_dataset = load_json(args.output) if args.output.is_file() else None
        dataset = build_dataset(load_json(args.sample_queue), load_json(args.authoring))
        if prior_dataset is not None:
            dataset = preserve_unchanged_reviews(dataset, prior_dataset)
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
                "researcher_verified": sum(
                    case["review"]["researcher_verified"]
                    for case in dataset["cases"]
                ),
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
