# Bug audit of the Codex commits merged into main (8786375..2bdfea9)

Date: 2026-09-02

Audit ID: `main-commit-audit-8786375-2bdfea9-001`

Status: complete for the verified findings below; four verification agents and
the automated report step were lost to session limits, so the items in
"Unverified and open" remain outstanding. No code was changed by this audit.

Scope: the seventeen commits between `8786375` and `2bdfea9` on `main`, which
publish the cross-engine evaluation 010 result, the grounding successor 011,
actual-product confirmations 012 and 013 with a reference-validity correction,
the governed autonomy release-profile selection, and the local release
qualification 002. The audit ran on the isolated branch
`claude/sota-autonomous-digital-twin-study` after merging `origin/main`.

Method: a fan-out review over four angles (product runtime, evaluation
integrity, deployment and configuration, tests) looped until two consecutive
rounds surfaced nothing new, and every candidate was then judged by three
independent agents with different mandates: reproduce it, refute it, and
assess reachability in the documented configuration. A finding is listed only
when at least two of three agreed; severity is the median of the three. All
agents worked read-only and network-free, running reproduction scripts in the
worktree. 167 agents ran; 147 completed.

The four most consequential findings (A1, A2, B1, B4) were re-verified by hand
against the repository before publication and are marked accordingly.

## What the audit changes about the release story

Two independent classes of problem emerged.

**The deployed governed configuration is not the configuration the evidence
measured.** The factory builds the release's generator without the boundary
router that every evaluation runtime used, the documented environment block
cannot start the API as written, and the qualification record binds a profile
hash that the confirmation runs did not load. Each is verified below.

**Two evaluation results were repaired after their outputs were seen.** The
013 confirmation flipped from Refine to Keep by rewriting thirty
pre-registered references to match what the product actually emitted, and the
correction record names a code revision at which its own script does not
exist. This does not make the underlying runs wrong, but it means the Keep
that the local release selection rests on is a post-hoc rescoring, and the
repository's own evaluation-first rules ask for that to be visible.

## A. Product findings

### A1. Governed generator ships without the boundary router (high, reachable, hand-verified)

`services/api/app/factory.py:418-423` returns
`DeterministicEvidenceSetGroundedGenerator()` with no `policy_enforcer` when
`APP_GENERATOR_MODE=deterministic` and
`APP_STUDENT_TUTORING_MODE=governed-autonomous-tutoring-graph-v2.1`. The
default enforcer leaves `action_router=None`
(`src/digital_twin/generation/policy.py:36-40`), so only the narrow V1
graded-work regex applies. The live branch of the same function
(`factory.py:492-496`), the runtime behind confirmations 012 and 013
(`scripts/governed_full_autonomy_v2_1_actual_product_runtime.py:529-534`), and
the grounding-successor adapter
(`scripts/academic_factual_qa_open_10000_t0_adapter.py:901-921`) all wire
`DeterministicActionRouterV2`. The V2 router's rules for submission-ready and
graded requests, unresolved referents, cross-course probes, and withdrawn
sources are therefore absent from the deployed app but present in every
measurement. The qualification record binds the generator id only, not the
router.

Fix: construct the governed deterministic generator with
`DeterministicPolicyEnforcer(action_router=DeterministicActionRouterV2())`,
ideally through one shared helper, and assert the router identity in the
factory test.

### A2. Proactive deliveries dropped by a claim-count mismatch (high, reachable)

