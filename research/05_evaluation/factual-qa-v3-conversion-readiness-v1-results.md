# Evaluation result: factual-qa-v3-conversion-readiness-v1

Date: 2026-08-19

Decision: **Refine; integrity passed for all 610 pending sources and 586
(96.1%) are locally conversion-ready, while 24 require remediation**

## Scope and reproducibility

This local-only Stage A audit checked every source in corrected disposition
manifest v2. The unit of analysis is one canonical unique-content source still
awaiting semantic role or conversion review. The audit verifies path
containment, regular-file and symlink state, exact SHA-256 stability, and a
format-specific local parser probe without retaining extracted content in the
durable summary.

The run used base revision `bb6e894` with a dirty tree containing the
prospective audit implementation, synthetic tests, and this result. Reproduce
it with:

```bash
uv run python -m scripts.audit_factual_qa_v3_conversion_readiness
```

The private per-source audit remains ignored at
`data/interim/factual_qa_v3/conversion_readiness_v1.json`. Its stable record
SHA-256 is
`1464e3e03b5b05b4abee16f7066bf34b86710bbcb757f7972d4232dc7a771f19`.

## Results

| Conversion status | Sources | Share |
| --- | ---: | ---: |
| Ready local text | 382 | 62.6% |
| Ready structured | 83 | 13.6% |
| Ready PDF text | 110 | 18.0% |
| Ready visual | 11 | 1.8% |
| Needs OCR | 4 | 0.7% |
| Needs office conversion | 4 | 0.7% |
| Unsupported format | 11 | 1.8% |
| Empty source | 1 | 0.2% |
| Invalid for current parser | 4 | 0.7% |
| **Total** | **610** | **100.0%** |

The rounded shares sum to 100.1%. Exact counts are authoritative.

- File-integrity gate: passed, 610/610
- Local-conversion gate: failed, 586/610 ready
- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Private paths or extracted source content committed: 0

Ready sources include 110 text-bearing PDFs, 382 code/text/TeX files, 83
notebooks/tables/structured files/diagrams, and 11 raster images. The 24-source
remediation queue contains four OCR-only PDFs, four office documents, eleven
unsupported files, one empty source, and four parser-invalid sources. MuPDF
emitted recoverable xref warnings while reading at least one PDF; the file
remained readable and is not counted as an integrity failure.

## Risk and limitations

Severity is high for release but low for source preservation: no file drift or
path-integrity failure was found, but silently dropping 24 sources would violate
the complete-corpus requirement. A successful parser probe establishes only
technical readability. It does not establish that a source is authoritative,
permission-safe, relevant, or semantically suitable for factual QA.

The PDF probe distinguishes text-bearing from OCR-required documents but does
not yet validate layout fidelity for tables, diagrams, equations, or reading
order. Raster/vector readiness proves file validity, not usable visual
extraction. Office and unsupported formats need explicit adapters or exclusion
decisions.

## Decision

**Refine.** Keep the integrity and parser audit. Remediate the 24-source
conversion queue locally, then assign semantic source roles across all 610
sources. No model, pilot, or scale execution is authorized by this result.
