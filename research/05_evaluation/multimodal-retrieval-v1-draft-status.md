# Multimodal retrieval v1 private draft status

Date: 2026-07-31

Status: private assistant-authored draft; structurally valid; zero cases
researcher-verified; not sealed and not runnable

## Current allocation

The ignored private draft contains 25 rendered page assets and 40 cases across
nine courses.

| Slice | Cases |
| --- | ---: |
| Visual answerable | 24 |
| Text-sufficient control | 8 |
| No evidence | 4 |
| Adversarial integrity | 4 |
| **Total** | **40** |

The visual-answerable slice contains nine diagram, four table, four annotation,
four screenshot, one scanned-page, one photo, and one equation case. Four
modality groups therefore meet the prospective minimum of four cases each;
the smaller slices remain explicitly descriptive.

## Provenance and privacy

Every asset is bound to a source artifact ID, course ID, document SHA-256, page
number, rendered-image SHA-256, local-only permission, and normalized evidence
region. Source filenames, page text, queries, claims, renders, and review notes
remain under ignored `data/interim/` or `data/processed/` storage.

No model or external provider authored or evaluated the private draft. The
assistant proposed the wording after visual inspection; that does not count as
researcher verification.

## Required review

The generated ignored checklist is
`data/processed/multimodal_retrieval_v1/researcher_review_v1.md`. A private
browser-based version at
`data/processed/multimodal_retrieval_v1/researcher_review_v1.html` shows each
render beside its query and claims, stores decisions locally, and exports a
JSON review without uploading content. For every case, the researcher must
confirm:

1. source eligibility and absence of graded answers or personal data;
2. query clarity and required-claim correctness;
3. evidence-region adequacy;
4. visual-dependency and modality labels; and
5. accept or reject, with notes.

Rejected or edited cases receive new review state and are revalidated. The
development/held-out split and access ledger are created only after every case
is verified and the allocation still passes. Until then, V0-V3 must not run.

Rebuild and validate the private draft with:

```bash
npm run draft:multimodal-private-benchmark
```
