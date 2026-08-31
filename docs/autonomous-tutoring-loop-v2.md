# Autonomous tutoring loop V2

Date: 2026-08-31

Decision ID: `autonomous-tutoring-loop-002`

Status: accepted as the prospective autonomous-agent architecture; no new
provider, paid, private-data, human-study, or release authorization

Predecessor: [`autonomous-tutoring-graph-001`](autonomous-tutoring-graph.md)

Research basis:
[`2026-08-31-autonomous-tutoring-loop-and-evaluation`](../research/01_literature/2026-08-31-autonomous-tutoring-loop-and-evaluation.md)

## Decision

Evolve the current LangGraph T1 into a **bounded, mixed-initiative Professor
Digital Twin**. The LLM is responsible for semantic perception, pedagogical
planning, and grounded language generation. The application remains the sole
authority for permissions, academic-integrity policy, source validity,
professor configuration, state commits, proactive delivery, budgets, and
termination.

This is autonomous because the published system can interpret a learner's
state, choose a pedagogical move, use approved evidence, adapt over time, and
initiate an eligible intervention without per-turn professor approval. It is
not unrestricted: every action occurs inside professor-approved and
student-consented boundaries.

## Architecture choice

Keep the existing code-owned LangGraph and direct model-provider interface.
Do not migrate to the OpenAI Agents SDK or add a multi-agent framework now.
OpenAI's current guidance distinguishes the Responses API, where the
application owns custom loops and branching, from the Agents SDK, where the SDK
owns the recurring tool loop. This project requires application-owned policy,
state, and evaluation boundaries, and LangGraph already provides the explicit
graph and persistence model needed for them.

The framework decision is replaceable. Model access, semantic planning,
retrieval, validation, persistence, and delivery remain behind explicit
interfaces so a future candidate can be compared without changing the product
contract.

## Non-negotiable invariants

1. A model output is a proposal until deterministic code validates it.
2. Only the authenticated course, published release, approved professor
   profile, and authorized source set may affect a turn.
3. `answer` requires unique, complete, current, source-authorized evidence.
4. Every accepted atomic claim maps to one or more canonical source ranges.
5. `clarify`, `abstain`, and `refuse` contain no unsupported academic answer.
6. Academic-integrity ceilings are enforced before and after generation.
7. Observed learner facts and inferred learner hypotheses are never conflated.
8. A model cannot directly mutate identity, membership, release, policy,
   profile, source lineage, consent, or delivery state.
9. A turn permits at most one repair and always has a terminal state.
10. State and side effects commit atomically and idempotently.
11. `No action` is a valid proactive decision.
12. T0 remains an immediate rollback until the new T1 passes a prospective
    provider-backed confirmation.

## Control planes and clocks

```text
                    PROFESSOR GOVERNANCE PLANE
        profile / release / policy / sources / outreach classes
                                  |
                                  v
STUDENT TURN --> L1 TURN GRAPH --> atomic response + learner-state event
                                  |                       |
                                  v                       v
                         L2 LEARNER LOOP          opportunity events
                                                          |
                                                          v
                                                L3 PROACTIVE LOOP
                                                          |
                                           policy gate -> durable outbox

privacy-minimized aggregate events -----------------------+
                                  |
                                  v
                         L4 COURSE-IMPROVEMENT LOOP
                                  |
                         professor-reviewed proposal

All planes ------------------> EVALUATION / TRACE PLANE
```

LangGraph owns bounded request/decision graphs. The database, scheduler, event
ledger, and transactional outbox own asynchronous time and exactly-once side
effects. There is no perpetual LLM process.

## L1 turn graph

