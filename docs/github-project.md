# Course Digital Twin Release

Project board: https://github.com/users/horiiiiii032929/projects/1

The board executes the
[release plan](release-plan.md) within the authoritative
[real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md).
Historical closed issues preserve the research and prototype record and are
archived from the live Project view; visible cards track only open product,
evaluation, and delivery work.

## Planning fields

- **Status:** Todo, In Progress, Done. Release goal #8 remains `In Progress` as
  the parent. Keep only one unblocked execution package in progress per
  independent track.
- **Decision:** Pending, Keep, Refine, Go Deeper, Drop.
- **Work Type:** Feature, Research, Design, Prototype, Documentation,
  Evaluation, Bug.
- **Area:** Instructor, Student, AI Agent, RAG, Analytics, Architecture,
  Documentation, Evaluation. GitHub labels add `area:multimodal` and
  `area:platform` where the older select field is too coarse.
- **Risk:** Low, Medium, High.
- **Evidence:** existing result, PR, revision, or limitation reference; never a
  promised result.
- **Sprint:** the active product phase and bounded work package.
- **Target Date:** prospective planning date, not a release claim.

Priority labels provide the critical path: `priority:p0` is work required next,
`priority:p1` is required for the release candidate, and `priority:p2` follows
the release-critical path.

## Active Sunday checkpoint

The local Sunday milestone is complete as `local-r1-release-qualification-001`
on immutable revision `c235e56`. The exact local images passed 24/24 clean HTTPS
journey checks, restart and clean-restore checks, and both the T0 rollback and
T1 restoration checks. #107, #132, and #134 are therefore `Done / Keep` for
their local R1 scopes. #88, #9, #25, and parent #8 remain open only for durable
hosting, target-host operations, and external workflow evidence. #105 remains
`Refine` because the four-model factual screen did not select an LLM path; the
qualified local release explicitly uses the deterministic fail-closed fallback
and makes no LLM-quality claim. #24 remains open because the synthetic demo
professor is not the fidelity reference.

Program 011 has completed the post-demo actual-product milestone in #127. All
10,000 candidate and 1,000 paired control responses were persisted before
hidden gold opened. The result is valid `Refine`, not another operational stop:
candidate grounded success was 44.16% with a source-family 95% interval of
41.03%–44.96%, boundary action accuracy was 72.9%, and 478 severe releases
occurred. It answered 433/500 explicit graded-work requests that required
refusal. The candidate beat the control comparatively, but both failed the
absolute release gates. Visual remains `Go Deeper` at 17/30 complete assets;
synthetic C0–C2 is not professor fidelity; provider-backed T0/T1 was skipped
after the factual failure.

