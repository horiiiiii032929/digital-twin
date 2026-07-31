# Multimodal source inventory v1 results

Date: 2026-07-31

Result ID: `multimodal-source-inventory-v1`

Decision: **Refine; keep 292 clear candidates, exclude generated and secret-
indicated artifacts, and require explicit review for 435 ambiguous sources**

## Scope and validity

This local-only source-governance run traversed the authorized canonical
academic vault without copying filenames or content into durable output. It
used prospective extension, course-scope, generated-state, secret-indicator,
and assessment-path rules. Filename rules do not grant final tutoring
eligibility; they create a conservative review queue.

The run used Git revision `8b56dca29b792ae74aca356820d09e22e9bdf600`
with a dirty tree containing the prospective inventory, sampling, and draft
tooling plus pre-existing user-owned report/plot changes. The private per-file
inventory remains under ignored `data/interim/`; its inventory SHA-256 is
`ac9b46c28856fc278a1254508ff90e5f8742c04d44e401c790e6a3e4691447eb`.

## Inventory result

| Classification | Files |
| --- | ---: |
| Clear course-scoped candidates | 292 |
| Review required | 435 |
| Generated/tool-state excluded | 1,906 |
| Secret-indicated excluded | 3 |
| **Total filesystem entries** | **2,636** |

Logical source size was 336,913,605 bytes. The full traversal includes hidden
and ignored tool state, while the earlier `rg --files` census found 673 visible
files. The difference is explained by generated environments, caches, and
repository internals; it is not an unexplained corpus change.

The source universe includes 123 PDFs, 27 Draw.io diagrams, 22 notebooks, 22
CSV files, 17 PNG/JPEG images, 10 TeX sources, and seven DOCX/Pages/EPS
artifacts. Code and text remain available to the text path; they are not forced
through image processing.

## PDF sampling checkpoint

The sampler inspected 2,317 pages from eligible PDFs and previously approved
manifest PDFs. It selected four high-visual-score pages from each of nine
courses, for 36 private rendered candidates and three contact sheets. No source
failed to open or render. One known PDF emitted recoverable MuPDF xref warnings;
the warnings did not stop text extraction or Poppler rendering.

Visual inspection retained 24 provisional positive pages covering diagrams,
tables, annotations, screenshots, one scanned reference, one photo/layout case,
and one equation case. Draw.io sources were not silently added because no
reliable renderer was available on the workstation.

## Privacy and operations

- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Durable filenames or source content: 0
- Private per-file inventory, renders, page text, authoring cases, and review
  sheets: ignored local storage only

## Decision and limitations

**Refine.** Use the 292 clear candidates as the first authoring pool, retain all
435 ambiguous sources for explicit eligibility review, and keep the 1,909 hard
exclusions out of sampling. This is a source-governance result, not evidence
that any retrieval candidate works.

Path heuristics can over-route legitimate lecture material in folders named
`final`, `project`, or `tutorial`; the active manifest override preserves known
approved PDFs, and the remainder requires human content review. The visual page
score is a sampling aid, not a modality classifier or relevance metric.

Reproduce the sanitized inventory and private sample with:

```bash
npm run inventory:multimodal-sources
npm run sample:multimodal-pdf-pages
```
