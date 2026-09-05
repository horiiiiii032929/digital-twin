# Local R1 correctness-fix qualification 011

## Run identity

- Status and decision: **completed / Keep** for corrected local operations.
- Date: 2026-09-05; executed by Codex for the repository owner.
- Source revision: `d9ec1a8eeb405fb0843d7cbc480c9636605cbde4`, clean at build.
- Predecessor: [qualification 010](local-r1-governed-v2-1-release-qualification-010-results.md).
- Prospective [plan](../04_experiments/2026-09-05-local-r1-governed-v2-1-release-qualification-011-plan.md)
  and [machine record](records/local-r1-governed-v2-1-release-qualification-011.json).
- Runtime: Docker 28.5.1, Compose 2.40.0-desktop.1, Linux arm64,
  container Python 3.12.12 on the development Mac.
- Raw artifacts: ignored `reports/generated/local-r1-q011/`; browser evidence:
  ignored `output/playwright/local-r1-q011/`. The machine record retains their
  hashes and all 43 sanitized individual acceptance outcomes.

## Decision context

The candidate fixes commit-time authorization and proactive-delivery races,
invalid outreach replies, long clarification labels, and stale course-switch
reply state. Historical qualification 010 is the operational control. The
prediction was that the corrected source would retain all 43 operations checks,
pass the focused container regressions, and produce no application or checkpoint
errors. All those gates passed; no additional runtime fix was needed in this run.

## Data and sample size

The existing versioned HTTPS verifier generated synthetic accounts, a course,
and a PDF. Its SHA-256 is recorded as the dataset version. This is a regression
checklist, with one execution per stage, not a held-out quality estimate. The
43 assertions span live workflow (25), restart (6), clean restore (6), T0 rollback
(3), and governed restoration (3). An additional 51 tests ran inside the built
API image. No real-student data, private corpus, consumed factual dataset, or
provider-backed evaluation was used. Population confidence intervals do not
apply to this finite operational checklist.

## Exact configuration and reproduction

The unchanged final profile is `student-tutor-r1-local-final` at
`v2.1-final-001-bm25-text-ocr`: BM25, dominance-scoped evidence gate, deterministic
generation, text/OCR fallback, governed V2.1, and the Luna policy-value planner
selection bound by the final release record. No component profile was changed.

Follow the [local runbook](../../docs/local-r1-runbook.md) using isolated project
`digital-twin-r1-q011`, port 8454, and image tag `r1-qualification-011`.
Use `digital-twin-r1-q011-restore` on 8455 for a fresh-volume restore. The private
`.env.local-r1-q011` uses the qualified example's selectors, new synthetic-account
secrets, and an inert provider key. It contains no billable provider credential.
The HTTPS verifier explicitly trusts each project's internal CA; the browser
uses a local context certificate exception without changing OS trust.

The API image is
`sha256:0477fc91610537bb2bfbf8a32e196fecd6233fcb1eac3632f5b46862291c8787`;
the web image is
`sha256:d1f2b6a005822673012bb37f0654e223074dfbb7e6353b5f92d5c34a2c514771`.
Image metadata, selectors, profile/configuration hashes, and the exact focused
container test command are preserved in the machine record. Test tooling was
installed only in a disposable container, leaving the release image unchanged.

## Aggregate and slice results

| Check | Passed / total | Gate |
| --- | ---: | --- |
| Live internal-CA HTTPS journey | 25/25 | All pass |
| Restart persistence | 6/6 | All pass |
| Clean backup restore | 6/6 | All pass |
| T0 rollback | 3/3 | All pass |
| Governed V2.1 restoration | 3/3 | All pass |
| Operational total | **43/43** | All pass |
| Built-image regression tests | **51/51** | All pass |
| Application/checkpoint error hits in four stage logs | **0** | Zero |
| Desktop / exact 390x844 login render | Passed / passed | No critical defect |
| Accessible login controls / keyboard order | 3/3; Email → Password → Sign in | All pass |
| Horizontal overflow at both sizes | 0 | Zero |
| Live API p95 | 8.857 ms | <=750 ms |

The main repository gate previously passed 1,952 Python and 51 frontend tests,
validators, lint, and production build for these fixes. There were no subsequent
runtime edits. Container regressions exercise the actual built code, including
access changes during generation, delivery preference/cap changes, and invalid
request and clarification boundaries.

## Operational measurements

The live journey took 6,568.656 ms; ingestion queue-to-completion was
1,286.195 ms. The backup and fresh restore verified schema v17 and seven data
files. Image sizes reported by Docker were 253,945,109 bytes for API and
21,941,788 bytes for web. A point memory sample was 241.7 MiB API, 29.69 MiB web,
86.48 MiB ingestion worker, and 238.8 MiB outreach worker; these are not peaks.

Final API and restore metrics showed zero planner calls, tokens, and reported
cost. No billable credential was available, and retained logs contained no
provider endpoint or failure entries. Counters reset with processes, so they do
not independently reconstruct pre-restart usage. This result qualifies only
deterministic fast paths, not live provider connectivity or answer quality.
Whole build/startup elapsed time and mean API latency were not separately
instrumented; build logs, image timestamps, live duration, and p95 are retained.

## Failures and surprises

The existing private environment selected an older candidate profile. This was
identified before execution; the isolated environment used the committed final
selectors. No failed acceptance attempt resulted.

The browser initially opened during the planned restart and displayed a
session-request HTTP 502. Reload after readiness recovered to the normal login;
the remaining HTTP 401 was the expected unauthenticated session response.
These events are preserved in the browser log. The run makes no zero-downtime
claim. The container tests emitted Starlette's `httpx` deprecation warning;
all 51 passed. No production code change was needed during qualification.

## Validity, decision, and limitations

The run is valid for the predefined operational checklist: all hard gates pass,
the fresh restore used a separate volume, and no model/data tuning occurred.
**Keep** the corrected local research release. Retain qualification 010 and T0
as rollback. Both temporary projects were stopped after testing; their volumes,
images, private test configuration, and backup remain available. The original
qualification-010 running project was left untouched. No hosted deployment or
remote push was performed.

The factual result remains 63.25% fully grounded and below its academic gate.
Visual, professor-fidelity, real-student usability, learning improvement, and
durable hosted-production claims remain unsupported by this qualification.

## Learning note

A preflight access check becomes stale while generation is running. Rechecking
inside the same database write transaction protects the actual commit. Unit
regressions reproduce this race; container startup and restore checks separately
establish that the correction works with the packaged runtime and durable state.
