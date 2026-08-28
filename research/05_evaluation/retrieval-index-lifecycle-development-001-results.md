# Retrieval-index lifecycle development result

## Outcome

**Keep** the immutable, release-bound retrieval-index lifecycle for the next
actual-product checkpoint. The real local-Qwen qualification passed every
prospective resource gate, and the supplemental runtime check verified that a
loaded index answers queries without re-embedding documents. This result does
not authorize the 500+100 product checkpoint or the sealed 10,000 cases.

## Decision question

Can the selected Qwen3 hybrid retriever build, load, restart, and query an
immutable index matching the exact course release, source set, component
profile, chunker, embedding revision, query instruction, and retrieval
parameters within the bounded local resource envelope?

## Real-Qwen result

At clean authorization revision `2424e05`, the pinned local
`Qwen/Qwen3-Embedding-0.6B` revision built four indexes over 2,100 public source
regions.

- Build time: **532.408 seconds** (gate: at most 1,800 seconds).
- Aggregate cold load: **0.372 seconds** (gate: at most 10 seconds).
- Peak process RSS: **1,808.484 MiB** (gate: at most 8,192 MiB).
- Artifact size: **12.659 MiB** (gate: at most 500 MiB).
- Build-time embedding batches: **133**.
- Artifacts and source regions: **4/4** and **2,100/2,100**.

The first run exposed a harness evidence omission: it loaded each index but did
not issue the promised real-Qwen queries. AFQC-067 corrected only that
measurement at clean revision `aa64641`; it reused the immutable artifacts and
made no document embeddings.

- Query cases: **40**.
- Non-empty retrieval results: **40/40**.
- Identical rankings after a fresh store restart: **40/40**.
- Runtime document-embedding requests: **0**.
- Query-embedding requests: **40 + 40** across the original and restarted
  stores.
- First and restarted load-plus-query time: **6.322** and **5.763 seconds**.
- Supplemental peak process RSS: **2,897.922 MiB**.

Provider calls, paid cost, private-data reads, product responses, hidden gold,
and final-case access were all **zero**. The one-time local authority was
revoked after the result.

## Durable evidence

- Generated build result SHA-256:
  `5c96e8d86402020f451ee7480761d0cff89050c97b6bf98bb16baffeef11ca27`.
- Generated runtime result SHA-256:
  `d993003fc4b840810c3dcd9bb4901d8ff9ab82b56c566076bed697294c1c8b29`.
- The four local artifact identifiers are recorded in the machine-readable
  result. Generated indexes and unrestricted runtime output remain ignored.

## Verification and limitations

- The preceding complete gate passed **1,145 Python tests**, **47 frontend
  tests**, frontend lint, and the production build.
- Repository correctness remained **649/649 audited**, and execution-freeze
  coverage remained **97/97**.
- The corpus is the public open-source benchmark corpus, not private course
  material. The run establishes retrieval-index lifecycle and resource
  feasibility, not answer quality, citation quality, boundary safety,
  professor fidelity, usability, or learning outcomes.
- The restart check reused the same exact Qwen model instance but a fresh index
  store and separately loaded retrievers. Model-process restart recovery remains
  covered structurally, while process-level persistence will be exercised in
  the next product checkpoint.

## Decision

Close issue #139 as **Done / Keep** after PR #140 merges. The next finite step is
to prepare one new 500-case candidate plus 100-case control actual-product
checkpoint using these prebuilt indexes. That checkpoint requires a separate
authorization and must pass before any sealed 10,000-case execution is opened.
