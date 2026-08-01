# Multimodal retrieval v1 private draft status

Date: 2026-08-01

Status: private assistant-authored draft; structurally valid; zero cases
researcher-verified; not sealed and not runnable

## Current allocation

The ignored private draft contains 26 rendered page assets and 40 cases across
nine courses.

| Slice | Cases |
| --- | ---: |
| Visual answerable | 24 |
| Text-sufficient control | 8 |
| No evidence | 4 |
| Adversarial integrity | 4 |
| **Total** | **40** |

The visual-answerable slice contains ten diagram, four table, four annotation,
four screenshot, one scanned-page, and one equation case. Four
modality groups therefore meet the prospective minimum of four cases each;
the smaller slices remain explicitly descriptive.

## Assistant visual QA

The first complete assistant visual review accepted 32 cases, marked seven for
revision, and rejected one ambiguous case. Six provisional positives leaked
their answers through selectable page text, the Pentium case used an incorrect
modality and shortened label, and the software-to-hardware mapping question
assumed an ambiguous intermediary.

The revised draft now requires genuinely visual color, position, direction, or
region binding for those cases. The IoT positive was replaced by an eligible
lab-note code screenshot whose selectable PDF text contains only its title.
A second complete assistant QA pass accepted all 40 draft cases and is retained
locally as `assistant_review_v2.json`. This is quality control only: it does not
count as researcher verification and does not authorize a benchmark run.

## Provenance and privacy

Every asset is bound to a source artifact ID, course ID, document SHA-256, page
number, rendered-image SHA-256, local-only permission, and normalized evidence
region. Source filenames, page text, queries, claims, renders, and review notes
remain under ignored `data/interim/` or `data/processed/` storage.

No external provider received or evaluated private content. The assistant
proposed and visually checked the wording locally; that does not count as
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
