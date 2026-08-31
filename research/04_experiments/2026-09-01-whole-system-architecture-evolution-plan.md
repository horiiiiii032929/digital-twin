# Whole-system architecture evolution plan

Date: 2026-09-01

Program: `course-digital-twin-whole-system-architecture-evolution-001`

Owner: issue #165; parent release goal #8; grounding evidence #153; autonomy
evidence #157.

## Decision question

Which coherent Course Digital Twin architecture best satisfies factual
grounding, governed autonomy, formal professor-profile adherence, simulated
learning utility, product reliability, privacy, usability, latency, cost, and
operational simplicity under architecture-neutral evaluation?

The objective is not to make V2.1 pass. V2.1 is the retained baseline. Any
system plane may be kept, replaced, recomposed, or redesigned when prospective
evidence supports the change.

## Prediction

The current event-driven governance and persistence planes will remain strong,
but the factual interaction path will require an evidence-first architecture
that fixes action before generation, plans required evidence and claims, and
uses the model for bounded pedagogy and wording. A more complex architecture is
not selected unless it passes the same hard gates and improves whole-product
quality without unacceptable latency, cost, or operational complexity.

## Immutable evidence rule

Every named build, simulation, preflight, live execution, invalid execution,
cancellation, comparison, and decision receives:

1. a stable run ID and immutable instrument;
2. a machine-readable record and readable result summary;
3. a result-registry row and GitHub checkpoint;
4. code, data, system, model, prompt, policy, and artifact bindings;
5. calls, tokens, latency, cost, malformed output, and provider failures;
6. aggregate and slice metrics, hard gates, causal failure classification, and
   limitations.

A correction uses a new run ID and links to the predecessor. No unfavorable
result is overwritten. Zero-call stops remain results.

## Frozen comparison boundary

The stable product evaluation interfaces remain factual
`TutorEvaluationAdapterV1` and autonomy `AutonomyEvaluationAdapterV1`. Candidate
code may change internal classes, graph nodes, tables, prompts, providers, and
UI flows, but every candidate must emit the same observable action, claim,
citation, state, outcome, latency, token, and cost contracts.

Three source-disjoint development folds are constructed and frozen before
Round 1 results are visible. The fresh 1,000-case confirmation is physically
separate and opened once after the winner is frozen. Program 011 remains a
known 10,000+1,000 regression benchmark and cannot regain fresh-confirmation
status.

## Round 1: divergent architectures

Implement at most four candidates behind the stable adapters:

1. `v2-1-bounded-single-graph`: unchanged software baseline.
2. `evidence-first-hierarchical-v1`: deterministic boundary action, explicit
   evidence requirements, source-range coverage, bounded claim plan,
   pedagogical realization, and post-generation validation.
3. `event-sourced-plan-observe-v1`: durable goal/opportunity planner with
   explicit outcome observation and replanning, using the selected grounding
   boundary for every action.
4. A fourth candidate is permitted only when the causal audit identifies a
   distinct architecture hypothesis; it cannot be a prompt-only or model-only
   variant.

Round 1 uses development fold 1. A hard-gate failure rejects a candidate before
quality ranking.

## Round 2: evidence-driven composition

Retain the strongest planes from Round 1 and replace the dominant weak planes.
Compare two or three coherent candidates on untouched development fold 2. Do
not combine multiple unexplained changes: each changed plane must link to a
Round 1 failure and an explicit causal hypothesis.

## Round 3: product convergence

Compare the strongest coherent successor with the retained rollback on
untouched development fold 3. Complete professor and student workflows,
provider boundaries, privacy, security, persistence, restart, backup/restore,
rollback, mobile, and accessibility before selection. Freeze one winner only
when all hard gates pass.

## Final evaluation

After winner freeze, execute and record in order:

1. fresh 1,000-case factual confirmation;
2. labelled known 10,000+1,000 regression;
3. provider-backed 820-case T0/T1-v1/T1-v2 portfolio;
4. 30-day virtual-time autonomy and proactive behavior;
5. visual 30-asset/60-case supplement;
6. 120-case security and policy red team;
7. complete local professor/student product qualification;
8. blinded multi-LLM C0-C3 formal-profile adherence proxy;
9. multi-simulator hidden-state learning-utility proxy.

The profile and learning tracks are explicitly non-human proxy evidence. They
cannot establish accurate representation of a real professor, real-student
usability, or real-student learning improvement.

## Selection rule

Hard gates have priority over averages. A design with a privacy, permission,
unsupported-action, wrong-scope, invalid-citation, duplicate-delivery,
unbounded-loop, identity, ledger, or gold-leakage defect cannot win.

Among complete hard-gate passes, rank in this order:

1. grounded factual and boundary success;
2. autonomous goal, transition, timing, and termination correctness;
3. formal-profile adherence and simulated learning utility;
4. reliability and restart consistency;
5. p95 latency;
6. reported cost;
7. operational and maintenance complexity.

## Finite correction rule

Each named run permits one harness-only correction for an evidenced operational
defect. A valid quality failure is never rerun on the same tranche. It creates
one causal successor for the next untouched development fold. After Round 3,
the winner is frozen; a valid final failure produces `No release` and a new
benchmark version rather than tuning the final set.

## Required outputs

- architecture traceability and causal-failure matrix;
- per-round candidate manifests and comparison tables;
- every run summary and machine record;
- fresh confirmation and known-regression charts;
- autonomy timeline and failure taxonomy;
- profile-proxy and learning-utility reports;
- exact final system manifest and Docker image digests;
- professor-ready summary and release/no-release decision.
