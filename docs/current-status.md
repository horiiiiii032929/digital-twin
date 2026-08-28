# Current project status

Status date: 2026-08-28

This is the operational starting point for prospective work. Frozen experiment
plans, result records, corrections, profiles, and the technical evidence freeze
remain authoritative for the historical runs and claims they document.

R1 consolidation is complete on `main`: PR #130 merged the flow-independent
evaluation, PR #133 merged the privacy-preserving learning-gap core, and PR
#135 merged the opt-in proactive-outreach core. The prospective R1 continuation
is now one finite OpenAI-only path. PR #136 merged the direct-provider base at
revision `492979e`; checkpoint 003 then added the exact GPT-5.4 calibration and
bounded development path. Checkpoint 004 spent USD 0.555499 on 50 wording calls,
accepted 452/500 variants, and stopped before product execution. Checkpoint 005
reused those 452 variants plus 48 explicit canonical fallbacks but is now
terminal after two invalid zero-provider-call attempts. Issue #139 is the active
P0 retrieval-index qualification; #127 is Refine and blocked until it passes.
Issues #132 and #134 stay
open for their API/UI, method-confirmation, and activation gates rather than
being treated as completed products.

The active #127 successor is now
`academic-factual-qa-open-10000-v1`: a flow-independent 500-case development
and sealed 10,000-case final evaluation of the actual T0 product. The response
process receives only a versioned public case, retrieves from the course corpus,
and persists its normalized response before a separate process may open hidden
gold. Canonical evidence uses source artifact hashes and character/region
coordinates rather than runtime chunk IDs, so the same cases can compare T0,
future T1/T2 graphs, an HTTP deployment, and the any-hit control under separate
system manifests. The prior 10,000 rows remain engineering-scale history.

The build-only source scan found that the requested course allocation cannot
satisfy its own five-clusters-per-original-section cap: networking requests
1,075 development-plus-final clusters but permits at most 495; data structures
requests 425 but permits at most 400. No dataset was written and no threshold
was weakened. A pre-spend source audit then found that the first frozen plan
counted tiny markup/import fragments and mid-token cuts as clusters. No provider
call was made. AFQC-035 corrects the allocator to require token-aligned windows
of at least 100 characters and four tokens. The tested feasible allocation is
396 operating-systems, 450 networking, 350 data-structures, and 904 Python
clusters including 25
development clusters per course. It produces exactly 2,100 non-overlapping
source windows and 10,500 prospective cases with the requested code, equation,
table, answerable, and boundary strata. AFQC-035 freezes this correction because
it preserves the academically important source-diversity cap instead of
inflating the row count through repeated use of a few sections. The deterministic
source/claim layer is authoritative before model calls. AFQC-044 has now
produced the provider-free development package: 500 public cases and separate
hidden gold over 100 source clusters, including 400 answerable and 100 boundary
cases, plus a fixed 100-case control subset. Every construction, separation,
lineage, uniqueness, and leakage gate passed with zero provider calls. This is
build evidence, not a product-quality result. AFQC-045 then added the missing
fitness-for-use gate before spending: 227/400 answerable cases across 68/100
clusters triggered conservative fragment, raw-artifact, or structured-modality
diagnostics. A 12-case Codex-assisted audit confirmed material reference defects.
The package is retained as deterministic scaffolding but is blocked from product
execution until a prospective source-plan, extraction, and wording successor
passes. The same allocation cannot be patched only in the answer parser: just
16/35 code-labelled development windows and 2/3 table-labelled windows contain
a complete detected region; equations are 6/6. Future
models may paraphrase wording and provide advisory review but cannot define or
mutate gold. The 500-case T0 product run and sealed 10,000-case final run remain
unauthorized. AFQC-046 now closes the reference-quality correction
prospectively: a development-only source plan selects complete semantic regions
before constructing 100 non-overlapping clusters. The rebuilt package retains
400 answerable and 100 boundary cases plus the fixed 100-case control. All
224 text targets and 176 structured targets pass exact source and
original-region lineage checks with zero defects, duplicates, answer leakage,
provider calls, private-data reads, or final-split access. A 12-case
Codex-assisted packet found 12/12 usable source truths and 10/12 serviceable
development questions; two template cues still require wording refinement.
The corrected reference layer is Keep, while provider-neutral wording is Go
Deeper. AFQC-047 remains preserved as the earlier unexecuted OpenAI/Mistral
binding. AFQC-048 prospectively replaces only the active provider boundary:
exact OpenAI `gpt-5.4-mini-2026-03-17` performs public question wording and T0
generation, while exact OpenAI `gpt-5.4-2026-03-05` performs advisory semantic
review. They are separate models from the same provider family, not independent
providers. Direct Responses API payloads use strict structured output,
`store: false`, zero retries, no router, and no fallback. The active preflight
requires only `OPENAI_API_KEY`, rejects historical non-OpenAI manifests, and
remains `blocked-not-authorized`. Network-free wording and adapter simulations
pass with zero calls. No T0 product-quality claim exists yet.

AFQC-049 adds the finite successor
`academic-factual-qa-open-10000-development-checkpoint-003`. It first evaluates
exact `gpt-5.4-2026-03-05` on the unchanged 40 planted controls. Only a complete
calibration pass may continue to 25 GPT-5.4 mini wording batches, 25 GPT-5.4
wording-review batches, 500 candidate product cases, 100 paired any-hit control
cases, and deterministic scoring. Pass, calibration-failure, wording-failure,
and product-failure simulations stop at the expected boundary with zero calls.
The checkpoint is capped at 660 calls and USD 18 across four separately enforced
stage budgets. AFQC-050 authorized it once. Attempts 001 and 002 each stopped
after the first four-control GPT-5.4 batch, before hidden-label opening or any
wording/product call. Attempt 001 exposed a schema/parser taxonomy mismatch;
the corrected attempt 002 then returned two defect-bearing records marked
semantically valid. Both executions are preserved as invalid, with two total
calls and USD 0.02635 reported cost. AFQC-052 revokes the authorization and
requires an explicit reviewer-method decision. The sealed 10,000-case final run
remains unauthorized.

AFQC-053 completes that method decision in build-only calibration 004. GPT-5.4
now returns only atomic action, claim, citation, ambiguity, boundary, and
evidence judgments; deterministic code owns overall validity. The unchanged
40-control packet and quality gates are retained, prior votes are not imported,
and pass, quality-failure, and malformed simulations all behave correctly.
Calibration 004 has fresh exclusive outputs, a ten-call/USD 3 ceiling, no
product-progression command, and no execution authority. The next human input
is authorization for this calibration only after a fresh clean preflight.

AFQC-054 records the researcher's explicit authorization for calibration 004.
Only its 40-control GPT-5.4 semantic review is allowlisted: at most ten calls,
zero retries, and the USD 3 emergency stop. Product development, the paired
control, private data, and the sealed 10,000-case run remain unauthorized.

AFQC-055 records calibration 004 as invalid and revokes AFQC-054. Three exact
GPT-5.4 calls covered 12 controls before a `clarify` vote omitted the mandatory
boundary reason. The first eight votes passed deterministic semantics, but the
third batch was rejected before hidden labels opened. The ledger records 7,036
input and 1,443 output tokens, 15.511 seconds aggregate latency, and USD
0.039235 cost. No later calibration, wording, product, control, private, or
final call occurred. Reviewer quality remains unmeasured; the next action is a
method-level decision rather than another silent contract revision.

AFQC-056 implements that method-level decision without starting another
reviewer-calibration loop. The build-only successor
`academic-factual-qa-open-10000-development-checkpoint-004` makes deterministic
source, action, claim, citation, boundary, and policy scoring the decision
authority. Exact `gpt-5.4-mini-2026-03-17` remains the public-question wording
and T0 generation model. Exact `gpt-5.4-2026-03-05` reviews wording and, only
after both response ledgers and deterministic scoring are complete, audits
every deterministic failure plus a seeded 40-case passing sample. Missing or
malformed post-score reviews are recorded as limitations and cannot change the
deterministic metrics; only a potential authoritative source-truth defect opens
researcher review. Five network-free terminal simulations pass, product inputs
remain physically separated from hidden gold, and all provider, paid, final
10,000-case, promotion, and deployment authority was initially false.

AFQC-057 records the researcher's explicit one-time authorization for this
500-case candidate plus 100-case control checkpoint. Official OpenAI metadata
was refreshed on 2026-08-28: both exact snapshots, recorded prices, Responses
API structured output, and `store: false` remain documented. Only checkpoint
004 now has bounded external-model and method-evaluation authority. The
untouched 10,000 cases, T1 confirmation, professor profile, promotion, and
deployment remain unauthorized.

