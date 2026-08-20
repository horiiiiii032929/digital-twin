# Evaluation result: factual-qa-v3-source-disposition-v1

Date: 2026-08-19

Decision: **Refine; complete accounting passed, but 663 unique sources still
require explicit content-role or conversion review**

## Scope and reproducibility

This zero-model Stage A checkpoint transformed the refreshed private Academia
Vault inventory into a private source-disposition manifest. It accounts for
every regular file, applies conservative sensitive-hash handling, chooses one
canonical path for exact duplicate content, and emits only sanitized aggregate
counts publicly.

The run used base revision `046c65f` with a dirty tree containing only the
prospective disposition builder and its synthetic tests. Reproduce it with:

```bash
uv run python -m scripts.build_factual_qa_v3_source_dispositions
```

The private manifest remains ignored at
`data/interim/factual_qa_v3/source_dispositions_v1.json`. Its stable disposition
SHA-256, computed without the generation timestamp, is
`e43db04886a565733f176c4c5ea5a0e81b20af83002acd44ec61cce4bb4f3ed8`.

## Result

| Disposition | Files |
| --- | ---: |
| Excluded duplicate/generated/tool state | 1,971 |
| Excluded integrity/privacy | 3 |
| Review or conversion required | 663 |
| **Total accounted for** | **2,637** |

The source universe contains 2,497 unique content hashes and 140 non-canonical
duplicate files. Of the 663 pending records, 275 came from clear inventory
candidates and 388 came from the prior review queue after duplicate handling.

- Complete-accounting gate: passed
- Release-ready gate: failed as intended
- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Private paths or source content committed: 0

## Safeguards and limitations

Every exact-content group with a sensitive-indicated member is conservatively
excluded in full. Otherwise, canonical selection prioritizes a clear candidate,
then a review candidate, then generated state; non-canonical paths remain in the
private lineage record.

Inventory eligibility is not treated as authoritative evidence. All unique
eligible and ambiguous content remains `review_or_conversion_required` until a
later local pass assigns an approved evidence role and verifies conversion.
This checkpoint therefore makes no corpus-quality, retrieval, generation, or
scale claim.

## Decision

**Refine.** Keep the complete-accounting implementation and its private
manifest. Next, classify the 663 unique pending sources by content role and
conversion support, fail closed on mandatory exclusions, and leave uncertain
items for a compact human review. No provider call or factual-QA pilot is
authorized.
