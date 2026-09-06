# Software decision and failure review

Date: 6 September 2026. Scope: manuscript, diagrams, summary appendices,
configuration identity and supporting evidence navigation. No runtime changes.
This is a report/evidence consistency review, not a fresh full-code audit or
re-execution of all historical experiments.

## Resolved reader-facing issues

1. The previous design table gave architectural reasons but left key comparative
   evidence in later sections. The revised table identifies the retained mechanism,
   its alternative, the observed outcome and unresolved acceptance for six boundaries.
2. The evidence-to-generator interface failure was insufficiently explained.
   The any-hit arm retrieved complete evidence at 98% but passed an unrestricted
   set into a one/two-atom generator contract, producing safe abstention and 0%
   grounded success. The manuscript now distinguishes retrieval quality from
   compatibility of component inputs and outputs.
3. Earlier candidate profiles still select Qwen. The final report now names the
   actual final profile referenced by the qualified environment, rather than
   implying that every candidate manifest agrees with the selected BM25 runtime.
4. The visual benchmark label text/OCR could imply arbitrary scanned-PDF ingestion.
   The final parser profile explicitly has selectable_text_only=true. Benchmark
   comparison and accepted input capability are now distinguished.
5. An added appendix maps seven unsuccessful or corrected designs to observed
   failure mechanisms and Keep/Refine/Drop implications. It distinguishes lack of
   improvement from a proven component defect and does not pool different datasets.

## Evidence inspected

- `research/05_evaluation/profiles/student-tutor-r1-local-final-v1.json`
  (v2.1-final-001-bm25-text-ocr) and the historical candidate-v3 profile.
- `deploy/local-r1.qualified.env.example` and qualification 011's stored environment.
- `src/digital_twin/grounding/ambiguity_safe_evidence.py`: leading interpretation
  uniqueness and precise-region preference before the bounded candidate window.
- `research/05_evaluation/final-cross-method-factual-confirmation-001-results.md`
  and analysis-correction-001: actual shared-arm scores and metric interpretation.
- `research/05_evaluation/true-visual-omni-confirmation-002-results.md`: 16/30 versus
  26/30; region lineage failure and the control's citation limitation.
- `research/05_evaluation/independent-factual-revision-controls-001-fresh-v16-live-001-results.md`:
  necessary-condition versus sufficiency error despite good aggregate repair.
- Multi-concept confirmation 025 and saved dialogue findings already traced in
  `professor-reader-review.md`: correction acceptance, weak predictive diagnostics
  and generic proactive wording.
- Logical architecture, autonomy activity, native response sequence and the main
  design summary: responsibility and scope consistency, not a strict UML audit.

## Remaining substantive limitations

The final profile is an operational fallback, not high factual-quality acceptance.
Real instructor fidelity and measured student learning remain unestablished.
Model-assisted assessment is not independent human validation. Some older trials
retain only aggregate evidence and hashes; PDF coverage does not reconstruct
missing original ledgers. Local operational evidence does not establish a best
production topology. None of these issues was hidden by this editorial revision.

## Package verification

The main report has 21 pages: 13 main/declaration, two references and six appendix
pages. The detailed companion remains 324 pages. The existing package verifier
checks all 470 registry IDs and stable companion destinations, allocation source
existence, bibliography consistency and both PDFs' text bounds. Main design and
failure-table pages are rendered for visual review. Compilation diagnostics,
local Markdown links and whitespace checks are also verified. Artifacts and logs
are local in `reports/generated/software-decision-review-20260906/`.
