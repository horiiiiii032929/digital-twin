# OpenAI model selection — main-deck slides

[Editable PowerPoint with English speaker notes](openai-models-and-selection-v2.pptx).

These three slides belong in the main presentation, not an appendix. The full
revision-15 presentation has not yet been rebuilt; this file supplies the new
slides without modifying the superseded Hikaru deck or submitted report.

## Content and placement

1. **OpenAI models and their roles** — after the C4 system view (revision15 page07).
   Name the four OpenAI tutoring models actually compared, define planning versus
   generation, and separate the selected local profile from the deterministic
   recording configuration.
2. **All four models failed the factual-answer gate** — after the full-course
   failure explanation (page22), before the later fresh factual comparison.
   Four models received the same200 cases. Define the denominator and the
   grounded-answer measure locally. Historical run cost is not a current price.
3. **Why the system uses a limited model set** — after the planner-design
   comparison (page24). Explain the Terra comparison and the latest Sol revision
   failure, including uncertainty and the pending independent review.

The scope is OpenAI models evaluated for tutoring. This is not a complete
catalogue of every embedding, vision, local model or development assistant used
in the repository. A configured model or candidate name alone does not count as
an executed evaluation. Uncompared OpenAI models are not labelled inferior.

## Evidence and interpretation

- [Four-model factual screening](../../../research/05_evaluation/academic-factual-qa-r1-model-cascade-001-attempt-002-refine-results.md):
  GPT-5.4 mini, GPT-5.6 Luna/Terra/Sol; same200 cases per arm,160 answerable and40
  boundary cases. All fail at least one gate. Correct direct bindings include
  `gpt-5.4-mini-2026-03-17`. This historical retrieval composition differs from
  later factual experiments, so the percentages are not a cross-run ranking.
- [Planner/generator factorial comparison](../../../research/05_evaluation/successor-architecture-engine-comparison-006-001-results.md):
  300 contexts,1,200 cells. Terra-minus-Luna synthetic utility effect+0.000354,
  95% interval0.000000–0.001062. It fails the preregistered positive-lower-bound
  adoption rule; this is not proof of equivalence. E1 was selected for subsequent
  system confirmation, not directly released by this component experiment.
- [Selected local manifest](../../../research/05_evaluation/profiles/local-r1-final-system-manifest-v1.json):
  deterministic factual generator and Luna guarded planning. No claim of a
  factual-quality pass or real-student learning. The new video uses a separate
  deterministic recording configuration.
- [Post-report Sol revision probe](../../../research/05_evaluation/post-report-paired-quality-003-results.md):
  four known failure contexts,16 total responses across V4 and V14. V14 uses
  Luna-low planning/generation and Sol-medium conditional revision. Improvements
  in calculations coexist with an assistant-reviewed critical unsupported
  guarantee. Independent review remains pending; no profile promotion.
- [Earlier generation stability review](../../../research/05_evaluation/generation-model-dialogue-stability-development-001-aggregate-assistant-review.md):
  Luna-low, Luna-medium and Sol-low all fail at least one selection gate. This
  supports caution but is not added as another dense result table on the slide.

## Presentation integration

Plan about45 seconds per new slide before rehearsal. Adding all three unchanged
to revision15's34:35 budget and replacing the2:00 placeholder with the2:14 video
would yield37:04. To retain the30–35 minute main-talk target, integration must
remove at least2:04 of repeated explanation elsewhere; do not rely on faster
English delivery. Keep the new slides' definitions and conclusions visible.

English speaker notes include natural read-through text and source paths.
The native comparison tables and text remain editable. The build source and
validation receipt are in `reports/generated/model-slides-build/`; this is a
presentation-only change, with no model configuration or evaluation selection
change.
