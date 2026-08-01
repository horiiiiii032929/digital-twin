# Academics source permission

Decision date: 2026-07-27

Decision owner: project researcher and source holder

Status: approved for inventory and research evaluation; canonical source
location confirmed and cross-course portfolio v2 selected

Multimodal clarification date: 2026-07-31

External review clarification date: 2026-08-01

## Approved collection

All course materials contained in the user's `academics` collection may be:

- inventoried locally;
- parsed and normalized for this project;
- used to construct researcher-authored development, calibration, and sealed
  evaluation cases;
- used for retrieval, reranking, generation, and end-to-end research
  evaluation; and
- processed by a prospectively approved external embedding, reranking, or
  generation provider within the project's recorded cost and data boundary.

This decision replaces the earlier assumption that private IT5002 lecture
material was automatically prohibited from every external provider. It does not
select or approve a specific provider, model, retention policy, region, or
experiment. Each provider use still requires the prospective record defined in
the active scope.

The source holder removed the multimodal experiment's blanket prohibition on
external course-content transfer and authorized a governed cross-model QA run
over eligible study material. This authorization does not extend to any
mandatory exclusion below. Each external run must still name the provider,
account class, model, transferred fields or pixels, retention and training
state, region where known, call count, cost, and deletion or expiry procedure.

## Mandatory exclusions

Permission for the collection does not make every file eligible for tutoring or
external processing. Exclude:

- solutions and answer keys;
- completed assignments, exams, quizzes, and graded-work answers;
- student submissions, student records, feedback tied to an identity, or
  participant data;
- credentials, secrets, access tokens, private keys, and environment files; and
- files whose content is unrelated to course teaching material.

Assessment instructions, rubrics, and academic-integrity policies may be used
when they do not disclose answers or student data.

## Release boundary

Research use and provider processing do not publish a course Digital Twin.
Every student-facing release still requires:

- course membership and isolation;
- a professor-approved source/version set;
- professor-approved teaching behaviour and tutoring policy;
- evaluation-before-publication gates; and
- explicit professor publication, withdrawal, and rollback control.

## Access state

The canonical collection is available locally at
`/Users/hikaru/Documents/academia_vault`. Durable records use relative source
paths beginning with `academia_vault/` and never require that workstation path.
The similarly named `Downloads/academia_vault` directory is a partial copy and
must not be used for active corpus selection. The existing ignored IT5002
snapshot remains under `data/raw/course_materials/`.

Therefore:

- permission is resolved;
- all nine course folders across semesters one and two were inventoried;
- the active 32-PDF, four-course primary corpus is recorded in
  `research/05_evaluation/cross_course_portfolio_v2.manifest.json`;
- the earlier 17-PDF inventory is retained as a superseded partial-source
  snapshot; and
- source files remain outside Git.

## Multimodal clarification

The source holder confirmed that all eligible study materials inside the
canonical `Documents/academia_vault` collection may be used for the local
multimodal retrieval study in issue #60. This expands the candidate source
universe beyond the active 32-PDF text benchmark; it does not modify that
sealed benchmark or automatically make every file a student-facing source.

A first sanitized visible-file census at clarification time found 673 files
and `du` reported 329 MiB on disk, including:

| Format group | Observed files |
| --- | ---: |
| PDF | 123 |
| Markdown and plain text | 136 |
| Source code and SQL | 255 |
| Draw.io diagrams | 27 |
| CSV and notebooks | 44 |
| PNG and JPEG images | 17 |
| TeX | 10 |
| DOCX, Pages, and EPS | 7 |
| Other metadata, generated, archive, and extensionless files | 54 |
| **Total** | **673** |

A subsequent hash-bound filesystem inventory also traversed hidden and ignored
tool state. It found 2,636 entries and 336,913,605 logical bytes: 1,906 were
generated/tool-state exclusions, three had secret indicators and were excluded,
435 require content review, and 292 are clear course-scoped candidates. The
visible census and full traversal answer different questions and are both
retained; neither count is a tutoring denominator.

Counts are inventory evidence, not an ingestion denominator. The multimodal
benchmark will sample evidence-bearing study artifacts by course, format, and
observed modality. Generated files, caches, archives, duplicates, and unrelated
software artifacts are classified before sampling. The mandatory exclusions
above still apply to solutions, graded answers, student or participant data,
credentials, and secrets even when such files are physically inside the vault.

All visual rendering, OCR, layout extraction, descriptions, and embeddings for
this study remain local-only. This clarification does not activate the earlier
prospective external-provider permission.
