# True-visual product checkpoint 001 — attempt 001 invalid result

## Decision

`invalid-execution`. No product-quality interpretation is permitted.

## What happened

The clean authorized run stopped before its first provider call. The product
runner attempted to read a `title` field that is intentionally absent from the
frozen source package. Titles are presentation metadata, not source truth, so
this was a harness contract defect rather than a method or dataset failure.

## Evidence boundary

- Durable product responses: 0.
- Jina calls/tokens/cost: 0 / 0 / USD 0.
- Hidden gold opened: no.
- Private data used: no.
- Known 10,000+1,000 package touched: no.

The ignored raw ledgers and result are preserved under
`reports/generated/true-visual-product-checkpoint-001-attempt-001-invalid/` and
their hashes are recorded in the machine-readable record.

## One permitted correction

The sole harness-only correction derives a display title from the already
public `source_document_path`, with `source_artifact_id` as fallback. Cases,
gold, source claims, lineage, retriever, gates, provider, and token ceiling are
unchanged. The same frozen checkpoint may then execute once from a new clean
code revision.

## Links

- [Machine-readable record](records/true-visual-product-checkpoint-001-attempt-001-invalid.json)
- [Issue #210](https://github.com/horiiiiii032929/digital-twin/issues/210)
