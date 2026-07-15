# Local document ingestion and chunking

## Decision

Sprint 2 uses a small, inspectable local ingestion baseline for approved UTF-8
text, Markdown, and selectable-text PDFs. Source bytes stay outside domain
models and Git. Parsing produces normalized documents, text segments, figure
metadata, and deterministic chunks with explicit lineage.

The implementation uses PyMuPDF for selectable-text PDF blocks, embedded image
extraction, page geometry, and normalized figure bounding boxes. This was chosen
over a text-only PDF library because issue #22 requires both text and figure
provenance. OCR, layout reconstruction, and vision-generated descriptions are
deliberately deferred.

## Data flow

```text
Local file
  + SourceArtifact(checksum, version, label, opaque storage ref)
  + ApprovalRecord(professor decision and three permissions)
        |
        v
LocalDocumentParser
  |- CourseDocument + ordered DocumentSegments
  `- FigureAssets -> caller-provided FigureStore
        |
        v
HeadingParagraphChunker
  `- DocumentChunks with stable IDs, locators, hashes, and permission snapshot
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

## Chunking decision

The baseline groups ordered heading, paragraph, or PDF-block segments up to
1,200 characters, with up to 160 characters of whole-segment overlap. Character
limits were selected instead of tokenizer-specific limits to keep the baseline
provider-neutral and reproducible. Oversized individual segments are split on
word boundaries, with a hard character fallback for unusually long tokens.

Chunk IDs are SHA-256-derived from the versioned document ID, ordinal, locator,
and content hash. Repeated runs over identical inputs therefore produce the
same document, figure, and chunk identifiers. The issue #23 evaluation keeps
the algorithm unchanged and tests a smaller 220-character, 60-character-overlap
configuration over the compact synthetic corpus. See
[local-retrieval.md](local-retrieval.md) for its measured retrieval behavior;
chunk settings for a larger corpus must still be selected by evaluation rather
than intuition.

## Verification

Run the focused synthetic verification:

```bash
npm run verify:ingestion
```

It processes five approved synthetic sources across TXT, Markdown, and PDF,
including one embedded PDF figure. Every document is parsed and chunked twice;
the command fails if identities change or provenance is lost.

Run the automated tests or complete repository check:

```bash
uv run pytest tests/digital_twin/test_local_ingestion.py
npm run check
```

## Known limitations and failure cases

- Scanned/image-only PDFs are rejected because OCR is not implemented.
- Encrypted PDFs and malformed PDFs are rejected.
- PDF reading order depends on the source's selectable-text layout metadata;
  complex multi-column slides may need a later layout-aware parser.
- Only embedded raster images are extracted. Vector drawings and tables are not
  converted into figure assets.
- Caption detection uses nearby text geometry and can select the wrong text in
  dense layouts; figure descriptions remain a separate, reviewable model.
- TXT, Markdown, and PDF are the only supported formats. Word, PowerPoint,
  audio, video, Canvas, and Obsidian integration remain out of scope.
- Retrieval filters non-tutoring and superseded chunks. The local store still
  does not provide lifecycle cleanup or durable artifact registration, so
  production persistence must revoke derived artifacts when source permissions
  or versions change.