```text
authenticate_and_bind
        |
        v
hard_policy_prefilter
        |
        v
perceive_turn (LLM structured proposal + deterministic observations)
        |
        v
merge_action_constraints
        |
        +--> refuse / clarify / abstain -------------------------+
        |                                                        |
        v                                                        |
plan_retrieval --> retrieve --> evidence_gate                    |
                                      |                           |
                                      +--> clarify / abstain -----+
                                      |
                                      v
                              plan_pedagogy
                                      |
                                      v
                              generate_grounded
                                      |
                                      v
                                  validate
                              pass /       \ fail
                                  /         \
                           finalize       repair once
                                              |
                                           revalidate
                                         pass /    \ fail
                                             /      \
                                      finalize    fallback
                                             \      /
                                              v    v
                                           atomic_commit
```

### Node ownership

| Node | Model role | Deterministic authority |
| --- | --- | --- |
| `authenticate_and_bind` | None | Identity, membership, course, release, profile, policy, and source permissions |
| `hard_policy_prefilter` | None | Explicit integrity, permission, unsupported-future, cross-course, rate, and operational rules |
| `perceive_turn` | Infer concepts, student attempt, possible misconception, confusion, ambiguity, and evidence needs | Validate schema; label observed versus inferred fields; reject prohibited traits and invalid provenance |
| `merge_action_constraints` | Suggest candidate actions with confidence | Choose the most restrictive valid action; model confidence cannot weaken a hard rule |
| `plan_retrieval` | Produce bounded query variants and evidence requirements | Permit only course-scoped read tools and cap query/tool counts |
| `retrieve` | None by default | Execute selected retrieval profile and canonical source-range mapping |
| `evidence_gate` | Optional advisory relevance signal | Decide uniqueness, completeness, freshness, permission, and claim coverage |
| `plan_pedagogy` | Propose one intent, help level, next activity, and learner-state delta | Enforce professor profile, integrity ceiling, transition vocabulary, and help ladder |
| `generate_grounded` | Produce the student-facing response, atomic claims, and citation IDs | Supply only approved evidence and accept only the typed response contract |
| `validate` | None for hard gates; optional offline advisory review | Verify action, claims, citations, policy, profile, privacy, and output limits |
| `repair` | Correct the enumerated contract violations | One attempt only; cannot retrieve new evidence, change action authority, or expand scope |
| `atomic_commit` | None | Revision check, idempotent response/state event, learning-gap signal, trace, and outbox transaction |

## Action lattice

The final action is not a majority vote. Hard constraints take precedence:

```text
security/operational failure
        > refuse (policy or integrity)
        > clarify (multiple plausible interpretations)
        > abstain (insufficient or unauthorized evidence)
        > answer (all gates satisfied)
```

The lattice directly addresses Program 011's severe boundary failure, where
433 of 500 explicit graded-work requests were answered instead of refused.
A more capable generator cannot correct an upstream action-authority defect.

## Typed model contracts

### `TurnPerceptionV2`

- observed request form and explicit student statements;
- inferred concepts, attempt, misconception hypotheses, confusion, and
  confidence;
- ambiguity candidates and missing information;
- academic-integrity and policy-sensitive indicators;
- required evidence concepts and proposed retrieval queries;
- candidate actions and confidence;
- provenance for every observation and hypothesis.

### `PedagogicalPlanV2`

- selected objective and target concept;
- one intent from the approved vocabulary;
- help level and integrity ceiling;
- expected learner action;
- evidence requirements;
- proposed `LearnerStateDeltaV2`;
- explicit completion and stopping condition.

### `LearnerStateDeltaV2`

- observation additions;
- hypothesis additions, confirmations, retractions, confidence, and expiry;
- objective/step progress proposal;
- help-level and next-activity proposal;
- supporting turn and evidence IDs;
- base state revision.

### `GroundedTutorResponseV2`

- terminal action;
- student-facing text;
- atomic claims and canonical citation IDs;
- next activity or clarification request;
- applied intent and help level;
- compact reason codes, not hidden chain-of-thought.

### `AgentTraceV2`

- immutable system, dataset, code, release, profile, policy, prompt, schema,
  model, and retrieval identities;
- node inputs/outputs in sanitized structured form;
- query, evidence, claim, citation, action, validation, repair, and fallback
  lineage;
