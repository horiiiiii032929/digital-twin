# Factual-QA v3 120-case rehearsal plan

Date: 2026-08-20

Issue: #87

Status: frozen pending implementation verification and explicit execution

## Decision question

Can the corrected source-linked factual-QA v3 method produce and review 120
synthetic-public cases quickly enough for the next scale step while preserving
deterministic source, action, claim, and exact-citation acceptance?

This is a single-method scale rehearsal, not a model leaderboard. If a quality,
reviewer-sensitivity, privacy, cost, identity, or latency gate fails, the method
is **Refine** and must change before another run. No result from this rehearsal
can authorize a 10,000-case run.

## Why this reviewer transport

The 40-case oracle pilot found that local `qwen3.5:9b-q4_K_M` took 12.47 seconds
per review and missed the known incomplete citation. The successor therefore
uses the already registered OpenRouter route for Mistral Small 4,
`mistralai/mistral-small-2603`, as the independent advisory reviewer. It is a
different family from the DeepSeek author, supports structured outputs, and is
served through a pinned first-party Mistral route with provider fallback
disabled. Deterministic checks—not Mistral, DeepSeek, or model agreement—remain
the retention authority.

The model and transport facts were checked on 2026-08-20 against the official
Mistral model card and OpenRouter model and routing documentation:

- <https://docs.mistral.ai/models/mistral-small-4-0-26-03>
- <https://openrouter.ai/mistralai/mistral-small-2603>
- <https://openrouter.ai/docs/guides/routing/provider-selection>
- <https://openrouter.ai/docs/guides/features/zdr>

## Frozen corpus and slices

The rehearsal reuses only the 21 approved synthetic-public source units from
`factual-qa-pilot-corpus-v1`. It deterministically expands them to 120
blueprints:

| Slice | Cases |
| --- | ---: |
| Direct text | 30 |
| Paraphrase text | 30 |
| Multi-evidence text | 18 |
| Controlled multimodal description | 18 |
| No evidence | 6 |
| Ambiguous | 6 |
| Cross-course confusion | 6 |
| Adversarial integrity | 6 |
| Total | 120 |

The 96 answerable cases cover all 36 approved claims. The visual cases use the
same synthetic fixture plus accessibility-description path as the 40-case
pilot; they do not establish raw image-only understanding. The 24 boundary
cases require abstention, clarification, or refusal and carry no answer
evidence where inappropriate.

## Fixed pipeline

1. Validate the instrument, source hashes, permissions, claim IDs, slice
   composition, provider identities, and call/cost limits before any call.
2. Render and ingest four synthetic selectable-text PDFs through the product
   ingestion and chunking path.
3. Generate all 120 cases with direct DeepSeek V4 Flash, temperature zero, and
   concurrency eight.
4. Apply deterministic action, claim, source, course, and exact-quote checks.
5. Retrieve without injecting gold evidence using the selected BM25 plus local
   Qwen3 embedding hybrid.
6. Review all 120 cases with OpenRouter Mistral Small 4, structured JSON,
   concurrency eight, first-party Mistral only, no provider fallback, parameter
   enforcement, data collection denied, and zero-data-retention required.
7. Send at most 24 deterministic/Mistral disagreements to direct DeepSeek V4
   Pro for diagnosis only.
8. Run 20 paired mutation probes through Mistral: five truncated citations,
   five missing citations, five invalid claim bindings, and five invalid source
   bindings. Their clean originals measure paired specificity. Mutation probes
   never enter the retained dataset.
9. Produce a 12-case audit packet prioritizing deterministic failures, reviewer
   disagreements, mutation-related risk, and slice coverage.

## Primary metrics and gates

The primary outcome is a trustworthy retained set, measured by deterministic
provenance validity of at least 95%. The second primary outcome is retrieval:
all-evidence@3 must be at least 90% and mean Evidence Recall@5 at least 95%.
Every boundary action must be correct and cross-course leakage must remain zero.

The hosted-review transport must complete 100% of 140 planned reviews, reject
at least 90% of the 20 deterministic mutations, accept at least 90% of their 20
clean paired originals, keep reviewer p95 latency at or below eight seconds,
and finish its review stage within four minutes. Agreement on ordinary cases is
diagnostic and cannot accept or reject a case.

Additional hard guardrails are 100% PDF ingestion and source integrity, stable
registered model identities, zero private-data calls, zero malformed structured
responses, a clean execution revision, no retries, at most 284 total provider
calls, end-to-end wall time at or below 15 minutes, and external cost at or
below USD 3.00. Any execution exception consumes the run ID and writes an
invalid-run envelope; a retry requires a successor instrument ID.

## Interpretation and next gate

- **Refine:** any frozen gate fails; classify the owning source, blueprint,
  prompt, deterministic check, retrieval, reviewer, or operational defect and
  change the method prospectively.
- **Go Deeper:** every machine gate passes; complete the 12-case human audit.
- **No 10,000 authorization:** even a passed audit only permits planning the
  next scale stage with the professor. It does not establish quality on private
  Academia Vault sources or raw image-only multimodal inputs.
