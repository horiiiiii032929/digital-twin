# Goal completion scope review audit 001

Decision: **Refine**. The actual student-turn service can complete an unassessed
goal when a different concept has two correct assessments. This is a lifecycle
defect, separate from correctness of the individual assessment.

## Observations

A two-objective synthetic service reproduction completed both cache coherence and
virtual memory after two cache-coherence attempts. The wrong virtual-memory status
survived reopening SQLite. A direct counterexample completed a goal with two
incorrect target assessments because another concept had two correct assessments.
The original verified diagnostic had two expected-behaviour failures and five
passing controls; the repeated four-case reproduction had two failures/two passes.

| Historical run inspected | Saved histories | Completed goals | Target-unmet, other-concept-qualified | Affected histories |
| --- | ---: | ---: | ---: | ---: |
| Multi-concept confirmation 025 | 72 | 22 | 10 | 8 |
| Full provider-backed operational dialogue 001 | 24 | 4 | 0 | 0 |

The diagnostic matches exact approved objective statements to domain concepts and
counts only observations joined to committed state deltas before virtual completion
time. Every inspected completed objective maps to one concept. No nonempty WAL
was skipped. The 025 response hash matches its original registered hash. These
are retrospective findings, not revised assessment scores or corrected learning
effects. The four provider-run completions do not establish general correctness.

## Measurement corrections and provenance

An initial harness tried to overwrite an immutable domain and failed setup four
times. It was corrected by creating another release. An initial historical audit
counted rejected observations, producing an extra false flag in the provider run;
joining committed deltas corrected that measurement. Both superseded artifacts
and corrected outputs are preserved; neither error is reported as a product defect.

The [machine record](records/goal-completion-scope-review-audit-001.json) includes
per-goal evidence, database hashes, the original response hash and artifact hashes.
The scripts, JUnit and both measurement versions are retained under
`reports/generated/goal-completion-scope-review-audit-001/`. All data are synthetic.
No external LLM was called for this review. HEAD was `e441193c7fa1260ed327ebf43c59483f85817be8`
with a dirty tree; original relevant source hashes are in the archived audit.

Follow-up: the [prospective correction plan](../04_experiments/2026-09-06-goal-completion-scope-plan.md)
defines objective-scoped completion, regression tests, and a separately named paired
30-day experiment. Existing results remain historical evidence for the code they ran.
