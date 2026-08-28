# Retrieval-index lifecycle development result

## Outcome

**Go Deeper** with immutable, release-bound retrieval indexes. The network-free
development qualification passed every lifecycle gate and removes document
embedding from the product request path. This result selects the lifecycle for
one real local-Qwen qualification; it does not select a release profile or
authorize another 500+100 product run.

## Decision question

Can the selected hybrid retriever load a precomputed index matching the exact
course release, source set, component profile, chunker, embedding model,
revision, query instruction, and retrieval parameters without re-embedding the
corpus at runtime?

## Result

At clean implementation revision `c63f7815eb9de9d6b61af64efbe5755ed2ed7f40`,
the deterministic simulation built four immutable indexes over 2,100 synthetic
source regions and issued 40 retrieval queries.

- Runtime document-embedding calls: **0**.
- Loaded-versus-live top-five ranking equivalence: **40/40**.
- Restart retrieval consistency: **40/40**.
- Stale binding rejection: **passed**.
- Corruption detection: **passed**.
- Synthetic cold load: **1.072 seconds** in aggregate across four indexes.
- Synthetic artifact size: **2.391 MiB**.
- Peak traced Python allocation: **8.370 MiB**.
- Provider calls, private-data reads, and final-case access: **0**.

The actual-product adapter now verifies that every exact artifact already
exists before loading Qwen. It cannot build document vectors during product
startup. Publication may prepare an index before state mutation, and missing,
stale, mixed-version, cross-course, or corrupt artifacts fail closed.

## Verification

- The focused retrieval, product, publication, API, provider, runner, and freeze
  suite passed **120 tests**.
- The complete repository gate passed **1,145 Python tests**, **47 frontend
  tests**, frontend lint, and the production build.
- Repository correctness is **649/649 audited** with zero pending findings.
- Execution-freeze coverage is **97/97** entrypoints.
- The live preflight is correctly `blocked-not-authorized`; no local model or
  provider was called.

## Limitations

- The simulation uses deterministic 64-dimensional synthetic vectors. Its
  memory, build time, load time, and artifact size are not measurements of the
  real Qwen3 0.6B index.
- The earlier 14.7 GB process sample includes the local model and on-demand
  construction and is not directly comparable with Python allocation tracing.
- Product answer quality, citations, boundary safety, and the sealed 10,000
  cases were not evaluated here.
- The local artifact remains unbuilt. Its exact build time, process RSS,
  artifact size, and loaded-query behavior must pass a separately authorized
  qualification before a successor product checkpoint is designed.

## Next action

Authorize exactly `retrieval-index-lifecycle-development-001` for a resumable,
local-only Qwen3 build over the 2,100 public source regions. The run makes no
paid/provider call and opens no final case. A pass permits design review of one
new 500+100 product checkpoint; it does not authorize that checkpoint or the
final 10,000-case execution.
