# Repository cleanup and reference preservation

The 7 September 2026 cleanup separates the repository's entry points from its
historical implementation narrative. Application behaviour, selected component
profiles, experimental results and submitted PDFs are unchanged.

## Changes and retained history

- The root README now provides setup, navigation and verification commands.
  Its existing section headings remain available for fragment links. Earlier
  staging and implementation claims are preserved in the
  [README history](archive/readme-implementation-history-20260907.md).
- The original design QA record moved to
  [the issue 80 report](../reports/issue-80-design-qa.md); the original
  [root path](../design-qa.md) remains as a compatibility entry.
- Empty notebook and bibliography scaffolds were removed. Actual literature
  stays in [research literature](../research/01_literature/README.md), and the
  report bibliography stays with its LaTeX source.
- No nontrivial byte-identical tracked duplicates were found. Evaluation
  retries, unsuccessful designs, result records and versioned scripts remain
  at their existing paths because they provide distinct historical evidence.
- Source datasets, provider ledgers, reports, browser evidence, environment
  files and installed dependencies are retained locally. Only disposable
  Python/lint caches and Finder metadata are eligible for local removal.

## Link protection

`npm run check:report-links` reads the two submitted PDFs, checks internal PDF
destinations, verifies the submission file hashes, and resolves their 14 cited
repository files against the tracked checkout. It also checks the 12-study
evidence index. [The baseline](submitted-report-links.json) records cited file
hashes at commit `d25e2727336c48cced3c84ce680fc25c7554e91c`.

Together with `npm run check:docs`, this check is part of `npm run check`.
It rejects removed, ignored or changed cited files. It does not claim to check
the availability of external publisher or DOI websites. The submitted files
and their original evidence paths must remain stable; corrections should be
recorded separately and linked explicitly.

The full pre-cleanup README remains in
[Git history](https://github.com/horiiiiii032929/digital-twin/blob/d25e2727336c48cced3c84ce680fc25c7554e91c/README.md).
Historical experiment hashes continue to refer to their recorded revisions,
not to a newly rewritten history.

## Cleanup verification

Removed 30 disposable cache directories or Finder metadata files from the
working checkout. Dependency environments, datasets and generated evidence were
excluded from traversal; later test runs may recreate caches.

Validation on this cleanup checkout:

- `npm run check:docs`: 2,013 local Markdown links passed.
- `npm run check:report-links`: 3 submission artifacts, 14 cited files and
  12 indexed studies passed.
- Focused pytest run: 37 passed across submitted-link, Markdown-link, report
  evidence inventory, repository configuration, correctness inventory and
  execution-freeze tests.
- Correctness inventory: all 1,252 entries current and audited.
- Execution freeze: all 201 protected entry points retained their guards;
  no model calls or held-out data access.

These are maintenance checks, not new pedagogical or model-quality evaluations.
The complete CI suite runs separately for the pull request.
