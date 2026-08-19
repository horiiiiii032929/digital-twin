# Evaluation result: deployable-product-foundation-v3-model-policy-001

## Run identity

- Component: model execution policy plus single-host deployment package
- Status: local model-policy/container qualification complete; public-host
  rehearsal remains pending
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Clean implementation revision: `101ce0642d4c1d91807b7fc1d8cf41ea3fb069eb`
- Plan: `2026-08-19-current-model-policy-deployment-v1-plan.md`
- Runtime: Docker Engine 28.5.1, Linux ARM64 containers on an Apple Silicon
  development host; local Ollama inventory checked without inference
- Data: synthetic administrator, professor, student, course, policy, one-page
  PDF, release, conversation, answer, and citation only
- Boundary: no private or held-out data and zero external model calls
- Generated live result:
  `reports/generated/deployable-product-foundation-v3-model-policy-001/result.json`
- Generated result SHA-256:
  `017e04b7bfcd91fe7b367f7356fc7181635a7b8d2e18f745bd9e115f0b24ee0d`

## Exact candidate

Candidate `a1-single-node-staging-v3-model-policy` retains the V2 deployment
architecture and selected product components, then adds:

- a central pre-I/O rejection policy for every Gemma identity, `qwen3:4b`, and
  the retired abliterated Qwen3 reviewer;
- exact current-role bindings for DeepSeek V4 Flash/Pro, Claude Sonnet 5,
  Qwen3.5 4B, and Qwen3 Embedding/Reranker;
- pinned local `qwen3.5:4b` digest
  `2a654d98e6fba55d452b7043684e9b57a947e393bbffa62485a7aac05ee4eefd`;
- guarded historical entrypoints without rewriting historical results; and
- a network-free policy validator in the full repository check.

The retired local Gemma, Qwen3 4B, and abliterated-Qwen artifacts were removed.
Only `qwen3.5:4b` remained in the scoped local model inventory. This is identity
and installation evidence, not a quality result or product-role selection.

Built images:

- API: `sha256:1de9c871a1b24a84528449ef422e105fc274dd751a81d6bed8f698e0df6c9f36`,
  252,692,283 bytes, runtime user `app`
- Web: `sha256:4dc17ed8463da0427ab4e74c463b0c7680a09c64345327684036a6a0948bd11b`,
  21,904,167 bytes, runtime user `caddy`

## Results

The candidate passed every frozen local gate:

- current-model policy validator passed without calling a model;
- 95/95 focused policy, transport, generation, and professor-fidelity tests;
- 31/31 focused deployment tests;
- 41/41 complete in-process deployment checks;
- both container images built successfully;
- 15/15 new live HTTPS workflow checks;
- 5/5 clean-volume restore replay checks; and
- 5/5 original-volume rollback replay checks.

The old model names remain only where needed to preserve historical inputs,
unfavorable results, and explicit rejection tests. Package commands no longer
expose a Gemma or retired general-Qwen execution binding.

## Operational measurements

| Measure | Result | Gate |
|---|---:|---:|
| Prohibited-model rejection tests | 6/6 | 100% |
| Registered-current-model acceptance tests | 6/6 | 100% |
| In-process deployment checks | 41/41 | 100% |
| Live HTTPS / clean restore / rollback | 15/15, 5/5, 5/5 | 100% |
| Live API p95, 25 requests | 4.733 ms | <= 750 ms |
| Queue to worker completion | 1,071.570 ms | <= 10,000 ms |
| Full live journey duration | 1,855.336 ms | diagnostic |
| API / worker / web memory | 228.4 / 72.64 / 16.34 MiB | combined < 4 GiB |
| Backup | 7 data files, schema v5 | checksum-valid |
| Backup SHA-256 | `9a785f96d6ebef5bfeeec094256c1f40bfca4d912e5e33f9ecff882ec50276e9` | diagnostic |
| External model calls / cost | 0 / USD 0 | zero |

A scan of 224 final container-log lines found no request body, synthetic course
sentence, temporary-password field, or credential value. Two benign Caddy
messages contained the word `password` while describing local root-certificate
installation; they contained no secret.

## Decision

- Outcome: **Go Deeper**
- Selected local candidate: `a1-single-node-staging-v3-model-policy`
- Keep the no-Gemma/current-model policy and V3 package as the local staging
  candidate.
- Preserve V2 and the deterministic generator as rollbacks.
- Do not select Qwen3.5 as a generator, evaluator, or multimodal method from
  this result; a new project-specific quality evaluation is still required.

Public DNS and trusted certificate issuance, clean restore on the chosen host,
and the same credentialed workflow through the public HTTPS origin remain the
deployment gates. Professor-fidelity calibration, multimodal quality, factual-
QA scaling, real-user usability, and production capacity remain separate.
