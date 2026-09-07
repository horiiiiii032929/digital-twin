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
npm run check
```

`check` uses committed synthetic fixtures, operational regressions and instrument
validation. Tests may start loopback HTTP/HTTPS servers. No external model key is
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
Publication remains blocked pending explicit scope approval for the large
evaluation-record payload. The first standard run found stale audit
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
