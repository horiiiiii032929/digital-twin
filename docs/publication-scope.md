# Proposed public GitHub publication

Destination: `horiiiiii032929/digital-twin` (public), ultimately `main` so the
submitted report's repository links resolve.

The proposed snapshot is commit `4556185db789799ab495124680f4c57fbf05540e`. Its comparison with the
remote main branch contains 768 changed files, approximately 65 MB on disk:

- Application, API, domain code, scripts, regression tests, CI and instructions.
- Submitted PDFs and their source package, retained unchanged with hashes.
- Research plans, readable result summaries and report-source evidence indices.
- 141 machine-readable evaluation record files, approximately 35 MB, including
  synthetic cases and recorded model outputs used in the comparisons.

Ignored raw course data, local environment files, model downloads and bulk run
directories are not in this payload. A secret-pattern scan found no matching
credentials in the proposed changes. That scan is not comprehensive human review
of every record and does not itself establish publication authorization.

Automatic approval review rejected the first public push because the large
research/evaluation payload's sensitivity and publication authorization were not
sufficiently established. No push succeeded. The exact file/size/hash inventory
is retained locally at
`reports/generated/post-submission-verification/publication-manifest.json`.

Confirm whether the public publication should include these evaluation records,
in addition to code and documents, before retrying this action. Test completion
and publication approval are separate conditions; this note is not a test pass.
