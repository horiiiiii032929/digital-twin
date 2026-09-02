# Bug audit of the Codex commits merged into main (8786375..2bdfea9)

Date: 2026-09-02

Audit ID: `main-commit-audit-8786375-2bdfea9-001`

Status: verification of ten prior candidates complete; the independent sweep
for new defects did not run (usage limit) and is listed as open work; no code
was changed by this audit

Scope: the seventeen commits between `8786375` and `2bdfea9` on `main`, which
publish the cross-engine evaluation 010 result, the grounding successor 011,
actual-product confirmations 012 and 013, the governed autonomy release
profile selection, and the local release qualification 002. The audit was run
on the isolated branch `claude/sota-autonomous-digital-twin-study` after
merging `origin/main`.

Method: each candidate defect from an earlier finder pass was examined by
three independent agents with different mandates (reproduce, refute, assess
reachability in the shipped configuration), read-only and network-free, with
reproduction scripts run in the worktree. A candidate is confirmed when at
least two of three agree; severity is the median of the three. "Reachable"
means reachable with the documented local R1 configuration
(`docs/local-r1-runbook.md`, `compose.local-r1.yml`, `deploy/local-r1.env.example`)
as judged by the reachability lens.

## Summary table

| # | Location | Defect | Severity | Reachable in documented config | Votes |
| --- | --- | --- | --- | --- | --- |
| 1 | `services/api/app/factory.py:418-423` | Governed v2.1 + deterministic generator is built without `DeterministicActionRouterV2`; the evaluated runtime for confirmations 012/013 and the grounding successor used the router | high | yes | 3/3 |
| 2 | `src/digital_twin/student/autonomy_service.py:118-157` | Proactive wording recomputes the required claim count on a synthesized question while the evidence set was sized by the objective text; mismatches turn a valid delivery into a silent `no-action` | high | yes | 3/3 |
| 3 | `src/digital_twin/grounding/ambiguity_safe_evidence.py:44-51` | Hits are sliced to `evidence_limit` before page-fallback removal; a precise sibling just outside the window is never seen and an answerable question flips to `clarify` | medium | yes (majority) | 3/3 |
| 4 | `services/api/app/factory.py:418-423` with `config.py` | No validation couples the evidence gate to the governed deterministic generator; with `structured-lexical-v1` the generator abstains on ordinary questions when two or three chunks match | medium | no (runbook pins the question-targeted gate; compose default mode is bounded graph) | 3/3 |
| 5 | `services/api/app/config.py:248-252, 315-393` | The staging T1 qualification check binds profile hash and generator but not the planner; governed v2.1 with a deterministic planner passes as hash-bound qualified although the record names `gpt-5.6-terra` | medium | no by default, yes if the runbook line is omitted | 3/3 |
| 6 | `compose.local-r1.yml:16-17` | Evidence gate became a shell-overridable interpolation with no startup binding to the profile or record; the profile-path half of the claim fails closed and is refuted | medium | no | 3/3 |
| 7 | `scripts/academic_factual_qa_open_10000_t0_adapter.py:907-916` | Canonical claim verifier override keyed only on the gate replaces the manifest's verifier for live engines too, so a future cross-engine live run would fail claim validation on atom-bearing chunks | medium (evaluation instrument) | not a product path | 3/3 |
| 8 | `services/api/app/factory.py:230-238` | Canonical verifier applied for every generator mode under governed v2.1, including live generators that quote raw chunk text | low | no (qualified release uses the deterministic generator) | 3/3 |
| 9 | `src/digital_twin/generation/generator.py:33`, `grounding/claim_validation.py:151`, `grounding/reference_uniqueness.py:87` | Atom version literal duplicated in three modules instead of one accessor on `ATOM_VERSION`; not a defect at HEAD, but a version bump silently releases raw markup or fails all claims depending on which copy is missed | hygiene | n/a | rejected as a bug 1/2, duplication confirmed |
| 10 | `scripts/run_governed_full_autonomy_v2_1_actual_product_evaluation_002.py:137` | `.claude/` carve-out in the dirty-worktree gate, duplicated in the 011 runner | unverified | n/a | 0/3 (agents hit the usage limit) |

## Confirmed findings

### 1. Router-less generator in the shipped governed configuration (high)

