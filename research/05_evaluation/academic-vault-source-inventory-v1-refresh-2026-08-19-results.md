# Evaluation result: academic-vault-source-inventory-v1-refresh-2026-08-19

Date: 2026-08-19

Decision: **Refine; use 294 clear candidates, resolve 437 review items, and
retain 1,906 hard exclusions before corpus release**

## Scope and reproducibility

This local, metadata-only refresh reran the existing v1 inventory against the
canonical `Documents/academia_vault` collection before freezing factual-QA v3.
It used clean Git revision `3df17c8649c7a4783356495f53f46ea916fbcdfd`.
There were no tracked working-tree changes before the run.

Command:

```bash
npm run inventory:multimodal-sources
```

The ignored private inventory is stored under `data/interim/`. Its SHA-256 is
`41370d3d25157896320c881d95bc605781d166ac653b6f67d6f3e2a1ae05ebb3`.
The ignored sanitized aggregate is stored at
`reports/generated/multimodal-source-inventory-v1.json`; the durable aggregate
evidence is recorded in this result.

## Aggregate result

| Classification | Files |
| --- | ---: |
| Clear course-scoped candidates | 294 |
| Review required | 437 |
| Generated/tool-state excluded | 1,903 |
| Secret-indicated excluded | 3 |
| **Total regular files** | **2,637** |

Logical size was 337,556,462 bytes. The inventory contained 2,497 unique
content hashes, 46 zero-byte files, 66 exact-duplicate groups containing 206
files, and nine duplicate groups that included clear candidates. V3 therefore
deduplicates processing by content hash while retaining every source path and
disposition for audit.

Relative to the preserved 2026-07-31 inventory, the vault has one additional
regular file and 642,857 additional logical bytes. Classification changed by
+2 clear candidates, +2 review-required files, -3 generated exclusions, and no
change to the three sensitive exclusions. The previous private path-level
snapshot was not retained, so this result does not claim which files caused
the drift.

## Privacy, cost, and validity

- External provider calls: 0
- Model calls: 0
- API cost: USD 0
- Committed private paths or source content: 0
- Corpus-quality claim: none

This result proves only that the complete local file universe was traversed and
sanitized aggregate classifications were reproduced. Filename and extension
heuristics cannot establish final content eligibility. Assessment-like paths,
unassigned files, unsupported formats, archives, and ambiguous items remain in
the review queue. Zero-byte and exact-duplicate findings are operational risks,
not automatic evidence exclusions without a recorded disposition.

## Decision

**Refine.** Freeze the snapshot as the v3 source universe. Give all 2,637
regular files one of the six v3 source roles; process the 294 clear candidates
first, resolve all 437 review items before release, and preserve the 1,906 hard
exclusions. No model run or scale stage is authorized by this inventory.
