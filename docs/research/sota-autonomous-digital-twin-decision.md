# Architecture decision: prospective successor for the autonomous Digital Twin

Date: 2026-09-02

Decision ID: `sota-autonomous-digital-twin-decision-001`

Status: independent recommendation for a prospective successor; not an
accepted decision, not a release selection, and not an authorization for any
provider, paid, private-data, human-study, or release activity; requires the
experiment in section 6 before adoption

Implementation checkpoint (2026-09-02): the shared switchable A/B/C runtime and
the C+V reject-only ablation are now implemented prospectively under issue
#184 and draft PR #185. This changes the recommendation from design-only to
build-ready; it does not select candidate C or authorize a provider run.

Companion documents:

- [Independent study](sota-autonomous-digital-twin-independent-study.md)
  (audit, sources, candidate architectures, full successor definition)
- [Flow-independent evaluation design](sota-autonomous-digital-twin-evaluation-design.md)

## 1. Recommendation

Adopt candidate C from the study, the hierarchical, model-based governed
planner, as the prospective successor, implemented so that candidate B (the
governed single planner) is C with lookahead depth zero and candidate A (the
deterministic workflow) is B with the planner disabled. Retain the current
grounding chain, action lattice, exactly-once mechanisms, lineage pinning,
cascade cancellation, injectable clock, and the two existing evaluation
contracts unchanged. Do not adopt a multi-agent design; run the verifier step
from candidate D only as a test.

The recommendation is conditional. It stands only if the experiment in
section 6 shows that C beats B on the primary metrics with its cost inside the
budget. If C does not beat B, B is the successor. If B does not beat A, the
current deterministic configuration cleaned up as A is the successor, and the
planner is not earned.

## 2. Why it is preferable to the current design

The current T1-v2.1 design has a sound authority model and sound exactly-once
mechanics, and the study keeps both. What it lacks is structural, not
incremental:

1. Its learner model is count based, keyed by conversation, never calibrated,
   never decays, and overwrites hypotheses each turn (study section 2.3). The
   successor uses a per-learner calibrated estimator with decay and a
   hypothesis ledger, selected by measured calibration.
2. Its policy never reads outcomes; wake-ups are a constant +24 h and windows
   are constants (study section 2.2, 2.4). The successor replans on closed
   predicates and chooses proactive contact by expected effect against
   `no action`.
3. It has no forward model, so goal selection and proactive ranking cannot be
   value based (study section 2.9). The successor adds one behind an interface
   with an analytic default.
4. It carries two learner models, three action vocabularies, two proactive
   stacks, and three eligibility layers (study section 2.9). The successor has
   one event stream, one move enum, one opportunity ledger, and one eligibility
   function.
5. It delivers before it commits and has no global kill switch (study section
   2.2, 2.5). The successor commits then relays through an outbox and adds a
   process-level and database-level switch.
6. Its engine allowlist is single-vendor and its prompts are unhashed labels
   (study section 2.8). The successor's task registry makes swaps a profile
   change and prompts content-addressed.

The evidence base for these choices is primary (study section 3): interleaved
observe-act loops and conditional replanning beat always-on or act-only
loops; external verification beats self-critique; multi-agent designs hurt on
sequential tool-heavy decisions; calibrated small-data estimators outperform
deep tracing for new learners; answer-withholding is a learning requirement;
and nudges have a prior near zero effect, which is why proactive contact must
clear a margin over `no action`.

## 3. Decision matrix

Scores are the author's structural judgments on a 1 to 5 scale before any
experiment; they are hypotheses for the experiment to overturn, not results.
Weights reflect the scope authority's priority order (professor fidelity,
pedagogy and misconception handling, evaluation-before-publication,
evidence-complete grounding, reliable workflows) with safety as a gate rather
than a weighted item.

