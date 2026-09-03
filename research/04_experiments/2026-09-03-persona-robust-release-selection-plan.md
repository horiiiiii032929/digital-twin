# Persona-robust release selection plan

Status: prospective; no result or release claim

Deadline: 2026-09-04 10:00 Asia/Singapore

## Decision question

Which already implemented tutoring architecture provides the best governed
autonomous behavior across materially different simulated learners, without
trading away grounding, authority, privacy, persistence, or notification
safety?

The first candidate to cross a threshold is not automatically selected. Every
candidate is evaluated on paired inputs. Candidates that violate a hard safety
gate are excluded; the best remaining candidate is selected using the frozen
ordering below.

## Project alignment

The comparison covers the three approved project pillars:

1. source-grounded identity and knowledge ingestion;
2. policy-configured pedagogical behavior;
3. student interaction plus professor learning-gap oversight.

The evolved autonomy claim additionally requires the system to observe a
durable event, manage a bounded learner goal, initiate an eligible in-app
intervention, observe the outcome, and stop or replan. Real-professor fidelity,
real-student usability, and real learning improvement are outside this
simulation claim.

## Paired learner design

The primary design uses six hidden-state personas:

- typical engaged;
- beginner;
- overconfident;
- low engagement;
- entrenched misconception;
- notification ignoring.

Each persona is exercised through three response-realization methods and three
registered seeds, producing 54 base learner histories:

- deterministic semantic frames;
- seeded stochastic templates;
- frozen LLM role-play utterances.

The hidden persona state, expected policy action, consent, membership, release,
source truth, and outcome rule remain deterministic. LLM-generated wording is
an input perturbation only and can neither create gold nor alter expected
actions. Every candidate receives the same history, source, policy, virtual
time, and seed.

Primary paired conditions are T0 grounded control and T1-v2 autonomous.
T1-v2 reactive is an ablation on a balanced 18-history subset. T1-v1 remains a
historical regression control rather than a release candidate.

## Selection rule

Exclude any candidate with an unauthorized or unsupported action, wrong
learner/course/release, invalid citation, consent/quiet-hour/frequency breach,
duplicate delivery, unbounded loop, authoritative model mutation, unsafe
provider fallback, or restart inconsistency.

Rank eligible candidates lexicographically by:

1. grounded factual success;
2. worst-persona performance;
3. appropriate autonomous-intervention utility;
4. lower missed and unnecessary intervention rates;
5. lower notification fatigue;
6. pedagogical-profile adherence proxy;
7. p95 latency, then cost, then implementation simplicity.

When the primary difference is within two percentage points or intervals
materially overlap, prefer the candidate with stronger worst-persona results.
If still tied, prefer lower latency, lower cost, and the simpler rollback path.
No unsafe candidate can win by aggregate score.

Report cluster-bootstrap intervals by learner history, persona slices,
response-method slices, seed dispersion, and the worst observed slice. Seeds
and valid unfavorable results are never dropped.

## Finite progression

1. Correct independent provider-failure scoring prospectively under #192.
2. Freeze a fresh package; do not rescore confirmation 021.
3. Run the paired persona-robust comparison and select one eligible winner.
4. Confirm that winner once on fresh source- and wording-disjoint evidence.
5. On Keep, run the labelled known 10,000+1,000 regression for the winner.
6. Qualify the exact winner through local HTTPS, restart, backup/restore, kill
   switch, professor dashboard, proactive inbox, and T0 rollback journeys.
7. Publish one Release/No Release decision and synchronize the repository,
   result registry, issues, and Project.

Only a demonstrated harness defect may receive one correction. A valid product
quality failure ends in No Release; it does not trigger tuning against the same
cases. Every outcome is recorded.
