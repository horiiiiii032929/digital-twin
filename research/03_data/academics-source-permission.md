# Academics source permission

Decision date: 2026-07-27

Decision owner: project researcher and source holder

Status: approved for inventory and research evaluation; canonical source
location confirmed and cross-course portfolio v2 selected

Multimodal clarification date: 2026-07-31

External review clarification date: 2026-08-01

Professor-fidelity provider clarification date: 2026-08-10

Course-tutor judge clarification date: 2026-08-14

## Course-tutor authoring-review DeepSeek authorization

On 2026-08-14, the source holder explicitly authorized the official DeepSeek
Open Platform as a judge for the single
`course-tutor-hybrid-authoring-review-v3` run. This amendment supersedes the
earlier judge exclusion only for this named authoring review. It authorizes
`deepseek-v4-pro`, documented by DeepSeek as `DeepSeek-V4-Pro-0813`, at
`https://api.deepseek.com` in thinking mode with effort `high`.

The permitted payload is limited to synthetic student questions and states,
authored expected behavior, atomic claims, exact approved IT5002 evidence
passages and metadata, and eight deterministic approved lexical neighbors for
each no-evidence check. It excludes real student or participant data,
solutions, graded answers, credentials, environment values, tutor outputs,
hidden condition mappings, other reviewers' verdicts, and human decisions.

The authorization permits one public synthetic preflight and 152 private case
judgments, with no retries and a cumulative USD 2 hard stop. Requests use a
non-personal `user_id`; records must capture call count, model, system
fingerprint, token use, latency, and approximate cost without exposing the API
key or private text in committed artifacts.

DeepSeek's default context caching and the absence of a project-specific
no-training guarantee remain explicit limitations. This amendment does not
authorize general DeepSeek judging, professor approval, public deployment,
student-facing use, or any transfer outside the named v3 fields and limits.

### V4 authoring-review continuation

The same 2026-08-14 source-holder direction authorizes the prospective
`course-tutor-hybrid-authoring-review-v4` replacement after v3 stopped at its
human-workload gate. V4 keeps the identical provider, model, private fields,
exclusions, non-personal identity, and USD 2 ceiling. It changes transport to
the official OpenAI-compatible client and permits ten public synthetic stress
probes plus at most two attempts per private case, for 314 external requests
maximum. A second private attempt is permitted only for empty or malformed
structured output; valid approve/revise decisions are never retried. V3
judgments are not sent to the provider or reused in v4.

### V5 transient-failure continuation

The same source-holder direction authorizes
`course-tutor-hybrid-authoring-review-v5` after v4 exposed a private-request
timeout classification bug. V5 keeps every v4 data field, exclusion, provider,
model, non-personal identity, 314-request maximum, and USD 2 ceiling. Its one
bounded second attempt may follow empty/malformed structured output or a
transient API timeout/connection failure. Authentication, configuration,
model, and fingerprint failures remain hard stops. Valid approve/revise
decisions are never retried, and no v4 private judgment is reused or sent.

### V6 alias-and-output continuation

The same source-holder direction authorizes
`course-tutor-hybrid-authoring-review-v6` after v5 exposed a prompt alias
ambiguity and a 4,096-token thinking-output ceiling. V6 keeps every v5 private
field, exclusion, provider, `deepseek-v4-pro` model, non-personal identity,
314-request maximum, and USD 2 ceiling. It may identify `dev` and `test` as the
repository's canonical family-token aliases for `development` and `heldout`,
respectively, and may increase the per-response output allowance to 8,192
tokens. The same single bounded retry classes apply. Finish reason and
reasoning-token usage may be recorded when returned. Valid decisions are never
retried, and no judgment from v1 through v5 is reused or sent.

## Professor-fidelity DeepSeek authorization

The source holder explicitly authorizes the issue #24 single-turn C0-C3
research evaluation to send eligible IT5002 lecture passages, synthetic
student questions and states, the frozen tutoring policy, and derived tutor
outputs to the official DeepSeek Open Platform endpoint at
`https://api.deepseek.com` using `deepseek-v4-flash` in non-thinking mode.
The authorization is limited to the qualified prompt and model binding recorded
in `student-tutor-v1`, the cumulative USD 10 research cap, and the mandatory
exclusions below. It does not authorize DeepSeek as a judge, simulator, public
deployment, or student-facing service.

DeepSeek's official API documentation states that disk context caching is
enabled by default and that unused cache entries are normally cleared within
hours to days. The public Open Platform terms assign input responsibility to
the developer and do not provide a project-specific no-training guarantee.
The evaluation therefore treats provider retention/training location as an
explicit limitation, sends only source-holder-authorized teaching material,
uses a non-personal `user_id`, and sends no participant or student data.

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

Visual rendering, OCR, layout extraction, descriptions, and embeddings for the
retrieval study remain local by default. The governed Claude second-review run
is the recorded exception: it transferred only eligible rendered pages and
blinded case fields under the external review clarification above. Any later
external processing requires its own prospective provider record.
