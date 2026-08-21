# Factual-QA v3 scale pilot 100 attempt 002 build result

## Decision

**Keep the corrected build for a separately authorized pilot; do not claim paid-method quality and do not scale.**

Attempt 002 corrects the method defects exposed by attempt 001. Provider
execution remains unauthorized, so this result establishes implementation and
simulation readiness only.

## Bound implementation

- Clean implementation revision: `d5fe8745a5b4415d71272f4040ad7b411c3f56f0`
- Instrument SHA-256: `3c2898280a5ef8821abbcc33bb7e6ac8fd7898d6cdbae3b53ca1d9f5f2a9fd90`
- Runner SHA-256: `fce54a086f313e2597beef8680941db08f80bb463fc7561caf67c90d4d5d082d`
- Corpus design: unchanged deterministic 1,000-source, 8,000-claim,
  10,000-blueprint artifact; first 100 stratified cases only
- Private data and provider calls: zero

## Corrections

1. The author request now uses the repository's full nested JSON schema and an
   explicit exact-key contract. Citation values must be objects containing only
   `source_unit_id` and `quote`; observed string and alternate-key forms are
   rejected by regression tests.
2. Scale review now imports the same schema, system prompt, review prompt, and
   validator used by reviewer qualification 006. The qualification and scale
   contracts can no longer drift independently in this runner.
3. All 20 mutation controls are built from deterministic canonical valid cases,
   not from successful model-authored cases. Mutation sensitivity remains
   measurable even when every author call is malformed.

## Verification

- Normal network-free simulation: 222/222 simulated calls, all machine gates
  passed, 100/100 deterministic controls valid, and 20/20 mutations rejected.
- Maximum-dispute simulation: disputes stopped at 24 and total calls at 246.
- Total-author-malformation simulation: 100 malformed authors were retained as
  failures while all 20 independent mutations were still constructed and
  reviewed.
- Focused successor/freeze tests: 25 passed.
- Complete repository gate: 682 Python tests and 46 frontend tests passed;
  frontend lint and production build passed.
- Repository inventory: 449/449 audited.
- Clean no-call preflight: `blocked-not-authorized`; instrument not frozen,
  working tree clean, credentials present, output unused.

## Limitations and next gate

Simulated responses prove orchestration and contract consistency, not hosted
model compliance or dataset quality. A separate commit and explicit user
authorization are required before attempt 002 may make provider calls. The
1,000- and 10,000-case stages remain unauthorized regardless of the next
100-case outcome.