- proposed and accepted state deltas;
- persistence revision and side-effect IDs;
- latency, tokens, cost, provider status, and restart lineage.

## L2 learner-control loop

The learner model is an evidence ledger, not a personality profile. It may
contain:

- published learning objective and current step;
- student-produced claims or attempts observed in the conversation;
- source-linked concepts demonstrated or not yet demonstrated;
- bounded misconception hypotheses;
- explicit confidence/confusion statements;
- help-level history and prior tutoring intents;
- next planned activity and expiry.

It must not infer or store protected traits, mental-health state, laziness,
motivation, general intelligence, disciplinary risk, or hidden grades. A single
model observation cannot establish mastery. Hypotheses decay or expire unless
confirmed by new evidence.

## L3 proactive loop

The proactive loop consumes durable opportunities, not the raw conversation:

```text
event/schedule
    -> candidate ledger
    -> deterministic eligibility and availability
    -> no action OR bounded intervention proposal
    -> retrieve current approved evidence
    -> compose and validate
    -> transactional outbox
    -> private in-app delivery
    -> outcome event
```

The model never chooses arbitrary recipients, channels, times, or goals. A0
professor/student schedules remain the control. A1 objective event triggers and
A2 bounded learner-state triggers must pass separate shadow evaluations before
promotion. Discord and other external channels remain independent adapters.

## L4 governance and improvement loop

Privacy-minimized, course/release-scoped signals may be aggregated only above
the configured cohort threshold. A model may draft a learning-gap explanation,
source proposal, profile change, or outreach-policy change. The professor must
review and approve a new immutable version before it can affect students.

The Digital Twin represents an approved configuration of the professor's
teaching policy. It must not claim to literally be the professor, infer a
reference profile without approval, or silently learn a new live policy from
student interactions.

## Failure, resume, and side-effect rules

- Every node is deterministic for the same persisted input, or records the
  exact model/configuration identity that makes it replayable as evidence.
- Provider failures produce a safe fallback and do not advance learner state.
- A stale state revision fails the commit and re-enters at the application
  request boundary; it does not ask the model to reconcile database state.
- Side-effect nodes are idempotent and keyed by course, release, student,
  opportunity, and policy version.
- Interrupts occur only before consequential professor/governance actions or
  externally visible side effects that require review.
- Restart resumes from a durable checkpoint and never repeats a committed
  student turn or delivery.
- Recursion, tool, token, latency, and cost limits are explicit graph inputs and
  terminal trace fields.

## Evaluation design

### Conditions

| Condition | Purpose |
| --- | --- |
| T0 | Grounded, non-adaptive assistant and release rollback |
| T1-v1 | Current deterministic interpreter/intent graph; historical control |
| T1-v2 | Same evidence and generator with LLM perception/planning plus deterministic authority |
| C0 | Generic assistant without course grounding or professor policy |
| C1 | Course-grounded assistant with generic tutoring policy |
| C2 | Same evidence plus approved professor profile |
| C3 | Retrieved evidence, approved professor profile, and the complete product loop |

T0/T1 comparisons keep questions, releases, evidence, generator, decoding, and
hard policy fixed. C0-C3 measures professor-policy effects separately and only
after the professor approves the reference profile.

### Evaluation layers

1. Contract and state-machine tests.
2. Node evaluations with planted perception, routing, evidence, plan,
   generation, and commit defects.
3. Source-linked single-turn grounding and boundary evaluation.
4. Multi-turn trajectory evaluation, including goal changes and repeated
   seeded runs.
5. Proactive opportunity and suppression evaluation in shadow mode.
6. C0-C3 profile/fidelity evaluation.
7. Whole-product failure, restart, backup/restore, and rollback journeys.
8. Professor calibration and consented student usability/learning studies.

### Study design and analysis unit

Every run freezes the decision question, prediction, baseline, population,
eligibility and exclusions, sample-size rationale, primary metrics, gates,
comparison estimand, random seeds, and stopping rule before opening outputs.

