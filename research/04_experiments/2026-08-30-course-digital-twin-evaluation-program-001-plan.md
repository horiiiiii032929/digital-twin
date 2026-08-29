# Course Digital Twin finite evaluation program

Date: 2026-08-30

Program ID: `course-digital-twin-evaluation-program-001`

Owner: issue #127

Status: reviewed, built, and provider-unauthorized

## Decision question

Can one prospective, finite program select a safer retrieval/evidence method,
evaluate the actual T0 product on 500 development and 10,000 sealed cases, and
produce useful visual, autonomous-graph, and synthetic-profile diagnostics
without gold leakage or another prompt-tuning loop?

## Prediction

Structured hierarchical retrieval should improve complete evidence recovery
over BM25 and the current hybrid retriever. Bounded nano reranking may help
hard questions, but the deterministic hierarchy should be preferred when its
complete-evidence rate is within two percentage points. If the selected method
passes development, the exact product configuration should retain at least 95%
fully grounded factual success and at least 98% boundary action accuracy on the
sealed final set.

## Frozen comparisons

- Retrieval: BM25, current BM25/Qwen3 hybrid, deterministic hierarchical
  retrieval, and hierarchical retrieval with question-only nano reranking.
- Product: structured hierarchical evidence coverage versus the current
  any-hit release control.
- Tutoring flow: provider-backed T0 versus bounded LangGraph T1 over 50 fresh
  final-source trajectories outside the paired control subset.
- Visual: text fallback versus question-independent nano visual descriptions
  with citations resolving to original visual regions.
- Professor behavior: synthetic C0-C2 diagnostics and C3 only after factual
  development passes. These conditions are not professor-fidelity evidence.

## Authoritative boundaries

- `EvaluationCaseV1` is the only product-visible benchmark input.
- `EvaluationGoldV1` is held separately and opens only after every product
  response in that arm is durable.
- `TutorEvaluationAdapterV1` normalizes T0, T1/T2, and future HTTP flows.
- `SystemUnderTestManifestV1` binds the exact evaluated product configuration.
- Deterministic source, action, claim, citation, version, and policy checks own
  the decision. Model reviews are advisory and cannot edit reference truth.
- Public questions, hidden gold, product responses, reviewer ledgers, and
  provider accounting use distinct hash-bound artifacts.

## Method

1. Compare the four retrieval methods on the untouched 300 cases left after
   retaining the earlier 200 as known diagnostics. Nano may rerank at most 40%
   of public questions and may only reorder supplied chunk IDs.
2. Run the selected method on 500 product cases and the fixed 100-case any-hit
   control. Audit every deterministic failure and a seeded 10% passing sample.
3. If development passes, construct 10,000 cases from the pinned 2,000 final
   source clusters. Code owns canonical truth; nano writes natural wording and
   Luna independently recovers action and evidence. Rejected wording receives
   a labelled deterministic fallback rather than a weakened gate.
4. Freeze a 1,000-case paired control subset, run 10,000 candidate and 1,000
   control responses, then open gold and score. Audit all failures, every
   paired candidate, and a seeded 200-case passing sample.
5. Run independent visual and synthetic-profile diagnostics. Run provider T0
   versus T1 only after the factual final passes. Revalidate the unchanged
   qualified local R1 and generate the professor package.

## Models and budget

- `gpt-5.4-nano-2026-03-17`: reranking, wording, visual transcription, and
  routine advisory review.
- `gpt-5.4-mini-2026-03-17`: product generation and synthetic diagnostics.
- `gpt-5.6-luna`: independent final-question action/evidence verification.
- `gpt-5.4-2026-03-05`: at most 20 source-truth escalations.

All calls use the direct OpenAI Responses API, strict structured output,
`store: false`, exact returned identities, and no router fallback. The global
absolute stop is USD 50. Stage budgets are hash-bound in the program manifest.
The frozen token-envelope p99 projection is USD 44.60: each stage projection
must fit its reserve and the aggregate must remain below the program ceiling
before paid execution can begin.

Official model pages were refreshed on 2026-08-30 for
[GPT-5.4 nano](https://developers.openai.com/api/docs/models/gpt-5.4-nano),
[GPT-5.4 mini](https://developers.openai.com/api/docs/models/gpt-5.4-mini),
[GPT-5.4](https://developers.openai.com/api/docs/models/gpt-5.4), and
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
The recorded prices, Responses API support, structured-output support, and
dated snapshots match the official pages; Luna remains an undated alias and
therefore requires exact returned-identity recording plus package freezing.
OpenAI's [data-control documentation](https://platform.openai.com/docs/models/default-usage-policies-by-endpoint)
states that API content is not used for training unless the customer opts in,
but default abuse-monitoring logs may be retained for up to 30 days. Therefore
the program uses public/synthetic inputs only, sets `store: false`, does not use
background mode, and makes no zero-data-retention claim.

## Gates and decisions

The factual gates are preregistered in the program instrument. They include
complete evidence@3 at least 90%, Evidence Recall@5 at least 95%, grounded
factual success at least 95%, boundary action accuracy at least 98%, claim and
citation precision/recall thresholds, 100% citation source-version validity,
no severe release, no gold leakage, and paired non-inferiority.

A valid quality failure records `completed-refine` and stops the dependent
factual branch. A transport or harness defect receives at most one correction
without changing the method, cases, prompts, gold, gates, or model roles. A
second invalid execution stops the branch. Visual and synthetic-profile
diagnostics may continue independently. The sealed set is never tuned or run
again after a valid result.

## Reproduction

```bash
npm run verify:finite-evaluation-program
npm run simulate:finite-evaluation-program
npm run preflight:finite-evaluation-program
```

Paid execution remains impossible until the manifest and repository freeze are
separately changed after the exact authorization:

`Authorize course-digital-twin-evaluation-program-001 up to USD 50.`

## Claim limits

This program uses open educational sources and synthetic users. It does not
establish professor fidelity, external usability, learning outcomes, durable
hosting, or independent external human annotation. The 30-cluster visual
result remains `Go Deeper` even if it passes. Real professor calibration and an
external human pilot remain prepared but unexecuted.
