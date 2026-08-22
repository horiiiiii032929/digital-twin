# Factual-QA cumulative 1,000-case checkpoint

## Decision

**Keep.** The validated deterministic factual-QA method remained stable across
the additional 900 cases. The result supports preparing, but does not authorize,
the remaining 9,000-case completion stage.

## Result

- New cases: 900; cumulative cases: 1,000.
- Deterministic validity: 900/900 new; 1,000/1,000 cumulative.
- Citation validity: 720/720 new answerable; 800/800 cumulative.
- Boundary action accuracy: 180/180 new.
- Independent reviewer agreement: 898/900 new; 997/1,000 cumulative.
- Mutation detection: 179/180 new; 199/200 cumulative.
- Exact normalized duplicates: 0 across the combined 1,000 questions.
- Malformed responses: 0.
- Provider responses: 1,984/1,984 attempts.
- Cost: USD 0.736348 new; USD 0.821754 cumulative.
- New-run p95 latency: 2.230 seconds.

The two advisory false rejections were resolved as valid cases. Direct review
also confirmed the one missed truncated-citation mutation was a real defect that
the deterministic validator correctly rejected. The 12-case priority review
confirmed all inspected decisions.

## Boundaries

This result validates synthetic-public scale mechanics and the deterministic
truth method. It does not validate real Academia Vault sources, teaching style,
Professor Digital Twin fidelity, or production deployment. Raw provider output
remains ignored at
`reports/generated/factual-qa-v3-scale-checkpoint-1000-002.json`, SHA-256
`ae8a1349d303bf73c7099a6e3544fda0ae7a23bc2019d8dc51ef9f42e650fe8e`.
Authorization is revoked; the remaining 9,000 cases require a new decision.
