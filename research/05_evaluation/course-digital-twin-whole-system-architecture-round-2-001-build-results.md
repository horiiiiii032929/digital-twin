# Whole-system architecture round 2 build results

## Outcome

**Build-only qualified — Go Deeper.** Round 2 is frozen over the 497-case
second development fold, which has no source-range or normalized-question
overlap with Round 1.

The comparison retains the Round 1 lexical winner only as a baseline and adds:

1. typed public-question evidence targets with one distinct region per target;
2. the same target/cardinality contract with source-section metadata ranking.

The candidates keep deterministic boundary routing and authority checks. Their
atomic response path emits one exact source-region claim and citation for every
resolved target. No candidate can read hidden gold or call a provider.

## Verification

- 29 architecture-focused tests passed.
- Five target-planner/retriever/gate tests passed.
- The 12-case Round 2 simulation persisted responses before opening gold.
- Freeze coverage passed 123/123 entrypoints.
- Provider calls and paid cost were zero.

## Decision

Execute the frozen 497-case Round 2 once from a clean revision. Do not modify
the target parser, ranker, gate, cases, or thresholds after opening this fold.

## Limitations

- Build qualification is not a quality result.
- This deterministic comparison does not estimate hosted-model generation.
- No professor-fidelity, usability, or real-learning claim is supported.
