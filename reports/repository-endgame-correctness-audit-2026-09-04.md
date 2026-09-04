# Repository endgame correctness audit

Status date: 2026-09-04

## Decision

The active repository code and the PR #199 evidence line are internally
consistent after the corrections below. The selected configuration may proceed
to one fresh local HTTPS qualification, but it must not be described as passing
the academic factual-grounding benchmark.

The known 10,000-candidate plus 1,000-control package remains immutable
`No Release` evidence. It was not read, rerun, or rescored during this audit.

## Findings and resolutions

| Finding | Resolution | Evaluation impact |
| --- | --- | --- |
| Selection 004 labelled overall task success as answerable fully grounded factual success. | Recomputed from the immutable, hash-verified selection-003 ledgers and corrected the label. Candidate factual success is 42.50% versus 26.00%; overall success remains 50.00% versus 36.80%. | The +16.50-point relative selection and zero-severe-release result remain, but both arms fail 12 absolute gates. The gate is the best tested development option, not an absolute pass. |
| Local qualification 004 used Terra and a historical qualification record, while confirmation 024 selected Luna H+E1. | Added an exact binding record and candidate profile; startup now rejects missing or mismatched evidence-gate bindings. | Qualification 004 remains historical operational evidence. The exact Luna H+E1 composition requires fresh qualification 005. |
| Selection 004 accepted prior ledgers from status and row count alone. | Added instrument, manifest, configuration, case-ID-set, and payload-hash verification. | Prevents a valid-looking but unrelated ledger from influencing a future selection. |
| Generic evaluation-record dispatch misclassified some whole-system records when a component label was present without candidate rows. | Corrected dispatch and added regression coverage. | The machine-readable registry now validates all 235 records and 307 summaries. |
| The default repository gate implicitly depended on ignored historical/generated artifacts and could open sealed material. | Moved those operations to `verify:historical-generated-artifacts`; the default API suite excludes only four artifact-bound historical tests. | `npm run check` is self-contained for committed code and does not touch the sealed package. Historical source tests remain available explicitly. |
| Four post-selection floor audits were not exactly reproducible from committed commands and their summaries disagreed on some counts. | Added a provider-free reproduction command and narrowed the claim. | The convergent safety/no-safe-gain finding is reproduced for the bounded mechanisms; a universal task floor is not claimed. |
| Two active evaluation modules had unused imports. | Removed the imports and ran focused Ruff checks. | No metric or result changed. Frozen historical scripts were not rewritten. |

## Verification

- `npm run check`: passed.
- Python/API: 1,845 passed, 0 failed.
- Frontend: 50 passed, lint passed, TypeScript and production build passed.
- Evaluation registry: 235 machine records and 307 result summaries validated.
- Repository inventory: 1,073/1,073 audited before this report was added; it is rebuilt with this report before publication.
- Execution freeze: active, 174/174 entrypoints guarded, zero provider calls and zero held-out reads.
- Focused correction tests: 19 passed.
- Focused Ruff check: passed.
- `git diff --check`: passed.

## Non-blocking limitations

- The frontend production bundle emits a 506.69 kB chunk-size warning. This is
  a performance optimization item, not a correctness failure.
- The live npm registry audit endpoint timed out during this checkpoint.
  Cached offline npm audit data reports zero vulnerabilities, but a fresh live
  registry audit should be rerun when the endpoint is responsive.
- Thirty-nine Ruff findings remain in frozen historical scripts. They are not
  active runtime defects and are preserved to avoid rewriting historical
  evidence tooling.

## Next bounded action

Run `local-r1-governed-v2-1-release-qualification-005` against a clean commit
using the exact Luna H+E1, deterministic generator,
`dominance-scoped-ambiguity-safe-v3`, and candidate-v3 profile binding. Record
the outcome whether it passes or fails. A pass supports only a local research
demo claim; it cannot override the unfavorable academic grounding result.
