# Evidence-design comparisons: slides 12–18

Current review artifact: `slides-12-18-v6.pptx`. English slides; chapter 2; editable native tables and chart. Approved slides 01–06 v3 and 07–11 v1 are unchanged. This batch expands the former three-slide allocation to seven, including an opening and closing explanation of the LLM connection; the provisional full outline is 44 slides.

## Content and evidence

- 12: Historical deterministic evidence path versus the actual V19 authorized-top5 admission and LLM generation/audit. These gates differ.
- 18: Actual request fields connecting retrieved evidence to the model; the saved turn contains three excerpts, Luna low draft and Luna medium audit, no repair.

- 13: Seven design families. Includes whole-question hierarchical/event-based checks, explicit targets, section ranking, question-side semantic interpretation, source facts, ambiguity handling and lexical/hybrid retrieval.
- 14: Simplified pseudocode mapped to `plan_public_evidence_targets` and `TargetEvidenceGateV1.assess`. IT5004 example is illustrative, not a recorded benchmark case.
- 15: Same 397 answerable cases, counts 253 / 355 / 355. Additional section ranking increased p95 processing time from 1.36 to 2.79 ms without improving passes.
- 16: Separate comparisons, each 500 cases with 400 answerable. Known 16-case ambiguity regression is distinct from the fresh unique-answer evaluation.
- 17: Fresh 1000-case product-path comparison, 800 answerable and 200 boundary cases. BM25 plus dominance ties for most complete answers and wins the boundary tie-break by one case. The 95% / 98% targets remain unmet. Any-hit failed the answer assembler input contract; it did not have zero retrieval recall.

Sources under `research/05_evaluation/`: `course-digital-twin-whole-system-architecture-round-1-001-results.md`, `course-digital-twin-whole-system-architecture-round-2-001-results.md`, `academic-factual-qa-semantic-target-comparison-002-results.md`, `academic-factual-qa-source-semantic-atom-comparison-001-results.md`, `academic-factual-qa-source-semantic-atom-failure-validity-audit-001-results.md`, `academic-factual-qa-ambiguity-safe-comparison-002-results.md`, `product-evidence-gate-selection-004-results.md`, `final-cross-method-factual-confirmation-001-results.md`.

The comparisons shown use no external model calls. They do not measure V19 generative-answer quality or real student learning. Independent datasets are not presented as one improvement curve. Existing evaluations, submitted report and release profiles were not modified.

## Production

Author: `reports/generated/design-comparison-batch/build.mjs`.
Run with the bundled Node runtime and `RUNTIME_NODE_MODULES` pointing at its dependency directory. Outputs are immutable versioned PowerPoints plus rendered PNG previews. Validation receipt: `reports/generated/design-comparison-batch/validation-v6.json`. New opening and closing slides rendered and inspected; existing comparison content preserved with shifted numbering. No native PowerPoint application inspection claimed.

## LLM connection verification

Verified `AsyncAnswerabilityAdmissionGateV1.assess` in `src/digital_twin/generation/question_specific.py`: authorized hits capped at five, semantic answerability deferred. The actual turn admits three. `SourceStateInstructionalGenerator` inherits compact generation and final-response audit. `compact_instruction.py` constructs evidence entries containing citation IDs and text together with question, history and teaching profile. `audited_instruction.py` passes prepared context and draft to `audit_final_response`. The saved provider ledger in `reports/generated/course-answer-batch/provenance.json` confirms two actual calls. No new provider calls or application changes.

## Review revision

12 explains the purpose of separately configured local and V19 paths. 13 groups all seven design families by four problems. 14 adds illustrative before/after lecture paraphrases, distinct from measured outputs. 16 separates known ambiguity regressions from fresh unambiguous cases. 17 names a retained local configuration rather than implying automatic LLM failover. 18 quotes actual request evidence S2/S3, teaching preferences and empty first-turn history, verified directly against the saved provider request. No new model calls.

## Readable design names, 2026-09-09

Latest artifact: `slides-12-18-v7.pptx`. Visible internal generation version labels removed. “Excerpt tutor” means the experimental control that assembles source excerpts/fixed wording. “Audited tutor” means the candidate that generates teaching text and reviews it. Original implementation/run IDs remain in provenance notes and source records. Official model names and implementation identifiers needed to explain actual code are retained. Comparison numbers and release selection unchanged.