The proactive evidence set is sized from `goal.approved_course_objective`
through `QuestionTargetedAtomicEvidenceGate`, which selects exactly
`required_atomic_claim_count(objective)` hits. The wording generator then calls
the generator with a synthesized instruction ("Create one concise in-app
tutoring intervention for ...") and passes all selected chunks
(`src/digital_twin/student/autonomy_service.py:118-149`).
`DeterministicEvidenceSetGroundedGenerator` recomputes the required count on
that synthesized text (`src/digital_twin/generation/generator.py:133-140`) and
returns `no-evidence` when the counts differ. The service converts that into a
failed grounded response, the graph fails `claim-lineage-complete`, the single
repair repeats the same failure, and the opportunity is recorded as
`no-action`. The goal attempt is not consumed and the observer's idempotency
key prevents recreating the opportunity, so the intervention is permanently
lost. A two-evidence objective (any phrasing matching "relationship between",
"which two", "both statements") triggers it.

Reproduced with a pytest against the existing autonomy fixture: the
evidence-set generator produced `no-action claim-lineage-complete` where the
previous generator delivered.

Fix: validate the hit count against the gate's own selection instead of
re-deriving it from prose, or pass the assessor's query as the question and
carry pedagogical intent separately.

### A3. Evidence-set generator is only usable with one gate (medium, latent)

The same count rule means the generator abstains whenever the gate approves
more hits than required. `structured-lexical-v1` selects every matching hit up
to three; the question-targeted gate trims to exactly the required count.
Nothing in `AppSettings.validate` couples the gate to the tutoring or
generator mode, so the mismatched pairing starts cleanly and then answers
`no-evidence` on answerable questions, with the audit trail showing sufficient
evidence selected. Two earlier claims were refuted: an unselected gate fails
closed at construction rather than abstaining, and the compose default
tutoring mode is the bounded graph, which never wires this generator.

Fix: require the question-targeted gate whenever the evidence-set generator is
wired, and fail startup with a message naming the runbook pairing.

### A4. Clarify turns persist as `no-action` (medium, reachable)

The policy-boundary short-circuit feeds a `clarify-request` policy action into
`_grounded_response_v2`, whose action map
(`src/digital_twin/student/tutoring_graph.py:1698-1705`) knows only `clarify`.
Every delivered clarification is therefore stored in the durable governed
response table as `no-action` while the student sees a clarification and the
trace reports success. The sibling intents (abstain, refuse) map correctly.

Fix: add the missing map entry, or emit `clarify` from the boundary helper.

### A5. Failed provider calls report zero usage (medium, reachable)

`generation_calls` was changed to test `provider_model != "not-called"`
(`tutoring_graph.py:892`). The safe fallback after a provider failure carries
`not-called`, so a turn whose generator was called and raised now persists
`generation_calls=0`. Because the evaluation adapter only demands an exact
metrics collector when the call counts sum above zero, a run can silently
report zero provider usage for a turn that made a billable call.

### A6. Planner spend invisible to operators (high, reachable)

In the decoupled governed mode the live planner's budget client is stored in
`app.state.autonomy_planner_budget` while `provider_budget` stays `None`, and
`/api/operations/metrics` reports only the latter
(`services/api/app/routers/operations.py:63`). An operator running the
documented governed release sees zero calls and zero cost while paid planner
calls are made and capped; budget exhaustion is invisible until it bites.

### A7. Page-fallback removal after truncation (medium, reachable)

`AmbiguitySafeEvidenceGateV1.assess` slices to `evidence_limit` and only then
drops page fallbacks, so a precise sibling ranked just outside the window is
never considered and the page aggregate survives as a competing answer class,
flipping an answerable question to `clarify`. A related finding: the filter
drops a page chunk whenever any other region merely overlaps the same page
numbers rather than actually containing the page text
(`src/digital_twin/grounding/reference_uniqueness.py:215`).

### A8. Canonical claim verifier applied beyond its generator (low to medium)

The canonical verifier is now used for every governed generator mode
(`factory.py:230-238`) and requires whole-atom equality, which contradicts the
live prompt's instruction to quote the shortest contiguous span. Unreachable
in the qualified release, which uses the deterministic generator, but it makes
the live path unusable over atom-bearing sources without a change.

## B. Evaluation-integrity findings

### B1. Confirmation 013 gold rewritten after the responses were seen (high, hand-verified)

`scripts/analyze_governed_full_autonomy_v2_1_actual_product_confirmation_013.py:63-121`
rewrites, for exactly thirty V2 provider-failure cases, the pre-registered
reference action from `no-action` to `provide-hint-or-example` and flips
`must_have_valid_lineage` from false to true, then rescores the same immutable
responses against the same frozen gates. The guards require exactly thirty
corrections and require the original result to have exactly thirty unexpected
actions, so the correction is defined to neutralise precisely the observed
failures. The terminal outcome moves from Refine to Keep, and the release
selection record and local R1 qualification rest on that rescoring. The frozen
013 instrument still declares the provider-failure action as `no-action`, and
the original test still asserts the old gold, so both the old and new
expectations pass simultaneously.

I read the code and confirmed the mechanism and the guards.

This is not automatically illegitimate: if the pre-registered reference was
genuinely wrong about how the product should behave under provider failure,
correcting it is defensible. But the correction was authored after seeing
which cases failed, it is not visible in the instrument, and no
pre-registration explains why a delivered hint is the correct behaviour when
the design documents state that provider failures must fail closed. The
accompanying gold flip also leaves the lineage requirement inconsistent across
sibling cases (`build_...confirmation_013.py:132`).

### B2. Correction record names a revision where its script does not exist (medium, hand-verified)

The correction record claims `code_revision`
`27568e4379f5079493d08d0f633edfd85bc4f9fa`. The analyzer that produced it was
first committed in `547f2db`. I confirmed both facts directly. The
Keep-producing rescoring therefore cannot be reproduced at the revision it
records, and the analyzer writes no revision or dirty-tree stamp of its own.

### B3. The 012 analysis correction has no durable record (low)

The 013 instrument names
`governed-full-autonomy-v2-1-actual-product-confirmation-012-analysis-correction-001`
as its predecessor, but no record, results page, or registry row exists for
it; its output goes only to ignored generated files with no revision stamp.
The chain from the 012 responses to the 013 gold design cannot be audited.

### B4. Release record binds a profile the evidence run did not load (medium, hand-verified)

`records/governed-full-autonomy-v2-1-confirmation-001.json` binds
`profile_sha256` `43da7e1b…`, which is `student-tutor-r1-local-candidate-v2.json`.
The actual-product runtime that produced confirmations 012 and 013 loads
`student-tutor-r1-openai-candidate-v1.json`
(`scripts/governed_full_autonomy_v2_1_actual_product_runtime.py:82-84`), whose
hash is `10d6012e…`. I computed both hashes and read the constant. The record
therefore binds the release to a profile that the run behind its evidence did
not use.

### B5. Network-free simulation diverges from the paid path (high for method, not reachable in production)

The `--simulate` mode's provider-failure stand-ins behave differently from the
live components: the reactive planner stand-in raises out of `propose()` and
routes to the safe no-action path, while the live planner swallows the error
and returns a deterministic fallback that delivers a hint
(`runtime.py:175-188`). With `hybrid_safe_generation=True` the generator
switch is a no-op because the provider-backed generator is deterministic
(`runtime.py:616-635`). The consequence is that `--simulate` validated the
`no-action` gold that the USD 3.85 paid run then contradicted on thirty
trajectories, which is the undisclosed reason the references were rewritten in
B1. A re-indentation in the same area also pauses the autonomy policy on
provider-backed runs where it previously did not (`runtime.py:626`).

### B6. Sealed 010 baseline changed behaviour under an unchanged identity (low to medium)

The e0 deterministic generator in the 10,000-case adapter now delegates to the
evidence-set generator while keeping `implementation_id`
`deterministic-atomic-grounded-generator-v1` and the manifest identity
`deterministic-grounded-generator-v1`
(`scripts/academic_factual_qa_open_10000_t0_adapter.py:523-556`,
`scripts/cross_engine_factual.py:74`). A read-only replay of the 500
development cases flips 18 from abstain to answer. The terminal 010 e0 result
cannot be reproduced by the code that still claims its identity, and no test
notices.

### B7. Weaker binding in the 011 and 012 harnesses (low to medium)

The 011 runner injects `profile_sha256` as an unverified literal copied from
its instrument, so the hash bound into the ledger is never checked against the
policy actually executed; its network-free "no provider calls" assertion
inspects an aggregate that is hard-coded to zero and so can never fire. The
012 builder dropped the `selected_grounding.result_sha256` verification that
every predecessor performed, and the hash its instrument pins matches no file
in the repository.

### B8. Claim-validator override reaches live engines (medium, instrument only)

The canonical verifier override in the 10,000-case adapter is keyed only on
the gate and sits before the deterministic-engine branch, so a future live
cross-engine run over atom-bearing sources would have every quoted claim
scored unsupported.

## C. Configuration and documentation findings

### C1. The documented governed configuration cannot start (high, hand-verified)

The runbook's governed V2.1 block sets five variables and omits
`APP_STUDENT_PROFILE_PATH`, while both `compose.local-r1.yml:17` and
`deploy/local-r1.env.example:8` pin the v1 profile. The qualification record
binds the v2 profile hash. I verified the block, both pins, and the three
profile hashes: following the runbook as written leaves the runtime on v1
(`1b3257e8…`) against a record binding `43da7e1b…`, and configuration
validation rejects the pairing, so every container refuses to start. The same
omission breaks the documented "restore governed V2.1 after T0 rollback" step.

Fix: add the profile path to the runbook block, or default it to the v2
profile in compose and the env example.

### C2. Qualification check does not bind planner or gate (medium)

`_validate_t1_qualification_result` binds run id, implementation id, generator
model and profile hash, but never the planner mode or the evidence gate, even
though the record it binds qualified one specific combination. A governed
configuration with the default deterministic planner and the lexical gate
passes as hash-bound qualified, and the staging verifier's mode check passes
too, so an unqualified runtime is labelled as the qualified release. The
runbook's claim that the API fails closed for any non-qualified governed
pairing is not accurate.

### C3. Release-critical settings are shell-overridable (medium)

The R1 compose file moved the gate and profile path from pinned literals to
`${VAR:-default}` interpolations, and an exported shell variable beats
`--env-file`. The profile half fails closed; the gate half does not. Related:
`compose.staging.yml` has no planner key at all, so the governed planner can
never be enabled there while the tutoring mode and record still can be.

### C4. `.claude/` carve-out in the dirty-worktree gate (low)

The integrity gate drops porcelain rows beginning with `.claude/` by fixed
slicing, duplicated across two runners. Session-tooling edits escape the gate,
and renamed entries would be mis-parsed.

## D. Test-coverage findings

- No test pairs the evidence-set generator with a real gate, so the abstain
  branch that A3 describes is uncovered (`tests/digital_twin/test_generation.py:526`).
- Every governed staging-configuration test is a rejection test; nothing
  asserts that the shipped pairing validates, which is why C1 escaped
  (`tests/api/test_auth_api.py:431`).
- The compose test was weakened from pinning the profile path to accepting any
  env-overridable default (`tests/test_local_r1_compose.py:26`).
- The provider-failure test pins generator call counts but never the persisted
  trace field, hiding A5 (`tests/digital_twin/test_governed_autonomy.py:1435`).

## Rejected candidates

- Atom version literal duplicated across three modules: real duplication, but
  no defect at HEAD. The hazard is prospective, and a single accessor keyed on
  `ATOM_VERSION` is the hygiene fix.
- Two parts of earlier claims were refuted outright: an unselected gate under
  governed mode fails closed at startup rather than abstaining silently, and
  the compose profile-path override also fails closed.

## Unverified and open

- Four verification agents (covering a config binding, a grounding-successor
  runner check, an evaluation-002 item, and two test items) were lost to the
  session limit; their candidates are recorded in the workflow journal and
  have not been judged.
- One agent's output could not be safety-reviewed because the classifier timed
  out. Nothing from that agent is reported here except where another lens
  independently reached the same conclusion.
- The automated synthesis step never ran; this report was consolidated by hand
  from the verdicts, with the four hand-verified items checked directly.

## Recommended order of work

1. Fix A1 and A2 with regression tests; they are the two places where the
   deployed product diverges from its own evidence in a way a student would
   see.
2. Fix C1 so the documented release can start, and add the positive
   configuration test that would have caught it.
3. Decide how to record B1: either restore the pre-registered gold and let 013
   stand as Refine, or publish the reference correction as its own decision
   with a stated rationale, a correct revision, and an updated instrument.
   Also record B3 and correct B2 and B4.
4. Then the remaining medium items: A3 to A7, C2, C3, B5 to B8.

None of this was applied. The audit changed no code and filed no issues.
