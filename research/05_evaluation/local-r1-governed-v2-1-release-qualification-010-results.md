# Local R1 governed V2.1 release qualification 010

## Decision

`completed-keep` for the exact local research-release scope. The final profile
uses BM25 retrieval, the dominance-scoped ambiguity-safe gate, deterministic
grounded generation, governed T1-v2 autonomy, Luna policy-value planning for
complex autonomous decisions, text/OCR visual fallback, and a one-setting T0
rollback.

This is the corrected successor to qualification 009 attempt 001. It proves
that the best measured composition is operational and restart-safe; it does
not convert the unfavorable factual, visual, or profile evaluations into
quality passes.

## Results

| Check | Result |
| --- | ---: |
| Internal-CA HTTPS journey | 25/25 |
| Restart persistence | 6/6 |
| Clean backup restore | 6/6 |
| T0 rollback | 3/3 |
| Governed V2.1 restoration | 3/3 |
| Machine-verifiable total | 43/43 |
| Checkpoint/application log errors | 0 / 0 |
| Desktop / exact 390x844 render | Passed / passed |
| Horizontal overflow | 0 |
| Labelled login controls | 3/3 |
| Keyboard order | Email → Password → Sign in |
| Live API p95 | 5.664 ms |
| Provider calls / cost | 0 / USD 0 |

The source revision was
`6449dcfeb6945d3a4d035d3216eaafd68e414524`. The API image digest is
`sha256:e081445a9653c27d3644712f0a402c70f80c50e2c3fd712851d88138ec3076ed`
and the web image digest is
`sha256:144ba61cc6bfa8c4bb24ccaf0b9787764716ca8bc99561ce41c086b41a249527`.
The schema-v17 backup contained seven verified data files.

## Corrective evidence

The previous image restored a live citation containing `RegionKind.TEXT` but
the restricted LangGraph serializer did not allow that nested enum. The
correction added the exact enum to the allowlist and extended the pre-existing
interrupt/restart test to persist and restore a region-bearing citation. The
full repository gate then passed with 1,937 Python/API tests and 51 frontend
tests before these images were built. Log audit after restart, clean restore,
T0 rollback, and governed restoration found no deserialization or application
errors.

## Claim boundary

- Fresh factual comparison: best arm 63.25% fully grounded; academic threshold
  not passed.
- Fresh true-visual comparison: Jina v5 16/30 versus text/OCR 26/30; Jina
  dropped and no representative visual claim.
- Synthetic profile proxy: Refine; no real-professor fidelity claim.
- Autonomy: confirmation 024 and multi-concept confirmation 025 remain the
  provider-backed and multi-concept evidence; this qualification exercised
  deterministic fast paths.
- No real-student usability, real learning improvement, or durable-hosting
  claim is made.
