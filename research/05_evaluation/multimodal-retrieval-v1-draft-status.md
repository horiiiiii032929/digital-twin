# Multimodal retrieval v1 private draft status

Date: 2026-08-01

Status: private researcher-reviewed draft; structurally valid; 40/40 cases
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

The recorded Claude second-review run received 26 eligible rendered pages under
the documented consumer-account boundary; no mandatory exclusions were
transferred. The assistant visual review and the final researcher review were
local. The final local export confirmed 40/40 cases, with 39 accepted as
authored and one revised and then approved after its wording was rewritten.

## Review record and next gate

The generated ignored checklist is
`data/processed/multimodal_retrieval_v1/researcher_review_v1.md`. A private
browser-based version at
`data/processed/multimodal_retrieval_v1/researcher_review_v1.html` shows each
render beside its query and claims, stores decisions locally, and exports a
JSON review without uploading content. Codex pre-adjudicated modality and
visual-dependency taxonomy, so those fields are displayed for context and are
not another decision the researcher must make. For every case, the researcher
was completed with:

1. source eligibility and absence of graded answers or personal data;
2. query clarity and required-claim correctness;
3. evidence-region adequacy; and
4. accept, reject, or revise disposition, with notes as needed.

The edited partition case was revalidated after its query was rewritten around
the S1/S2 partition invariant. The private draft now has 40 researcher-verified
cases, but the development/held-out split and access ledger are not frozen.
Author seven genuinely visual replacement cases, freeze the split and ledger,
and rerun structural checks before sealing; until then, V0-V3 must not run.

Rebuild and validate the private draft with:

```bash
npm run draft:multimodal-private-benchmark
```