| Criterion (weight) | T1-v2.1 as built | A deterministic | B single planner | C hierarchical | D multi-agent |
| --- | --- | --- | --- | --- | --- |
| Safety gates (gate) | pass with two defects | pass | pass | pass | pass, more surface |
| Professor-profile adherence (5) | 2: hash only, no checks | 3: checkable envelope, fixed moves | 4: envelope plus planner within it | 4 | 4 |
| Pedagogical action quality (5) | 2: decision table | 2 | 4: typed move from state card | 4 to 5: plus lookahead | 4 to 5, unverified |
| Learner-state calibration (4) | 1: counts | 2: counts with decay | 4: calibrated estimator | 4 | 4 |
| Long-horizon goal management (4) | 2: constant timing | 2 | 3: conditional replanning | 5: value-based selection | 5 |
| Proactive quality and timing (4) | 2: trigger match | 2 | 3 | 4: expected-effect margin | 4 |
| Grounding (gate plus 3) | 4 | 4 | 4 | 4 | 4 |
| Restart and idempotency (gate plus 3) | 3: ordering defect | 5 | 5 | 5 | 4: more calls to journal |
| Cost per decision (3) | 4 | 5 | 3 | 3: episode call amortised | 1 |
| Implementation effort (3) | n/a | 5 | 3 | 2 | 1 |
| Operational complexity (3) | 2 | 5 | 4 | 3 | 1 |
| Evaluability (4) | 3 | 5 | 4 | 4 | 2 |
| Weighted total (max 5) | 2.5 | 3.5 | 3.8 | 4.0 | 3.3 |

The margin between B and C is small and rests on two rows (long-horizon and
proactive) whose scores depend on the forward model being well calibrated.
That is exactly what the experiment tests.

## 4. Causal failure hypotheses

Each hypothesis names a mechanism, the observable that would confirm it, and
the design element that addresses it.

| Hypothesis | If true, we would observe | Addressed by |
| --- | --- | --- |
| H1. Count-based belief misroutes help: mastery is over-estimated after one lucky attempt or under-estimated after one confusion signal | Brier and calibration error far above the estimator baseline; wasted-intervention rate high; help level oscillates | Calibrated estimator, decay, hypothesis ledger |
| H2. Constant timing wastes budget: interventions land when the learner is inactive or already at mastery | Low assessed-follow-up fraction; high wasted-intervention rate; frequency budget exhausted early in the seven-day window | Replan predicates; value margin over no action |
| H3. Greedy move choice over-helps: the planner picks the most helpful eligible move rather than the one that produces an attempt | Help-ladder violations at the deterministic check; answer-ceiling near-misses; fewer assessed observations per intervention | Envelope enforcement; forward-model preference for moves that elicit observations |
| H4. The forward model is mis-calibrated and confidently wrong | C worse than B on wasted interventions while reporting higher expected effect | Depth-zero switch; calibration reported separately; analytic default |
| H5. Per-conversation belief fragments the learner | Second-conversation cold-start error equals first-conversation error | Per-learner keying |
| H6. Delivery-before-commit produces phantom outcomes | Attempt counts below delivered counts after injected crashes | Commit then relay |
| H7. A single vendor allowlist hides engine effects | Architecture ranking flips between engines | Registry; every claim tested on two engines |
| H8. A verifier agent adds cost without reducing defects | C+V defect rate within the confidence interval of C at higher cost | D defined as a test with a stopping rule |
| H9. Lexical grounding under-serves paraphrased evidence | Abstain rate high on paraphrase cases that a semantic gate would answer correctly, with no unsupported claims | Kept lexical; semantic gate as a separate candidate |

## 5. Predicted advantages and risks

Predicted advantages of C over T1-v2.1, in the order they should show up:

1. Restart and duplication defects go to zero, including the crash window
   between delivery and commit.
2. Learner-state calibration improves from uncalibrated to measurably
   calibrated against both simulator families.
3. Wasted-intervention rate and frequency-budget exhaustion fall.
4. Acceptable-move rate rises with no change in safety-gate outcomes.
5. Cost per acceptable move stays within 1.5 times B's because the episode
   call is amortised and the fast path handles most turns.

Risks, with the mitigation built into the design:

- Over-engineering: C may not beat B. Mitigated by the depth-zero switch and
  the requirement that C beat B before adoption.
- Calibration to the wrong simulator: the estimator could be tuned to the
  simulator's transition model. Mitigated by two simulator families and by
  reporting agreement between them.
- Migration risk: the event-sourced store touches every table. Mitigated by
  the staged plan in section 7, which keeps the current tables as the write
  model until projections are proven equal.
- Provider dependence: a frontier episode planner may be unavailable or
  change. Mitigated by the registry and the deterministic template fallback.
- Regulatory exposure: an autonomous twin that assesses and steers learning is
  plausibly high-risk under the EU AI Act Annex III(3)(b). Mitigated by
  professor authority over policy, learner-visible explanations and opt-out,
  and by keeping learning-outcome claims out of scope until a human study.

## 6. Exact experiment required before adoption