#127 moved to `Done / Refine` as the completed measurement milestone. At that
checkpoint, [#153](https://github.com/horiiiiii032929/digital-twin/issues/153)
became the active `In Progress / Refine` P0 for the deterministic action-router
and grounding architecture change on fresh development evidence. #105 remained `In Progress / Refine`,
#131 remains `Go Deeper`, #24 remains open for real professor approval, and the
parent release goal remains open. Program 011 paid authority is revoked; the
qualified local deterministic R1 is unchanged.

The V2.1 governed-autonomy implementation is now a `Go Deeper` candidate, not a
new release selection. Its network-free development checkpoint passed 500/500
fresh routing cases and seven simulated days with bounded cited delivery,
restart, reply linkage, consent termination, and restore. The student surface
remains conversation-first; professor autonomy is operated through an explicit
workflow-first governance console. T1-v1 and T0 remain the selected control and
rollback until prospective provider-backed and held-out product evidence passes.

Merged PR #158 now contains the complete software implementation checkpoint for
governed autonomy V2.1: release-bound domain semantics, V2 perception and
belief planes, deterministic evidence-count updates, an independently
implemented reactive/autonomous graph, node-level SQLite checkpoints, durable
provider-call ledgers, APIs/UI, and a flow-independent autonomy evaluation
adapter. A 30-day network-free regression passes restart, expiry, finite-loop,
and duplicate-suppression gates. The successor provider integration also
passes, so #155 closes as `Done / Keep` for implementation readiness. No
held-out run, A2 qualification, or full-autonomy evaluation was performed.
T1-v2.1 remains unselected and the selected local R1 profile is unchanged.

Revision `adfc8bd7` is frozen as build-only release candidate 001 with exact
profile, source, and local image hashes. The successor provider-integration
instrument was bounded to 12 calls, zero retries, and USD 1. Live execution
completed with all 12 aggregate gates passing, five calls, one delivered in-app
message, and USD 0.0017055 reported cost. Authority is revoked and V2.1 remains
unselected. Token and per-call latency totals were not surfaced by the aggregate
runner, so #157 still owns complete academic and operational evaluation.

The remaining full-autonomy work is now separated in GitHub rather than hidden
inside the release parent. Completed [#155](https://github.com/horiiiiii032929/digital-twin/issues/155)
owns the immutable governed T1-v2.1 implementation milestone,
[#156](https://github.com/horiiiiii032929/digital-twin/issues/156) owns A2
learner-state-driven in-app intervention, and
[#157](https://github.com/horiiiiii032929/digital-twin/issues/157) owns the
immutable full-autonomy product evaluation. At this implementation checkpoint,
issue #153 was the first P0 dependency because no autonomous release was safe
before the grounding successor passed.

#157 now has a complete realistic-time actual-product boundary rather than an
open-ended design task. Per-call provider identity, tokens, latency, cost, and
failure status are prospectively captured without prompt content. Its 820 cases
cover four conditions, 50 multi-turn templates across three seeds, 100 learners
over 30 virtual days, and 120 proactive opportunities.

`governed-full-autonomy-v2-1-actual-product-evaluation-002` injects one
monotonic `VirtualUtcClock` through the real tutoring, autonomy, outreach,
worker, lease, checkpoint, outbox, and delivery paths. The final network-free
qualification passed all 820 cases with 100% action, termination, transition,
fallback, and restart rates and zero scope, citation, consent, duplicate, loop,
or authority defects. This selects the realistic-time evaluation
infrastructure only; at that checkpoint #157 remained
`In Progress / Go Deeper` and T1-v2.1 remained unselected.

#153 is `Done / Refine`. Its historical paid checkpoint and the later
network-free method comparisons are complete evidence. No execution authority
remains active.

The later source-semantic-atom successor is now terminal `Refine`. It reached
96.0% fully grounded success and 100% retrieval/boundary safety on a fresh
500-case set, but failed claim/citation precision and exact source-version
validity gates. No final architecture was selected. The repository-owner
decision is **No Release** for the autonomous LLM-backed R1; #157 remains
blocked and the fresh 1,000, known 10,000+1,000, and provider-backed 820-case
stages stay unopened. The deterministic fail-closed local candidate remains a
demo/development baseline only.

#172 is complete as `Done / Keep`. Corrective attempt 002 passed every frozen
gate on 500 fresh source-disjoint cases: V1 and ambiguity-safe V2 each reached
97.75% grounded success, while V2 additionally passed 6/6 planted ambiguity
controls and the 16/16 known clarify regression. V2 is selected for the next
product confirmation with V1 rollback. The result does not promote a release.
#157 is the active downstream `In Progress / Refine` decision. Attempts 003–007
remain immutable invalid evidence. Successor 008 completed all 820 cases for
USD 5.5902555 and produced a valid Refine result. Every safety, authority,
citation, fallback, persistence, restart, transition, termination, corrected
frequency, and paired-grounding gate passed. Promotion failed because every one
of 290 expected proactive check-ins was classified as a diagnostic question.
Post-run audit also corrected two scorer false negatives without changing the
decision. The next method must deterministically restrict eligible actions by
event before model planning and must use fresh confirmation cases. Current
governed T1-v2.1 remains unselected; deterministic T1-v1/T0 remains the local
release baseline.

Successor 009 is now the active `In Progress / Go Deeper` checkpoint. It adds a
versioned deterministic event-scoped action envelope before live planning and
uses 50 fresh source families across 820 source-disjoint cases. The complete
network-free actual-product simulation passed every condition and hard gate at
100% action accuracy with zero provider calls. Official OpenAI metadata was
refreshed on 2026-09-01 and the package is frozen. Paid authority, the bounded
freeze allowlist, and a clean live confirmation remain outstanding; no
promotion or deployment follows from the network-free pass.

PR #176 has now merged that checkpoint. Issue #157 moves prospectively to
cross-engine program 010 rather than paying for 009 in isolation. The new
program keeps one evaluation method across six engine bindings, excludes Sol
and OpenRouter, and uses an independent raw-evidence scorer that does not trust
the graph's own invariant flags. Its deterministic E0 run passed all 820
network-free actual-product cases; this is `Keep` for the scorer/controller and
`Go Deeper` for product quality. The finite runner and fresh source-disjoint
1,000-case package are now complete. The board should retain #157 as the only
active `In Progress / Go Deeper` evaluation: next publish the build-only PR,
refresh direct-provider metadata, freeze the single USD 50 authority, and run
once through 500+100, 820 per engine, top-two 1,000, winner 10,000+1,000,
proxy synthesis, and local release/no-release. No intermediate stage requires
a new issue or user decision.

That immutable candidate is now
`governed-full-autonomy-v2-1-actual-product-evaluation-003`. It binds #172's
exact Keep record and selected architecture, adds only public source/section
scope to the prospective questions, and injects the source-semantic retriever
plus ambiguity-safe V2 gate through the actual tutoring service. Its complete
820-case network-free run passed every hard gate with zero provider calls.
Provider attempt 003 stopped at the canary gate because its strict schema was
not API-compatible; all 818 bulk cases and hidden gold stayed closed. #157 is
therefore retained as invalid operational evidence. Final attempt 004 changed
only schema translation and proved that corrected schemas support exact Terra
and GPT-5.4 mini calls in its T1-v2 canary, but its T0 GPT-5.4 mini response was
classified malformed. The run failed closed after eight calls and USD
0.00900625; all 818 bulk cases and hidden gold stayed closed. #157 is now
`In Progress / Refine` for the invalid result and 004 authority is revoked.
The user then explicitly requested one unchanged connectivity retry. Attempt
005 reproduced the same T0 malformed response while the following seven T1-v2
calls succeeded. It stopped before all 818 bulk cases and hidden gold. #157 is
`In Progress / Refine`, all authority is revoked, and another identical retry
is not justified. No autonomous release claim exists.

## Release stages and product gates

The release stages are R0 local baseline, R1 hosted release candidate, R2
invite-only pilot, and R3 final project release. Product gates P0-P3 supply the
evidence needed to promote between those stages.

| Gate | Milestone | Purpose |
| --- | --- | --- |
| P0 | Product UX baseline — complete | Merged professor/student conversation-first workspace in PR #83 |
| P1 | Multimodal Product Grounding | Correct metrics, implement region-aware ingestion/retrieval, integrate visual citations, select or retain fallback |
| P2 | Deployable Product Foundation | Identity, durable data/storage, jobs, deployment, observability, security, recovery, and capacity |
| P3 | Pilot Validation and Release | Large factual-QA dataset quality, calibrated fidelity, end-to-end evidence, and approval-gated usability pilot |

The older F1/F2 milestones are closed history. F3 is superseded by P1-P3 after
its open issues were reassigned. F4 remains the report, presentation, and
professor-communication track.

## Critical path

1. Preserve #127 and Program 011 as completed unfavorable evidence; do not tune
   or rerun the sealed 10,000+1,000 package.
2. Preserve both `course-digital-twin-autonomous-long-run-001` attempts as
   zero-call invalid integration evidence. Authority is revoked; there is no
   third attempt. Keep the local fail-closed fallback selected.
3. Preserve #172's ambiguity-safe V2 `Keep`, then create a new immutable #157
   product manifest that binds that selected method. Execute the provider-backed
   820-case autonomy confirmation only under its own future authority; the
   historical evaluation-002 build remains unexecuted.
4. #24 — obtain real professor approval for the profile and calibrate fidelity
   separately from factual QA.
5. #131 — retain the terminal visual diagnostic and design a separate true-
   visual successor; text/OCR remains the release fallback.
6. #88 — externally blocked on host/domain selection; merged PR #93
   (`adf39af`) retains the passed local/container foundation and recovery
   evidence.
7. #9 and #25 — production operations and deployed end-to-end validation after
   their platform/fidelity dependencies clear.
8. #10 — approval-gated professor/student workflow and usability pilot.

The critical path follows the finite
[software improvement loop](software-improvement-loop.md). An operationally
invalid run may receive only a preregistered harness correction; a valid quality
failure creates one causal, method-level successor on fresh development data.
No iteration tunes against or reruns a sealed confirmation package.

Issue #87 is completed historical method-building work. Issues #85 and #86 are
completed `Refine` history. Issue #110 is complete only as a 10,000-row
engineering pipeline-scale milestone; analysis correction 001 prevents it from
being used as Digital Twin factual-accuracy or independent-sample evidence.
Issues #13 and #44 remain parallel final-delivery and professor-communication
work.

Issue #86 merged region-aware product ingestion, access-checked original-crop
citations, and three registered prospective development attempts in PR #91.
Attempt 003
passed all quality/integration gates but failed the frozen relative p95 gate, so
no multimodal profile is selected and the text profile remains the fallback.

GitHub parent/sub-issue and blocked-by links encode this order under release
goal #8. Issue #13 and communication ledger #44 remain parallel academic
delivery work and do not substitute for product gates.

## Issue workflow

1. Define the outcome, baseline/control, inputs, metrics, hard gates, failure
   cases, operational measures, privacy boundary, and rollback before work.
2. Use one bounded issue for one measurable decision or product capability.
3. Move only the current unblocked execution item to `In Progress`.
4. Preserve all old results and create corrections rather than overwriting.
5. Add `Evidence` only after an inspectable artifact exists.
6. Close only when implementation, tests, evidence, limitations,
   documentation, rollback, and full checks satisfy the shared definition of
   done.

## Professor checkpoints

Use issue #44 for concise decision-bearing updates. Report the product outcome,
evaluation design, exact sample/metrics when available, one important
limitation, and the next decision. Routine commits remain on the board. Ask the
professor for research, pilot, consent, or fidelity-calibration advice where
their judgment is materially required; do not ask them to choose ordinary
implementation details.

## Safety and claim rules

- Keep private course data, student data, credentials, consent records, and
  bulky run outputs outside Git.
- Do not use solutions, answer keys, or submissions.
- Do not open a held-out split before the prospective candidate and gates are
  frozen.
- Do not treat multi-model agreement as ground truth or LLM judging as a
  replacement for independent expert calibration.
- Do not describe the product as deployed, production-ready, usable, faithful,
  or learning-effective until the corresponding gate passes.
