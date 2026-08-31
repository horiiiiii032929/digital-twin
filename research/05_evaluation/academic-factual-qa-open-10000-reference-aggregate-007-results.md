# Question-stratified reference aggregate 007

## Outcome

`completed-keep` for development-package construction. The package contains 500
source-linked cases and a frozen paired 100-case control without provider calls.

## Result

- 500 total cases: 400 answerable and 100 boundary cases.
- 125 cases per course and 100 cases per question position.
- 134 source clusters; source cluster remains the uncertainty/resampling unit.
- Every answerable question previously passed exact action and answer-span
  recovery, naturalness, ambiguity, leakage, and normalized-duplicate checks.
- Every boundary case uses a versioned deterministic template with empty evidence
  lineage.
- The paired control contains 100 candidate-subset cases, balanced at 25 per
  course and 20 per question position.
- Zero provider or product calls; no private data or final split was opened.

## Decision

Keep this package for one actual-product 500+100 development confirmation. The
sampling unit is the individual question rather than a complete five-question
cluster. This removes a construction constraint that discarded four valid
questions whenever a fifth question failed, while preserving source clusters for
hierarchical confidence intervals.

This is development evidence, not a fresh confirmatory benchmark. It reuses
accepted candidate-level outputs from attempts 003–006, including completed calls
inside two operationally invalid attempts. Those historical attempt outcomes
remain unchanged and the reuse is disclosed in the package provenance.

## Limitations

- The question-level aggregation rule was adopted after observing the
  complete-cluster shortfalls, so later product results on this package are method
  development rather than untouched confirmation.
- Review used OpenAI model configurations and no independent external human
  annotation.
- The sealed 10,000-case final split remains unopened and must not be tuned after
  execution.
