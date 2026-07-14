# Local ingestion learning log

## Component

Local permission-gated TXT, Markdown, and selectable-text PDF ingestion,
embedded PDF figure extraction, provenance modeling, and deterministic
heading/paragraph chunking.

## Prediction

I expected unsupported file extensions and documents that were not chunked
correctly to be the main ingestion failure risks.

## How it works

In the knowledge check, I identified the flow as `SourceArtifact` plus
`ApprovalRecord`, then `CourseDocument`, `DocumentSegment`, and `DocumentChunk`.
I understood that processing and tutoring permissions are independent, that the
retriever must exclude chunks without tutoring permission, and that unchanged
input produces stable identifiers. If the bytes change, the checksum changes,
the old approval no longer matches, and a new approved source version produces
new derived identifiers.

## Evidence

- Tests: `uv run pytest tests/digital_twin/test_local_ingestion.py`
- Experiment: `npm run verify:ingestion`
- Synthetic corpus: five approved TXT, Markdown, and generated PDF documents
- Covered failures: rejected, excluded, sensitive, processing-disabled,
  checksum/version mismatch, invalid UTF-8, empty, unsupported, MIME mismatch,
  and image-only PDF
- Pull request: #30, merged with passing CI
- Knowledge check: 8/10 on the initial MCQ set, followed by a correct mastery
  check explaining that changed bytes require a new checksum, approval, source
  version, and derived identifiers

## What failed or surprised me

Not much in the baseline surprised me. The state-of-the-art approach that
converts document pages to images and processes meaningful visual regions was
impressive, and it was my first time learning about that algorithm.

## What I learned

I can explain the ingestion sequence, why approval must match the exact source
version and checksum, why permissions are separate, and why unchanged inputs
must produce stable document, figure, and chunk identifiers.

## Next decision

Refactor the code as needed to make the complete flow work in the actual
project. We should also think about the complete deployment picture, potentially
running the system in one container and Dockerizing everything. This is an
architecture follow-up rather than part of ingestion issue #22. Before changing
the 1,200-character size or 160-character overlap, use retrieval results from
issue #23 to decide whether they need refinement.

## Discussion record

### Baseline algorithm

We described #22 as a permission-safe preprocessing baseline rather than a full
RAG or multimedia system. The implemented sequence is:

`SourceArtifact + ApprovalRecord -> CourseDocument -> DocumentSegment -> DocumentChunk`

Before reading source bytes, the parser checks the source identity, version,
professor approval, exclusion state, sensitivity state, processing permission,
extension, and MIME type. After reading, it verifies the approved SHA-256
checksum and rejects empty content. TXT is split by paragraphs, Markdown keeps
ATX headings and fenced code boundaries, and selectable-text PDFs retain sorted
text blocks, one-based pages, normalized coordinates, and embedded figure
provenance.

The deterministic chunker greedily groups complete structural segments up to
1,200 characters. Oversized segments are split on word boundaries, and up to
160 characters of complete trailing segments are reused as overlap. Document,
figure, and chunk identifiers are derived from versioned source identity,
locators, and content hashes so unchanged inputs reproduce unchanged IDs.

### State-of-the-art comparison

We agreed that this is not state-of-the-art multimedia processing. It does not
perform OCR, learned layout reconstruction, table or formula recognition,
diagram understanding, audio processing, or video processing. Current advanced
document systems render pages visually, detect meaningful regions and reading
order, then apply specialized vision-language recognition to high-resolution
crops. Visual retrieval systems may also index page-image patches directly.

The current baseline remains useful because its approval, permissions,
versioning, checksum, and provenance boundaries should remain in place even if
a Docling, MinerU, PaddleOCR-VL, or visual-retrieval adapter is evaluated later.
Advanced parsers should sit behind the same governance boundary and be compared
against the deterministic baseline using project-specific evidence.

### Knowledge check

The MCQ review covered data flow, independent permissions, checksums, PDF safety,
greedy chunking, whole-segment overlap, stable identifiers, source versioning,
multi-column PDF limitations, and future parser adapters. The initial result was
8/10. The missed concepts were stable derived IDs and the requirement to create
a new approved version when bytes change; both were answered correctly in the
follow-up mastery check.

### Diff review

Before merging, the complete diff was reviewed for correctness, privacy,
compatibility, test coverage, and documentation consistency. The review found
and fixed four issues:

- approval metadata is now checked before source bytes are read;
- the verification command now fails if provenance is not preserved;
- Markdown headings inside fenced code blocks are no longer misclassified;
- PDF coordinate normalization now accounts for non-zero page origins.

The final validation included 62 Python tests, 15 frontend tests, Ruff static
analysis, documentation validation, frontend lint and build, deterministic
five-document ingestion verification, and GitHub CI. PR #30 merged and issue
#22 moved to Done.

### Complete-system follow-up

The next implementation step is issue #23: lexical retrieval, visible evidence,
Recall@5, Mean Reciprocal Rank, and failed-query analysis. In parallel, the
architecture should be considered end to end rather than as isolated modules.
A possible deployment direction is a Dockerized system, potentially beginning
with one container for the prototype. That decision should account for the web
app, FastAPI service, model or provider boundaries, persistent storage, local
source and figure volumes, secrets, health checks, and whether later components
need separate scaling or isolation.
