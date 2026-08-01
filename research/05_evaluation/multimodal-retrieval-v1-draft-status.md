# Multimodal retrieval v1 private draft status

Date: 2026-08-01

Status: private researcher-review draft; structurally valid; 33/40 unchanged
cases researcher-verified; seven visual replacements pending; not sealed or runnable

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

The later cross-model review identified seven cases whose answers remained
recoverable from linear page text. On 2026-08-01, those questions were replaced
with checks that depend on handwritten labels, filled-versus-hollow ER nodes,
receipt-image OCR, vehicle icons, chevron emphasis, color highlighting, or a
hand-drawn oval. Structural validation passes with the original 24-case visual
slice and the required four modality groups. These seven changed cases require
fresh researcher confirmation; reviews for the other 33 cases were retained
only after an exact evidence-bearing field comparison.

## Provenance and privacy

Every asset is bound to a source artifact ID, course ID, document SHA-256, page
number, rendered-image SHA-256, local-only permission, and normalized evidence
region. Source filenames, page text, queries, claims, renders, and review notes
remain under ignored `data/interim/` or `data/processed/` storage.

The recorded Claude second-review run received 26 eligible rendered pages under
the documented consumer-account boundary; no mandatory exclusions were
transferred. The assistant visual review and researcher review were local. The
previous local export confirmed 40/40 cases, with 39 accepted as authored and
one revised and then approved. Replacing seven questions invalidated only those
seven confirmations; 33 unchanged confirmations remain applicable.

## Review record and next gate

The generated ignored checklist is
`data/processed/multimodal_retrieval_v1/researcher_review_v1.md`. A private
browser-based version at
`data/processed/multimodal_retrieval_v1/researcher_review_v1.html` shows each
render beside its query and claims, stores decisions locally, and exports a
JSON review without uploading content. It hides the 33 retained cases by
default and presents the seven replacements as purple cards. Codex
pre-adjudicated the unchanged taxonomy; the seven replacement cards require a
fresh taxonomy confirmation because their visual dependency changed. Review
checks cover:

1. source eligibility and absence of graded answers or personal data;
2. query clarity and required-claim correctness;
3. evidence-region adequacy; and
4. accept, reject, or revise disposition, with notes as needed.

The edited partition case remains verified after its S1/S2 invariant rewrite.
The next gate is researcher confirmation of the seven purple replacement cards.
After all 40 cases are verified, freeze the development/held-out split and
access ledger, rerun structural checks, and seal. Until then, V0-V3 must not run.

Rebuild and validate the private draft with:

```bash
npm run draft:multimodal-private-benchmark
```
