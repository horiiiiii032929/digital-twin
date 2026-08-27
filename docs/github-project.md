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

1. #127 flow-independent 10,000-case product evaluation and #105 — preserve the
   120-row NLI result as provisional development evidence and the completed
   10,000-row pipeline as engineering history. The active successor binds
   public-case, hidden-gold, adapter, system-manifest, atomic response-ledger,
   and source-range scoring contracts across T0, T1/T2, HTTP, and any-hit flows.
   Its source inventory proves the originally requested networking and
   data-structures allocation impossible under the five-per-section cap. A
   deterministic feasible 2,100-cluster correction is build-verified and frozen
   under AFQC-035 after excluding tiny markup fragments and mid-token windows.
   Construction attempt 001 failed closed on its first DeepSeek canary because
   the runtime fingerprint differed from the frozen binding; no bulk case ran
   and authorization is revoked. Provider binding 002 passed both exact-route
   canaries, but the first bulk DeepSeek response violated the frozen author
   schema. Attempt 002 is preserved as invalid with three recorded calls, zero
   accepted clusters, and revoked authority. The runner also exposed a gap in
   its preregistered malformed-output fallback; that correction must be built
   prospectively before any successor authorization. Attempt 003
   quarantines malformed author content, labels deterministic canonical
   fallback wording, and retains independent verification. Its run is invalid:
   Google AI Studio failed one verifier call after 15 completed responses, while
   repeated DeepSeek schema drift produced four author fallbacks and three
   verifier rejections. AFQC-043 revokes authority and stops another operational
   retry. AFQC-044 resolves the method decision with a provider-free 500-case
   package and 100-case paired control. AFQC-046 replaces its defective
   reference windows with complete semantic regions and passes all source,
   lineage, uniqueness, leakage, and byte-stability gates. AFQC-047 then binds
   public-only wording to the dated OpenAI GPT-5.4 mini snapshot and independent
   Mistral Small 4 review through first-party endpoints. Its complete 500-case
   network-free simulation passes; paid wording remains unauthorized. The next
   #127 checkpoint is this finite wording run, followed only after a valid result
   by the separately authorized 500-case candidate plus 100-case control run.
   The 10,000-case final run remains unauthorized. Issue #131 separately
   owns the provider-unauthorized true-visual supplement.
2. #107 — preserve T0 as the release control and prepare one separately frozen
   T0/T1 confirmation before staging promotion.
3. #134 — evaluate the A0 opt-in in-app baseline and A1 deterministic
   evidence-recovery trigger. Keep learner-state inference in shadow mode and
   external Discord delivery disabled until its payload is reduced to a generic
   alert and authenticated deep link.
4. #88 — externally blocked on host/domain selection; merged PR #93
   (`adf39af`) retains the passed local/container foundation and recovery
   evidence.
5. #24 — calibrate Professor Digital Twin fidelity against independent expert
   labels, separately from factual QA.
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
