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
- Pull request or artifact: add after the implementation PR is opened
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
