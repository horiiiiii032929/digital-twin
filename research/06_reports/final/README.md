# Submission: abstract and concise report

Author: Hikaru (Rawin) Horinouchi. Student ID: A0330350X.

Submit two PDFs:

- `reports/generated/final-report/abstract.pdf` — 1 page.
- `reports/generated/final-report/report-with-appendices.pdf` — 34 pages:
  main report and references pp. 1–25; curated appendices pp. 26–34.

The 326-page automatic trial archive is no longer part of the submission.
The curated appendices retain failed design mechanisms, publication/data diagrams,
software references, SDLC traceability, an evidence index, planner calculations,
saved teaching examples and the historical simulator correction. Repeated runtime
settings, approvals and plan inventories remain in repository records.

## Build

Run from the repository root with Tectonic and Python with PyMuPDF:

```sh
mkdir -p reports/generated/final-report/components
tectonic -X compile research/06_reports/final/abstract.tex --outdir reports/generated/final-report/components --keep-logs --keep-intermediates
tectonic -X compile research/06_reports/final/report.tex --outdir reports/generated/final-report/components --keep-logs --keep-intermediates
uv run python reports/build_submission_pdfs.py
```

The builder checks authorship, one-page abstract, AI disclosure and link targets.
`submission-manifest.json` records output hashes. `report-source.zip` includes
active LaTeX, figures, the builder and linked local evidence summaries, with a
source manifest. It excludes application secrets, raw data and bulky run outputs.

## Evidence and historical exports

`submission-evidence-index.csv/json` describes the current concise submission.
The old `design-trial-index.csv/json` page destinations apply only to the historical
full export, not this revised report. Original full PDFs and the old source ZIP
are preserved under `reports/generated/final-report/historical-full-submission-20260906/`.
Do not submit those files in place of the current outputs. `design-appendix.tex`
is a historical archive source, not an input to the current build.

See `archive-errata-20260906.md` for confirmed archival corrections and unresolved
upstream evidence; `review-resolution-20260906.json` maps the full reading review
to correction or exclusion. Removing an inconsistent number from the submission
does not resolve its original ledger. Historical review notes keep their original
scope and are not new integrity certifications.
