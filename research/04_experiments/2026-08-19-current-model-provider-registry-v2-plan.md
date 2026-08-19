# Current model provider-registry qualification plan

Date: 2026-08-19  
Run ID: `deployable-product-foundation-v4-provider-registry-001`  
Status: Frozen before qualification

## Decision question

Can the current-model policy cover every executable provider candidate,
including the optional hosted Jina retrieval pair, while preserving the
qualified no-Gemma staging package?

This run checks model identity, fail-before-I/O enforcement, and deployment
regression. It does not compare model quality or select Jina for the product.

## Baseline and candidate

- Baseline `A1-single-node-staging-v3-model-policy`: exact current bindings for
  the selected product profile and governed evaluator candidates, with Gemma
  and retired general Qwen models prohibited.
- Candidate `A1-single-node-staging-v4-provider-registry`: the V3 package plus
  exact registration and adapter-level enforcement for
  `jina-embeddings-v5-text-small` and `jina-reranker-v3`.
- Rejected alternative: allow arbitrary Jina model strings because the
  defaults are current. That would permit silent model drift through a runtime
  override.

V3 and the deterministic grounded generator remain rollback options.

## Evidence and boundaries

- Verify Jina model identity from Jina's official model catalog and exact model
  pages.
- Use synthetic tests and deployment fixtures only.
- Read no private or held-out dataset.
- Make no external model call and incur no provider cost.

## Metrics and hard gates

| Measure | Frozen gate |
|---|---:|
| Gemma and retired general-Qwen rejection | 100% before provider I/O |
| Registered exact-model acceptance | 100% |
| Jina adapter model-drift rejection | 100% before provider I/O |
| Focused policy, transport, generation, provider, and fidelity tests | 100% |
| Full repository check | 100% |
| In-process deployment checks | 41/41 |
| Container build | API and web images build successfully |
| Live HTTPS / restore / rollback | 15/15, 5/5, 5/5 |
| External model calls / cost | 0 / USD 0 |
| Private or held-out data read | 0 |

Any unregistered Jina identity reaching provider I/O, successful Gemma call,
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

- **Keep** the exact-provider registry in the staging candidate when every gate
  passes.
- **Refine** a repairable matching, packaging, or deployment defect and record
  the failed attempt.
- **Drop** the change if it weakens the no-Gemma boundary, provider isolation,
  recovery, or historical provenance.

Public hosting, Jina retrieval quality, professor-fidelity calibration,
multimodal quality, factual-QA scale, and human usability remain separate.
