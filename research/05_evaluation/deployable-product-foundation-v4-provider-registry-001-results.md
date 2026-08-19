# Evaluation result: deployable-product-foundation-v4-provider-registry-001

## Run identity

- Component: exact provider-model registry plus single-host deployment package
- Status: local provider-policy/container qualification complete; public-host
  rehearsal remains pending
- Date and owner: 2026-08-19, researcher with Codex implementation support
- Clean implementation revision: `9966f5f106468bec93af8e69d740099910824ae7`
- Plan: `2026-08-19-current-model-provider-registry-v2-plan.md`
- Data: synthetic model identities, accounts, course, one-page PDF, release,
  conversation, answer, and citation only
- Boundary: no private or held-out data and zero external model calls
- Generated live result:
  `reports/generated/deployable-product-foundation-v4-provider-registry-001/result.json`
- Generated result SHA-256:
  `fddb13ad246c645f975cbac02178774ddb5dbc88b73631aab100695a2b98057a`

## Exact candidate

Candidate `a1-single-node-staging-v4-provider-registry` retains the qualified V3
architecture and selected product profile, then registers the optional hosted
retrieval candidates by exact current identity:

- `jina-embeddings-v5-text-small`, official API release `2026-02-18`; and
- `jina-reranker-v3`, official API release `2025-10-01`.

Both Jina adapters now reject unregistered overrides through the repository's
central policy before provider I/O. The models remain unselected candidates;
this result establishes identity and execution control, not retrieval quality.

Built images:

- API: `sha256:cedb76c79c563200aae4802544eb5d0616157f14ac23da63a8717f9db4e1a440`,
  252,694,907 bytes, runtime user `app`
- Web: `sha256:e4f4a60903544afab70e93287c8add40499805cc088d28eaf605318642a24917`,
  21,904,167 bytes, runtime user `caddy`

## Results

The candidate passed every frozen local gate:

- current-model policy validation passed without calling a model;
- 107/107 focused policy, provider, transport, generation, and fidelity tests;
- 31/31 focused deployment tests;
- 41/41 complete in-process deployment checks;
- both container images built successfully;
- 15/15 new live HTTPS workflow checks;
- 5/5 restart replay checks;
- 5/5 clean-volume restore replay checks; and
- 5/5 original-volume rollback replay checks.

An initial harness preflight stopped before the workflow because a generated
hexadecimal synthetic password did not contain an uppercase character. The
credential validator failed closed; no evaluation case or model call ran. The
qualification then restarted with policy-compliant, process-only synthetic
credentials and produced the result above.

## Operational measurements

| Measure | Result | Gate |
|---|---:|---:|
| Prohibited/retired model rejection tests | 6/6 | 100% |
| Registered-current-model acceptance tests | 8/8 | 100% |
| Jina drift-rejection tests | 3/3 | 100% |
| In-process deployment checks | 41/41 | 100% |
| Live HTTPS / restart / clean restore / rollback | 15/15, 5/5, 5/5, 5/5 | 100% |
| Live API p95, 25 requests | 5.254 ms | <= 750 ms |
| Queue to worker completion | 1,108.672 ms | <= 10,000 ms |
| Full live journey duration | 1,951.189 ms | diagnostic |
| Backup | 7 data files, schema v5 | checksum-valid |
| Backup SHA-256 | `e5f92539dae146bae871829c547ccc3e8a7b4a1fda7108508e10c7104f9af0e0` | diagnostic |
| External model calls / cost | 0 / USD 0 | zero |

A scan of 310 final container-log lines found no request body, synthetic course
sentence, temporary-password field, authorization header, or credential value.

## Decision

- Outcome: **Go Deeper**
- Selected local candidate: `a1-single-node-staging-v4-provider-registry`
- Keep the no-Gemma policy and exact current provider registry in the local
  staging candidate.
- Preserve V3 and the deterministic generator as rollbacks.
- Do not select Jina, Qwen3.5, or any other prospective model from identity and
  transport evidence; each role still requires project-specific quality gates.

Public DNS/trusted certificate issuance, target-host restore, the public HTTPS
walkthrough, Jina retrieval quality, professor-fidelity calibration, multimodal
quality, factual-QA scaling, real-user usability, and production capacity remain
separate gates.
