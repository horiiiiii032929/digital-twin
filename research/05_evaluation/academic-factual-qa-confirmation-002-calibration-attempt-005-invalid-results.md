# Resilient reviewer calibration attempt 005 invalid result

## Decision

**Invalid execution / Refine.** Attempt 005 produced only 8/40 accepted Gemini
votes and cannot support a reviewer-quality, factual-QA, product, visual, or
release conclusion. The one-time authority is revoked. The sealed 200-case
panel remains closed.

## Run identity

- Date: 2026-08-26
- Clean execution revision: `013f2a975fe19000eddf159735d0cfbf1ec38bae`
- Attempt: `academic-factual-qa-confirmation-002-calibration-attempt-005`
- Binding: `academic-factual-qa-confirmation-002-reviewer-bindings-004`
- Packet hash: `8ba652e718ec2cdeb3e718413f45975d0abd99a5adf0ef36bf071409e1f5bf8c`
- Ignored ledger: `reports/generated/academic-factual-qa-confirmation-002-calibration-attempt-005-ledger.json`
- Ledger SHA-256: `9171b3a780c154d53d224197ea4cf32342fd0291cf911ac86a6e3bb21f0e9fe5`
- Private data: none

## What happened

The clean live preflight reported no blocker and made zero inference calls. All
three requests used the exact `google/gemini-3.7-flash` model through Google
Vertex priority routing. The first two four-case batches passed parsing and
deterministic semantic validation, producing 8 accepted Gemini votes.

The third provider response was valid JSON and had complete identity, token,
latency, and cost accounting, but one boundary vote was internally
inconsistent. The frozen contract classifies parsed schema or semantic
violations as non-retryable, so the executor checkpointed the failure and
stopped without opening another batch.

## Accounting and access

- Provider calls: 3
- Provider transport completions: 3
- Accepted Gemini votes: 8/40
- Immutable Codex votes: 40/40
- Malformed semantic responses: 1
- Transport retries: 0
- Later Gemini batches opened: 0/7
- Confirmation cases opened: 0/200
- Reported input/output tokens: 10,393/5,220
- Reported cost: USD 0.024632775
- Call latency: 9.654–13.379 seconds

## Boundary and next decision

Attempt 005 is immutable invalid execution evidence and must not be rerun. The
transport correction solved the prior HTTP 429 availability problem, but it did
not produce a complete calibrated Gemini reviewer. No evaluation authority is
active. The 200-case panel, visual evaluation, live T0 run, private data, and
larger academic stages remain closed. Per the prospective protocol, the next
step is a reviewer-method decision, not another automatic model or prompt loop.
