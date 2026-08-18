# Local document ingestion and chunking

## Decision

The repository retains the selected, inspectable text-ingestion baseline and
now adds a prospective region-aware product path for approved PDFs. Source
bytes and original crops stay outside domain models and Git. Parsing can
produce normalized documents, ordered text segments, tables/rows/cells,
figures, vector diagrams, equation-like blocks, OCR regions, page fallbacks,
and release-ready chunks with explicit lineage.

The implementation uses PyMuPDF for selectable text, page geometry, table
structure, embedded images, vector clusters, and normalized region boxes. OCR
and region descriptions are provider-neutral injected interfaces. No OCR or
vision provider is selected by default, and generated descriptions are
searchable metadata rather than authoritative evidence.

## Data flow

```text
Local file
  + SourceArtifact(checksum, version, label, opaque storage ref)
  + ApprovalRecord(professor decision and three permissions)
        |
        v
LocalDocumentParser
  |- CourseDocument + ordered DocumentSegments
  |- FigureAssets -> caller-provided FigureStore
  `- DocumentRegions -> caller-provided RegionCropStore
        |
        v
PageBoundedHeadingParagraphChunker (selected text baseline)
or RegionAwareChunker (prospective multimodal path)
  `- DocumentChunks with stable IDs, region/crop lineage, and permission snapshot
```

The parser verifies that the bytes match the approved SHA-256 checksum and
source version. A checksum change therefore requires a new `SourceArtifact`
version and approval. Derived identifiers include that versioned identity, so
old evaluations remain traceable to the exact input.

## Permission and exclusion rules

All permissions default to `false` and remain independent:

- `processing_allowed` permits parsing and figure extraction.
- `tutoring_allowed` marks produced chunks as eligible for later retrieval.
- `display_allowed` records whether excerpts or figures may be shown later.

Only an approval record with `reviewer_role="professor"` can approve a source.
Rejected, excluded, sensitive-by-default, mismatched-version, checksum-mismatched,
or processing-disabled sources fail explicitly. System-proposed sources cannot
approve themselves. Retrieval implementation in issue #23 must filter every
chunk whose `retrieval_allowed` value is false and must also check the active
source version.

## Normalization and locators

- Plain text is decoded strictly as UTF-8 and split on paragraph boundaries.
- Markdown preserves ATX heading hierarchy, fenced code blocks, and paragraph
  boundaries.
- PDF text uses sorted text blocks with one-based pages and normalized block
  coordinates.
- Embedded PDF figures preserve document and artifact identity, one-based page,
  normalized `(x0, y0, x1, y1)` bounds, caption context, extraction method,
  checksum, and an opaque image reference.
- Figure bytes are persisted only through a caller-provided store. The included
  local store must point to a Git-ignored directory.
- Region crops preserve source checksum and version, page, normalized
  `(x0, y0, x1, y1)` bounds, region kind, extraction method, parent region,
  permission snapshot, crop checksum, and opaque crop reference.
- Scanned and large-image pages use an injected OCR provider. A configured
  provider returns normalized text regions; the parser never grants permission
  or treats OCR/model metadata as an independent source.
- Table cells retain the original cell value and add source-derived row and
  column labels only to the searchable representation.

## Chunking decision

The selected cross-course baseline groups ordered heading, paragraph, or
PDF-block segments within each page up to 1,200 characters, with up to 160
characters of whole-segment overlap. Character limits remain
tokenizer-independent. Oversized individual segments are split on word
boundaries, with a hard character fallback for unusually long tokens.

Chunk IDs are SHA-256-derived from the versioned document ID, ordinal, locator,
and content hash. Repeated runs over identical inputs therefore produce the
same document, figure, and chunk identifiers. The cross-course ingestion
comparison found that the document-wide control crossed PDF page boundaries in
591 of 598 chunks. The page-bounded candidate produced 1,322 chunks with zero
cross-page chunks, complete provenance, stable identities, and no empty or
oversized chunks. It is selected in
[`student-tutor-v1`](../research/05_evaluation/profiles/student-tutor-v1.json).
See the
[result summary](../research/05_evaluation/cross-course-ingestion-v1-results.md)
for limitations. Retrieval quality and size sensitivity remain separate
evaluation questions.

## Verification

Run the focused synthetic verification:

```bash
npm run verify:ingestion
```

Run the private cross-course audit only when the approved local corpus is
available:

```bash
npm run audit:cross-course-ingestion
```

It processes five approved synthetic sources across TXT, Markdown, and PDF,
including one embedded PDF figure. Every document is parsed and chunked twice;
the command fails if identities change or provenance is lost.

Run the automated tests or complete repository check:

```bash
uv run pytest tests/digital_twin/test_local_ingestion.py
npm run check
```

Validate and execute the new public-synthetic development pilot with:

```bash
npm run verify:multimodal-product-grounding
npm run benchmark:multimodal-product-grounding-development
```

## Known limitations and failure cases

- Scanned/image-only PDFs require a configured OCR provider. The current
  product foundation proves the injected path with authored synthetic OCR but
  does not select or ship a production OCR engine.
- Encrypted PDFs and malformed PDFs are rejected.
- Reading order and column detection remain deterministic heuristics. Complex
  lecture layouts still need representative provider/layout qualification.
- Vector clusters are coarse diagram regions; they do not yet recover graph
  semantics, equation structure, or arbitrary nested layout.
- Caption detection uses nearby text geometry and can select the wrong text in
  dense layouts; figure descriptions remain a separate, reviewable model.
- Eighty-four selected cross-course chunks are shorter than 80 characters,
  including page-number-only and title-slide content.
- Five of eight visually inspected cross-course pages contained important
  diagram or spatial meaning not fully represented by selectable text.
- The new 21-case synthetic V2 pilot reached 13/13 complete visual evidence and
  citation lineage with the compact deterministic route, but failed its frozen
  relative p95 gate. No multimodal profile is selected, and the historical
  24-case held-out split remains unopened. See the
  [attempt-003 result](../research/05_evaluation/multimodal-product-grounding-v2-development-attempt-003-results.md).
- TXT, Markdown, and PDF are the only supported formats. Word, PowerPoint,
  audio, video, Canvas, and Obsidian integration remain out of scope.
- Retrieval filters non-tutoring and superseded chunks. The local store still
  does not provide lifecycle cleanup or durable artifact registration, so
  production persistence must revoke derived artifacts when source permissions
  or versions change.
