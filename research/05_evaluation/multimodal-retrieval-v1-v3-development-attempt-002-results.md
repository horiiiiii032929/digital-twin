# Multimodal retrieval V3 development attempt 002

Date: 2026-08-01

Run ID: `multimodal-retrieval-v1-v3-development-attempt-002`

Decision: **Drop this V3 configuration. Retain V0 as the text rollback, keep V2
as research evidence only, and do not open held-out or select a multimodal
profile.**

> **Correction (2026-08-18):** The reported region metric was inflated by
> duplicate representation gains. A registered no-model correction replaces
> V2 `0.212` and V3 `0.186` with corrected nDCG values `0.0676` and `0.0756`.
> Complete evidence, atomic recall, controls, and the Drop decision are
> unchanged. See the [corrective analysis](multimodal-retrieval-v1-v3-development-attempt-002-analysis-correction-001-results.md).

## Decision context

Development attempt 001 activated the predeclared V3 branch after V1 and V2
failed the relative visual-quality gate. This run compared V2 with a frozen V3
using precomputed OpenCLIP image vectors and lexical/visual reciprocal-rank
fusion. It was restricted to the failed table and scanned-page modalities plus
all fixed text-control, no-evidence, and integrity cases: three visual cases and
six controls. The other development modalities were not remeasured.

V3 used `open-clip-torch==3.3.0`, `ViT-B-32-quickgelu`, pretrained tag
`openai`, weight SHA-256
`e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31`,
512-dimensional normalized vectors, and RRF with `k=60` and depth 20. Page and
contextual region vectors were generated locally from the sealed development
assets. There were zero external calls and zero paid cost.

## Aggregate results

| Candidate | Failed-slice complete evidence @3 | Atomic recall @5 | Region nDCG @10 | Text control @3 | No evidence | Integrity | Warm p95 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| V2 lexical/layout/description | 1/3 (33.3%) | 2/3 (66.7%) | 0.212 | 3/3 | 1/1 | 2/2 | 0.209 ms |
| V3 V2 + OpenCLIP RRF | 1/3 (33.3%) | 1/3 (33.3%) | 0.186 | 3/3 | 1/1 | 2/2 | 31.395 ms |

V3 tied V2 on complete evidence, halved atomic recall, and reduced region nDCG.
The CPU query-text encoder itself measured 29.32 ms p50 and 30.85 ms p95 on the
research workstation, so latency was not the decision-limiting failure.

## Operational evidence

The offline image-vector job produced 153 vectors in 4.47 seconds after a 2.85
second model load (0.029 seconds per region). Its peak RSS was 1,011,318,784
bytes. The ignored vector artifact was 2,468,245 bytes. The CPU comparison
process loaded 151,277,313 parameters, took 1.46 seconds to load, and observed a
1,681,686,528-byte peak RSS.

Although the memory and latency measurements fit their numeric development
ceilings, this implementation loads the full OpenCLIP model, including the
visual tower, on the request path. It therefore fails the explicit architecture
gate that no vision model be resident in the deployed service.

## Failures

- The scanned MIPS case remained below the region threshold. V3 preserved the
  top OCR crop but displaced the broader fifth-ranked region that let V2 reach
  atomic evidence at five. This is a region-granularity and fusion failure.
- The email-table case still selected a broad OCR row rather than the narrow
  gold region. Visual fusion ranked the alternative page first and the correct
  page second, reducing region nDCG. This is a table-structure and ranking
  failure.
- V3 preserved all three text-control page hits, but its fused top-three records
  caused the conservative lexical action heuristic to abstain on all three.
  This is a query/policy integration regression, not a page-retrieval miss.
- The full CLIP model remained resident for query encoding. This is an
  architecture/operations failure even though observed RSS stayed below 2.5
  GiB.

## Hard gates and decision

| Gate | V2 | V3 |
| --- | --- | --- |
| Development scope complete; held-out unopened | Pass | Pass |
| Improve failed-slice quality over V2 | Control | Fail |
| Text-control page regression | Pass | Pass |
| No-evidence and integrity accuracy 100% | Pass | Pass |
| Warm retrieval p95 at most 2 seconds | Pass | Pass |
| No vision model resident online | Pass | Fail |
| External calls and paid cost | Pass | Pass |

Apply the stop rule: **Drop this V3 configuration**. Further tuning on these
nine cases would reuse the same calibration evidence and is not justified.
Retain V0 for supported text behavior and keep visual claims unsupported where
V2 cannot provide sufficient page-local evidence. V2's improved localization
remains useful research evidence but does not become a selected profile.

## Validity and limitations

- The sealed development loader verified a pristine ledger; `heldout_read` is
  false and the 24-case held-out partition remains unopened.
- The run is deliberately scoped and cannot estimate overall or held-out V3
  quality.
- Workstation timing is not concurrent two-vCPU server capacity evidence.
- The run does not test a separately exported CLIP text-only tower. That
  alternative would address the residency failure but not the observed quality
  regression, so it is not pursued on this development set.
- Private per-case evidence remains ignored at
  `experiments/runs/multimodal_retrieval_v1_v3_development_attempt_002/result.json`.

## Reproduction

```bash
npm run build:multimodal-visual-embeddings
npm run benchmark:multimodal-v3-development
```
