# Evaluation result: factual-qa-v3-conversion-resolution-v1

Date: 2026-08-19

Decision: **Keep the local conversion boundary; all 2,637 physical files are
resolved and 602 technically readable sources advance to semantic role review**

## Scope

This Stage A result resolves every exception from conversion-readiness v3. It
combines direct local parsing, local Apple Vision OCR, office/preview adapters,
archive inspection, and explicit empty/redundant exclusions into one private
hash-bound disposition manifest.

The final private manifest remains ignored at
`data/interim/factual_qa_v3/source_dispositions_v4.json`. Its stable SHA-256 is
`2e8fff17d60de28d260e56ea753b18a452d097862833b1a1e3fca98c87a0313e`.

## Result

| Resolution | Sources |
| --- | ---: |
| Direct local text/structured/PDF/visual adapters | 598 |
| Local Apple Vision OCR | 4 |
| Excluded whitespace-only sources | 2 |
| Excluded redundant archive container | 1 |
| Previously resolved exclusion/duplicate records | 2,032 |
| **Total physical files** | **2,637** |

Apple Vision processed four one-page PDFs and returned non-empty OCR for 4/4.
The private OCR record SHA-256 is
`d8e671485ee185f0aaae267f8ed3e0bdf40e26f9f36096df3595103e5dcd8e46`.

The ZIP safety audit found 21 entries, no path traversal, encryption, symlinks,
or read errors. Ten entries exactly duplicate already inventoried sources and
eleven are AppleDouble macOS sidecars, so the archive adds no unique teaching
source. The private archive record SHA-256 is
`f2add35c0cb3ec9065ddd5b6a404c50992b0ee659e229a0ce845c16136e61abf`.

- Conversion gate: passed
- Unresolved conversion cases: 0
- Sources advancing to semantic role review: 602
- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Private paths, OCR text, or source content committed: 0

## Validity and limitations

This proves local technical readability and complete source accounting, not
semantic eligibility or extraction fidelity. OCR output still requires
claim-level source alignment and visual audit. Pages previews preserve visual
access but may not expose all editable document structure. Plain-text fallback
for malformed structured files preserves inspectability without claiming
schema validity.

## Decision

**Keep.** Freeze the v4 conversion-resolved manifest as the input to semantic
role classification. The next gate must distinguish authoritative evidence,
supporting context, question inspiration, and mandatory exclusions across all
602 sources. No factual-QA model run or scale stage is authorized yet.