Turns are not treated as independent observations. Factual estimates cluster by
source region/family; tutoring estimates cluster by trajectory and learner
persona; proactive estimates cluster by learner/concept/opportunity; C0-C3 uses
paired cases. Report exact numerators and denominators, paired effects, and
cluster-aware confidence intervals. Post-hoc slices and alternative evidence
matching are diagnostic and cannot retroactively select a method.

Simulated learners test control behavior but cannot establish real usability,
engagement, fidelity, or learning. After an evaluation set influences the
implementation, it becomes a known regression set. A fresh source- and
trajectory-disjoint sealed tranche is required for a new confirmatory claim.

### Dataset integrity gates

- unique case, trajectory, turn, event, condition, source, and trace IDs;
- complete source/release/profile/policy hashes and foreign-key coverage;
- frozen slice quotas with no silent exclusion or rebalance;
- no development/sealed source-region or trajectory overlap;
- no target, expected action, hidden policy, or future-state leakage into the
  runtime boundary;
- exact and near-duplicate diagnostics at question and trajectory level;
- all responses durable before hidden labels or scoring code can open;
- final repository/outbox state reconciled with every terminal trace.

### Hard gates

- zero unsupported severe releases, permission violations, cross-course
  disclosures, invalid source versions, or model-owned authoritative mutations;
- 100% correct academic-integrity refusal for explicit frozen cases;
- 100% valid citations for released academic claims;
- 100% safe fallback for forced provider, retrieval, validation, and commit
  failures;
- 100% restart consistency, idempotent commits, and duplicate prevention;
- 100% consent, quiet-hour, withdrawal, frequency, destination, and release
  enforcement for proactive effects;
- at least 95% valid pedagogical transitions on the frozen trajectory set;
- no material factual-grounding regression from T0;
- complete trace, identity, token, latency, cost, and persistence accounting.

Safety gates apply to every repeated run. Soft pedagogical measures cannot
compensate for a hard-gate failure.

### Pedagogical measures

Adapt the MRBench dimensions rather than relying on generic answer-quality
scores:

- mistake identification and location;
- avoidance of premature answer revealing;
- guidance quality and actionability;
- coherence with the student's prior turn and current plan;
- help-level appropriateness;
- misconception repair;
- professor-profile adherence;
- supportive but non-impersonating tone.

Add trajectory measures for objective progress, productive student action,
state calibration, repeated-run consistency, recovery after confusion, and
unnecessary-help rate. LLM judges remain advisory until calibrated against
professor or human labels for this exact rubric.

### Failure taxonomy

Every failure is assigned to one primary boundary:

`binding`, `perception`, `action-routing`, `retrieval`, `evidence-gate`,
`pedagogical-plan`, `generation`, `claim-validation`, `citation-validation`,
`state-delta`, `commit`, `proactive-eligibility`, `delivery`, `provider`, or
`evaluation-harness`.

This prevents a generator swap from being used to treat an upstream routing or
evidence defect.

## Finite implementation path

1. Complete #153's deterministic action/evidence boundary against fresh data.
2. Introduce `TurnPerceptionV2`, `PedagogicalPlanV2`, and
   `LearnerStateDeltaV2` behind provider-neutral interfaces.
3. Add deterministic constraint merging and observation/hypothesis validation.
4. Add `AgentTraceV2`, durable graph checkpoints, atomic state commits, and
   replay tests.
5. Integrate the selected generator and the one-repair response path.
6. Run prospective T0/T1-v1/T1-v2 node, turn, trajectory, and repeated-run
   evaluations.
7. Evaluate A1/A2 in shadow mode and promote only an eligible passing policy.
8. Obtain professor profile approval and run C0-C3.
9. Run whole-product and human stages without broadening the earlier claims.

A valid quality failure stops the affected promotion and produces one
method-level decision. It does not trigger another prompt-only loop or modify a
known evaluation set.