`_configured_generator` returns `DeterministicEvidenceSetGroundedGenerator()`
with no `policy_enforcer` when `APP_GENERATOR_MODE=deterministic` and
`APP_STUDENT_TUTORING_MODE=governed-autonomous-tutoring-graph-v2.1`
(`services/api/app/factory.py:418-423`). The default enforcer has
`action_router=None` (`src/digital_twin/generation/policy.py:36-40`), so only
the narrow V1 graded-work regex applies. The live branch of the same function
(`factory.py:492-496`) and the runtime that produced confirmations 012 and 013
(`scripts/governed_full_autonomy_v2_1_actual_product_runtime.py:529-534`,
`hybrid_safe_generation=True`) both wire `DeterministicActionRouterV2`. The
grounding successor 011 evidence was also produced with the router
(`scripts/academic_factual_qa_open_10000_t0_adapter.py:901-921`). The
qualification record binds the generator id only, not the router. The V2
graph's own perception regexes are narrower than the router's rules
(submission-ready or graded requests, unresolved referents, cross-course and
withdrawn-source probes), so those boundary cases are routed differently in
the deployed app than in the evidence.

Reproduction: build `AppSettings` for the documented governed configuration,
call `_configured_generator`, and inspect `policy_enforcer.action_router`
(`None`); run the five boundary questions through the shipped enforcer and
through an enforcer with the V2 router and compare actions.

Fix direction: construct the governed deterministic generator with
`DeterministicPolicyEnforcer(action_router=DeterministicActionRouterV2())`,
hoist one enforcer helper used by both branches, and add a factory test that
asserts the router identity next to the existing model-id test
(`tests/api/test_auth_api.py:571-586`).

### 2. Proactive deliveries dropped by a claim-count mismatch (high)

The evidence assessor sizes the proactive evidence set from
`goal.approved_course_objective` through `QuestionTargetedAtomicEvidenceGate`,
which selects exactly `required_atomic_claim_count(query)` hits, 2 only when
the objective matches the explicit multi-evidence pattern
(`src/digital_twin/action_router.py:40-44, 181-184`). The wording generator
then calls the generator with a synthesized instruction
("Create one concise in-app tutoring intervention for ...") and passes all
selected chunks (`autonomy_service.py:118-149`).
`DeterministicEvidenceSetGroundedGenerator.generate` recomputes the required
count on that synthesized text (`generator.py:133-140`) and returns
`no-evidence` when the counts differ. The service converts that into
`_failed_grounded_response`, the graph fails `claim-lineage-complete`, one
repair repeats the identical failure, and the opportunity is recorded as
`no-action` with a misleading reason; the goal attempt is not consumed and the
observer's idempotency key prevents recreating the opportunity, so the
intervention is permanently dropped for that event.

Reproduction: a pytest in the scratchpad using the existing autonomy fixture
with objective "Explain the relationship between cache coherence ... and
virtual memory ..." produced `no-action claim-lineage-complete` under the
evidence-set generator and `delivered event-spaced-review-due` under the
default generator; a single-chunk objective delivered under both.

Fix direction: validate `len(approved_hits)` against the gate's own selection
rather than re-deriving a count from prose; either pass the assessor's query as
the `question` and carry intent separately, or add an explicit
`required_evidence_count` parameter to the generator for the autonomy path.

### 3. Page-fallback removal after truncation (medium)

`AmbiguitySafeEvidenceGateV1.assess` slices `hits[: evidence_limit]` and only
then runs `prefer_specific_source_regions` on the window
(`ambiguity_safe_evidence.py:44-51`; introduced in `b4d25fa`). A selected-text
page fallback inside the window is kept when its precise sibling ranks just
outside it, and the page aggregate then counts as a competing answer class.
Reproduced with the exact shipped gate composition: six hits with the page-1
fallback at rank 1 and its precise sibling at rank 6 yield `clarify` with the
current ordering and a sufficient single selection when filtering precedes
slicing. The same slice-before-filter shape exists in
`SourceSemanticEvidenceAtomGateV2.assess`. Two of three lenses judged the
scenario reachable through the product retriever, which caps at five hits;
the third judged it unreachable in practice, so treat reachability as
majority, not unanimous.

Fix direction: filter page fallbacks over the full hit sequence first, then
slice; add a test with `evidence_limit + 1` hits where the precise sibling is
last; consider collapsing page fallbacks at index time.

### 4. No coupling between evidence gate and the evidence-set generator (medium, latent)

The generator abstains whenever the selected hit count differs from the
required count; `structured-lexical-v1` selects every matching hit up to three
(`factory.py:505-509`; not five as first claimed). `AppSettings.validate` has
no rule relating `evidence_gate_mode` to the tutoring or generator mode, and
the mismatched pairing starts successfully. Reproduced end to end: three
lexically matching hits, `sufficient=True selected=3`, then `no-evidence`
released to the student with no audit event. The `unselected` half of the
original claim is refuted: the service raises at construction for governed
v2.1 with no gate. Not reachable with the documented configuration because the
runbook pins `question-targeted-ambiguity-safe-v2` and the compose default
mode is the bounded graph.

