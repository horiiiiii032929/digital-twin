# Whole-system architecture round 3 analysis correction 001

## Correction

The raw Round 3 execution completed technically and reported
`completed-refine`, but it is **invalid for preregistered architecture
selection**. The frozen parent program allowed at most two total Round 3
architectures: the retained rollback and one strongest coherent successor.
The Round 3 instrument contained one baseline and two successors, for three
total architectures.

The build validator did not compare the child instrument's architecture count
with the parent program. This is an evaluation-harness defect, not a provider,
data, or product failure.

## Evidence retained

All 481-case responses, aggregate metrics, hashes, and the raw `Refine` output
remain immutable and are useful only as development-visible diagnostics. They
still show that no condition passed every quality gate and therefore cannot
support a release under any interpretation.

The fold has now been opened. It must not be rerun or retrospectively reduced
to two conditions for a confirmatory claim. Doing so would choose the
comparison after observing the result.

## Decision

Record **invalid execution / no release** for Round 3 selection. The whole
program ends without a winner. The fresh 1,000-case confirmation and all
dependent final stages remain unopened.

Any successor program must:

- validate child candidate counts against its parent before execution;
- use fresh source-disjoint development evidence;
- treat all three current folds as known regression data;
- retain the raw Round 3 metrics and this correction together.

No provider calls, paid cost, private data, or real-human evaluation were
involved.
