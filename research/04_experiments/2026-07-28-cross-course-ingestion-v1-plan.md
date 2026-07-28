# Cross-course ingestion v1 plan

Date frozen: 2026-07-28

Status: prospective; no canonical-corpus measurements inspected before this
plan was recorded

## Decision question

Can the selected parser and heading/paragraph chunker process the active
four-course portfolio with stable provenance and page-precise evidence units,
or must chunking be refined before benchmark authoring?

## Prediction

All 32 manifest-enumerated PDFs will pass integrity and selectable-text
parsing. The existing document-wide chunker will preserve provenance and size
bounds, but it will sometimes combine text blocks from adjacent lecture-slide
pages. A page-bounded variant should eliminate that failure without changing
the parser or exceeding the same 1,200-character size bound.

## Shared data

- Corpus: `cross-course-portfolio-v2`
- Documents: 32 approved lecture PDFs across IT5002, CS5421, IT5100B, and
  IT5100E
- Source root: local canonical `Documents/academia_vault`
- Permissions: `research/03_data/academics-source-permission.md`
- Exclusions: assignments, answers, tutorials, projects, graded work, student
  data, credentials, secrets, and files outside the v2 manifest
- Repeats: two deterministic parses and chunking passes per document

Private text, extracted figures, and per-chunk content remain ignored. Durable
results contain only identifiers, counts, rates, hashes, and classified
failures.

## Candidates

### C0: document-wide heading/paragraph baseline

- `HeadingParagraphChunker`
- `max_chars = 1200`
- `overlap_chars = 160`
- grouping may cross PDF page boundaries

### C1: page-bounded heading/paragraph candidate

- the same parser, segment splitting, size, and overlap configuration
- apply the chunker independently to each PDF page
- preserve document-global stable chunk ordinals and identities
- never combine separate slide pages

## Metrics and hard gates

| Measure | Role | Gate |
| --- | --- | ---: |
| Manifest hash match | Integrity hard gate | 32 / 32 |
| Parse success | Parser hard gate | 32 / 32 |
| Stable document, figure, and chunk identities | Reproducibility hard gate | 32 / 32 |
| Complete source ID, version, locator, page, permission, and content hash | Provenance hard gate | 100% of chunks |
| Chunks within 1,200 characters | Size hard gate | 100% |
| Cross-page chunks | Evidence-locality hard gate | 0 for selected candidate |
| Empty chunks | Validity hard gate | 0 |
| Exact duplicate selected chunk IDs | Integrity hard gate | 0 |
| Pages with selectable-text segments | Coverage diagnostic | report by course; visually classify every sampled gap |
| Tiny chunks below 80 characters | Diagnostic | report rate by course |
| Normalized duplicate text | Boilerplate diagnostic | report exact count and rate |
| Extracted figures and pages containing figures | Multimodal diagnostic | report by course |
| Parse and chunk latency | Operational diagnostic | report median and p95 by document |

The candidate is selected only if every hard gate passes. Lower tiny-chunk or
duplicate-text rates do not override provenance, permission, integrity, or
page-locality failures.

## Visual inspection

Render and inspect at least two pages per course:

- one page with the highest extracted-figure count; and
- one deterministic content page from the middle of the sequence.

Classify whether selectable text represents the page adequately, whether
important meaning is carried only by diagrams or layout, and whether page-local
chunking is a defensible evidence unit. Visual inspection is qualitative
diagnostic evidence, not a substitute for benchmark retrieval metrics.

## Failure taxonomy

- source: manifest path, permission, or checksum failure;
- parsing: missing, garbled, or incorrectly ordered selectable text;
- layout: table, diagram, equation, or spatial relationship not represented by
  extracted text;
- chunking: cross-page grouping, poor split, tiny fragment, or duplicated
  boilerplate;
- provenance: missing or inconsistent source, version, page, locator,
  permission, or hash;
- operational: exception, timeout, excessive latency, or memory failure.

## Decision rule

- **Keep C0** only if it passes every hard gate.
- **Keep C1** if C0 fails page locality and C1 passes every hard gate.
- **Refine** if parsing succeeds but neither chunker passes.
- **Drop** a candidate with integrity, permission, or provenance failure.

This run can select the ingestion/chunking configuration used to author the
private benchmark. It cannot establish retrieval quality, answerability,
professor fidelity, usability, or learning effectiveness.
