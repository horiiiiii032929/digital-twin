# R1 OpenAI-only build checkpoint

## Outcome

The prospective R1 runtime and flow-independent development evaluation now have
one direct, version-locked OpenAI provider boundary. The build is **Go Deeper**
to a separately authorized 500-case development run. This result does not
evaluate product quality and does not authorize any provider call.

## Method

The checkpoint binds GPT-5.4 mini snapshot
`gpt-5.4-mini-2026-03-17` to public question wording and T0 product generation,
and GPT-5.4 snapshot `gpt-5.4-2026-03-05` to advisory semantic review. Both use
the direct Responses API, exact returned-model checks, strict structured output,
`store: false`, zero retries, and the single environment-owned
`OPENAI_API_KEY`. Active preflight rejects historical non-OpenAI manifests.

The deterministic reference package remains authoritative. The product receives
only `EvaluationCaseV1`; hidden `EvaluationGoldV1` is opened only by the scorer
after durable response completion. Separate system manifests bind the
structured-evidence candidate and any-hit control.

## Build evidence

- 500/500 public wording cases completed the network-free simulation with zero
  normalized duplicates and zero provider calls.
- Both OpenAI wording/review payloads request strict JSON schema and
  `store: false`.
- Five flow-independent adapters completed ten-case network-free simulations
  with no reference-answer access.
- Focused OpenAI runtime, policy, API, wording, adapter, and historical
  compatibility tests passed 90/90; the complete gate then passed 1,077 Python
  and 47 frontend tests, lint, and the production build.
- Repository correctness is 616/616 audited files and the active freeze covers
  86/86 protected entrypoints.
- Model-policy, staging-config, execution-freeze, lint, and diff checks passed.
- The active development preflight requires only `OPENAI_API_KEY` and remains
  blocked by false provider/paid/development authorization and the repository
  freeze.

## Decision and limitations

**Go Deeper** with the exact OpenAI snapshots for one 500-case candidate and
paired 100-case control development checkpoint after key rotation and explicit
paid authorization. Do not call the two models independent provider families;
review is advisory and deterministic source truth remains authoritative.

No provider, paid, private-data, held-out, final 10,000-case, professor-fidelity,
visual, staging-promotion, or deployment execution occurred. Historical
provider evidence and unfavorable results remain unchanged.

Implementation revision: `82347c0067e10504c8e66bc60188ad8673b12d7d`.
