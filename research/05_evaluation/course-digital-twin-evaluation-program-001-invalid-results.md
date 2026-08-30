# Finite evaluation program invalid result

## Outcome

`course-digital-twin-evaluation-program-001` terminated as
`invalid-execution` in its first stage. No academic or product-quality result
was produced.

The exact program was authorized on 2026-08-30 under a USD 50 emergency ceiling.
Both execution attempts stopped while materializing the local Qwen3 retrieval
index, before retrieval scoring, hidden-gold access, or any provider call.

## Attempt evidence

| Attempt | Revision | Manifest hash | Execution path | Observed outcome | Calls / cost |
| --- | --- | --- | --- | --- | --- |
| 001 | `c9213eaeb69b304e973338087f98442007c6a44c` | `d22fc60bd40b483fca6a0f1a437dca467d753815ce77a629a9022fe2a2a14e07` | Apple MPS / original frozen embedding configuration | The first retrieval index made no durable progress for about five minutes and the process was interrupted. No index artifact was created. | 0 / USD 0 |
| 002 | `164e934ab84948154571e1d6b3106b62b1f2b94e` | `6d612e2154199b1ced73d846ca2e7fb8c8acd615d218bc73faec8d518cb2ffd6` | Sole harness correction: CPU / float16; the method, corpus, cases, prompts, models, gates, and budgets were unchanged | The first frozen 16-item, 2,048-token batch caused resident memory to rise to approximately 8 GB and ceased useful progress. The process was interrupted to protect the host. No index artifact was created. | 0 / USD 0 |

The ignored atomic ledgers are retained at:

- `reports/generated/course-digital-twin-evaluation-program-001-attempt-001-interrupted/program-ledger.sqlite3`
- `reports/generated/course-digital-twin-evaluation-program-001/program-ledger.sqlite3`

Each ledger binds the exact program, manifest, code revision, stage order, and
accounting state. Both record `retrieval-decision` as interrupted, every later
stage as pending, and zero calls and cost. The external result classifies the
program as invalid because the second operational failure activated the frozen
`second-invalid-execution-in-one-stage` hard stop.

## Interpretation

This is harness and resource-envelope evidence, not retrieval-quality evidence.
It does not measure complete evidence@3, Evidence Recall@5, factual grounding,
boundary safety, visual grounding, synthetic C0-C3 behavior, or provider-backed
T0/T1 behavior. The 10,000-question package was not constructed or executed.

The failure does not change `local-r1-release-qualification-001`: the qualified
local R1 remains the selected release baseline and continues to use its existing
deterministic, fail-closed configuration.

## Decision

Refine the index-materialization harness only through a new prospective
instrument that proves a memory-bounded execution envelope before reopening the
academic program. Candidate controls include a smaller hash-bound embedding
batch, streamed index construction, and persisted per-source checkpoints, but
none is selected by this result.

The original program cannot be resumed or retried. Its provider and paid
authorization are revoked. No OpenAI balance was consumed.

## Limitations

- The interruption was operator-initiated after bounded observation of no
  useful progress; there was no operating-system out-of-memory termination.
- Resident-memory observation is diagnostic rather than a calibrated benchmark.
- No provider, model, benchmark-case, or product response quality was tested.
- Raw runtime ledgers remain local and ignored; only sanitized evidence is
  committed.
