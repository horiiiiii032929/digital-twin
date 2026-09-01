# Cross-engine evaluation 010 attempt 001 invalid result

Decision: **Invalid execution; apply the one allowed harness-only correction.**

The finite program completed the deterministic, GPT-5.4 nano, GPT-5.6 Luna,
and GPT-5.4 mini factual arms before stopping at the first direct-DeepSeek
batch. The shared DeepSeek transport required a privacy-safe
`provider_user_id`, but the cross-engine adapter did not include that field.
Four concurrent requests failed locally with `KeyError` before any DeepSeek
network request was constructed.

The attempt persisted 1,084 ledger entries: 1,079 completed provider calls, one
ordinary GPT-5.4-nano provider failure, and four local DeepSeek harness
failures. It used 530,969 input tokens, 56,303 output tokens, and USD
0.3407715. No autonomy, sealed 1,000-case, known 10,000+1,000, proxy, or local
release stage was opened or interpreted.

The raw ignored output was preserved under
`reports/generated/governed-full-autonomy-v2-1-cross-engine-evaluation-010-attempt-001-invalid/`.
The sole correction adds the non-identifying fixed provider user ID already
required by the historical direct-DeepSeek binding. It changes no case, gold,
retrieval method, prompt, policy, model role, quality gate, or budget. Attempt
002 must start from a fresh exclusive program output and is the final allowed
harness-correction attempt.
