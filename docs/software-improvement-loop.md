# Software improvement loop

The Course Digital Twin uses a finite, evidence-driven improvement loop across
retrieval, grounding, tutoring behavior, autonomy, product workflows, privacy,
and operations.

## Loop contract

Each iteration must complete these stages in order:

1. Freeze the current release, rollback, dataset, metrics, and known result.
2. Classify the observed failure as an operational defect, data defect,
   component-quality defect, integration defect, or product-quality defect.
3. State one causal hypothesis and one method-level change. Do not bundle an
   evaluator search, prompt search, model search, and architecture replacement
   into the same decision.
4. Prove the harness and product boundary network-free before provider use.
5. Compare the candidate with the retained control on fresh development data.
6. Record `Keep`, `Refine`, or `invalid-execution` with every failed gate and
   operational measurement.
7. Promote only after a valid pass. Keep the previous selected implementation
   as rollback until a source-disjoint confirmation also passes.

An operationally invalid execution permits a harness-only correction when that
correction was preregistered. It does not justify changing the method or making
a quality claim. A valid quality failure requires a new causal hypothesis and a
new development tranche. The same sealed confirmation set is never tuned and
rerun.

## Current iteration

Program 011 is immutable `Refine` evidence. Its decisive product defects were
academic-integrity routing, boundary handling, incomplete evidence, unsupported
claims, and incomplete citations. Issue #153 therefore owns one method-level
candidate: deterministic pre-generation action routing plus question-targeted
complete evidence and canonical atomic-claim validation.

The two `course-digital-twin-autonomous-long-run-001` attempts supplied no new
quality evidence because they stopped before provider I/O. The second attempt
exposed an adapter/system-manifest version mismatch. The immediate successor
corrects that integration contract and detects future drift before provider
construction. It does not alter the candidate, questions, hidden gold, model,
prompt, or quality gates.

The next valid 500+100 result controls progression:

- `Keep`: select the grounding candidate provisionally, retain T0 rollback,
  and open one source-disjoint confirmation before provider-backed autonomy.
- `Refine`: classify the dominant failure slice, design one new method-level
  successor on fresh development evidence, and keep #157 blocked.
- `invalid-execution`: publish the operational defect; correct only a frozen
  harness fault. Do not treat it as product quality.

## Non-removable stops

Every iteration stops on private-data exposure, hidden-gold leakage, identity
drift, corrupted hashes or ledgers, security failure, unbounded execution, or
the recorded cost ceiling. These stops protect validity and users; they are not
prompt-tuning gates.
