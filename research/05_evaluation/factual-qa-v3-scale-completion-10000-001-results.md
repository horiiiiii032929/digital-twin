# Factual-QA cumulative 10,000-case completion

## Decision

**Keep.** The deterministic, source-linked factual-QA method passed every
predefined gate across the final 9,000 cases and now has cumulative evidence
for 10,000 synthetic-public cases. No further factual-QA scale is authorized.

## Result

- New cases: 9,000; cumulative cases: 10,000.
- New action mix: 7,200 answer, 900 abstain, 450 clarify, and 450 refuse.
- Deterministic validity: 9,000/9,000 new; 10,000/10,000 cumulative.
- Citation validity: 7,200/7,200 new answerable; 8,000/8,000 cumulative.
- Boundary action accuracy: 1,800/1,800 new.
- Independent reviewer agreement: 8,927/9,000 new; 9,924/10,000 cumulative.
- Mutation detection by the advisory reviewer: 1,795/1,800 new; 1,994/2,000 cumulative.
- Deterministic mutation rejection: 1,800/1,800 new.
- Exact normalized duplicates: 0 across all 10,000 questions.
- Malformed reviewer responses: 3; one additional mutation review had no provider response.
- Provider responses: 19,874/19,875 attempts.
- Cost: USD 7.632671 new; USD 8.454425 cumulative.
- New-run p95 latency: 2.358 seconds.

All 73 advisory disagreements were resolved by bounded dispute review. Direct
review confirmed all 12 priority cases as valid: each question matched its
target, and each answer, claim ID, source ID, and quote exactly matched the
authoritative truth package. Separate failure analysis confirmed the five
mutation misses were genuine defects—two missing citations, two truncated
citations, and one paraphrased citation/provider error—that deterministic
validation rejected correctly.

## Boundaries

This is synthetic-public scale evidence for the dataset-generation and
verification method. It does not validate real Academia Vault sources,
retrieval over real course materials, autonomous tutoring behavior, Professor
Digital Twin fidelity, or production deployment. The advisory reviewer remains
imperfect and cannot override deterministic truth.

Raw output remains ignored at
`reports/generated/factual-qa-v3-scale-completion-10000-001.sqlite3`, SHA-256
`e8074bc90bff77fc1e3565fa44d92b32ab46fea7513eea1a05fb1d1375eb2a23`.
The one-time authorization is revoked.
