# Evaluation result: deployable-product-foundation-v5-local-multimodel-policy-001

## Run identity

- Component: local/multi-model execution policy plus single-host deployment
  package
- Status: local policy/container qualification complete; model quality and
  public-host rehearsal remain pending
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Clean implementation revision: `c28ae5f8dda1c7e240156268ad0620fa04730cf4`
- Plan: `2026-08-19-local-multimodel-policy-deployment-v3-plan.md`
- Runtime: Docker Engine on Apple Silicon; Ollama 0.32.14 on a 16 GiB M1 Pro
- Data: synthetic model identities, accounts, course, one-page PDF, release,
  conversation, answer, and citation only
- Boundary: no private or held-out data and zero model calls
- Generated live result:
  `reports/generated/deployable-product-foundation-v5-local-multimodel-policy-001/result.json`
- Generated result SHA-256:
  `fe695c2a55b0f6d8aa87d0aa61f2034bb10943d0f6d7b6eaded84ad677367c6c`

## Exact candidate

Candidate `a1-single-node-staging-v5-local-multimodel-policy` retains the V4
architecture, exact retrieval provider registry, direct DeepSeek product
binding, and deterministic rollback, then adds:

- pre-I/O rejection for every Gemma and Claude identity and the retired Qwen3,
  Qwen3-derived, and Qwen3.5 4B general-review artifacts;
- exact local `qwen3.5:9b-q4_K_M` manifest digest
  `6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7`;
- prospective exact OpenRouter routes
  `openrouter/deepseek/deepseek-v4-flash-0731` and
  `openrouter/mistralai/mistral-small-2603`; and
- immutable OpenRouter provider options that disable fallback, require all
  request parameters, deny data-collecting endpoints, and require ZDR.

The scoped Ollama inventory contained only the exact 6.6 GB Qwen3.5 9B tag
after the retired 4B artifact and floating 9B alias were removed. This is local
feasibility and identity evidence, not answer-quality evidence.

Built images:

- API: `sha256:595e59041e63c54cd29e9c35f3e3f934c23689b3adfe58c95e26360b131258cc`,
  252,697,338 bytes, runtime user `app`
- Web: `sha256:a0af70e70c542dcb04131236d7ebe854aa3161612b32098bfc6a2371f4ebbaea`,
  21,904,167 bytes, runtime user `caddy`

## Results

The candidate passed every frozen local gate:

- current-model policy validation passed without calling a model;
- 113/113 focused policy, provider, transport, generation, and fidelity tests;
- the full repository check passed, including 404 Python tests, 30 frontend
  tests, frontend lint, and the production build;
- dependency review passed with nine current documented Python exceptions and
  zero JavaScript vulnerabilities at moderate-or-higher severity;
- 31/31 focused deployment tests and 41/41 in-process deployment checks;
- both container images built successfully;
- 15/15 new live HTTPS workflow checks; and
- 5/5 restart, 5/5 clean-volume restore, and 5/5 original-volume rollback
  replay checks.

An initial naked `npm run verify:staging-https` invocation stopped at argument
validation because no explicit HTTPS target was provided. It made no request or
model call. The frozen local invocation was then run with `https://localhost`,
the isolated Caddy CA, and process-only synthetic credentials.

## Operational measurements

| Measure | Result | Gate |
|---|---:|---:|
| Prohibited-model rejection / exact-model acceptance | 100% | 100% |
| OpenRouter routing-control checks | 4/4 | 4/4 |
| In-process deployment checks | 41/41 | 100% |
| Live HTTPS / restart / clean restore / rollback | 15/15, 5/5, 5/5, 5/5 | 100% |
| Live API p95, 25 requests | 4.908 ms | <= 750 ms |
| Queue to worker completion | 546.093 ms | <= 10,000 ms |
| Full live journey duration | 1,358.584 ms | diagnostic |
| API / worker / web memory | 228.4 / 72.59 / 15.91 MiB | combined < 4 GiB |
| Backup | 7 data files, schema v5 | checksum-valid |
| Backup SHA-256 | `d57ccd90e0b24fcf00ad9dfecf0babd6dcf457cb6e2496c23b9d9831b00a24ca` | diagnostic |
| External/local model calls and provider cost | 0 / USD 0 | zero |

A scan of 276 final container-log lines found no authorization header,
temporary-password field, process-only synthetic credential, or synthetic
course sentence.

## Decision

- Outcome: **Go Deeper**
- Selected local deployment candidate:
  `a1-single-node-staging-v5-local-multimodel-policy`
- Keep direct DeepSeek selected for its currently recorded product/evaluation
  roles and keep the deterministic generator as rollback.
- Keep Qwen3.5 9B and the OpenRouter Mistral/DeepSeek routes prospective only.
  This run does not establish their factual, citation, multimodal, or evaluator
  quality.
- Preserve V1-V4 as historical freezes and use V5 for future model-policy and
  deployment changes.

The next in-scope decision is a public/synthetic #87 quality instrument for
Qwen3.5 9B and Mistral Small 4. OpenRouter BYOK setup, public DNS/trusted TLS,
target-host restore, Professor Digital Twin evaluator calibration, real-course
multimodal quality, factual-QA scaling, and human usability remain separate
gates.
