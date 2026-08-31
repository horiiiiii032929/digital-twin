# Whole-system causal audit

Date: 2026-09-01

Program: `course-digital-twin-whole-system-architecture-evolution-001`

Status: initial evidence synthesis; no candidate selection

## Executive finding

The repository contains a substantially implemented governed-autonomy product,
but its strongest software evidence and its strongest academic evidence point
in different directions.

- V2.1 passes network-free service, persistence, restart, timing, policy, and
  820-case harness checks.
- The minimal live provider integration passed, but it was too small to support
  promotion.
- Program 011 completed the actual T0 product on 10,000 candidate and 1,000
  paired control cases without gold leakage and produced a valid `Refine`.
- The factual candidate reached 44.16% fully grounded success, 88.19% overall
  action accuracy, 72.90% boundary action accuracy, 46.43% claim precision and
  recall, 67.75% citation recall, and 478 severe unsupported releases. It
  answered 433/500 explicit graded-work requests.

The primary problem is therefore not missing autonomous plumbing. It is the
contract between action selection, complete evidence, atomic claims, and
generation. Provider-backed autonomy remains blocked until that contract has a
valid fresh pass.

## Causal map

| Plane | Existing evidence | Classification | Current decision | Round 1 implication |
| --- | --- | --- | --- | --- |
| Domain | Versioned concepts, objectives, misconceptions, releases, and source ranges are implemented | Implementation largely complete; representative quality unconfirmed | Keep as baseline | Require every candidate to use the same release-bound domain contract |
| Retrieval | Program 011 candidate all-evidence@3 88.33% and Recall@5 93.29%; prior atomic-M2 retrieval passed on development | Method quality is close but incomplete and may not match question requirements | Refine | Compare evidence-requirement planning and source-range coverage, not another embedding leaderboard |
| Action routing | Program 011 boundary 72.90%; 433/500 integrity requests answered | Architecture defect at the pre-generation authority boundary | Replace | Action must become authoritative before retrieval/generation; semantic ambiguity may only tighten the action |
| Claim/citation | Claim precision/recall 46.43%; citation recall 67.75% | Architecture defect between evidence and generated answer | Replace | Build an explicit bounded claim plan from canonical ranges before wording |
| Learner state | V2 observation, attribution, deterministic belief revision, uncertainty, and persistence are implemented | Software complete; calibration quality unconfirmed | Keep as baseline / Go Deeper | Compare only when autonomy evidence identifies a learner-state failure |
| Pedagogical policy | Versioned plans, help level, integrity ceiling, and bounded semantic proposals exist | Method quality unconfirmed | Compare | Keep policy authority deterministic; compare pedagogical selection separately from language quality |
| Reactive loop | Independent V2 graph, one repair, fallback, checkpoint, and atomic commit pass network-free checks | Software complete; provider-backed quality blocked | Keep as baseline | All candidates retain finite termination and T0 rollback |
| Proactive loop | Due opportunity can deliver once without a student turn; consent, timing, deduplication, restart, and outbox pass network-free | Software complete; representative usefulness unconfirmed | Keep as baseline / Go Deeper | Evaluate action usefulness and timing only after grounding passes |
| Governance | Identity, membership, release, policy, consent, budgets, delivery, kill switch, and rollback remain code-owned | Strong architecture evidence | Keep | No candidate may grant an LLM mutation authority |
| Persistence | SQLite WAL, node checkpoints, request ledger, outbox, lease, idempotency, backup/restore are implemented | Strong software evidence | Keep | Event-sourced challenger must meet or exceed exact restart semantics |
| Product experience | Professor governance and student conversation/inbox flows exist; prior desktop/mobile walkthrough passed | Integration evidence exists; final candidate UX unqualified | Refine after architecture selection | Avoid redesigning screens before final control and state contracts settle |
| Operations | Docker, local HTTPS, logs, budgets, rollback, and verification exist | Local qualification only | Keep as baseline / requalify | Rebuild immutable images and rerun release journeys for the selected winner |
| Evaluation | Flow-independent factual/autonomy adapters, VirtualUtcClock, hidden gold, and registries exist | Strong boundary; historical run orchestration has several invalid attempts | Refine | New program schema requires a terminal record before every progression |

## Failure dependency chain

```text
boundary misclassification
  -> answer route remains open
  -> retrieval is asked to support an action that should not occur
  -> incomplete or mismatched evidence reaches generation
  -> model creates unsupported/overbroad claims
  -> citations cannot cover all claims
  -> factual hard gates fail
  -> provider-backed autonomy and proactive pedagogy remain blocked
```

This chain explains why changing only the model, prompt, embedding, or reviewer
is not a sufficient successor.

## Round 1 architecture hypotheses

### A. V2.1 bounded single graph

Retain the current product unchanged as the control. This gives the strongest
governance, persistence, and rollback evidence, but the historical factual path
is not selected.

### B. Evidence-first hierarchical architecture

Separate authoritative action, evidence requirements, retrieval, source-range
coverage, bounded atomic claim planning, pedagogical realization, and wording.
Generation cannot create a claim or citation absent from the accepted plan.

Prediction: this should address the dominant Program 011 causal chain while
preserving the existing governance and persistence planes.

### C. Event-sourced plan-observe architecture

Make goal, observation, plan, action, outcome, and replan explicit durable
objects. Reuse the evidence-first action contract for every reactive and
proactive intervention.

Prediction: this may improve long-horizon autonomy and learning-utility proxy
results, but it cannot compensate for a failing factual boundary.

### D. Optional distinct challenger

A fourth candidate is allowed only when further audit identifies a distinct
whole-system hypothesis. A model-only, prompt-only, threshold-only, or reviewer
swap does not qualify as an architecture candidate.

## Evidence gaps before Round 1

1. Construct and hash three source-disjoint 500+100 development folds.
2. Define the evidence-first and event-sourced candidate manifests without
   implementation-specific gold.
3. Freeze common hard gates, model/provider roles, latency/cost accounting, and
   complexity measurements.
4. Add non-human profile reviewer controls and hidden-state learner simulator
   contracts.
5. Keep the fresh 1,000-case package unconstructed or cryptographically sealed
   until the Round 3 winner is immutable.

## Current conclusion

Record `Go Deeper`. Preserve V2.1 as the software baseline and rollback. Start
Round 1 with the evidence-first architecture as the primary challenger and the
event-sourced plan-observe architecture as the autonomy challenger. Do not run
provider-backed autonomy or reopen Program 011 as fresh evidence before a
source-disjoint factual development pass.
