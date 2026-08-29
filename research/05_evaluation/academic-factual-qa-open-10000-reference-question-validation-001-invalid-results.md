# Independent reference-question validation 001 — invalid execution

## Outcome

`invalid-execution`. No reference-question quality estimate or product decision
can be drawn from this run.

## What happened

The authorized run started from clean revision `f974e5d` and completed three
source-visible author batches, three target-blind reviewer batches, and a fourth
author batch. The fourth author response satisfied the provider-side JSON
schema, but one question did not end with the question mark required by the
local `ReferenceQuestionAuthorResponseV1` contract. Local parsing therefore
failed before the fourth batch could enter deterministic scoring.

This is a provider-schema/local-validator contract mismatch. It is not evidence
that the reference-question method passed or failed its academic quality gates.
The zero-retry rule was preserved and no automatic correction or rerun occurred.

## Accounting

- Completed provider calls: 7 of at most 80.
- Input tokens: 17,042.
- Output tokens: 7,807.
- Reported cost: USD 0.110227 of the USD 12 emergency ceiling.
- Total recorded provider latency: 50.365 seconds.
- Retries: 0.
- Product calls: 0.
- Private-data calls: 0.
- Final 10,000-case access: 0.

The ignored SQLite ledger is retained locally at
`reports/generated/academic-factual-qa-open-10000-reference-question-validation-001.sqlite3`
with SHA-256
`63a80bdab3fc1d060368e1aa93b6a6820ac3827dd1e3579c3a20847157193323`.
Unrestricted provider output remains ignored and is not reproduced here.

## Decision

Preserve attempt 001 as invalid, revoke its one-time authorization, and keep the
fresh 500+100 product confirmation and sealed 10,000-case execution closed.

A prospective successor may align the provider schema with the already-required
local question-format invariant. That would be a new immutable attempt with a
fresh ledger and separate paid authorization; attempt 001 must not be retried or
overwritten.

## Limitations

- The run did not complete all 40 author/reviewer batch pairs.
- No selected 100-cluster/500-case package was produced.
- No acceptance, ambiguity, span-recovery, duplicate, or quota metric is valid.
- Both roles use separate OpenAI model configurations from one provider family;
  they are not independent human annotation.
