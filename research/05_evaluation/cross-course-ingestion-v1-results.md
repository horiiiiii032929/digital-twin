# Evaluation result: cross-course-ingestion-v1

## Run identity

- Component: parser and chunker
- Status: completed
- Date and owner: 2026-07-28, project researcher
- Code revision: `fcd607fb968b64cf054e47cdffc460f1085de592`
- Working tree: dirty during the run; task implementation was subsequently
  committed unchanged at the revision above, while unrelated user-owned report
  and plotting files remained outside the commit
- Reproduction:
  `npm run audit:cross-course-ingestion`
- Runtime: Python 3.12, PyMuPDF parser, no model or provider calls
- Generated artifact:
  `reports/generated/cross-course-ingestion-v1.json` (ignored; contains no
  course text)
- Plan:
  [`2026-07-28-cross-course-ingestion-v1-plan.md`](../04_experiments/2026-07-28-cross-course-ingestion-v1-plan.md)

## Decision context

The prospective question was whether document-wide heading/paragraph chunking
could preserve page-precise evidence on lecture slides, or whether the same
algorithm had to be constrained to one page at a time.

- Control: document-wide `HeadingParagraphChunker`
- Candidate: `PageBoundedHeadingParagraphChunker`
- Shared configuration: `max_chars = 1200`, `overlap_chars = 160`
- Corpus: all 32 PDFs in `cross-course-portfolio-v2`
- Repeats: two parse and chunk passes per document
- Prediction: parsing would pass, but the control would combine adjacent pages

## Data and sample size

This was a census of the selected private corpus, not a sample:

| Course | Documents | Pages | Parsed text pages | Segments | Raw embedded-image objects |
| --- | ---: | ---: | ---: | ---: | ---: |
| IT5002 | 13 | 508 | 508 | 5,957 | 1,067 |
| CS5421 | 8 | 429 | 429 | 5,293 | 322 |
| IT5100B | 5 | 169 | 169 | 1,255 | 11 |
| IT5100E | 6 | 212 | 212 | 1,956 | 223 |
| **Total** | **32** | **1,318** | **1,318** | **14,461** | **1,623** |

All 32 source hashes matched the manifest, all 32 PDFs parsed, and all 32
documents reproduced the same document, figure, and chunk identities on the
second pass. No private text, figure bytes, assignment, answer, student data,
credential, or secret entered the durable artifact.

The embedded-image count is not a semantic figure count. One visually coherent
slide can contain many small image objects.

## Aggregate results

| Candidate | Chunks | Cross-page | Provenance complete | Oversized | Empty | Tiny `<80` chars | Normalized duplicates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Document-wide control | 598 | 591 (98.8%) | 598 (100%) | 0 | 0 | 0 | 0 |
| Page-bounded candidate | 1,322 | 0 (0%) | 1,322 (100%) | 0 | 0 | 84 (6.35%) | 0 |

The control failed the evidence-locality gate: only 7 of 598 chunks stayed on
one page. The candidate passed every predeclared hard gate. It produced 1,322
unique IDs, a maximum length of 1,198 characters, and no empty or cross-page
chunks.

Tiny candidate chunks were concentrated in IT5002 (52), IT5100B (22), and
IT5100E (10). Follow-up inspection found 25 IT5002 pages whose selectable text
was only a page number. Other tiny chunks were mainly section-title slides.
Page-number-only chunks should be filtered as deterministic low-information
content before retrieval; title slides remain available unless development
evidence shows they harm ranking.

## Hard gates

| Gate | Control | Candidate | Evidence |
| --- | --- | --- | --- |
| Manifest integrity | Pass | Pass | 32/32 source hashes matched |
| Parse and deterministic identity | Pass | Pass | 32/32 repeated documents stable |
| Page locality | **Fail** | Pass | 591/598 versus 0/1,322 cross-page chunks |
| Source/version/locator/page/permission/hash provenance | Pass | Pass | 100% of chunks |
| Maximum 1,200 characters | Pass | Pass | maxima 1,200 and 1,198 |
| Empty chunks | Pass | Pass | 0 for both |
| Unique IDs | Pass | Pass | every chunk ID unique |
| Private-output boundary | Pass | Pass | sanitized counts and IDs only |

## Operational results

