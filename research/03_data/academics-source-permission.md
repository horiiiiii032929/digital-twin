# Academics source permission

Decision date: 2026-07-27

Decision owner: project researcher and source holder

Status: approved for inventory and research evaluation; canonical source
location confirmed and cross-course portfolio v2 selected

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
