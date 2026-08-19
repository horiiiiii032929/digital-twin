# Current model policy and deployment requalification plan

Date: 2026-08-19  
Run ID: `deployable-product-foundation-v3-model-policy-001`  
Status: Frozen before deployment requalification

## Decision question

Can the repository prohibit Gemma and retired local general-review models,
retain only verified current role-specific bindings, and preserve the complete
single-host staging behavior after the policy is included in the packaged API?

This is an execution-policy and deployment-regression decision. It does not
compare model answer quality and cannot select Qwen3.5 for a product role.

## Baseline and candidate

- Baseline `A1-single-node-staging-v2`: locally qualified deployment with
  current DeepSeek product bindings, but executable historical Gemma/Qwen
  routes and no central model-identity guard.
- Candidate `A1-single-node-staging-v3-model-policy`: the same architecture and
  selected product components, plus a central fail-before-I/O model policy,
  current-model registry, exact `qwen3.5:4b` artifact digest, guarded historical
  entrypoints, and automated policy validation.
- Alternative rejected before execution: silently replace every old model name
  inside historical instruments. That would corrupt result provenance and
  imply that old judgments came from models that were never used.

The deployment rollback remains V2 and the deterministic grounded generator.

## Prediction

The candidate should reject every Gemma identifier and the retired local
general Qwen identities before provider I/O, leave historical evidence
unchanged, pass all repository tests, rebuild the API image, and preserve all
25 live HTTPS, restore, restart, and citation checks from V2.

## Data and permissions

- Synthetic accounts, one synthetic PDF, policies, question, answer, and
  citation only for deployment verification.
- No private or held-out data may be read.
- No external model may be called.
- Official provider documentation may be used only to verify model identity.
- Local model inventory may be read; retired local model artifacts may be
  removed because this run explicitly prohibits their future use.

## Metrics and hard gates

| Measure | Frozen gate |
|---|---:|
| Prohibited model rejection | 100% of Gemma and retired-Qwen test identities fail before transport I/O |
| Current binding validation | 100% of registered product/review/retrieval bindings validate by exact ID |
| Local model inventory | only pinned `qwen3.5:4b` remains from the scoped local general-review artifacts |
| Focused policy and transport tests | 100% pass |
| Full repository check | 100% pass after the prospective freeze is registered |
| In-process deployment checks | 41/41 |
| Container build | API and web images build successfully |
| Live HTTPS workflow | 15/15 |
| Clean restore replay | 5/5 |
| Original-volume rollback replay | 5/5 |
| External model calls / cost | 0 / USD 0 |
| Private or held-out data read | 0 |

The local Qwen3.5 model is installation and identity evidence only. Do not run
answer-quality, reviewer-quality, or multimodal-quality cases in this run.

## Failure classes

Classify failures as policy matching, unguarded transport, stale model binding,
historical-provenance corruption, packaging, deployment, restore, security,
test regression, evaluator defect, or operational failure.

Any successful Gemma/retired-Qwen request, changed historical result, private
data access, external model call, failed isolation/restore/citation gate, or
unregistered unfavorable result fails the candidate.

## Reproduction

```text
uv run python -m scripts.validate_model_policy
uv run pytest tests/test_model_policy.py tests/services/test_litellm_client.py tests/digital_twin/test_generation.py tests/test_professor_fidelity_runner.py -q
npm run verify:deployable-foundation
npm run benchmark:deployable-foundation-development
npm run staging:build
npm run verify:staging-https
npm run check
```

Generated container and per-check details remain ignored under
`reports/generated/`. Commit a sanitized result summary, machine-readable
record, and prospective V3 freeze only after the measurements complete.

## Decision rule

- **Keep** the model policy inside the current local staging candidate if every
  policy and regression gate passes.
- **Refine** if the policy is sound but matching, packaging, or deployment has
  a repairable defect.
- **Drop** the policy implementation if it permits a prohibited call, corrupts
  historical provenance, or weakens deployment isolation/recovery.

Public DNS, trusted certificate issuance, target-host restore, professor-
fidelity calibration, multimodal quality, and factual-QA scaling remain
separate gates.
