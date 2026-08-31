# Whole-system architecture round 3 build results

## Outcome

**Build-only qualified — Go Deeper.** Round 3 is frozen over the untouched
481-case third development fold. It has no source-range or normalized-question
overlap with Rounds 1 or 2.

The comparison retains the Round 2 typed-target method as the within-fold
control and adds two coherent successors:

1. source-range candidate-set retrieval with deterministic canonical source
   rendering;
2. the same method with explicit clarification for unresolved low-information
   source targets.

Round 3 prospectively uses `source-semantic-token-v2`. This scorer removes only
non-visible RST/LaTeX authoring markup before semantic token comparison. The
historical lexical scorer and all Round 1/2 results remain unchanged.

## Verification

- 37 architecture-focused tests passed, including six new source-range tests.
- The 12-case Round 3 simulation persisted responses before opening its gold
  subset.
- The complete gate passed 1,480 Python and 50 frontend tests, lint, and the
  production build.
- Repository correctness is complete at 845/845 files; the execution freeze is
  complete at 123/123 entrypoints.
- Provider calls, tokens, and paid cost were zero.

## Decision

Execute the frozen 481-case Round 3 exactly once from a clean revision. Do not
change the source-range planner, scorer, cases, or hard gates after execution.

## Limitations

- Build qualification is not a quality result.
- This deterministic comparison isolates architecture behavior rather than
  hosted-model generation quality.
- No professor-fidelity, usability, real-human, or student-learning claim is
  supported.
