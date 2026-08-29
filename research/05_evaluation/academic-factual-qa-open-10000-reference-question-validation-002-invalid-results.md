# Independent reference-question validation 002 — invalid execution

## Outcome

`invalid-execution`. No reference-question quality estimate or product decision
can be drawn from this run.

## What happened

The authorized run started from clean revision `eccdb8d` and completed 18 paired
author/reviewer batches plus the author call for batch 19. The nineteenth author
response contained all 20 expected case IDs exactly once and satisfied the
strict JSON schema, including the terminal question-mark rule added after
attempt 001. It returned those IDs in a different order from the frozen request.

The immutable runner required exact ID order and rejected the response before
batch 19 could enter blind review or deterministic scoring. This is an
operational output-order contract failure, not evidence that the reference-
question method passed or failed its academic quality gates. The zero-retry
rule was preserved; the response was not reordered or silently normalized.

## Accounting

- Completed provider calls: 37 of at most 80.
- Completed author calls: 19; completed reviewer calls: 18.
- Fully persisted author/reviewer batch pairs: 18 of 40.
- Input tokens: 93,609.
- Output tokens: 44,527.
- Reported cost: USD 0.65079725 of the USD 12 emergency ceiling.
- Total recorded provider latency: 242.120 seconds.
- Transport failures and retries: 0.
- Product calls: 0.
- Private-data calls: 0.
- Final 10,000-case access: 0.

The ignored SQLite ledger is retained locally at
`reports/generated/academic-factual-qa-open-10000-reference-question-validation-002.sqlite3`
with SHA-256
`b38f77823fb8f47febcb4112f37423ab8a792bc372bba0b46d403d2fd91fcc08`.
Unrestricted provider output remains ignored and is not reproduced here.

## Decision

Preserve attempt 002 as invalid, revoke its one-time authorization, and keep the
fresh 500+100 product confirmation and sealed 10,000-case execution closed.
This was the single schema-aligned successor permitted after attempt 001, so no
third attempt or paid continuation is authorized. The next checkpoint is an
explicit method decision, not another automatic correction.

## Limitations

- The run did not complete all 40 author/reviewer batch pairs.
- No selected 100-cluster/500-case package was produced.
- No acceptance, ambiguity, span-recovery, duplicate, or quota metric is valid.
- Both roles use separate OpenAI model configurations from one provider family;
  they are not independent human annotation.
