# Successor autonomy architecture tournament plan

Date: 2026-09-02

Program: `successor-architecture-paired-comparison-001`

Owner: issue #184; parent release issue #8.

## Decision question

Does hierarchical candidate C improve pedagogical action quality, learner-state
calibration, long-horizon intervention efficiency, and proactive precision over
single-planner B, and does B improve over deterministic A, while every
deterministic safety gate passes and cost remains justified?

## One-factor implementation

The candidates are configurations of one runtime:

| Condition | Planner | Lookahead | Added mechanism |
| --- | --- | ---: | --- |
| A | disabled | 0 | deterministic event workflow |
| B | one typed proposal | 0 | bounded semantic move selection |
| C | same proposal | 2 | analytic forward-model comparison |
| C+V | same as C | 2 | reject-only verifier |

Every condition uses the same action envelope, professor policy, evidence and
citation authority, consent/timing limits, commit-then-relay delivery,
injectable clock, and T0 rollback. A model cannot mutate identity, policy,
source lineage, learner state, persistence, or delivery.

## Engine factor

Architecture is compared with a fixed engine first. The best two architectures
then run under the same four economical allocations:

- E1: Luna planner / Luna generator;
- E2: Terra planner / Luna generator;
- E3: Luna planner / GPT-5.4 Mini generator;
- E4: Terra planner / GPT-5.4 Mini generator.

The active comparison excludes Sol, Gemma, Claude, DeepSeek, OpenRouter
routing, and retired local general models. GPT-5.4 Nano may be used only for
ranking, classification, extraction, or advisory audit outside the product
engine factor.

## Finite progression

1. Close all common audit defects before comparison.
2. Pass network-free runtime conformance.
3. Use three source-disjoint development folds for at most three coherent
   improvement rounds.
4. Freeze the best valid architecture and engine allocation.
5. Execute one fresh 1,000-case confirmation.
6. Execute the labelled known 10,000+1,000 factual regression.
7. Execute the 820-case actual-product autonomy portfolio.
8. Complete local product and browser qualification.
9. Record Keep, Refine, Redesign, or No Release.

No valid quality result is rerun on the same confirmation set. Every build,
invalid execution, unfavorable result, and final decision receives a stable
record, readable summary, registry entry, hashes, accounting, limitations, and
GitHub checkpoint.

## Primary analysis

- acceptable pedagogical move: paired McNemar;
- hidden learner-state accuracy: Brier score and calibration error;
- wasted intervention and follow-up rates: paired cluster bootstrap;
- proactive precision at fixed recall;
- cost and latency per acceptable move;
- zero-failure safety gates with one-sided exact confidence bounds.

Candidate C is selected over B only when it wins at least three of the four
pre-registered quality dimensions with lower confidence bounds above zero,
loses none, passes both simulator families and every tested engine allocation,
and costs no more than 1.5 times B per acceptable move. The same rule applies
to B over A. C+V is retained only when its defect reduction is larger than its
added cost and latency.

## Claim boundary

The LLM-only panel may support claims about bounded autonomy, grounding,
formal profile adherence, simulated learner utility, and software reliability
under the recorded conditions. It does not establish real-professor identity,
real-student usability, or real-world learning improvement.
