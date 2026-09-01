# Actual-product autonomy evaluation 007 invalid result

Decision: **Invalid execution — correct the infeasible call ceiling before
resuming the unchanged evaluation.**

The prompt-schema correction worked: both T0 and T1-v2 provider canaries
passed and bulk execution began. During the first 32 durable cases, the observed
call pattern showed that the frozen 3,000-call ceiling was mathematically below
the conservative 5,740-call upper bound derived from the canaries. Continuing
would therefore have guaranteed an invalid result after unnecessary spend.

- Persisted cases: 32/820.
- Provider calls: 170; 124 completed and 46 expected/handled failures.
- Reported tokens: 67,339 input and 7,343 output.
- Reported cost: USD 0.12250275.
- Hidden gold: unopened.
- Prompt-schema canaries: passed.

Attempt 007 was deliberately interrupted before opening hidden gold and is
preserved as invalid execution evidence. Successor 008 adds a pre-bulk call
projection, raises only the operational safety ceiling to 10,000, and runs up
to eight independent cases concurrently with atomic per-case persistence.
Cases, gold, product behavior, retrieval, model roles, and hard gates are
unchanged.
