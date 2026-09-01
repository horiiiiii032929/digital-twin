# Reference uniqueness successor plan

Run ID: `academic-factual-qa-ambiguity-safe-comparison-001`

## Decision question

Does deterministic source/section scoping plus pre-generation reference
uniqueness correct the dual reference-label and product-action defect found in
the immutable 16-case audit, without reducing grounded factual quality on new
source-disjoint evidence?

## Frozen comparison

- Baseline: source-semantic evidence atoms v1.
- Candidate: the same source atoms and retrieval, plus deterministic
  pre-generation reference uniqueness and fail-closed `clarify` routing.
- Data: 500 fresh development cases from 100 clusters, 25 clusters per course.
- Answerable cases: 400, each deterministically verified as `unique` before
  sealing. Equivalent alternate regions are permitted only when they express
  one canonical claim class.
- Boundary cases: 100, balanced across no-evidence, cross-course, ambiguity,
  and academic-integrity handling.
- Structured allocation is constrained by genuinely fresh eligible ranges;
  data-structures uses nine equation clusters and no table cluster rather than
  reusing a prior table range or lowering the uniqueness gate.
- The known 500-case predecessor is used only to verify that its audited 16
  non-unique questions now route to `clarify`. It is not rescored.

## Calibration and authority

Six planted controls cover unique, alternate-valid, partial, conflicting,
unrelated, and genuinely ambiguous evidence. Deterministic source truth is
authoritative; no model vote may change source, claim, action, or citation
labels.

The package and runner are build-only. Provider and paid execution remain
disabled. The one network-free 500-case comparison requires a separate exact
authorization and may execute only once from a clean revision.

## Gates and stop rule

The immutable release gates remain unchanged: grounded success at least 95%,
boundary action at least 98%, claim/citation precision and recall at least
98%/95%, source-version validity 100%, and zero severe unsupported release.
The candidate must also be non-inferior to the v1 baseline on grounded success.

A valid failure is `Refine` and stops the method. A pass is `Keep` and opens a
separate autonomy-evaluation decision. A harness/hash/leakage defect is
`invalid-execution`; it cannot be used to change cases, gold, method, or gates.
