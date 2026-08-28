# Product checkpoint 005 — attempt 002

Result ID: `academic-factual-qa-open-10000-development-product-checkpoint-005-attempt-002-invalid`

Decision: **Invalid execution / stop checkpoint 005**

The single harness-corrective attempt started from clean revision `2f72e2a`
with the locked retrieval dependency installed. The local Qwen3 model loaded,
but the first course index did not finish after more than 2 hours 15 minutes.
No product response or provider request was reached.

A process sample showed a 14.7 GB physical footprint on the 16 GB host and the
main thread waiting for an MPS synchronization while constructing dense
embeddings. The run was terminated to protect the host after 8,100-plus seconds
without a first response. This is an operational failure of on-demand dense
index construction under the frozen batch and sequence configuration, not a
factual-quality result.

The provider and response ledgers contain zero calls, responses, tokens, and
cost. Hidden gold remained sealed; control, scoring, and advisory stages never
opened. The final 10,000-case split remained unauthorized.

Ignored attempt snapshots are preserved with these hashes:

- interrupted state: `11e77cfc83dfe3ee539c9972320f43ad5336295c2aee4ab9dcc93a5ced56601b`;
- zero-call provider ledger: `33baf88ced81a3782bb5892f0df236045eced568cdc88537bbba98ba225bbdb0`;
- initialized product state: `8008ccb2fa89ad874f76d1e8c4496a1e4db191e49a829291aaa74470d00110da`;
- zero-response ledger: `bff7f9a7a27c6c4fcaedef072be65174fca0be593367dad88da5b48db9f8fc86`.

Checkpoint 005 authority is revoked. Per the finite evaluation plan, there is
no third attempt and no 10,000-case progression. The next method-level work is
to build immutable, hash-bound retrieval indexes during ingestion or release
publication, load them without re-embedding on each process start, and qualify
that lifecycle independently before a new product-evaluation checkpoint.
