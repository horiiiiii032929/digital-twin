# Evaluation result: factual-qa-v3-source-disposition-v2-correction-001

Date: 2026-08-19

Predecessor: `factual-qa-v3-source-disposition-v1`

Decision: **Keep the accounting method after correction; reduce the pending
review queue from 663 to 610 by excluding 53 missed tool-state artifacts**

## Correction trigger

The format-level quality profile found `.DS_Store`, nested pytest-cache,
editor-swap, and backup artifacts in v1's explicit-review queue. The original
inventory's extension/path heuristic did not recognize all nested or
extensionless forms. This wasted review capacity and could allow unrelated tool
state into later conversion attempts.

The v1 result remains unchanged and reproducible at commit `ccefefd`.

## Prospective repair

V2 adds exact, deterministic path-part and basename rules for:

- `.DS_Store`;
- any `.pytest_cache` path component;
- `*.swp`; and
- `*.bkp`.

The rules classify only generated metadata or transient tool state. They do not
promote any file to evidence and do not inspect or emit private content.

## Corrected result

| Disposition | V1 | V2 | Change |
| --- | ---: | ---: | ---: |
| Excluded duplicate/generated/tool state | 1,971 | 2,024 | +53 |
| Excluded integrity/privacy | 3 | 3 | 0 |
| Review or conversion required | 663 | 610 | -53 |
| **Total accounted for** | **2,637** | **2,637** | **0** |

V2 retains 2,497 unique content hashes and 140 non-canonical duplicate files.
Its stable disposition SHA-256 is
`45057bd4a2f01e3c7bd96ada37236fb51ecfbf2a6ebc5dae1964f4af23090c9e`.

- Complete-accounting gate: passed
- Release-ready gate: failed as intended
- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Private paths or source content committed: 0

## Decision

**Keep the corrected accounting implementation and continue Refine overall.**
Use v2 for conversion readiness and semantic role review. The remaining 610
sources still require explicit evidence-role, exclusion, or conversion
decisions before release.
