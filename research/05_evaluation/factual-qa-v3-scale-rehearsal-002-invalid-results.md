# Factual-QA v3 scale rehearsal 002 invalid results

## Technical summary

The first paid 120-case rehearsal is **invalid**, not a quality result. All 120
DeepSeek V4 Flash author calls completed in memory, but the first-party Mistral
Small 4 ZDR route returned an upstream `401 Invalid API Key` when independent
review began. The OpenRouter account key itself remained valid and its credit
endpoint reported zero usage; the failure came from the sole first-party
Mistral ZDR endpoint. No generated case, retrieval, reviewer-quality, mutation,
or aggregate metric may be reported from this attempt.

The run exposed a method defect: the credential-only preflight did not verify
both provider routes before bulk authoring. The successor must add schema-valid
author and reviewer canaries before any bulk call, preserve exact failure-stage
accounting, and use a new run identifier.

## Run identity

- Run ID: `factual-qa-v3-scale-rehearsal-002`
- Status: `invalid-execution`
- Decision: **Refine method**
- Execution revision: `4e4bc22717d89c8ae14ad4164588ef5ee0c8efa3`, clean worktree
- Executed at: 2026-08-20 21:38 SGT
- Instrument SHA-256: `49996c91264c6413f167c3d1beb8f43931f0c72b12b247905751aa0a91d1ae38`
- Ignored invalid artifact: `reports/generated/factual-qa-v3-scale-rehearsal-002.json`, SHA-256 `5cf3e81d6253bf8b3da7c2eae94d046c77b262b07586994be22413e856880755`
- Data boundary: synthetic-public only; zero private, instructor, course, or student data
- Scale toward 10,000: unauthorized

## What is known

| Item | Evidence | Interpretation |
| --- | --- | --- |
| DeepSeek author stage | The awaited 120-call batch returned before reviewer construction began | 120 author calls completed, but outputs were not persisted after failure |
| Independent reviewer | Concurrent Mistral review raised upstream `401 Invalid API Key` | Reviewer completion is invalid and exact attempted-call count is unavailable |
| OpenRouter account | `/api/v1/credits` returned HTTP 200, USD 5 total credit, zero usage | The OpenRouter key was valid; failed reviewer requests were not billed |
| Mistral route | OpenRouter endpoint metadata showed normal first-party Mistral healthy and the Mistral ZDR endpoint unavailable | The frozen ZDR-only route, not the model identity, was operationally unavailable |
| DeepSeek account | Post-run balance endpoint returned HTTP 200 and USD 9.57 available | Exact attempt cost cannot be reconstructed because no pre-run balance or partial call ledger was persisted |
| Durable output | Exclusive invalid artifact was written | Attempt 002 cannot be silently rerun or overwritten |

## Failed gates and limitations

- Provider readiness was not tested before bulk authoring.
- Provider-call accounting is incomplete for the concurrent failed review batch.
- Exact external cost is unknown and must not be inferred from the post-run balance.
- The 120 in-memory authored outputs are unavailable for evaluation.
- No factual correctness, citation, retrieval, multimodal, reviewer-sensitivity,
  latency, or quality gate was evaluated.

## Correction decision

Create `factual-qa-v3-scale-rehearsal-003` with the same reviewed 120-case source
design and model roles, but add one author and one independent-reviewer canary
before bulk execution. Because every request is synthetic-public, route the
same first-party Mistral model with `data_collection=deny` and a documented
request-level ZDR exception; product and private-data routes retain the strict
ZDR policy. Revoke attempt 002 authorization, keep 003 blocked until separate
review and authorization, and require a new exclusive output.
