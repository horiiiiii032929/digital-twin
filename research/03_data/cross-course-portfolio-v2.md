# Cross-course portfolio v2

Decision date: 2026-07-27

Status: active inventory boundary; benchmark questions and sealed split are not
yet frozen

Machine-readable inventory:
[`cross_course_portfolio_v2.manifest.json`](../05_evaluation/cross_course_portfolio_v2.manifest.json)

## Correction

Portfolio v1 inspected `Downloads/academia_vault`, which was a partial copy. The
source holder subsequently confirmed `Documents/academia_vault` as the exact
canonical collection. V1 remains recorded for traceability but is superseded
for benchmark design and all future portfolio claims.

The canonical vault contains nine courses across two semesters. Candidate
lecture sequences were measured using only course lecture or slide PDFs, with
assignments, tutorials, exams, solutions, projects, and student work excluded.

| Course | Candidate PDFs | Pages | Extracted characters | Selection |
| --- | ---: | ---: | ---: | --- |
| IT5001 | 2 | 116 | 17,271 | Defer: only lectures 1 and 3 are present |
| IT5002 | 13 | 508 | 169,996 | Keep: contiguous lectures 1–13 and existing anchor |
| IT5004 | 2 | 109 | 38,696 | Defer: only lectures 4 and 5 are present |
| IT5008 | 5 | 278 | 161,594 | Defer: non-contiguous lectures 1–3, 7, and 8 |
| CS5421 | 8 | 429 | 275,704 | Keep: contiguous lectures 1–8 |
| IT5003 | 3 | 40 | 85,106 | Defer: only weeks 1, 4, and 5 are present |
| IT5007 | 2 | 70 | 9,332 | Defer: only weeks 1 and 3 contain lecture PDFs |
| IT5100B | 5 | 169 | 56,833 | Keep: contiguous lectures 1–5 |
| IT5100E | 6 | 212 | 103,629 | Keep: contiguous lectures 1–6 |

“Defer” does not mean the product cannot ingest the course. It means that the
course does not enter the first decision-bearing research benchmark because
the local official lecture sequence is visibly incomplete.

## Active portfolio

| Course | Role in study | Primary retrieval challenges |
| --- | --- | --- |
| IT5002 Computer Systems and Applications | Systems anchor | diagrams, MIPS terminology, caches, operating systems, multi-evidence questions |
| CS5421 Database Tuning | Advanced database generalization | SQL, query plans, tuning, dense technical slides, annotated material |
| IT5100B Stream Processing | Distributed-systems generalization | streams, delayed events, reactive programming, Kafka, temporal explanations |
| IT5100E Security Best Practices | Security and policy generalization | cryptography, authentication, injection, LLM security, security boundaries |

The selection favors evidence completeness and technical heterogeneity. It also
retains deliberately difficult shared vocabulary: database/stream systems and
stream/security courses share platform, application, data, and course-template
language. This supports realistic course-isolation and cross-course-confusion
tests.

## Primary corpus

Use only the 32 PDFs enumerated and hashed in the v2 manifest:

| Course | Lecture PDFs | Pages | Extracted characters | Bytes |
| --- | ---: | ---: | ---: | ---: |
| IT5002 | 13 | 508 | 169,996 | 15,738,973 |
| CS5421 | 8 | 429 | 275,704 | 61,274,646 |
| IT5100B | 5 | 169 | 56,833 | 2,357,251 |
| IT5100E | 6 | 212 | 103,629 | 31,736,230 |
| **Total** | **32** | **1,318** | **606,162** | **111,107,100** |

All selected PDFs have selectable text and no two selected files have the same
SHA-256 hash. The PDFs remain outside Git.

Some official slides are stored under directories named `midterm`, `final`, or
`note`. They are included only when their filenames form the numbered lecture
sequence and their contents are teaching slides. Practice questions,
tutorials, assessment instructions, answers, and submissions remain excluded.

## Overlap and deduplication policy

Raw bag-of-words cosine similarity over each selected course's aggregated PDF
text ranges from 0.355 to 0.730:

| Pair | Raw cosine |
| --- | ---: |
| IT5002–CS5421 | 0.426 |
| IT5002–IT5100B | 0.510 |
| IT5002–IT5100E | 0.577 |
| CS5421–IT5100B | 0.355 |
| CS5421–IT5100E | 0.467 |
| IT5100B–IT5100E | 0.730 |

These are descriptive inventory diagnostics, not retrieval-quality metrics.
The high IT5100B–IT5100E value includes shared institutional and course-slide
boilerplate, so exact-file deduplication alone is insufficient. Ingestion must
detect or suppress repeated administrative/template chunks while retaining
course identity. Cross-course evaluation must include misleading boilerplate
and shared terminology.

Therefore:

- only manifest-enumerated lecture PDFs are primary indexed evidence;
- researcher notes may support benchmark authoring but never count as gold
  evidence;
- course identity and source identity must remain attached to every chunk;
- repeated boilerplate must be classified during ingestion and tested as a
  ranking failure mode;
- assignments, solutions, tutorial answers, projects, submissions, labs,
  midterms, finals, student data, credentials, and secrets are excluded; and
- a source may enter only through a versioned successor manifest.

## Evaluation allocation

Use a balanced approximately 100-case design rather than allocating in
proportion to pages:

| Slice | Target cases |
| --- | ---: |
| IT5002 answerable | 15 |
| CS5421 answerable | 15 |
| IT5100B answerable | 15 |
| IT5100E answerable | 15 |
| No-evidence | 15 |
| Cross-course confusion and shared-boilerplate | 15 |
| Adversarial, permission, or integrity boundary | 10 |
| **Total** | **100** |

At least 20 cases receive independent second review. Per-course metrics are
mandatory so larger courses cannot hide failures in smaller courses.

## Claim boundary

This inventory establishes local availability, permission, a versioned corpus,
text extractability, exact-file deduplication, and a defensible selection
boundary. It does not establish benchmark validity, retrieval quality,
provider selection, professor fidelity, usability, or learning effectiveness.
Those require the prospective experiments tracked in issues #49, #50, #7, #24,
and #25.