Name: `successor-architecture-paired-comparison-001` (proposed).

Decision question: does C beat B, and does B beat A, on the primary metrics
under identical grounding, policy, engines, and simulator, with cost inside
budget and every hard gate passed?

Conditions: A, B, C, C+V, T1-v2.1 (deterministic and live), T0; oracle and
never-intervene bounds from the simulator.

Engines: for each of A to C+V, two allocations from different providers at
the same tier per role (study section 3.9), plus the deterministic
configuration. Same allocations across candidates.

Fixture: one sealed course fixture from an approved corpus; six personas;
two simulator families; fresh seeds; development folds for building, one
sealed confirmation tranche opened once.

Primary metrics, pre-registered:

- pedagogy: acceptable-move rate on the frozen move set (paired, McNemar);
- learner state: Brier score against hidden mastery at day 30 (paired
  bootstrap over trajectories);
- long horizon: wasted-intervention rate over 30 days (paired bootstrap);
- proactive: precision of `proactive_message` against hidden need at fixed
  recall, and zero timing violations (gate);
- cost: cost per acceptable move (descriptive, with a ceiling as a gate).

Minimum effects of interest: 5 points on acceptable-move rate; 0.02 Brier;
5 points on wasted-intervention rate; 5 points on proactive precision. Sample:
on the order of 300 tutoring trajectories, 100 thirty-day learners, and 200
proactive opportunities per condition per engine, sized from the paired
binary power calculation in the evaluation design.

Hard gates on every condition: all gates in evaluation-design sections 3.1,
3.2, 3.3, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10. A failed gate excludes the condition
from ranking regardless of soft scores.

Decision rule: adopt C if C beats B on at least three of the four primary
quality metrics with the lower confidence bound above zero, loses on none,
passes every gate, and costs no more than 1.5 times B per acceptable move,
for both engines. Otherwise adopt B by the same rule against A. Otherwise A.
C+V replaces C only if it reduces the pedagogy or safety defect rate by more
than its cost ratio, again for both engines.

Smallest fair experiment that can reject each alternative:

| Alternative | Rejecting experiment |
| --- | --- |
| A over B | 300 paired tutoring trajectories: if B's acceptable-move rate does not exceed A's by 5 points with a lower bound above zero, the planner is not earned |
| B over C | 100 paired thirty-day learners: if C's wasted-intervention rate and Brier do not improve on B's, the forward model is not earned |
| C over C+V | 300 paired proposals through the verifier: if the defect rate does not fall by more than the cost ratio, the verifier is rejected |
| Any candidate over T1-v2.1 | The same runs include T1-v2.1; a candidate that does not beat it on pedagogy and long horizon while matching its gates is rejected |
| Lexical grounding over semantic | Separate: 500 paraphrase cases; the semantic gate must add zero unsupported claims while lowering abstain rate |

## 7. Migration plan from the current implementation

Staged so that every stage is independently evaluable and reversible by one
setting, and so that T0 remains the rollback throughout.

1. Stabilise (no behaviour change). Fix the delivery-before-commit ordering
   by moving commit before delivery and adding an outbox relay; add the global
   kill switch; construct the claim validator for every mode; hash prompts;
   apply the model-call ledger to deterministic engines too. Verify with the
   restart and duplication suite.
2. Unify vocabularies. Introduce the single move enum and the single
   eligibility function; map the three existing vocabularies onto them with
   explicit tables; delete nothing yet. Verify with contract tests and the
   adapter conformance suite.
3. Event stream and projections. Add the append-only event table; write every
   existing producer to it alongside current tables; build belief, goal, and
   opportunity projections keyed by learner and course; run projections in
   shadow and assert equality with current rows for thirty virtual days.
4. Estimator and calibration. Add the estimator interface with counts as
   the first implementation (equal to today), then BKT and PFA; select by the
   calibration dimension against both simulator families.
5. Candidate A. Switch the write model to projections; disable the planner;
   run the paired experiment's A arm.
6. Candidate B. Add the state card, the typed turn planner, the policy
   envelope compiler, replan predicates, and the registry; run the B arm.
7. Candidate C. Add the forward model interface with the analytic default,
   the episode planner, and value-based selection; run the C arm and the C+V
   test.
8. Decommission. Remove the v1 learner model, the A0 trigger laundering path,
   the duplicate helpers, and the pseudo-nodes, only after the chosen
   candidate passes confirmation.

