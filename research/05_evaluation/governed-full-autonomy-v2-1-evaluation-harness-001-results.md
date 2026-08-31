# Evaluation result: governed-full-autonomy-v2-1-evaluation-harness-001

## Run identity

- Component: flow-independent full-autonomy evaluation harness
- Date: 2026-08-31
- Clean code revision: `0ce63dfa07a81ff772a2fa9532cc4abdaad48212`
- Instrument SHA-256:
  `2ade9060b38465d3902ac2f390735cb2a66c7dd4c60af5baee4ee2ffac9196d8`
- Public contract SHA-256:
  `d3327cf6d71ac1c8c320916214c38a0e3700192770c8857c795ea0afd363231a`
- Hidden gold contract SHA-256:
  `3c80f2e5557f171d9d267a55f9ee86938091ad4d5f37579a6365e1b69d0ba0ca`
- Reproducible command:
  `npm run simulate:governed-autonomy-v2-1-evaluation-harness`
- Provider boundary: network-free; zero calls, tokens, and cost
- Machine record:
  `research/05_evaluation/records/governed-full-autonomy-v2-1-evaluation-harness-001.json`

## Decision question

Can one stable public-case, hidden-gold, observable-response contract compare
T0, T1-v1, T1-v2 reactive, and T1-v2 autonomous behavior without depending on
LangGraph nodes, Python classes, SQLite tables, prompts, UI routes, or runtime
chunk identifiers?

## Method

The instrument expands deterministic templates into 820 cases:

- 600 multi-turn cases: 50 templates × four conditions × three seeds;
- 100 synthetic learners over 30 simulated days; and
- 120 proactive opportunities spanning eligible action, consent suppression,
  release change, and provider-failure behavior.

Public cases include only scope, event, and time inputs. Expected actions,
terminal goal status, and required invariants remain in a separate gold object.
The simulation uses a disclosed deterministic reference driver to exercise the
harness and scorer. It does not run the Course Digital Twin product.

The operational contract now requires one privacy-safe row per provider call:
task, returned identity, input/output tokens, reported cost, latency, status,
and bounded error code. Prompt content is excluded.

## Result

The clean network-free simulation completed all 820 cases:

- exact action matching: 820/820 cases;
- valid pedagogical transition: 820/820;
- goal termination: 820/820;
- provider-failure safe fallback: 100%;
- restart consistency: 100%;
- zero unexpected/unauthorized actions;
- zero wrong-recipient, wrong-course, or wrong-release actions;
- zero invalid citation lineage, consent violations, duplicate deliveries,
  unbounded loops, or model-owned authority mutations; and
- zero provider calls, tokens, or cost.

These perfect rates are expected for the reference driver and must not be
reported as product performance.

## Decision

Outcome: **Go Deeper**.

Use this harness and scorer for the actual product comparison in #157. The
harness implementation is selected for evaluation infrastructure only. T1-v2.1
remains unselected; T1-v1 and T0 remain the active control and rollback.

## Limitations

- This run validates evaluation plumbing, not the Digital Twin's teaching,
  grounding, or autonomous-action quality.
- The reference driver is deterministic and scripted to the observable
  contract; it is not a system-under-test condition.
- No provider-backed product adapter, sealed factual tranche, professor profile
  reference, external human, or learning outcome was evaluated.
- The next result must report actual product responses and complete per-call
  identity, token, latency, cost, failure, persistence, and restart evidence.
