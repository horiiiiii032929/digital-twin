# Learning-gap source readability

## Decision and scope

The professor dashboard previously displayed only signal type and counts. Real
student turns group signals by a hash of the retrieved source identity; the
concept-labelled fixtures do not mean that real turns classify concepts. A
professor therefore could not identify which material a visible group concerned.

Keep the existing deterministic aggregation, privacy threshold, and signal
generation. Add an optional source title, resolved from the authorized release's
source metadata after small cells are suppressed. Display it explicitly as
"Source", not a concept or diagnosed learning outcome. Ambiguous or unavailable
titles remain absent. No raw student content or new model call is introduced.

Alternatives were leaving uninterpretable counts, or adding concept extraction.
The latter changes the measurement method and needs a separate dataset and
evaluation. Source metadata is the smallest reliable improvement now.

## Verification

`uv run pytest -q tests/api/test_learning_gap_journey.py` drives five fresh
synthetic students through actual API dialogue and StudentTutoringService, then
reads the professor route. It verifies suppression at one to four learners,
visibility and an exact release source title at five, retry deduplication,
absence of raw student identifiers and utterances, proposal review, and access
denial. Signals are not inserted directly. The deterministic test retriever and
bounded T1 mode make this integration coverage, not final-profile qualification
or a model-quality experiment.

## Remaining completion gaps

- Product upload jobs accept PDF only. Low-level text/Markdown parsing exists;
  transcripts and forum export ingestion are not yet a product workflow.
- Release preflight checks configuration, provenance, permission and index
  readiness. Passing it is not an empirical answer-quality evaluation.
- Source-level confusion counts are not concept mastery, cohort percentages or
  verified educational outcomes. A denominator/window definition and evaluated
  concept mapping are needed before claiming such analytics.
- The web panel does not yet show or implement the proposal-review workflow,
  although the API supports review. It does not automatically revise materials.
