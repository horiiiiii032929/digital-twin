# Professor-perspective reader revision

Date: 6 September 2026. Editorial scope only; no new experiment or runtime change.

## Changes and evidence

- Connect the brief's three pillars to Q1 (complete evidence-backed answers), Q2
  (teaching alignment) and Q3 (persistent, governed support). The conclusion
  answers those same questions without inventing retrospective hypotheses.
- Separate project-specific contracts, gates and event rules from framework
  infrastructure. Contributions are engineering and evaluated integration,
  not claims of a novel retrieval algorithm.
- Place a comparison-design table before scores: cases, reference construction,
  scoring method, fresh/held-out boundaries and shared-AI-review limitations.
- Replace the hypothetical autonomous scenario with one saved synthetic history.
- Illustrate SDLC with the multi-concept assessment correction and fresh
  72-history confirmation. Acceptance is limited to the correction, not every
  quality dimension of the complete system.
- Remove the duplicative requirement-results table; preserve its unique
  publication/operational counts in prose. Use descriptive planner names.

Sources for the evaluation table and comparison:

- `research/05_evaluation/final-cross-method-factual-confirmation-001-results.md`
  and its machine record: five arms, 200 source families, gold opened after
  outputs; BM25/dominance 63.25% and 96%, Qwen/dominance 62% and 95%.
- `research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-results.md`:
  56 fresh paired scenarios, pre-output references and AI assessment boundaries.
- `research/05_evaluation/governed-full-autonomy-v2-1-multi-concept-confirmation-025-results.md`:
  corrected concept assessment, fresh concepts/seeds and simulator limitations.
- `research/05_evaluation/dialogue-full-live-001-assistant-findings.json`:
  exact 77-case diagnostic selection, not a representative quality sample.

## Saved autonomous trace

This is a synthetic, deterministic history from confirmation 025, not a new
provider run. Selected identifiers below permit lookup without reproducing raw
conversation logs. Later assessments are not attributed causally to a check-in.

- Source: `reports/generated/governed-full-autonomy-v2-1-multi-concept-confirmation-025/responses.jsonl`.
- Source SHA-256: `9cffa68a654f98828feaa58e1852fcf68b2beb016ec4702fed889c516846c189`.
- Case: `hs-bkt-like-fast-learner-3101`; condition: `t1-v2-autonomous`.
- Initial action sequence: diagnostic question, hint, in-app check-in, next
  student turn. The check-in is at simulation second 223200.
- Trigger: `incomplete-objective`.
- Opportunity: `autonomous-opportunity-002da64c-7682-4f38-88ac-bbd31c5bb569`.
- Action: `autonomous:autonomous-action-919c1ec1-99d5-4c4c-97dc-424a57f9ade8`.
- Saved message: `proactive-message-1f4d8efc-64c8-4241-b3d6-67614fbde2cd`.
- Restart: before/after state hashes match in the recorded restart check.
- Final token-bucket assessment counts: eight correct, four incorrect.

The manifest and action-linked citation metadata retain configuration and
source identity. The trace demonstrates recorded state and effects; it does not
provide a controlled estimate of the intervention's educational impact.

## Validation

The main PDF remains 19 pages (12 main/declaration, two references, five
appendices). Compilation, citations, local links and text bounds are checked;
changed pages are visually reviewed. The 324-page detailed trial appendix and
its 470-result snapshot are unchanged. Before/after artifacts and build/check
logs are local in `reports/generated/professor-reader-revision-20260906/`.