Components retained unchanged: the grounding chain (retrieval, evidence gate,
citation validation, claim validation, release binding, permission lineage);
the action lattice; the v2.1 invariants; the model-call ledger pattern; the
lease and idempotency-key scheme; cascade cancellation; the injectable clock;
the two evaluation contracts and independent scorers; the professor
publication and rollback services; account, membership, and consent models.

## 8. Estimated effort, runtime cost, and operational complexity

Effort is in engineer-weeks for one experienced engineer familiar with the
repository, excluding the evaluation-framework additions, which are estimated
separately.

| Item | Effort | Runtime cost | Operational complexity |
| --- | --- | --- | --- |
| Stage 1 stabilise | 1 to 2 weeks | none | reduces (one relay, one switch) |
| Stage 2 vocabularies | 1 week | none | reduces |
| Stage 3 event stream and projections | 3 to 4 weeks | storage only | adds one table family and a rebuild command; removes mutable-row races |
| Stage 4 estimator | 1 to 2 weeks | none (analytic) | none |
| Candidate A | 1 week | 0 to 1 small-model call per delivered message | lowest |
| Candidate B | 3 to 4 weeks | 1 to 2 calls per tutoring turn; 1 per proactive decision; with caching and small-model wording, per-learner-day cost in the low cents range at the section 3.9 prices | one planner task to monitor |
| Candidate C | 3 to 4 weeks on top of B | adds 1 frontier or mid-tier call per episode (roughly one per goal per week per learner), batchable | forward-model version tracking; surprise thresholds to tune |
| Candidate D test | 1 week | 1 extra mid-tier call per proposal | discarded after the test unless it wins |
| Evaluation framework additions (simulator, calibration, adversarial suite, out-of-process adapter, statistics) | 4 to 6 weeks | judge-panel batch calls capped by manifest | run ledger and confirmation-opening ledger |

Total to a confirmed successor: roughly 18 to 26 engineer-weeks including
the evaluation additions, of which the first two stages are worth doing under
any outcome because they remove defects the audit found in code.

## 9. Evidence still missing

Addendum (2026-09-02, same branch): the first two items below now have a
simulated, network-free result in
[`successor-learner-timing-simulation-001`](../../research/05_evaluation/successor-learner-timing-simulation-001-results.md),
summarised in the
[implementation report](sota-autonomous-digital-twin-implementation-report.md).
It supports H1 and H2 within the simulator and does not change any claim
boundary in section 10.

- Any measured calibration of any learner estimator on this repository's
  data; today no instrument exercises the belief module. (Simulated evidence
  now exists; product-data evidence does not.)
- Any measured effect of proactive timing on assessed follow-up; today no
  outcome feeds back into timing. (Simulated evidence now exists.)
- Any comparison of the planner across two providers under identical
  conditions; today the allowlist is single-vendor.
- Any adversarial answer-leakage result beyond explicit graded-work cases.
- Any human label set for the pedagogy rubric large enough to calibrate a
  judge panel for this course family.
- Professor approval of a reference policy envelope for the fidelity contrast.
- Any human data on usability, engagement, or learning.

## 10. Claims that would and would not be academically defensible

Defensible after the experiment in section 6, stated as measured:

- Under identical grounding, policy, engines, and simulated learners, the
  chosen architecture achieved a higher acceptable-move rate, lower
  wasted-intervention rate, and better learner-state calibration than the
  current design, with confidence intervals reported, and passed all
  deterministic safety, integrity, restart, and timing gates.
- The architecture ranking held across two model providers.
- The successor removed the delivery-before-commit and per-conversation-belief
  defects found in code.
- The professor-policy envelope was enforced with 100% move compliance, as a
  formal-adherence result.

Not defensible from this work, and not to be claimed:

- That the twin improves student learning, engagement, or retention. That
  requires a consented human study with pre-registered outcomes.
- That the twin is faithful to the professor as a teacher. LLM-judge or
  property-check adherence to a formal profile is not fidelity; only the
  professor's blinded rating on a fixed set can speak to resemblance, and even
  that is perception, not teaching equivalence.
- That proactive messages help learners. The simulator's receptivity model is
  a hypothesis, and the field's large trials mostly found null effects.
- That any method is state of the art. The study reviews the literature; the
  repository's own rule that a method earns selection only through
  project-specific evidence against a shared baseline applies to every
  candidate here, including the recommended one.
- Usability or acceptability to students or professors, which no simulated
  run can establish.
