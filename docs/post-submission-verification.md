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

Verification is in progress; final command outcomes and the published revision
will be recorded before completion. The first standard run found stale audit
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