AFQC-058 records checkpoint 004 as a valid wording-stage **Refine**. All 50
planned calls completed with exact identities and zero retries: 25 GPT-5.4 mini
author calls and 25 GPT-5.4 reviews. The stage accepted 452/500 questions
(90.4%), below the frozen 95% gate, while preserving 48 deterministic canonical
fallbacks, zero duplicates, and zero answer leaks. Reported use was 61,974
input tokens, 41,705 output tokens, 345.361 seconds aggregate provider latency,
and USD 0.555499. The runner stopped before any T0 candidate, control, scoring,
advisory-audit, private-data, or final-set call. All checkpoint-004 authority is
revoked. The wording result remains immutable and is not being rerun or
reinterpreted as a pass.

AFQC-059 records the researcher's decision to reuse that immutable mixed
wording package rather than rerun or retune the wording stage. The 452 accepted
model variants remain labelled as such; all 48 rejected cases use explicit,
byte-checked canonical fallbacks. This decision does not reinterpret checkpoint
004 as a pass.

AFQC-060 builds
`academic-factual-qa-open-10000-development-product-checkpoint-005`. It removes
wording calls entirely and prepares only the actual T0 product comparison: 500
structured-evidence candidate cases and the fixed paired 100-case any-hit
control. Both use the same corpus, retriever, exact GPT-5.4 mini generator,
policy, decoding, and public inputs. Hidden gold opens only after both response
ledgers are durable; deterministic scoring controls the decision. AFQC-061
replaces the overallocated routine review budget prospectively: exact GPT-5.4
nano audits routine failures and the seeded sample, while exact full GPT-5.4 is
reserved for at most 12 possible source-truth defects. Five finite simulations
and the complete gate pass. The maximum is 666 calls, zero retries, and USD 8.
AFQC-062 records the researcher's one-time authorization for checkpoint 005.
Attempt 001 stopped before provider I/O because the package command omitted the
locked Qwen3 retrieval extra. AFQC-063 corrected only that invocation. The sole
corrective attempt then loaded Qwen3 but did not finish the first course index
after more than 2 hours 15 minutes; a process sample showed a 14.7 GB footprint
on the 16 GB host. Both attempts recorded zero provider calls, responses,
tokens, or cost, and hidden gold stayed sealed. AFQC-064 revokes authority and
stops checkpoint 005. No product-quality conclusion or final 10,000-case claim
is available.

AFQC-065 selects an immutable, content-addressed retrieval-index lifecycle, and
AFQC-068 records its real local-Qwen qualification as `Keep`. Four exact
release-bound indexes over 2,100 public regions built in 532.408 seconds with
1,808.484 MiB peak RSS and 12.659 MiB of artifacts. Aggregate cold load was
0.372 seconds. A supplemental query-only check returned non-empty evidence for
40/40 queries with 40/40 identical rankings after a fresh index-store restart
and zero runtime document embeddings. The actual-product adapter verifies
prebuilt artifacts and cannot construct document vectors at startup.
Authorization is revoked; checkpoint 005 stays terminal and the final 10,000
cases remain closed.

