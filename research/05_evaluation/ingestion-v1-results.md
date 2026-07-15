# Ingestion v1 results

## Run identity

- Result ID: `ingestion-v1-clean`
- Components: parser and chunker
- Status: completed
- Date: 2026-07-14
- Clean merged revision: `43e65c0`
- Reproduction: `npm run verify:ingestion`
- Dataset: five approved synthetic TXT, Markdown, and generated PDF sources
- Private or real course content: none

This result predates the standard comparison record. It verifies one bounded
baseline rather than comparing multiple implementations, so it has a readable
result but no component-comparison JSON record.

## Configuration

- Parser: PyMuPDF-backed local document parser for selectable-text PDF plus
  deterministic UTF-8 TXT and Markdown parsing
- Chunker: heading/paragraph chunker with `max_chars = 480` and
  `overlap_chars = 80` for the verification command
- Repeated trials: every source parsed and chunked twice
- Permissions: synthetic professor approval with processing and tutoring
  permission; display permission disabled

## Results

| Measure | Result | Raw count | Gate |
| --- | ---: | ---: | --- |
| Documents parsed deterministically | 1.00 | 5 / 5 | Pass |
| Sources with stable chunk identifiers | 1.00 | 5 / 5 | Pass |
| Sources with provenance and retrieval permission preserved | 1.00 | 5 / 5 | Pass |
| Extracted embedded figures | 1 | 1 expected | Pass |
| Produced chunks | 5 | 5 sources | Diagnostic |

The focused automated suite also covers rejected, excluded, sensitive,
processing-disabled, checksum/version mismatch, invalid UTF-8, empty,
unsupported, MIME mismatch, and image-only PDF failures. The current
reproduction has 18 focused ingestion tests; the original merged PR passed the
then-current full repository and GitHub CI suites.

## Failures and corrections

Diff review before the recorded merge found and corrected four implementation
problems:

- approval metadata is checked before source bytes are read;
- verification fails when provenance is not preserved;
- Markdown headings inside fenced code are not treated as structure;
- PDF coordinate normalization handles non-zero page origins.

No known source, determinism, or provenance failure remained in the final
synthetic verification.

## Decision

- Parser: Keep the PyMuPDF selectable-text baseline behind the parser contract.
- Chunker: Refine; retain the heading/paragraph algorithm, but select size and
  overlap only through retrieval evaluation on a larger corpus.
- Profile effect: parser and chunker remain selected in `student-tutor-v0`.
- Retained future candidates: layout-aware parsing, OCR, fixed-token chunking,
  and semantic chunking.

## Limitations

- Five documents and one simple generated PDF are contract-level verification,
  not a selection-grade parser benchmark.
- Complex reading order, scanned documents, tables, formulas, vector figures,
  and presentation files are not represented.
- The run does not compare PyMuPDF with a layout-aware parser or OCR system.
- Chunk count is too small to determine a production chunk size or overlap.

The next parser/chunker comparison must use the larger stratified sizes in the
component evaluation plan and report extraction completeness, reading order,
boundary loss, duplication, retrieval effects, and human-reviewed failures.