Fix direction: require the question-targeted gate whenever the governed
deterministic generator is wired, with a clear startup error naming the
runbook pairing.

### 5. Planner not bound by the qualification check (medium, latent)

The range introduced `APP_AUTONOMY_PLANNER_MODE` and decoupled it from the
generator mode, but `_validate_t1_qualification_result` still compares only
run id, implementation id, generator model, gates, rollback flag, and profile
hash (`config.py:315-393`). The confirmation-001 record names planner
`gpt-5.6-terra`; a governed configuration with the default deterministic
planner passes as hash-bound qualified and silently runs
`DeterministicAutonomousPlanner`. The only planner-dependent guard is the API
key presence check.

Fix direction: pass the planner mode into the record check and require the
record's `selected_configuration.planner` to equal the planner identity the
runtime will use.

### 6. Shell-overridable evidence gate in the R1 compose file (medium, latent)

`compose.local-r1.yml:16-17` changed pinned literals to `${VAR:-default}`
interpolations in `547f2db`. Docker Compose lets an exported shell variable
override `--env-file`, reproduced with Compose v2.40. The profile-path half
fails closed (the app refuses a missing or wrong profile), so only the gate
half stands: an exported `APP_EVIDENCE_GATE_MODE=unselected` with the
compose-default bounded graph starts the app with no gate and every turn
returns `no-evidence`. No startup validation binds the gate to the profile or
the qualification record.

Fix direction: bind the gate to the release like the profile hash and
generator, or derive it from the profile's evidence-sufficiency component
instead of a separate knob.

### 7. Verifier override for live engines in the 10,000-case adapter (medium, instrument)

`scripts/academic_factual_qa_open_10000_t0_adapter.py:907-916`, added in
`5747148`, rebinds the claim validator to
`CanonicalSourceAtomicClaimVerifier` whenever the manifest's gate is one of the
two semantic-atom gates, before the `deterministic_engine` branch, discarding
the generator-keyed `ContiguousQuoteAtomicClaimVerifier` for
`cross-engine-live-extractive-boundary-v1`. Live engines are prompted to copy
raw chunk text, while the canonical verifier requires equality with the
canonical atom claim, so a future live cross-engine run over atom-bearing
sources would score every quoted claim unsupported. The 011 record correctly
labels the verifier change prospective and not credited.

Fix direction: scope the override to the deterministic evidence-set
generator, or present canonical atoms to live engines and validate against
them consistently; add a test asserting which verifier the adapter wires per
engine.

### 8. Canonical verifier for all governed generator modes (low)

`factory.py:230-238` applies the canonical verifier under governed v2.1
regardless of generator mode. With a live OpenAI generator over atom-bearing
chunks, verbatim quotes of markup-bearing text fail (reproduced in isolation).
Unreachable in the qualified release, which uses the deterministic generator.

Fix direction: select the verifier by active generator, mirroring the
evaluation runtime.

## Rejected and unverified candidates

- Atom version literal duplication (`generator.py:33` and two siblings): the
  duplication is real, but no defect exists at HEAD. The reproduced hazard is
  prospective: bumping `ATOM_VERSION` without the generator copy silently
  releases raw authoring markup, and bumping it with the verifier copy but not
  the generator fails every claim. Recommended as hygiene: one accessor on
  `ATOM_VERSION`.
- `.claude/` carve-out in the dirty-worktree gate: all three verification
  agents failed on the session usage limit; unverified.

## Implications for the release qualification Keep decision

The qualification record binds the release by profile hash and generator id.
Findings 1 and 2 mean the deployed governed configuration is not the same
behaviour that the confirmation and grounding evidence measured: boundary
routing lacks the V2 router, and some proactive interventions the evaluated
runtime would have delivered are dropped. Neither invalidates the recorded
evidence, which is correct for the runtime that produced it, but the Keep
decision's implicit claim that the local release reproduces that evidence is
not established for those two paths. Findings 4, 5, and 6 are configuration
hazards that the current validation does not catch. The remaining findings are
instrument or hygiene items.

Recommended actions, in order: fix 1 and 2 with regression tests, re-run the
network-free confirmation path against the fixed factory, then add the
coupling checks from 4, 5, and 6.

## Open work

- Independent sweep for new defects in the range (four angles: runtime,
  evaluation integrity, deployment and configuration, tests) did not run; the
  workflow can be resumed from its journal once the usage limit resets.
- Verification of candidate 10.
- Filing findings 1 through 7 as issues; this audit changed no code.
