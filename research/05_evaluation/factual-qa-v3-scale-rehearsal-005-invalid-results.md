# Factual-QA v3 scale rehearsal 005 invalid results

## Technical summary

Rehearsal 005 is an **invalid execution**, not a reviewer-quality result. Both
provider canaries passed, and the author, independent case-review, and 24-probe
mutation-review batches completed in memory. During the bounded DeepSeek V4 Pro
dispute batch, one provider response contained unterminated JSON. The runner
failed closed and wrote an exclusive invalid artifact, but it did not preserve
the completed in-memory cases or a complete per-call ledger.

The attempt therefore cannot establish whether the stricter Mistral reviewer
passed its sensitivity gate. It also exposed a scale-readiness defect: one
malformed advisory-review response can discard otherwise completed work. The
next method must persist stage checkpoints and count malformed reviews as failed
review records instead of losing the entire run.

## Run identity

- Run ID: `factual-qa-v3-scale-rehearsal-005`
- Status: `invalid-execution`
- Decision: **Refine method**
- Execution revision: `fd942b6f93f93b1c7cee965e152ac34a3d99ad7a`, clean worktree
- Executed at: 2026-08-20 SGT
- Instrument SHA-256: `f5d068f8933eff4a29b000b0a3874f4f5bdcc72f8a12049348a90f74232c4e28`
- Ignored invalid artifact: `reports/generated/factual-qa-v3-scale-rehearsal-005.json`, SHA-256 `d20a978f860e3e3004206cdb726e1f55bb1eacd212d555d6c906db969dca9ede`
- Data boundary: synthetic-public only; zero private, instructor, course, or student data
- Scale toward 10,000: unauthorized

## What is known

| Item | Evidence | Interpretation |
| --- | --- | --- |
| Provider health gate | Both schema-valid canaries passed before bulk execution | Both exact provider routes were reachable |
| Completed pre-dispute stages | Execution reached dispute construction after awaiting authors, 120 case reviews, and 24 mutation reviews | At least 266 provider calls completed across health, author, and Mistral review stages |
| Dispute stage | DeepSeek returned a response with unterminated JSON | At least one dispute request completed externally; exact dispute request count is unavailable |
| Call bound | Frozen runner capped execution at 290 calls with no retries | Calls were between 267 and 290; no retry was attempted |
| Cost bound | The runner reserved maximum batch cost before every stage and retained the USD 3 hard stop | Exact cost is unavailable but the prospective USD 3 ceiling remained enforced |
| Durable output | Exclusive invalid artifact was written | Attempt 005 cannot be silently rerun or overwritten |

## Failed gates and limitations

- Exact provider-call, token, latency, and cost accounting is incomplete.
- Completed author, retrieval, Mistral sensitivity, and disagreement results
  were not persisted and cannot be reported.
- One malformed advisory dispute response aborted the entire result rather than
  becoming a counted malformed-review failure.
- No Keep decision, human audit, real-source execution, or 10,000-case scale may
  be authorized from this attempt.

## Correction decision

Do not repeat all 120 author and retrieval calls merely to test the reviewer.
Create a smaller successor reviewer qualification using deterministic clean and
mutated pairs, durable stage-level accounting, and explicit malformed-response
records. Require that focused gate to pass before the professor-requested
10,000-case dummy factual-QA pipeline begins. The larger pipeline must checkpoint
every batch so one provider failure cannot erase completed work.
