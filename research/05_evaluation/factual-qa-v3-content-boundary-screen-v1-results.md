# Evaluation result: factual-qa-v3-content-boundary-screen-v1

Date: 2026-08-19

Decision: **Keep the deterministic private screen; 570/570 candidates preserve
physical integrity and 35 receive priority boundary review without assigning a
final semantic role**

## Scope and method

This local-only correction-stage screen used the private
`factual-qa-v3-source-roles-v2` manifest. It verified each candidate's presence
and SHA-256 before extracting locally available text from PDFs, DOCX XML,
plain-text formats, code, notebooks, tables, structured files, diagrams, and
typeset sources. Raster or unsupported binary sources were routed to manual or
visual review.

The screen counts deterministic patterns for credential/private-key indicators,
student or participant identity, completed or graded work, answer or solution
material, and assessment instructions. A match is a review signal, not a final
exclusion. Absence of a match is not evidence of semantic eligibility.

The private per-file record remains ignored at
`data/interim/factual_qa_v3/content_boundary_screen_v1.json`. It contains source
IDs, private relative paths, hashes, counts, and routes but no extracted text or
snippets. Its stable record SHA-256 is
`75f8a76c19266708081b1a7bab508f98eeb3db2b30de18583f599b19e4537013`.

## Result

| Extraction outcome | Files |
| --- | ---: |
| Direct text | 471 |
| PDF text | 82 |
| DOCX XML | 1 |
| Binary/visual review required | 2 |
| Visual review required | 14 |
| **Total** | **570** |

| Review route | Files |
| --- | ---: |
| Mandatory-exclusion review signal | 2 |
| Privacy or academic-integrity review signal | 17 |
| Manual or visual boundary review | 16 |
| Semantic-role review | 535 |
| **Total** | **570** |

Signal-file counts may overlap: two credential/private-key indicators, nine
identity/student-record indicators, four completed/graded-work indicators, six
answer/solution indicators, and 126 assessment-instruction indicators. These
counts deliberately reveal neither paths nor source content and do not assert
that every lexical match is a true violation.

- Physical presence and hash integrity: 570/570
- Local content-screen completion: 570/570
- Final source roles assigned: 0
- Semantic-eligibility gate: failed by design
- External provider calls: 0
- Local model calls: 0
- API cost: USD 0
- Private paths or source content committed: 0

## Validity and limitations

The screen reduces the chance that obvious sensitive or answer-bearing content
reaches later review, but regular expressions cannot establish privacy safety or
semantic role. The 16 visual/binary records need visual boundary review, and all
flagged records need content-aware adjudication. The 535 unflagged records still
require semantic review because lexical silence is not eligibility evidence.

## Decision

**Keep as a routing control.** Review the 35 priority records during the
repository correctness program. Do not authorize model review, factual-QA
generation, held-out execution, or scale from this result.
