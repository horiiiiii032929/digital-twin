# Two-reviewer calibration attempt 004 invalid result

## Decision

**Invalid execution / Refine.** Attempt 004 produced no Gemini vote and cannot
support a reviewer-quality, factual-QA, product, visual, or release conclusion.
The one-time authority is revoked. Per AFQC-026, this result ends the reviewer
search rather than triggering another retry or substitution.

## Run identity

- Date: 2026-08-26
- Clean execution revision: `31bbc4ec8dbe8a7f4dc12d22b6f8ba67c87d6f92`
- Attempt: `academic-factual-qa-confirmation-002-calibration-attempt-004`
- Binding: `academic-factual-qa-confirmation-002-reviewer-bindings-003`
- Packet hash: `8ba652e718ec2cdeb3e718413f45975d0abd99a5adf0ef36bf071409e1f5bf8c`
- Ignored ledger: `reports/generated/academic-factual-qa-confirmation-002-calibration-attempt-004-ledger.json`
- Ledger SHA-256: `4255669778cc76d27818fd153d1c5f99aa95e5da9fc3c9ede42fceca39c641ee`
- Private data: none

## What happened

The clean live preflight was ready: exact Gemini 3.7 Flash revision, Google AI
Studio-only routing, pricing, parameters, retention metadata, credential,
unused ledger, and code/binding identities all matched. It made zero inference
calls.

The first four-control Gemini batch returned provider HTTP 429. This class was
eligible for the one frozen per-batch retry, so the failed call was checkpointed
and the identical batch was retried once. The retry also returned HTTP 429. The
runner then stopped as required.

## Accounting and access

- Attempted provider calls: 2
- Provider completions: 0
- Accepted Gemini votes: 0/40
- Immutable Codex votes: 40/40
- Transport retries used: 1
- Recovered transport failures: 0
- Later Gemini batches opened: 0/9
- Confirmation cases opened: 0/200
- Recorded input/output tokens: 0/0
- Ledger cumulative cost: USD 0

Both 429 responses lacked authoritative usage and cost fields. Therefore the
USD 0 ledger value means no cost was reported; it is not evidence that the
provider charged exactly zero.

## Boundary and next decision

Attempt 004 is immutable invalid operational evidence and must not be rerun.
DeepSeek remains absent from this attempt. No provider or evaluation authority
is active. The sealed 200-case panel, visual evaluation, live T0 run, private
data, and larger academic stages remain closed. The next decision is a research
method decision with the supervisor, not another automatic reviewer search.
