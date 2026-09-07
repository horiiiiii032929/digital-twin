# Post-submission repository verification

The report was submitted on 6 September 2026. Its immutable copies and hashes
are in [the submission snapshot](../reports/submitted/2026-09-06/README.md).
Publication work preserves those PDFs and does not rerun or rewrite historical
experimental results.

## Reproduce code checks

Use the versions in `.python-version` and `.node-version`, then run from a fresh
checkout:

```sh
uv sync --locked --dev
npm ci
npm run setup:evaluation-sources
npm run check
```

`check` uses committed synthetic fixtures, prepared publicly licensed source
snapshots, operational regressions and instrument validation. Source preparation
fetches exact Git revisions; the checks do not need external model access.
Tests may start loopback HTTP/HTTPS servers. No external model key is
needed for this suite. Historical generated-artifact tests are separate because
they require ignored, local-only run products; use the existing
`verify:historical-generated-artifacts` command only when those products exist.
This distinction is not permission to rerun sealed or provider-backed evaluations.

## Publication verification

The complete Python invocation passed 2,600 tests in 1,486.20 seconds (24m46s),
with zero failures or errors. Three new link cases were added during that run
and passed in a separate five-test validator invocation. The standard `npm run
check` pipeline subsequently completed: its Python selection passed 2,577 tests
in 1,340.68 seconds, followed by 71 frontend tests, lint and the production build.
The repository owner approved publication of the evaluation-record payload on
7 September 2026; remote CI remains to be checked after push. The first standard run found stale audit
hashes for the submitted goal-scope correction and missing report/tool entries.
The relevant source boundaries and evidence were reviewed, then audit metadata
was refreshed. This changes verification bookkeeping, not tutoring behaviour.

Frontend tests, lint and the production build passed. The build reports an
existing large-chunk warning, not a compilation failure. No speculative runtime
refactor is justified solely by that warning.

Raw command logs are local under `reports/generated/post-submission-verification/`.
The public record reports outcomes without exposing credentials or private inputs.

## Post-submission tooling correction

A clean clone exposed one result link into ignored `reports/generated/` content.
The historical fiction-only assistant disclosure review is now retained under
`research/05_evaluation/`, with its AI-review role explicit. The link validator
now rejects existing ignored/outside-repository targets instead of accepting
whatever happens to exist on the author's machine. All five validator tests pass.
No tutoring runtime behavior or submitted PDF changed.

The GitHub job retains every check and uses a 45-minute wall-time ceiling
instead of 15 minutes. The expanded synthetic integration suite is CPU-active
and takes substantially longer than the frontend checks; this changes only
the execution allowance, not pass criteria.

## Fresh checkout results

On a separate checkout of `32dc808`, `uv sync --locked --dev` and `npm ci`
completed. All 1,989 local Markdown links, 1,248 execution-file inventory entries
and 201 guarded entrypoints validated. The focused product/evaluation suite
passed 82 Python tests; all 71 frontend tests, lint and production build passed.
The only frontend build warning concerns the existing 527.86 kB JavaScript
chunk. Python and JavaScript dependency audits found zero vulnerabilities.

The submitted snapshot hashes and all twelve principal report evidence paths
were checked against committed files. This verifies code/doc availability; it
does not claim that all historical external-model experiments were repeated.

## Remote CI source-preparation correction

The first remote run, [34087150738](https://github.com/horiiiiii032929/digital-twin/actions/runs/34087150738),
failed because a source-derived dataset build required ignored public course
snapshots. The earlier focused clean-checkout test did not exercise that build;
its success was insufficient evidence for the complete clean-checkout suite.

The decision was to preserve the existing build checks and prepare their exact
public input revisions explicitly, instead of skipping source-dependent tests
or committing full upstream repositories. The prediction is that pinned source
preparation removes the machine-local prerequisite without changing evaluation
inputs or scores. Four network-free Git-fixture tests cover initial fetch,
offline reuse, dirty/revision-drift rejection, and failed-fetch cleanup. The
standard CI job now prepares these sources before the portable checks. A fifth
pinned public source, ThinkOS, is also required by successor-build regressions.
Remote verification of this correction is pending.

The second remote run, [34087950670](https://github.com/horiiiiii032929/digital-twin/actions/runs/34087950670),
passed source preparation but exposed another dependency on ignored generated
10,000-case inputs inside the old development-v2 validation command. Its two
source-bound subcommands and three source-bound tests were also separated into
explicit historical-artifact verification. The remaining source-derived checks
continue to run with the pinned public inputs.

Historical visual raster/ledger checks and individual tests requiring ignored
10,000-case run products are explicitly separated from the portable suite with
the `historical_artifact` marker. They remain runnable with `npm run
test:historical-artifacts`; commands requiring those products remain under
`verify:historical-generated-artifacts`. Absence of those inputs is not reported
as a successful historical revalidation.

The broader clean-checkout probe also found that the shared autonomy test
fixture mixed a fixed August 31 event time with the real wall clock. After
September 7 its goal expiry was no longer in the future. Passing the existing
`VirtualUtcClock` into that fixture fixed the test setup; all 67 related
autonomy/worker/freeze checks passed. Production expiry validation is unchanged.
