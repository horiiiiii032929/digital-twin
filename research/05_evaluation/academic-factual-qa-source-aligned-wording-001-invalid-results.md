# AFQC-101 source-aligned wording attempt 001

## Outcome

`invalid-execution`; no academic quality interpretation.

The run completed 44 calls and stopped on the 45th logical call, the GPT-5.4
nano author request for batch 23. OpenAI returned a response whose status was
not `completed`. The runner failed closed before using that batch.

## Accounting

- 45 provider calls and attempts: 44 completed, one failed.
- 117,184 input tokens and 76,006 output tokens.
- USD 0.73804025 reported cost.
- Maximum observed latency: 35.462 seconds.
- No private data, human participant, product call, or final-split access.

## Decision

Use the program's single permitted operational correction. Attempt 002 changes
only the provider output-token reservation and uses a fresh exclusive ledger.
The 500 cases, public sources, hidden truth, prompts, model roles, semantic
checks, batching, USD 4 ceiling, and progression gates remain unchanged.

The unrestricted provider ledger remains ignored. The sanitized machine record
is [academic-factual-qa-source-aligned-wording-001-invalid.json](records/academic-factual-qa-source-aligned-wording-001-invalid.json).
