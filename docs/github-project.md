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

#127 moves to `Done / Refine` as the completed measurement milestone. [#153](https://github.com/horiiiiii032929/digital-twin/issues/153)
is the active `In Progress / Refine` P0 and owns the deterministic action-router
and grounding architecture change on fresh development evidence. #105 remains `In Progress / Refine`,
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

PR #158 now contains the complete software implementation checkpoint for
governed autonomy V2.1: release-bound domain semantics, V2 perception and
belief planes, deterministic evidence-count updates, an independently
implemented reactive/autonomous graph, node-level SQLite checkpoints, durable
provider-call ledgers, APIs/UI, and a flow-independent autonomy evaluation
adapter. A 30-day network-free regression passes restart, expiry, finite-loop,
and duplicate-suppression gates. This is implementation evidence only. No paid
call, held-out run, A2 qualification, or full-autonomy evaluation was
performed, so #153, #155, #156, and #157 all remain open. T1-v2.1 remains
`Go Deeper` and the selected local R1 profile is unchanged.

The remaining full-autonomy work is now separated in GitHub rather than hidden
inside the release parent. [#155](https://github.com/horiiiiii032929/digital-twin/issues/155)
owns the governed T1-v2.1 product completion, [#156](https://github.com/horiiiiii032929/digital-twin/issues/156)
owns A2 learner-state-driven in-app intervention, and
[#157](https://github.com/horiiiiii032929/digital-twin/issues/157) owns the
immutable full-autonomy product evaluation. Issue #153 remains the first P0
dependency because no autonomous release is safe before the grounding successor
passes.

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
2. Execute #153 as the one fresh method-level successor for deterministic action routing,
   evidence sufficiency, and claim/citation release; keep the local fail-closed
   fallback selected until it passes.
3. #24 — obtain real professor approval for the profile and calibrate fidelity
   separately from factual QA.
4. #131 — retain the terminal visual diagnostic and design a separate true-
   visual successor; text/OCR remains the release fallback.
5. #88 — externally blocked on host/domain selection; merged PR #93
   (`adf39af`) retains the passed local/container foundation and recovery
   evidence.
6. #9 and #25 — production operations and deployed end-to-end validation after
   their platform/fidelity dependencies clear.
7. #10 — approval-gated professor/student workflow and usability pilot.

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
