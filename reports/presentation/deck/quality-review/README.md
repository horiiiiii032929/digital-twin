# Response quality: slides 22–24

Current artifact: `slides-22-24-v5.pptx`. Three English review slides following approved slides19–21. Earlier approved decks are unchanged.

- 22 explains five concrete quality checks in `final_response_audit.py`. Examples are explicitly illustrative IT5004 criteria, not invented observed failures. Slide11 already explains the audit algorithm, so this page focuses on why source-reference checks alone are insufficient.
- 23 now compares implemented V4 and V19 accepted generator paths in an editable draw.io UML activity diagram. V4 selects exact spans and renders excerpts/fixed wording. V19 generates typed instructional text, validates and optionally repairs the contract, then audits the rendered reply with a separate optional repair/re-audit. Each repair stage is bounded separately. The diagram explicitly omits error branches/shared application checks. The source-state routing change is identified separately. This is a bundled comparison, not an audit-only ablation. The standalone failed V4 example was removed because it did not establish why the design changed.
- 24 explains the separate historical12case comparison: two dependent turns per arm,24outputs per arm,48total,96ratings. V4 is an experimental control, not the submitted release. V19 bundles audit/repair and routing changes. The same reviewer rated all outputs twice.64calibration ratings are separate from96product ratings. One calibration evidence check and six product checks failed. The required gate remains failed and repeated model ratings are not human validation.

Sources: `reports/generated/it5004-presentation-teaching-live-002`, `research/05_evaluation/post-report-final-selection-decision-004-results.md`, its linked machine-readable record, and `scripts/run_post_report_blind_review.py`. Full provenance and exact models in notes. No new model calls, app changes, report changes or release-profile changes.

Author: `reports/generated/quality-review-batch/build.mjs`. Editable standard UML activity: `reports/presentation/diagrams/chapter03/24-comparison-activity.drawio`. Author `diagram.py` in build directory. Run diagram author, draw.io PNG export at2x, then bundledNode build with RUNTIME_NODE_MODULES set to bundledmodules. Native editable table on22. Page24 now explicitly tests the changes shown on23 using quality, withheld replies, time and cost. A withheld response to a supported question is not treated as sufficient. Private validation receipt `validation-v3.json`. Rendered images visually inspected. PowerPoint application and timed rehearsal not claimed.

Revision3 diagram: `reports/presentation/diagrams/chapter03/23-generator-comparison-v3.drawio`, author `reports/generated/quality-review-batch/design-diagram.py`. Pages22–24 rendered and individually inspected. User review of revision3 pending.

## Readable design names, 2026-09-09

Latest artifact: `slides-22-24-v5.pptx`. Visible internal generation version labels removed. “Excerpt tutor” means the experimental control that assembles source excerpts/fixed wording. “Audited tutor” means the candidate that generates teaching text and reviews it. Original implementation/run IDs remain in provenance notes and source records. Official model names and implementation identifiers needed to explain actual code are retained. Comparison numbers and release selection unchanged.