| Measure | Result |
| --- | ---: |
| Parse median per document | 448.3 ms |
| Parse p95 per document | 6,083.7 ms |
| Control chunk median / p95 | 0.42 / 1.20 ms |
| Candidate chunk median / p95 | 0.77 / 1.41 ms |
| Provider calls | 0 |
| Cost | USD 0 |

The candidate's additional chunking time is operationally negligible. Parser
latency varies with PDF size and image-object complexity and is reported only
as local operational evidence, not a quality criterion.

## Visual inspection

Eight pages were rendered and inspected: one figure-heavy and one deterministic
middle page per course.

| Course | Figure-heavy observation | Middle-page observation | Benchmark consequence |
| --- | --- | --- | --- |
| IT5002 | Data-transfer meaning depends on arrows and spatial relationships | sampled page was a blank transition containing only its page number | exclude page-number chunks; do not use diagram-only relationships as text gold |
| CS5421 | entity-relationship alternatives and handwritten annotations are spatial | relational-algebra example includes a diagram and non-selectable handwriting | printed text may be gold; handwriting and diagram-only conclusions may not |
| IT5100B | Kafka producer/consumer order is encoded by arrows | reactive-programming statement is adequately represented by selectable text | retain textual cases; mark flow-order cases as visual-unsupported |
| IT5100E | tokenization/vectorization is partly diagrammatic; 96 image objects were fragments, not 96 figures | revocation/refresh slide contains sufficient printed explanation plus diagrams | use printed claims only; never interpret raw image-object count as semantic coverage |

Five of eight pages carried important spatial or diagram meaning that plain
text did not fully represent. Two CS5421 samples also contained handwritten
annotations that were not selectable. A follow-up diagnostic emitted recoverable
MuPDF xref warnings while enumerating figures in IT5002 `9_caches.pdf`; text
extraction, page rendering, and deterministic output still completed. Therefore
the parser is kept for selectable text, but figure completeness is not claimed.

## Failures and surprises

- **Chunking:** 591 control chunks crossed page boundaries. This was the
  predicted decisive failure.
- **Chunking:** 84 candidate chunks were shorter than 80 characters; 25 source
  pages contained only a page number.
- **Layout:** five of eight visual samples contained relationships not fully
  recoverable from extracted text.
- **Parsing/operations:** one IT5002 PDF produced recoverable xref warnings
  during image enumeration. Figure counts for that source may be incomplete.
- **Measurement:** raw embedded-image objects substantially overcount semantic
  figures.

## Validity review

- The plan, candidates, metrics, hard gates, and decision rule were written
  before canonical-corpus measurements were inspected.
- Every selected document was included; no favorable subset was chosen.
- Two deterministic runs were compared.
- Private source text remained ignored.
- The run is not invalidated. The dirty state is disclosed, and the task code
  used by the run is preserved at the recorded revision.

## Decision

- Outcome: **Keep**
- Selected implementation:
  `page-bounded-heading-paragraph-chunker@v1`
- Retained control: document-wide heading/paragraph chunking for regression
- Parser: keep `pymupdf-document-parser@v1` for selectable text, with no claim
  of complete diagram, handwriting, or semantic-figure extraction

The selected candidate is the corpus-construction boundary for the private
cross-course benchmark. Page-number-only content receives a deterministic
low-information exclusion before retrieval. Visual-dependent claims are either
supported by adequate printed text or labeled unsupported; they are not silently
converted into text gold.

## Limitations and follow-up

This result establishes deterministic, page-local, permission-preserving text
chunks. It does not establish retrieval quality, optimal chunk size, semantic
figure handling, OCR, answerability, professor fidelity, or student usability.

Next:

1. freeze the private benchmark schema and review states;
2. draft answerable cases only from adequate printed evidence;
3. add no-evidence, cross-course confusion, low-information, and
   visual-unsupported slices;
4. have the researcher inspect at least 20 cases before sealing; and
5. qualify embedding and reranking providers only on the development split.

## Learning notes

Character limits alone do not create valid evidence units for slide decks. A
chunk can be short, deterministic, and provenance-complete while still joining
two unrelated pages. Constraining grouping by the source's natural page boundary
fixed that failure with negligible runtime cost. Selectable text also proves
only that characters can be extracted; visual review showed why diagrams,
handwriting, and image fragments require separate treatment.