Historical professor-checkpoint reviewer attempts 001–005 remain immutable
invalid operational evidence. Reviewer calibration is no longer the blocker
for #127 and none of those attempts is being retried. Issue
[#131](https://github.com/horiiiiii032929/digital-twin/issues/131) now owns the
separate provider-unauthorized true-visual 30-cluster/60-case supplement.

AFQC-066 was the one-time local authority, and AFQC-067 corrected a runtime
measurement omission before interpretation. Both generated result hashes are
registered, provider/private/product/final access was zero, and no execution is
now authorized. Issue #139 may close after PR #140 merges; #127 may prepare one
new 500+100 actual-product checkpoint but cannot execute it without separate
authorization.

AFQC-029 records the researcher-directed reliability correction. Attempt 005
keeps the exact Gemini 3.7 Flash revision and immutable Codex votes but replaces
the failed single AI Studio route with a bounded OpenRouter allowlist: Vertex
global priority/default followed by AI Studio priority/default. The runner
records the actual provider and service tier for every completed call while
holding model identity fixed. Its network-free simulation and live preflight
passed, but AFQC-031 records the live run as invalid after the third batch
violated a deterministic semantic invariant. Only 8/40 Gemini votes were
accepted, so no calibration metric is valid. No execution is now authorized.
This is historical evidence and no longer defines the immediate checkpoint.
The sealed 200-case panel is not being opened; visual work and private data
remain unauthorized.

The repository-wide correctness baseline was completed on `main` at merge revision
`db2f5e9` through PR
[#98](https://github.com/horiiiiii032929/digital-twin/pull/98):
the current branch now extends it to 649 executable or execution-affecting
files, including the retrieval-index lifecycle. All are audited with zero pending files and
zero open findings. The canonical verification gate
now fails if pending or open records reappear. The execution freeze remains
active for all general evaluation actions across 97 protected entrypoints. It protects the corrected deterministic
reference-package builders; no
provider, paid, method-evaluation, held-out, or final execution is active. The first open-benchmark
construction attempt is preserved as operationally invalid: its first DeepSeek
canary returned the requested model but a different runtime fingerprint, so the
executor stopped before Gemini or any bulk call. Zero development clusters were
processed; provider usage and cost are unavailable rather than claimed as zero.
The sealed final 10,000-case stage and held-out scoring remain unauthorized.
Provider binding 002 kept exact model and route checks while recording the
DeepSeek runtime fingerprint diagnostically. Both canaries passed, but the
first bulk DeepSeek author response used `items` instead of the frozen
`questions` field. Attempt 002 is therefore preserved as `invalid-execution`:
3 completed calls, 2,206 input and 477 output tokens, USD 0.00213626, and zero
accepted development clusters or cases. Authorization is revoked. The result
does not evaluate dataset or T0 quality, and the final 10,000-case execution
remains unauthorized.
Attempt 003 corrected the exposed harness gap without weakening
the schema: malformed author content remains rejected and hash-recorded, while
the cluster uses explicitly labelled deterministic canonical wording before the
independent verifier. Its bounded execution is preserved as `invalid-execution`:
16 calls were attempted, 15 completed, Google AI Studio failed one verifier
request, and USD 0.04438559 was reported. Four of seven author responses needed
canonical fallback and three DeepSeek verifier responses violated the schema.
No dataset package or product run was produced. AFQC-043 revokes authority and
requires a method-level construction decision rather than attempt 004. The
final 10,000-case execution remains unauthorized.
AFQC-044 resolves that method decision prospectively: deterministic v2
construction produced all 500 development cases, hidden gold, and the paired
100-case control without a provider call. The first validation caught 15
question cues that repeated their complete canonical answer; the fail-closed
cue logic was corrected before any output was written. The final package has
zero such leaks and zero normalized duplicates. Direct first-party OpenAI
`gpt-5.4-mini-2026-03-17` and Mistral `mistral-small-2603` contracts are
network-free tested with strict schema, exact identity, bounded transport-only
retry, and durable accounting. Credentials, fresh retention/pricing checks,
and separate paid authority are still required before product execution, but
they are no longer the first blocker: AFQC-046 keeps the corrected reference
layer, and the next bounded work is wording-only paraphrase/review before any
paid T0 run.
The proactive-outreach branch adds the A1 network-free development and
publication-integrated confirmation. Development completed as **Go Deeper**;
confirmation completed as **Refine** after 59/60 actions and reasons passed but
one supported paraphrase was missed by the lexical support gate. Both one-time
authorizations are revoked. No provider, paid, private-data, external-delivery,
or real-student operation is authorized.
Manual review found material source-design
defects in the unexecuted `factual-qa-v3-scale-rehearsal-001`, so its bounded
authorization was revoked. The corrected
`factual-qa-v3-scale-rehearsal-002` source and evaluation logic completed manual
review, but its one-time execution is invalid: all 120 author calls completed
before the first-party Mistral ZDR route returned an upstream authentication
failure. Its authorization is revoked and the invalid artifact is preserved.
Unexecuted successor `factual-qa-v3-scale-rehearsal-003` was superseded after the
researcher allowed provider data collection for this synthetic evaluation
phase. Reviewed `factual-qa-v3-scale-rehearsal-004` preserves the two pre-bulk
provider canaries, explicitly allows collection and retention only for committed
synthetic-public fixtures. Its one-time execution completed at clean revision
`6a75410`: 114/120 cases passed deterministic provenance and retrieval recovered
all required evidence in the top three for 96/96 answerable cases, but the
independent reviewer detected only 10/20 controlled mutations. It accepted every
missing- and truncated-citation defect, failing the 90% sensitivity gate. The
completed 12-case manual audit confirmed all six deterministic quarantines and
accepted six stratified controls. The decision is **Refine**; authorization is
revoked and 10,000-case scale remains closed. No path permits private or held-out
data, and the wider freeze remains active.

Successor `factual-qa-v3-scale-rehearsal-005` made exact target-claim, full
evidence-quote, verbatim-source, and no-extra-claim checks explicit. Its paid run
is invalid: both canaries and the pre-dispute stages completed, but one malformed
DeepSeek dispute response aborted the result before completed metrics and exact
accounting were persisted. Authorization is revoked. The correction is a small,
durably checkpointed reviewer qualification rather than another 120-case rerun;
10,000-case execution remains unauthorized.

Completed `factual-qa-v3-reviewer-qualification-006` replaced another full
rehearsal with 24 new deterministic clean/defect pairs. Mistral accepted all 24
clean controls and rejected all 24 defects, including 4/4 in every mutation
class. All 49 calls completed in 16.04 seconds for USD 0.012175 with zero
malformed/provider errors. The strict reviewer is kept as advisory quality
control for the 10,000-case design; deterministic lineage remains authoritative.
The one-time 006 authorization is revoked. The subsequent 24-pair hosted
Qwen3.7 Plus qualification 007 failed six gates: only 41/48 reviews were
contract-valid, clean specificity was 75.0%, mutation sensitivity was 83.3%,
reviewer p95 latency was 42.46 seconds, and measured cost was USD 0.128239.
The provider returned more output tokens than the requested cap, exposing that
the prospective reservation did not enforce the USD 0.10 limit. Qwen is not
selected, its one-time authorization is revoked, and qualified Mistral Small 4
remains the advisory reviewer. Cost enforcement was hardened before the two
paid 100-case attempts. Corrected attempt 002 completed safely as **Refine**:
93/100 cases passed deterministic validation, all 85 answerable cases had valid
citations, reviewer agreement was 97/100, and all 20 mutations were rejected.
Boundary handling, one multi-source claim binding, duplicate questions, and two
malformed outcomes still failed their gates. Its authorization is revoked; the
1,000- and 10,000-case stages remain unauthorized.

The provider-free successor is now implemented as
`factual-qa-v3-10000-pipeline-002`. On 2026-08-22 the researcher authorized and
completed exactly pilot 003, then revoked its one-time authorization.
Deterministic code owns canonical questions and answers, actions, claims, exact
quotes, citations, boundary reasons, and hashes; a model may propose only
question wording. Historical pipeline 001 remains unchanged. Pipeline 002
corrects its cross-course boundary mismatch prospectively, producing exactly 8,000
answerable and 2,000 empty-lineage boundary packages. All 10,000 are byte-stable
and normalized-question unique. The paid confirmation passed every gate:
100/100 deterministic-valid cases, 80/80 answerable citation-valid cases,
99/100 reviewer agreement, 20/20 mutation rejection, zero exact duplicates,
and zero malformed outcomes. A separate provider-unauthorized checkpoint now
selects exactly the additional 900 cases needed for cumulative 1,000-case
evidence. Its complete network-free simulation passed every gate with 1,982
simulated calls. Paid attempt 001 then stopped safely before bulk work because
its 67-character reviewer-canary task identifier exceeded the shared
64-character local contract. DeepSeek returned one health response, no Mistral
request or bulk call was made, and cost was USD 0.00004092. Attempt 001 is
invalid and revoked. Corrected attempt 002 then completed as **Keep**: 900/900
new cases were deterministic-valid, 720/720 answerable cases were citation-valid,
reviewer agreement was 898/900, and 179/180 controlled mutations were rejected.
The two false reviewer rejections were resolved and direct review confirmed the
single missed mutation was still caught by deterministic validation. Across the
cumulative 1,000 cases, deterministic validity is 1,000/1,000, citation validity
is 800/800, reviewer agreement is 997/1,000, mutation detection is 199/200, and
there are zero exact duplicates. Attempt 002 authorization is revoked; its
separately authorized successor result is recorded below.

The professor-requested approximately 10,000-row dummy factual-QA pipeline
milestone is complete. `factual-qa-v3-scale-completion-10000-001` finished as
**Keep for engineering pipeline scale** on
the exact remaining 9,000 truth packages: 7,200 answerable, 900 abstain, 450
clarify, and 450 refuse. All 9,000 were deterministic-valid, all 7,200
answerable cases had valid citations, boundary accuracy was 1,800/1,800,
reviewer agreement was 8,927/9,000, and advisory mutation detection was
1,795/1,800 while deterministic validation rejected all 1,800 mutations. There
were zero exact duplicates, 19,874 responses from 19,875 attempts, and USD
7.632671 cost. All predefined gates passed.

Direct review confirmed 12/12 priority cases as valid and separately confirmed
the five advisory mutation misses as genuine defects that deterministic checks
caught. Across all 10,000 cases, deterministic validity is 10,000/10,000,
citation validity is 8,000/8,000, reviewer agreement is 9,924/10,000, and
advisory mutation detection is 1,994/2,000. The one-time authorization is
revoked, the completion instrument is removed from the bounded allowlist, and
no further factual-QA scale is authorized. Analysis correction 001 establishes
that the author received canonical answers, claims, and citations and only
varied question wording; final answer metadata was copied from the truth
package. The rows derive from eight claim grammars and correlated template
families. This is not evidence that the Digital Twin independently retrieved
and answered 10,000 questions, and the row count is not an academic
independent-sample claim. It remains engineering evidence for deterministic
dataset assembly, provider workflow, mutation checks, latency, and cost.

Issue #127 now has a clean paired development result for the leakage-free
successor. On 160 synthetic-public cases across 80 clusters, the any-hit control
released 34/80 boundary requests as answers and achieved only 50% citation
precision. The structured evidence-selection ablation and two-boundary candidate
both passed 160/160 development cases, retained 80/80 supported answers, released
zero boundary answers, and achieved complete expected claims and citations.
All 160 ablation/candidate draft hashes matched, so the post-generation boundary
was not confounded by different drafts. The run used clean revision `74dcf8c`,
zero provider calls, zero cost, and no private or held-out data. The decision is
**Go Deeper**, not Keep: questions and source aliases came from the same
unblinded synthetic design, labels were not independently validated, and clean
drafts did not measure naturally occurring claim errors. Authorization is
revoked. The next academic checkpoint requires fresh independently validated
source/question clusters with frozen gates; no product promotion follows from
the 100% development score.

Confirmation 001 preregistered 200 cases in 100 independent source/question-
family clusters and an external two-human review workflow. It was never opened
or executed and is preserved unchanged. Because external review of all 200
cases is not feasible within the schedule, confirmation 002 now supersedes only
its review method. The sampling, product conditions, metrics, gates, and
cluster-aware analysis remain fixed. Deterministic source-derived fields remain
authoritative; an isolated blinded Codex task, Mistral Small 4, and DeepSeek V4
Pro reviewers cover all 200 cases after passing 40 planted controls. Automatic semantic
acceptance requires three-model unanimity, every disagreement goes to the
researcher, and a seeded balanced 20-case unanimous sample is also audited. If
disagreements exceed 40, the panel fails, bounding researcher review at 60
cases. This can produce only LLM-panel-reviewed, researcher-audited silver
evidence, not independent human ground truth.

The public-source build checkpoint is now complete. Four exact educational
repository revisions contribute 160 non-overlapping section sources: 120 for
100 confirmation clusters and 40 reserved for disjoint calibration controls.
The deterministic set contains 200 cases—100 answerable and 100 boundary—with
the frozen text, code, table, diagram, equation, ambiguity, scope, integrity,
permission, and unsupported-premise allocations. Exact normalized duplicates
and selected source-range overlap are both zero. File, section, dependent-asset,
license, dataset, and packet hashes are bound; complete public repositories
remain ignored under `data/external/`, and no Academia Vault or private data was
read. The blinded 240-item reviewer packet and atomic resume/accounting runner
pass clean, calibration-failure, disagreement-overflow, malformed-output, and
resume-drift simulations. These are build checks, not reviewer or product
results. The reviewer-binding successor now freezes a fresh isolated
`gpt-5.6-sol` Codex task, exact Mistral Small 4 ZDR/no-fallback routing, and
direct DeepSeek V4 Pro using current peak prices. Its two-phase executor
requires all three reviewers to pass calibration before confirmation, allows
120 provider calls with zero retries, checkpoints atomically, and enforces a
USD 3 emergency stop. The full network-free 720-judgment simulation passes and
the metadata-only live check reports no drift. AFQC-017 authorized one bounded
40-control calibration. The isolated Codex reviewer passed all four gates at
1.00, but the first Mistral batch stopped at the strict transport/parser
boundary before any provider vote was accepted; DeepSeek and confirmation were
never opened. Attempt 001 is therefore **invalid execution**, not a quality
failure. Its authority is revoked under AFQC-018. The ledger's USD 0 is
incomplete accounting rather than verified zero spend because the old failure
path retained neither provider usage nor exact error detail. After hardening
that path, AFQC-020 authorized corrective attempt 002 at clean revision
`d79bda5`. Its first Mistral batch again failed before any vote was accepted,
this time with a durable sanitized HTTP 400 record, 1.437-second latency, and
explicit unavailable usage/cost accounting. There was one provider call, zero
retries, zero DeepSeek calls, and no confirmation access. Attempt 002 is also
**invalid execution**, not a quality failure. AFQC-021 revokes all authority and
requires a reviewer-method redesign rather than another Mistral retry.
Confirmation, product binding, researcher audit, private data, promotion, and
the final tranche remain unauthorized.

AFQC-022 records the prospective successor research decision. OpenRouter
Gemini 3.7 Flash revision `20260813` through Google AI Studio is the build-only
default because it is a separate model family, currently reports 99.94% uptime,
1.71-second median latency, and 193 tokens/second, supports structured output,
and can also serve the later visual qualification. Google Vertex is cheaper but
currently slower and less available. The transport must use only the documented
Gemini JSON-Schema subset and move uniqueness plus full semantic validation
into deterministic local code. Qwen remains rejected by qualification 007;
Gemini 3.6 and Kimi remain fallbacks. Current conservative reservations are
USD 0.406 for calibration and USD 2.44 for the complete panel. This decision
authorizes no provider call. Promotional pricing and endpoint metadata must be
refreshed within 24 hours of any separately authorized execution.

AFQC-023 records the immutable build for calibration attempt 003. The existing
40 controls, 200-case sealed packet, deterministic truth, and 40/40 Codex votes
are unchanged. Only the failed Mistral reviewer slot is replaced by exact
Gemini 3.7 Flash revision `20260813` through the standard Google AI Studio
endpoint; direct DeepSeek V4 Pro remains the third reviewer. The Gemini request
uses the documented schema subset, with completeness, identity, uniqueness,
visible-evidence lineage, and semantic consistency enforced locally. The
20-call network-free simulation runs one Gemini and one DeepSeek canary first,
passes all calibration gates, and stops without opening confirmation. A fresh
metadata-only preflight found both credentials and zero model, endpoint,
pricing, routing, parameter, or retention drift; only the deliberate execution
locks remain. Google AI Studio currently retains these public evaluation inputs
for up to 55 days and does not train on them. No paid call has occurred at this
build checkpoint.

AFQC-024 is the one-time execution checkpoint. It authorizes only the 40-control
attempt-003 calibration under the existing 20-call, zero-retry, USD 0.406426
reservation, and USD 3 emergency stop. The 200-case panel, visual work, live T0
product execution, private data, and 600/10,000-case stages remain locked. This
authority must be revoked after a pass, quality failure, or invalid execution.

AFQC-025 records attempt 003 as **invalid execution** and revokes AFQC-024.
Gemini completed its four-control canary through the exact Google AI Studio
route, reporting 2,656 input tokens, 1,551 output tokens, 5.193 seconds, and USD
0.00780825. The direct DeepSeek V4 Pro canary then returned empty content. The
runner stopped after two calls with zero retries and zero bulk calls; all 200
confirmation cases remained sealed. DeepSeek usage and cost are unavailable,
so the Gemini amount is known partial cost rather than complete accounting.
This result supports no reviewer, factual-QA, product, or release-quality claim.
No evaluation execution is currently authorized.

AFQC-026 records the finite reviewer-method successor. Attempt 004 contains
only two reviewer families: immutable calibrated Codex `gpt-5.6-sol` votes and
exact Gemini 3.7 Flash through Google AI Studio. DeepSeek has no reviewer,
credential, pricing, route, call, or tie-break role in this attempt. Gemini must
review all 40 controls in ten fresh four-case batches; no attempt-003 vote is
imported. Only timeout, connection failure, HTTP 429/5xx, or empty content may
retry, once per batch and at most twice globally, with every failed call kept
in the ledger. The network-free pass and failure simulations succeed, and the
metadata-only live check reports zero drift and zero inference calls. The
maximum reservation is USD 0.211968 under the existing USD 3 stop. AFQC-027
authorized exactly one paid calibration. AFQC-028 records that run as invalid:
the first Gemini batch and its one permitted retry both returned HTTP 429.
There were two attempted calls, zero provider completions, zero accepted Gemini
votes, zero later batches, and no confirmation access. Provider usage and cost
were unavailable, so the ledger's USD 0 is not proof of zero charge. Authority
is revoked, attempt 004 cannot be rerun, and the reviewer search is stopped.

AFQC-029 records the fixed-model resilient transport successor. Attempt 005
keeps the immutable 40/40 Codex votes and exact Gemini 3.7 Flash revision, but
uses a bounded OpenRouter allowlist across Google Vertex global priority/default
and Google AI Studio priority/default routes. AFQC-030 now freezes and authorizes
only this 40-control calibration for at most ten primary calls plus two
transport-only retries, a USD 0.3815424 reservation, and the existing USD 3
emergency stop. The sealed 200 cases, visual and live-product evaluations,
private data, and 600/10,000-case academic stages remain unauthorized.

AFQC-031 records attempt 005 as **invalid execution** and revokes AFQC-030.
OpenRouter successfully routed three calls to Google Vertex priority with exact
model identity and complete accounting. The first two batches produced 8
accepted Gemini votes. The third response completed at the provider but failed
the frozen deterministic semantic validator because one boundary vote was
internally inconsistent; malformed semantic output is deliberately
non-retryable. The run stopped after 3 calls, 10,393 input tokens, 5,220 output
tokens, and USD 0.024632775 reported cost. No confirmation case opened. This
result supports no Gemini calibration or product-quality claim, and no
evaluation execution is currently authorized.

The current metadata checkpoint also found that older prospective DeepSeek
prices in the repository were stale. Pilot 003 binds the current documented
DeepSeek V4 Flash 0731 and V4 Pro 0813 revisions using conservative peak prices,
plus exact OpenRouter `mistralai/mistral-small-2603` routing with fallback
disabled. The frozen policy snapshot records DeepSeek account-linked retention
and PRC storage plus the OpenRouter registry's 30-day, no-training Mistral
policy. Only synthetic-public fixtures are permitted. Historical result
bindings were not changed. Paid execution requires another live metadata check
within 24 hours.

The complete locked dependency set now reports zero known Python or JavaScript
vulnerabilities and has no active exceptions. The optional retrieval stack was
upgraded to Torch 2.13.0, Transformers 5.15.1, and Sentence Transformers 6.0.0;
historical retrieval results remain bound to their old environment, and the
upgraded stack is not selected until a new post-freeze evaluation is authorized.

The runtime-boundary checkpoint is complete. Persistence updates are
non-destructive, release content is immutable, staging evidence is resolved
from successful server-side ingestion jobs, storage deletion is durable and
retryable, backup/restore is bounded and atomic, and concurrent student turns
converge on one response with authoritative citation metadata. The merged local
gate passes 1,106 Python tests and 47 frontend tests, frontend lint, and the
production build. This is a correctness closure, not a renewed deployment or
model-selection claim.

The onboarding and policy checkpoint is also complete. Professor session writes
now reject stale updates and owner takeover, each reviewed setup is bound to one
course, and source or policy changes revoke approvals that no longer match the
reviewed state. Preview decisions must match the current policy version, every
custom preview must be accepted, and staging release creation now carries only
server-owned ingestion job IDs from the browser. Rendered desktop navigation
from tutor setup to course delivery passed without console errors; the broader
frontend and cross-browser audit remains open.

The active-runtime audit is now complete at 99/99 inventoried files. Identity
security mutations and their audit records commit atomically; course ownership
creation is atomic; account, owner, and membership roles cannot drift; one
published release per course is enforced in SQLite; and repository writes
revalidate copied domain models. Publication cannot bypass evaluation/policy
gates, expired ingestion workers cannot finalize jobs, chunked uploads are
stream-bounded, rate-limit storage is bounded, and readiness checks all durable
connections. These corrections remain covered by the 1,106-test Python suite.
Frontend, verification, tooling, evaluation configuration, and historical
artifacts are also fully dispositioned in the current 649-file audit.
Evaluation execution remains frozen, with 97/97 protected entrypoints registered
and no prospective evaluation in the bounded allowlist. The completed A1 runs
have been removed from the bounded allowlist; no proactive-outreach execution is
authorized.

## Current outcome

The active goal is to release the system, not to maximize any individual
benchmark. The [release plan](release-plan.md) defines a hosted R1 release
candidate, an approval-gated R2 invite-only pilot, and an R3 final project
release. The [real-world product scope](../research/00_admin/2026-08-18-real-world-product-scope.md)
continues to define the product; evaluation tracks are evidence gates toward
that release.

On 2026-08-27, the project owner clarified that a Professor Digital Twin must
also be able to initiate an interaction rather than only respond to a student
turn. Issue [#134](https://github.com/horiiiiii032929/digital-twin/issues/134)
and [`proactive-outreach-001`](proactive-outreach.md) now own this core product
track. The build-only vertical slice provides opt-in private in-app check-ins,
source-linked deterministic triggers, quiet-hour/snooze/frequency suppression,
atomic idempotent materialization, withdrawal cancellation, and a disabled
Discord private-destination adapter. It makes no external-delivery or
real-student claim; the component remains `Go Deeper` pending a frozen synthetic
evaluation and separately gated worker/channel activation.

The 2026-08-27
[mixed-initiative tutoring review](../research/01_literature/2026-08-27-proactive-mixed-initiative-tutoring.md)
narrows the next research step. Professor-scheduled outreach is autonomy level
A0; deterministic evidence-recovery is the first A1 autonomous candidate.
Learner-state or misconception triggers remain shadow-mode-only until their
precision and interruption cost are measured. `No action` is a valid decision.
The current branch now implements the A1 detector in shadow-by-default mode: it
finds persisted no-evidence turns, searches only evidence lineage newly added by
the current release, applies a deterministic lexical support gate, and preserves
consent, snooze, membership, idempotency, and citation authority. Active mode
fails closed unless explicitly enabled. The Discord request builder is corrected
to emit only a generic alert and authenticated in-app deep link. Neither A1 nor
Discord is selected or enabled for real delivery. The frozen development
execution completed as **Go Deeper**: 12/12 P0 checks, 20/20 expected actions
and reasons, and 10/10 supported current-release lineage checks passed, with
zero provider calls, private-data reads, external deliveries, persisted shadow
triggers, tokens, or cost. This is synthetic mechanism evidence around one
source topic, not evidence of useful real-student intervention or learning
improvement. The one-time authorization is revoked; A0 remains the release
control and A1 requires a method-level support successor on fresh cases.

The next build-only integration now invokes A1 exactly once in shadow mode after
a new release is durably published. It does not run on rollback. A scanner
failure cannot reverse or falsely fail the completed publication; instead, the
system records a redacted failure type with no question or exception text. The
hook creates no trigger, message, outbox item, provider call, or external
delivery. Confirmation 002 executed 12 synthetic source clusters across
operating systems, networking, data structures, and Python, expanding to 60
cases (24 expected proposals and 36 no-actions). It completed as **Refine**:
59/60 actions and reasons, all 36 no-actions, all 12 integration checks, every
observed source-lineage check, and every zero-side-effect boundary passed. The
single failure was a supported hash-collision paraphrase: retrieval found the
correct source, but raw-token query coverage was 4/9 rather than the frozen 50%
minimum because the method does not normalize inflections or semantic
equivalence. The failure was conservative and released nothing. Authorization
is revoked; A0 remains the release control and A1 remains shadow-only. This is
synthetic integration evidence, not a representative student or learning
study.

The project owner accepted
[`autonomous-tutoring-graph-001`](autonomous-tutoring-graph.md) as the
student-facing architecture decision on 2026-08-21. The existing student
workflow is now named as the T0 grounded control. The build-only T1 successor
now adds a typed learner-state contract, deterministic pedagogical-intent
selection, a fixed LangGraph path, one-repair maximum, deterministic fallback,
atomic SQLite state revisions, race rejection, restart recovery, and an
explicit local demo/test mode. Its ten-trajectory network-free development
execution completed as **Go Deeper** at clean revision `51eb43a`: every T0
action and T1 action/intent matched, citation, fallback, persistence, and
restart checks were 100%, and no safety violation or provider use occurred. Its
one-time authorization is revoked. Staging still rejects T1 until one
separately frozen confirmation and release-profile decision pass. T2 applies
the professor-approved policy to the
same graph and remains pending professor-profile guidance. On 2026-08-21 the
professor replied “sounds good” after the deterministic source-linked Q&A and
separate C0-C3 directions were proposed. This is recorded as acknowledgment of
the working direction, not approval of every evaluation parameter or of the
explicit-versus-inferred professor-profile method.

PR [#83](https://github.com/horiiiiii032929/digital-twin/pull/83) merged the
reviewed conversation-first professor and student workspaces into `main` at
`acaaecd`. Issues #82 and #84 are `Done / Keep`. The merged flow passed the
recorded repository checks, 19/19 synthetic publication/student checks,
responsive browser QA, and independent Impeccable review. This establishes the
product UX baseline; it does not establish human usability or production
readiness.

Issue [#88](https://github.com/horiiiiii032929/digital-twin/issues/88) remains
in progress. Its V7 in-process result was **Go Deeper**, while the later V8
current-image result is **Refine**. The post-correctness V7 candidate at
clean implementation revision `f553be5` passed 42/42 current in-process checks:
credentialed professor/student journeys, server-owned ingestion lineage,
policy approval and publication, grounded answers and citations, restart,
schema-v8 backup/restore, security, lifecycle, and bounded capacity. Its
100-request error rate was 0%, API p50/p95 was 2.717/3.073 ms, ingestion was
52.342 ms, and dependency audits reported zero known vulnerabilities. The run
used no external model and no private data.

`deployable-product-foundation-freeze-v7` now binds that result to 14 current
runtime trees and 17 critical files. It makes no current container-image or
release claim. A later controlled Docker restart recovered the engine and
exposed two release-critical facts in attempt V8. First, the image omitted the
documented bootstrap, backup, restore, and lifecycle commands; the image now
copies those exact operational entrypoints and no broad tooling tree. Second,
the rebuilt API, worker, and Caddy containers became healthy, clean
administrator bootstrap worked, and source ingestion reached release
publication, but the real product profile correctly refused publication with
`evidence_sufficiency_required`. Evidence-sufficiency v1 selected no safe
method, while the 42/42 in-process harness explicitly injected an AnyHit test
control. V7 therefore proves those mechanics only under its synthetic control;
it does not prove a releasable product configuration. Attempt V8 is **Refine**
with no selected release candidate. A prospective evidence-sufficiency
successor must pass before public DNS/TLS, clean-host restore, and the public
walkthrough can support release.

Issue [#105](https://github.com/horiiiiii032929/digital-twin/issues/105) owns
that successor. V10 implemented a provider-neutral open-set gate that keeps
semantic scoring separate from the final answer/abstain policy and fails closed
for incomplete, contradictory, ambiguous, malformed, or unknown-lineage
evidence. A post-V9 review also corrected malformed plain-object verifier output
so it now follows the same redacted fail-closed path as raised verifier errors.
The historical deterministic 120-case synthetic-public decision draft contains
80 answerable and 40 abstain cases across nine slices and 40 source versions.
All answer cases bind exact active-source claims and quotes; all abstain cases
have empty authoritative lineage. The later full Codex audit inspected all 120
cases and found three benchmark-design gaps rather than answer-ground-truth
errors: the multi-evidence cases reused one source, permission/version cases did
not expose the stale pair, and the priority packet omitted three high-risk
slices. Corrected successor draft 002 fixes those gaps under a new hash and, at
that checkpoint, remained unfrozen pending four human policy/scope
confirmations. V12 binds a
deterministic review workflow: 12 blinded ten-case batches, six clean controls,
six planted defect classes, strict judgment accounting, and a maximum 12-case
priority packet. Its 132-judgment network-free simulation passes, but that is
orchestration evidence rather than review evidence. Prospective review
instrument `002` binds exact OpenRouter Mistral Small 4 routing, current
published pricing, synthetic-public inputs, and a USD 0.50 ceiling. Its new
sensitivity-first execution runner passed a complete 13-call/132-judgment
network-free simulation, checkpoint/resume and failure regressions, and the
complete repository gate. A clean live no-call preflight found matching model
metadata and pricing, an available credential, and an unused output path. It is
then blocked only by the three deliberate authorization locks. After explicit
authorization, attempt 002 made the sensitivity call once. The exact Mistral
identity matched, but its response failed the strict JSON/schema contract, so
the runner stopped before all 12 bulk batches. The invalid attempt used 3,861
input and 1,519 output tokens, cost USD 0.00149055, and recorded no accepted
judgment. Because the frozen runner did not preserve the malformed content or
exact parser error, no reviewer- or dataset-quality conclusion is valid.
Authorization is revoked and the unfavorable attempt is registered. Successor
`evidence-sufficiency-v2-independent-review-003` requested a per-batch strict
JSON Schema from an endpoint that advertised structured-output support, retained
malformed response content and exact parser detail, and preserved immutable 002
compatibility. Its 13-call/132-judgment network-free simulation, focused failure
and resume regressions, 792-test repository gate, and clean live no-call
preflight passed. After separate authorization, the paid execution stopped on
the first sensitivity call because the transport raised
`LlmAuthenticationError` before any provider response. No bulk batch ran, no
judgment was accepted, and provider-reported token use and cost were zero. A
read-only OpenRouter current-key check immediately afterward returned HTTP 200,
so the key existed and authenticated; the precise inference-path rejection was
not exposed by the frozen adapter. Attempt 003 is therefore invalid operational
evidence, not a reviewer- or dataset-quality result. Its authorization is
revoked. The draft remains unfrozen and unopened; no exact evidence-sufficiency
verifier is selected, and candidate execution remains unauthorized.
Successor `evidence-sufficiency-v2-independent-review-004` now calls
OpenRouter's official native chat-completions API rather than routing
inference through the opaque wrapper. It preserves sanitized upstream status,
message, request and generation IDs, and routing attempts; its exact
13-call/132-judgment network-free simulation, failure regressions, and clean
live no-call preflight passed. After separate authorization, its first native
sensitivity request reached OpenRouter routing but produced no provider
response: native router metadata recorded two first-party Mistral endpoint
attempts with statuses 400 and 401, followed by HTTP 401 `Provider returned
error`. All 12 bulk batches were suppressed. The same credential authenticated
against OpenRouter's current-key endpoint with HTTP 200 immediately afterward.
No judgment, reported token, or cost exists, so review 004 is invalid
operational evidence and supports no reviewer- or dataset-quality conclusion.
Authorization is revoked. The native runner build remains **Go Deeper**, while
the exact OpenRouter/Mistral execution binding is **Drop** and the product
decision remains **Refine** with no selected implementation. Because its source
tree differs from V8, the V8 image identities are historical evidence; the
current source has no image or publication claim.

Prospective `evidence-sufficiency-v2-independent-review-005` replaces only that
dropped reviewer binding. It pins stable `google/gemini-3.7-flash` to the exact
Google AI Studio standard endpoint through native OpenRouter routing, records
the dated backend identity `google/gemini-3.7-flash-20260813`, requires strict
structured output, and disables retries and fallbacks. Its 13-call/132-judgment
network-free simulation and complete repository gate pass. A clean live
metadata-only preflight found no provider mismatch, a present credential, an
unused output path, and exactly three deliberate locks: provider authorization,
instrument freeze, and bounded-freeze allowlisting. The USD 0.39 maximum
reservation remains below the USD 0.50 ceiling. No inference call occurred;
review 005 is build-only and provider-unauthorized.

`evidence-sufficiency-v2-independent-review-006` preserved review 005 unchanged
and replaced its unexecuted reviewer binding before any quality result existed.
Current official-model and endpoint research selected the exact
OpenRouter `openai/gpt-5.4-mini` standard route with dated backend
`openai/gpt-5.4-mini-20260317`: it is cross-family from the DeepSeek generator,
supports strict structured output, and fits the same 13-call boundary. Because
the endpoint does not advertise `temperature`, review 006 omits it and instead
fixes reasoning effort to `none` and seed to `0`. The USD 0.429 maximum
reservation remains below the USD 0.50 ceiling. This is a prospective
quality-first choice, not evidence that GPT-5.4 mini has passed the project
rubric. The separately authorized run stopped on its first sensitivity request:
OpenRouter returned HTTP 400 `Provider returned error` before any provider
response. No bulk call, judgment, reported token, or cost occurred; the current
key endpoint returned HTTP 200 immediately afterward. The result is invalid
operational evidence and supports no reviewer- or dataset-quality conclusion.
Authorization is revoked and this exact OpenRouter/GPT binding must not be
retried. Review 005 remains preserved and unexecuted rather than becoming an
outcome-based fallback. Issue #105 now requires one explicit method-level
decision instead of another OpenRouter prompt or routing refinement.

Review 007 applied that method-level correction without changing
the reviewer model or dataset. It keeps GPT-5.4 mini, the dated model snapshot,
strict structured output, deterministic authority, zero retries, and the
sensitivity-first stop. It removes nonessential reasoning and seed parameters,
allows OpenRouter to fall through from OpenAI to compatible Azure capacity for
the same model, and raises the emergency ceiling to USD 1.50 using a USD 0.858
worst-case reservation. The network-free 13-call/132-judgment simulation and
live metadata-only match passed. Its separately authorized run again stopped
on the first sensitivity request with HTTP 400 before any provider response.
OpenRouter exposed only the OpenAI endpoint as compatible under the request
contract and did not select it successfully; the Azure fallback did not become
an available route. The current-key endpoint still returned HTTP 200. No bulk
call, judgment, reported token, or cost occurred. Review 007 is invalid,
authorization is revoked, and the OpenRouter reviewer path must not be retried.
Dataset freezing and every downstream decision remain unauthorized.

Review 008 completed its direct DeepSeek sensitivity call at clean revision
`d55f256`. The exact model and fingerprint matched, the JSON contract was
valid, and all six clean controls were approved, but the reviewer detected only
5/6 deliberate defects. It incorrectly approved a wrong abstention for a
directly answerable linearizability question, missing the prospective 100%
sensitivity gate. The runner suppressed all 12 bulk batches after one provider
response, 3,819 input and 1,282 output tokens, 12.63 seconds, and USD
0.002776605. This is a valid reviewer-quality failure: review 008 is dropped for
this contract and authorization is revoked. The 120-case draft remained
unopened, so dataset freeze, candidate evaluation, and product selection remain
unauthorized. Issue #105 now moves to deterministic checks plus a bounded
researcher audit rather than another model or prompt search.

Deterministic audit 001 has now completed that bounded review. Draft 001 remains
immutable, while draft 002 has 15/15 distinct-source multi-evidence cases,
10/10 exact stale-version distractors, all seven high-risk slices in its
12-case priority packet, and zero exact normalized duplicates. The audit used
zero provider calls and no private data. Its one-time local-write authorization
is revoked. The researcher subsequently confirmed all four policy/scope
examples. Decision freeze 001 now binds immutable draft 002 and the confirmation
packet by exact hashes. The 120 cases are frozen and unopened; candidate
evaluation and every model, paid, private-source, and release authority remain
closed.

Candidate-comparison build 001 now implements the already-defined method
families without opening those cases. It fixes course-scoped eligible BM25 as
the controlled, non-gold retrieval input; keeps AnyHit unselectable; and binds
three selectable methods: an inspectable deterministic feature control, a
149M-parameter GTE ModernBERT cross-encoder support verifier, and the same
support verifier augmented by pairwise DeBERTa-v3-base NLI contradiction
checks. Both model revisions and Apache-2.0 licenses were verified against
official metadata on 2026-08-24. The runner records all 120 decisions,
lineage, mutation sensitivity, slices, latency, and peak memory with zero
provider calls. Its network-free simulation passes and its no-call preflight is
blocked only by candidate, local-model, and decision-split authorization. The
dataset remains unopened and no candidate is selected.

The separately authorized comparison then opened the corrected 120-case split
once at clean revision `1da528e` and completed validly as **Refine**. AnyHit
remained unselectable and failed with 39 false answers. The deterministic
feature control produced zero false answers but only 8.8% answer recall. GTE
support and GTE-plus-NLI each produced seven false answers, 15.0% answer
recall, 48.8% balanced accuracy, zero multi-evidence recall, and seven lineage
failures. Both learned methods passed the local latency and memory gates, but
NLI added no aggregate quality and produced false contradiction signals in the
priority audit. Codex reviewed all 12 prioritized cases and confirmed the
frozen labels and retrieval contract; no data or harness correction is needed.
Authorization is revoked, no gate is selected, and this consumed split cannot
be used for threshold tuning. Issue #105 now requires a method-level decision,
with claim-level post-generation support validation as the recommended
successor boundary.

That successor is implemented and has a completed development confirmation. Build checkpoint
`evidence-sufficiency-v3-atomic-claim-confirmation-001-build` moved the release
boundary after generation: the model may emit only structured atomic claims,
while the server owns eligible retrieval lineage, claim-set completeness, and
the final release-or-fallback decision. It compares an unselectable exact-quote
control with the pinned DeBERTa NLI verifier on a fresh, unopened 120-case
synthetic-public confirmation containing 40 supported and 80 reject cases over
12 balanced slices. Prospective gates require zero false releases, at least 90%
supported and multi-claim retention, complete mutation/lineage/malformed
rejection, p95 latency at or below 500 ms, and less than 2 GiB added memory.
The network-free simulation and complete repository gate pass at revision
`94e8ac5`: 856 Python tests, 46 frontend tests, 517/517 audited files, and 67/67
protected entrypoints. The separately authorized local run then completed once
at clean revision `c9208cb` as **Keep**: the NLI candidate produced zero false
releases, 95% supported-draft retention, 90% multi-claim retention, 100%
mutation/lineage/malformed rejection, 53.15 ms p95, and 599,932,928 bytes added
peak memory. The exact-quote control remained safe but retained only 50% of
supported drafts and is not selectable. Direct review confirmed all 12 priority
cases; the two candidate errors were conservative false rejections of valid
multi-claim paraphrases, not unsafe releases or label defects. Authorization is
revoked. Analysis correction 001 reclassifies the result as a provisional
development contract test: its 120 rows are ten fact groups crossed with twelve
templates, the rows are not independent, the direct Codex review is not
independent annotation, and the actual product retrieval/generation path was
not exercised. The NLI candidate is therefore **Go Deeper**, is not selected
for product binding, and must be evaluated in a leakage-free end-to-end T0 run
before any release-profile decision.

The exact local `qwen3.5:9b-q4_K_M` reviewer completed two 22-probe
synthetic-public method-development attempts. Both detected 11/11 planted
defects and 6/6 visual defects at USD 0. The corrected attempt also passed 6/6
clean visual controls and 11/11 derived failure labels, but falsely rejected
one correct cross-course abstention, so the local model remains advisory-only
and is not an autonomous acceptance gate. Every model-review authorization is
now revoked; deterministic draft 002 is the only active data successor and it
does not authorize provider or candidate execution.
PR [#93](https://github.com/horiiiiii032929/digital-twin/pull/93) merged the
earlier foundation into `main` at `adf39af`. PR
[#103](https://github.com/horiiiiii032929/digital-twin/pull/103) merged the
deterministic factual-QA successor and repository-correctness corrections at
`4657219`. PR
[#104](https://github.com/horiiiiii032929/digital-twin/pull/104) merged the V7/V8
requalification. V12 remains preserved as a historical corrected build-only
checkpoint. Reviewer-binding instrument `003` and the issue #107 T1 source
change supersede its current-tree match without promoting the still-pending
product or public deployment claim.

GitHub Project 1 is reorganized around release goal
[#8](https://github.com/horiiiiii032929/digital-twin/issues/8) and three active
gates:

- P1 — Multimodal Product Grounding;
- P2 — Deployable Product Foundation; and
- P3 — Pilot Validation and Release.

The older F2 milestone is closed. Open F3 work was reassigned into P1-P3. F4
continues to hold report, presentation, and professor-communication work.

## Evidence state

| Boundary | Current decision | Established | Missing before product release |
| --- | --- | --- | --- |
| Product UX and autonomous tutoring | Keep T0 as release baseline; T1 development Go Deeper | Professor and student conversation-first workspaces; typed T1 learner state and intent graph; atomic persistence, bounded repair/fallback, race/restart tests; ten-trajectory network-free development passed every gate | Design and separately authorize one untouched T0/T1 confirmation; add privacy-preserving course-improvement aggregation; then obtain human workflow/usability evidence. T2 waits for professor-profile guidance |
| Text retrieval | Keep experimentally | M2 hybrid BM25 plus local Qwen3 dense RRF selected on the one-time cross-course held-out comparison; BM25 rollback | Release-candidate end-to-end quality against realistic workload |
| Multimodal retrieval | Refine; no selection | Region-aware tables/cells/diagrams/equations/OCR, scanned-PDF API ingestion, original crop citations, 13/13 synthetic complete@3 and lineage; unfavorable historical and V2 attempt results preserved | Production OCR/layout qualification, representative real-PDF quality and end-to-end latency; frozen relative micro-p95 gate still failed |
| Generator and prompt | OpenAI R1 candidate Go Deeper; deterministic rollback retained | Historical provider evidence remains immutable. Exact GPT-5.4 mini generation, GPT-5.4 nano routine review, and bounded full GPT-5.4 escalation pass active network-free contracts with direct Responses API, one credential, and no fallback | Separately authorized 500-case product development result before profile selection |
| Professor fidelity | Refine / Paused | Invalid C0-C3 comparison and correction preserved; execution policy protects held-out | Independent expert calibration, valid prospective development comparison, and hard-gate pass |
| Publication/student core | Go Deeper; atomic-claim candidate provisional | V8 images built and became healthy; failed query/evidence comparison preserved; the 120-row NLI contract test passed its frozen synthetic gates | Evaluate T0 and the provisional validator on independently validated, source-linked examples through the actual retrieval/generation path before selection or product binding |
| Large factual QA | Immutable retrieval lifecycle Keep; actual-product checkpoint 005 invalid and stopped | The earlier synthetic workflow processed 10,000 correlated template rows. AFQC-068 passes the real 2,100-region Qwen qualification within every resource gate, with 40/40 non-empty restart-stable queries and zero runtime document embeddings | Design one new 500+100 actual-product checkpoint using the immutable indexes, then seek separate execution authorization. Do not open the sealed 10,000 cases or rerun checkpoint 005 |

## Release readiness and critical path

The repository and local product baseline are healthy, but the system is not
release-ready. The immediate correction is to obtain academically valid
end-to-end factual and evidence-sufficiency evidence before selecting a
grounding gate. T1 confirmation, host/domain selection, target-host operations,
professor-fidelity calibration, and human workflow evidence remain separate.

| Order | Issue | State | Exit condition |
| ---: | --- | --- | --- |
| 1 | [#8 Release goal](https://github.com/horiiiiii032929/digital-twin/issues/8) | In Progress / parent | Keep every implementation and evaluation item tied to the R1/R2/R3 definition of done |
| 2 | Repository correctness and execution freeze | Keep | Maintain a clean audited baseline; no prospective paid or held-out execution without its own authorization |
| 3 | [#139 Persisted retrieval indexes](https://github.com/horiiiiii032929/digital-twin/issues/139) | In Progress / Go Deeper | Authorize and complete one real local-Qwen 2,100-region build/load qualification with bounded time, memory, artifact size, exact bindings, and zero product/provider calls |
| 4 | [#127 Flow-independent 10,000-case product evaluation](https://github.com/horiiiiii032929/digital-twin/issues/127) | Todo / Refine / blocked by #139 | After #139 passes, design one new 500+100 checkpoint; keep checkpoint 005 terminal and the sealed 10,000 cases closed until a complete successor passes |
| 5 | [#105 Evidence-sufficiency successor](https://github.com/horiiiiii032929/digital-twin/issues/105) | Todo / Go Deeper | Preserve the product-integrated two-boundary candidate and select or reject it only after the independent confirmation |
| 6 | [#110 Synthetic pipeline scale](https://github.com/horiiiiii032929/digital-twin/issues/110) | Done / engineering Keep | Preserve the 10,000-row pipeline result and correction; make no Digital Twin accuracy or independent-sample claim from it |
| 7 | [#107 Autonomous tutoring graph](https://github.com/horiiiiii032929/digital-twin/issues/107) | Todo / development Go Deeper | Preserve T0 as rollback and design one separately frozen T0/T1 multi-turn confirmation before staging selection |
| 8 | [#88 Deployable product foundation](https://github.com/horiiiiii032929/digital-twin/issues/88) | Todo / Refine | Complete publication only after a grounding gate has academically valid end-to-end evidence, then select a host/domain and pass trusted TLS, restore, and walkthrough |
| 9 | [#24 Fidelity calibration](https://github.com/horiiiiii032929/digital-twin/issues/24) | Todo / Refine / professor input | Approve the profile-authoring method and calibrate behavior labels separately from factual hard gates |
| 10 | [#9 Operations](https://github.com/horiiiiii032929/digital-twin/issues/9) and [#25 end-to-end](https://github.com/horiiiiii032929/digital-twin/issues/25) | Todo / blocked | Qualify one immutable deployed revision for isolation, recovery, observability, latency, cost, complete journeys, and rollback |
| 11 | [#10 Invite-only pilot](https://github.com/horiiiiii032929/digital-twin/issues/10) | Todo / approval-gated | Complete consented professor/student workflows; keep usability separate from learning outcomes |

Issues #85 and #86 are complete and archived from the live Project view. PR #91 merged the tested multimodal product
foundation and three registered prospective development attempts. Attempt 003 passed 13/14 gates:
all quality, safety, action, text-control, and lineage gates passed; relative
warm p95 failed at 0.053 ms versus 0.023 ms. No multimodal profile was selected,
and the historical held-out split was not opened. Completed issue #87 preserves
paid attempt 002 and its completed 12-case cross-review as historical evidence.
Its deterministic successor and passing pilot 003 establish the method-level
Keep decision. Issue #110 owns separately authorized 1,000/9,000-case scale;
that follow-up is supporting evidence, not the current publication blocker.
Issue #88 remains active. V8 images are operational historical evidence, while
the changed V12 source is intentionally unbuilt. Product publication remains
blocked by the unselected evidence-sufficiency component; a host rehearsal is
premature until that gate is selected and the same source revision is rebuilt.

## Known multimodal correction

The suspected duplicated `for hit in raw_hit_rows` loop was not present in the
committed runner, and the preserved values match the single-pass legacy
formula. The actual defect was duplicate gain: overlapping OCR, layout, and
description records could each add discounted IoU for the same gold region,
after which the unnormalized total was capped at one.

Issue #85 replaces that metric with one-to-one region matching and normalized
discounted IoU, tests page/region ranking, IoU thresholds, complete evidence,
atomic recall, and nDCG, and registers a no-model correction. V2 changes from
0.212 to 0.0676 and V3 from 0.186 to 0.0756 on corrected region nDCG. Complete
evidence remains tied at 1/3, V3 atomic recall remains worse at 1/3 versus
V2's 2/3, and the V3 online-model gate still fails. The Drop decision and
text-only rollback therefore remain unchanged. The 24-case held-out split was
not read.

The prospective path now models columns, table rows/cells, figures, diagrams,
equation-like blocks, OCR, reading order, page/region checksums, and original
crops. Scanned PDFs work when an approved OCR provider is injected. Gemma
remains excluded. A production OCR/layout or replacement vision model is
selected only through a new prospective qualification and representative
course evidence.

The active model policy now blocks every Gemma and Claude call and all retired
local general-Qwen calls before provider I/O. Direct DeepSeek V4 Flash/Pro and
the selected task-specific Qwen3 Embedding binding remain current for their
recorded roles. Mistral Small 4 is retained as the qualified advisory reviewer.
Hosted Qwen3.7 Plus failed bounded qualification 007 and is not selected; its
one-time authorization is revoked and no local model is used. See
[the current model policy](../research/00_admin/2026-08-21-current-model-policy-v3.md).

## Large factual-QA method and scale successor

Completed issue #87 records the product-first v3 interpretation of the
professor's suggestion and the passing 100-case method confirmation. Issue #110
now owns staged 1,000/9,000-case scale. The primary corpus is every eligible
file in the canonical Academia
Vault, not a large dummy corpus. A small deterministic dummy corpus with a
hidden fact manifest remains only as an oracle control for extraction,
retrieval, citation, boundary-action, and mutation mechanics. The refreshed
inventory found 2,637 regular files: 294 clear candidates, 437 requiring
review, 1,903 generated/tool-state exclusions, and three sensitive exclusions.
Every file requires a recorded content-safe disposition before release. The v1
semantic triage is preserved but prospectively corrected: path and format alone
cannot finalize supporting or exclusion labels. V2 retains 32 approved
exact-hash authoritative sources and returns 570 readable candidates to
content-level review. This is a provisional queue, not a requirement for 570
manual judgments. The deterministic private content screen verified all 570
hashes, extracted local text for 554, and routed 19 lexical privacy/integrity
signals plus 16 visual/binary sources to priority review. The remaining 535 are
still semantically unresolved; absence of a lexical signal is not eligibility
evidence.

The historical 24-case attempts remain valid evidence about their frozen v2
method, but the preserved six-case audit is no longer the active product gate.
Corrected V3 requires claim-level exact evidence, retrieval without injected gold
passages, multimodal source lineage, deterministic mutation sensitivity, and a
compact human-audit packet. It remains separate from the verified 100-case
retrieval benchmark and Professor Digital Twin fidelity.

The separately authorized 40-case oracle pilot has now executed on four
synthetic selectable-text PDFs. Product ingestion created 115 chunks without
warnings. DeepSeek V4 Flash authored 40 cases, exact local Qwen 3.5 reviewed all
40, and DeepSeek V4 Pro reviewed two disputes. Thirty-nine cases passed exact
deterministic provenance; the one quarantined table case omitted the final words
from its citation, which both LLM reviewers incorrectly accepted. Hybrid
retrieval recovered all required evidence in the top three for 32/32 answerable
cases. The six controlled visual cases used approved accessibility descriptions
and do not establish raw image-only quality. The run passed its machine gates
and the corrected eight-case human audit is complete: seven retained controls
were accepted and the quarantined citation defect was confirmed as a rejection.
Rehearsal 002 completed all 120 direct DeepSeek V4 Flash author calls in memory,
then failed when the first-party OpenRouter Mistral Small 4 ZDR endpoint returned
an upstream `401 Invalid API Key`. The OpenRouter account key remained valid and
reported zero usage, so this is an endpoint-readiness and runner-order defect,
not a missing credential. Exact reviewer attempted-call and external-cost
accounting is incomplete; no generated outputs or quality metrics survive and
002 is registered as invalid. Unexecuted 003 added one schema-valid canary
through each provider before bulk authoring, then was superseded when the
researcher explicitly allowed provider data collection for this evaluation
phase. Successor 004 preserved those canaries and the exact source and model
design while allowing provider collection and retention only for the committed
synthetic-public fixtures. The run completed 268 provider calls for USD 0.046029
and passed every gate except reviewer mutation sensitivity: Mistral rejected all
invalid claim/source bindings but accepted all missing/truncated citations. The
manual audit confirmed six quarantines and six controls. The method must be
refined before real-source or larger execution, and scale toward 10,000 remains
unauthorized.

Rehearsal 005 implemented that refinement with 24 new paired defects across six
mutation classes. Its one-time execution is invalid because a malformed DeepSeek
dispute response discarded completed in-memory stages and left exact accounting
incomplete. Its authorization is revoked. Focused reviewer qualification 006
then passed all clean, defect, per-mutation, completion, latency, and cost gates.

The provider-free `factual-qa-v3-10000-pipeline-001` design now fixes 20 dummy
courses, 1,000 source units, 8,000 deterministic claims, and 10,000 blueprints:
8,000 answerable cases plus 2,000 no-evidence, ambiguity, cross-course, and
academic-integrity boundaries. The local builder passes exact grain, key,
lineage, distribution, stage, determinism, and privacy checks with zero model
calls. Dataset writing and every paid 100, 1,000, and 10,000 stage remain
unauthorized pending separate frozen checkpoints.

The shared `factual-qa-v3-scale-pilot-100` runner binds the first
100 stratified blueprints and validates a maximum of 246 calls under a USD 3.00
emergency stop. Its USD 0.323842 prospective reservation is informational;
actual provider-reported tokens and cost are checkpointed on every call, and
requested-versus-reported token-limit violations are counted explicitly.
Network-free simulations exercised the 222-call no-dispute path and the
246-call maximum-dispute path, including deterministic acceptance, 20 mutation
probes, malformed/provider failure accounting, exact model identity, atomic
checkpoints, safe resume, aggregate and slice gates, and a 12-case priority
packet. The paid run completed as **Refine** at revision `0d60f86`: 226/226
provider calls returned for USD 0.110512 with stable model identities, complete
accounting, and zero token-limit violations. However, only 4/100 authored cases
passed deterministic validity, 9 author responses were malformed, and all 100
Mistral review responses violated the scale-run contract. Because only four
valid cases were boundary cases, zero answerable cases were eligible for the
20 planned mutation probes. The 12-case priority cross-review confirmed all 12
deterministic quarantines. This exposes prompt/schema and mutation-eligibility
defects in the method, not a valid scale-quality result. Authorization is
revoked; the 1,000- and 10,000-case stages remain closed.

Successor `factual-qa-v3-scale-pilot-100-002` corrects those three method
defects without making provider calls. Authoring now uses the full shared JSON
schema plus an exact citation-object contract; scale review imports the same
strict schema, prompts, and validator used by qualification 006; and all 20
mutation probes are built from deterministic canonical controls independent of
author success. At clean revision `d5fe874`, the normal 222-call and maximum
246-call network-free paths passed, and a total-author-malformation regression
still constructed and reviewed all 20 mutations. The full repository gate
passed with 682 Python and 46 frontend tests, and the audit is 449/449 complete.
The paid attempt 002 completed as **Refine** at clean revision `1e2125b`. It
improved deterministic validity from 4/100 to 93/100, restored 97% reviewer
agreement, achieved 100% citation validity, and ran all 20 mutation probes with
20/20 rejection. The valid run used 225 calls and USD 0.102517 with stable
models, complete accounting, and zero token-limit violations. It still failed
five gates: all five ambiguity cases violated the boundary contract, one
multi-source claim/citation binding failed, one author and one review were
malformed, and five exact duplicate questions remained. Codex cross-review
confirmed seven quarantines and five retained controls; two Mistral false
accepts were correctly rejected by deterministic checks and DeepSeek disputes.
Attempt 002 authorization is revoked. The next method should deterministically
assemble actions, claim IDs, and citations, quarantine null authors before model
review, and enforce normalized question uniqueness. The 1,000- and 10,000-case
stages remain unauthorized.

Pipeline 002 implements that method-level correction rather than another prompt
revision. Its truth content hash is
`1b4bd3febd79ce828300b42cc23b379de85f7bf92fa07fe8493f22d56e7f5c8c`.
That merged provider-free checkpoint passed 713 Python and 46 frontend tests
with a 465/465 complete audit. The pre-authorization checkpoint passed 771
Python and 46 frontend tests with a 484/484 complete audit. Pilot 003 then
completed Keep in 223 calls for USD 0.085406. Direct review retained all 12
priority cases, including one independent-review false rejection. Its
authorization is revoked, and no larger execution is open. The separate
Professor Digital Twin transition now has a
validated C0-C3 contract, approval-gated explicit/inferred professor-profile
schema, and an empty 8-12-case calibration template. Fidelity judging and held-
out access remain paused pending professor guidance.

[Issue #102](https://github.com/horiiiiii032929/digital-twin/issues/102) now
tracks the separate `factual-qa-v3-real-source-pilot-001`. Its draft defines 40
cases across text, code, multi-source, table, diagram, other multimodal, and
boundary slices. It cannot execute until the large dummy-data checkpoint is
decided and every
selected Vault source has an explicit eligible exact-hash disposition. Raw Vault
files remain local; only sanitized evidence may enter GitHub.

## Human and safety boundary

A real-user pilot is now a product gate, but recruitment is not automatically
authorized. Issue #10 requires consent, privacy, recruitment, and supervisor
approval before exposure to real users. Until then, use synthetic accounts and
approved or dummy content.

Private course data, generated review packets, `.env`, build output,
dependencies, model artifacts, and bulky run outputs remain ignored. Do not use
solutions, answer keys, submissions, student data, credentials, or consent
records as committed fixtures.

## Source-of-truth order

When status statements conflict, use:

1. immutable run records and registered corrections for historical results;
2. versioned component/release profiles and the technical evidence freeze;
3. the prospective real-world product scope;
4. the active release plan;
5. this dated operational status;
6. the live GitHub Project fields and dependencies;
7. component guides and historical plans.

Never edit an old result to make it appear successful. Add a correction or a
new prospective run and retain the original evidence.
