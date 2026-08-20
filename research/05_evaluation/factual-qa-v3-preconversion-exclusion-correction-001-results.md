# Evaluation result: factual-qa-v3-preconversion-exclusion-correction-001

Date: 2026-08-19

Predecessors: `factual-qa-v3-source-disposition-v2-correction-001` and
`factual-qa-v3-conversion-readiness-v1`

Decision: **Keep the corrected v3 disposition; remove five non-evidence files
before conversion and reduce the genuine remediation queue from 24 to 19**

## Correction trigger

The first conversion audit included one zero-byte assembly source, three
`.gitignore` files, and one `.python-version` file. These are not conversion
failures: the empty source contains no evidence, and the configuration files
are unrelated project metadata. Sending them through OCR or document conversion
would violate the source-governance boundary.

One additional exact-duplicate configuration path was already excluded in v2;
v3 reclassifies its reason without changing the pending denominator.

## Corrected result

Source disposition v3 accounts for all 2,637 files:

| Role | Files |
| --- | ---: |
| Excluded duplicate/generated/tool state | 2,024 |
| Excluded integrity/privacy/unrelated | 8 |
| Review or conversion required | 605 |

Its stable disposition SHA-256 is
`2ae7b98f271086b4e38bbfe0d93b69fe688fbbae566dd6a74aac85571da7e2e1`.

The corrected conversion-readiness v2 audit reports:

| Status | Sources |
| --- | ---: |
| Locally conversion-ready | 586 |
| Needs OCR | 4 |
| Needs office conversion | 4 |
| Unsupported format | 7 |
| Invalid for current parser | 4 |
| **Total pending** | **605** |

- Integrity gate: passed, 605/605
- Local-conversion gate: failed, 586/605 ready (96.9%)
- Stable conversion record SHA-256:
  `7d9158127bdee9cb94802222adf4e841c97fe529c9fef91c5b52b18e0bec5824`
- External/model calls: 0
- API cost: USD 0
- Private paths or content committed: 0

## Decision

**Keep the corrected exclusion boundary and continue Refine.** Use Apple Vision
OCR for the four one-page scanned PDFs, local document adapters for the office
files, and explicit local inspection for the eleven unsupported/parser-invalid
sources. Semantic evidence roles remain unassigned, and model execution remains
unauthorized.
