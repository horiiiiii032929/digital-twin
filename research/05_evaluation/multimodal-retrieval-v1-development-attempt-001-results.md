# Multimodal retrieval v1 development attempt 001

Date: 2026-08-01

Run ID: `multimodal-retrieval-v1-development-attempt-001`

Decision: **Refine and go deeper; run the predeclared V3 visual-embedding candidate on the
failed development slices and fixed controls. Do not open held-out or select a
profile yet.**

## Decision context

This development-only run compared the selectable-text V0 control with local
Apple Vision OCR (V1) and V1 plus layout records and local `gemma3:4b`
descriptions (V2). The sealed 16-case development partition contained ten
visual-answerable, three text-control, one no-evidence, and two integrity cases.
The 24-case held-out partition remained unopened and its access ledger remained
pristine.

The private representations were bound to seal
`multimodal-retrieval-v1-seal`, development SHA-256
`bf4c6eee489bf2b8ea985e49f8430df1e87eaa49cf89ca7690270d5f3b9c905f`, and
representation SHA-256
`e5e29e4538d294c360e05bcb15d2936b19af805d567dd63c32652f288e4a1137`.
The run used code revision `38736159e9f37be7f0720e95b31af9b941f29a01`
with intentional uncommitted experiment implementation changes.

## Aggregate results

| Candidate | Visual complete evidence @3 | Atomic recall @5 | Region nDCG @10 | Text control @3 | No evidence | Integrity | Warm p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V0 selectable text | 9/10 (90%) | 90% | 0.315 | 2/3 (66.7%) | 1/1 | 2/2 | 0.132 ms |
| V1 Apple Vision OCR | 8/10 (80%) | 90% | 0.306 | 2/3 (66.7%) | 1/1 | 2/2 | 0.134 ms |
| V2 layout + local description | 8/10 (80%) | 90% | 0.496 | 3/3 (100%) | 1/1 | 2/2 | 0.177 ms |

V2 produced the best region ranking and removed the text-control retrieval miss,
but it did not improve complete-evidence success over V0. It therefore failed
the required absolute-plus-relative quality gate: at least 80% and at least 15
percentage points above V0. V1 failed the same relative gate. Safety-boundary
counts passed for every candidate, and all retrieval timings were far below the
two-second ceiling in this workstation development run.

Offline preprocessing covered 12 assets. Apple Vision OCR took 5.62 seconds
total (0.468 seconds per asset); local `gemma3:4b` description generation took
128.92 seconds total (10.743 seconds per asset). There were zero external or
paid-provider calls. The ignored representation artifact was 552 KiB. These
measurements do not establish concurrent commodity-server capacity; the
preprocessing models are explicitly excluded from the deployed request path.

## Failures

- `mmr1-it5008-email-02` remained the common miss: the correct page ranked
  first, but the retrieved table rows did not overlap the narrow gold region and
  the evidence-action heuristic abstained. Classify as region/table binding and
  query-evidence failure.
- `mmr1-it5002-mips-02` regressed in V1/V2 because line-level OCR results split
  the relevant scanned-page region; top-three region IoU was 0.094 for V1 and
  0.090 for V2, just below the 0.10 success threshold. Classify as layout/region
  grouping failure.
- V2 retrieved the missing packages text control at page rank one, but its
  conservative lexical action heuristic still abstained. This does not change
  the recorded page-success metric; classify it as a query/policy diagnostic.
- V0's whole-page boxes can receive non-zero IoU for visual regions. The
  separately reported region nDCG exposes this weak localization, so the high V0
  complete-evidence count must not be interpreted as precise visual grounding.

## Hard gates and decision

| Gate | V0 | V1 | V2 |
| --- | --- | --- | --- |
| Development complete; held-out unopened | Pass | Pass | Pass |
| Course isolation and hash-bound provenance | Pass | Pass | Pass |
| Visual success at least 80% and +15 points over V0 | Control | Fail | Fail |
| Text-control regression | Control | Pass | Pass |
| No-evidence and integrity accuracy 100% | Pass | Pass | Pass |
| External calls and paid cost | Pass | Pass | Pass |
| Warm retrieval p95 at most 2 seconds | Pass in workstation run | Pass in workstation run | Pass in workstation run |

Apply the predeclared conditional branch: **Refine and go deeper** with V3 on only the
observed failed visual slices plus the fixed controls. Keep V0 as rollback. Do
not open held-out, update a selected profile, or call V2 production-ready.

## Validity and limitations

- The development/held-out separation was preserved; `heldout_read` is false.
- The development sample is deliberately small. Counts and cases are primary;
  no held-out generalization claim is made.
- Generated V2 descriptions are unreviewed, non-authoritative ranking metadata;
  only original hash-bound pages or regions are evidence.
- The run did not measure deployed-service RSS, concurrent capacity, revocation,
  or a full-vault package. Those deployment gates remain pending.
- Private per-case evidence remains ignored at
  `experiments/runs/multimodal_retrieval_v1_development_attempt_001/result.json`.

## Reproduction

```bash
npm run build:multimodal-development-artifacts
npm run benchmark:multimodal-development
```
