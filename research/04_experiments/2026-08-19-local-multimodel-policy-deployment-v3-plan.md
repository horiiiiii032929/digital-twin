# Local and multi-model policy deployment qualification plan

Date: 2026-08-19

Run ID: `deployable-product-foundation-v5-local-multimodel-policy-001`

Status: Frozen before qualification

## Decision question

Can the repository prohibit Claude and retired Qwen3.5 4B execution, pin the
feasible Qwen3.5 9B local candidate, register exact controlled OpenRouter
DeepSeek/Mistral routes, and preserve the qualified single-host staging package?

This run evaluates model identity, routing controls, fail-before-I/O behavior,
and deployment regression. It does not evaluate answer quality or select a new
judge, generator, retriever, or multimodal method.

## Baseline and candidate

- Baseline `A1-single-node-staging-v4-provider-registry`: qualified no-Gemma
  package with exact direct DeepSeek, Qwen/Jina component identities, but a 4B
  local candidate and an executable Claude option.
- Candidate `A1-single-node-staging-v5-local-multimodel-policy`: the same
  architecture with Claude and Qwen3.5 4B prohibited, exact
  `qwen3.5:9b-q4_K_M` identity/digest, and exact OpenRouter DeepSeek/Mistral
  candidates under strict provider controls.
- Rejected alternative: route through floating OpenRouter aliases or allow
  automatic provider fallbacks. That would make failures and model identity
  ambiguous.

V4, direct DeepSeek, and the deterministic generator remain rollback options.

## Evidence and boundaries

- Verify provider/runtime behavior against official documentation.
- Verify the locally installed Qwen manifest digest without reading model
  weights into the repository.
- Use synthetic tests and deployment fixtures only.
- Read no private or held-out dataset.
- Make no model call and incur no provider cost in this policy/deployment run.
- Evaluate Qwen/Mistral quality separately under the prospective #87 instrument.

## Metrics and hard gates

| Measure | Frozen gate |
|---|---:|
| Gemma, Claude, and retired general-Qwen rejection | 100% before provider I/O |
| Registered exact-model acceptance | 100% |
| Qwen3.5 9B identity and full manifest digest | exact match |
| OpenRouter routing controls | no fallback; require parameters; deny collection; require ZDR |
| Focused policy, transport, generation, provider, and fidelity tests | 100% |
| Full repository check | 100% |
| In-process deployment checks | 41/41 |
| Container build | API and web images build successfully |
| Live HTTPS / restart / clean restore / rollback | 15/15, 5/5, 5/5, 5/5 |
| External model calls / cost | 0 / USD 0 |
| Private or held-out data read | 0 |

Any prohibited model reaching I/O, mutable routing control, unregistered model,
historical-evidence rewrite, private-data access, external model call, failed
deployment/recovery gate, or missing unfavorable result fails the candidate.

## Reproduction

```text
uv run python -m scripts.validate_model_policy
uv run pytest tests/test_model_policy.py tests/services/test_litellm_client.py tests/services/test_retrieval_provider.py tests/digital_twin/test_generation.py tests/test_professor_fidelity_runner.py -q
npm run verify:deployable-foundation
npm run benchmark:deployable-foundation-development
npm run staging:build
npm run verify:staging-https
npm run check
```

## Decision rule

- **Go Deeper** with V5 when every frozen local gate passes.
- **Refine** a repairable policy, packaging, or deployment defect and preserve
  the failed attempt.
- **Drop** the change if it weakens model control, privacy, recovery, or
  historical provenance.

Public hosting, provider/model quality, professor-fidelity calibration,
multimodal quality, factual-QA scale, and human usability remain separate gates.
