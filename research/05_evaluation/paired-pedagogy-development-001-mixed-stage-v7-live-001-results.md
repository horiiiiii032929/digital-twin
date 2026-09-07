# paired-pedagogy-development-001-mixed-stage-v7-live-001

**Refine: the fixed semantic coverage gates failed.** All 16 independent persistent runtime histories completed 24 student turns across 8 paired synthetic contexts. The experiment compares V4 with V7 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This mixed-evidence stage sidecar trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 120 calls and USD 3. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-mixed-stage-v7-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v4 | 16 | 0 | 0.0082168 |
| v7 | 16 | 0 | 0.0148124 |

There were 8 actual restarts and 0 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 36.188 seconds.

Local repository verification ran concurrently on the same host. These timings are descriptive, not a deployed capacity benchmark. Before dispatch, the stdin launch wrapper encountered a dotenv path-discovery assertion; specifying the existing `.env` path resolved it before any named output or model call, without changing repository source.

## Decision and limits

V7 achieved 5/8 useful contexts, including 3/4 initial and 2/4 post-attempt contexts; V4 achieved 0/8. The overall and post-attempt gates failed. No initial full-solution disclosure was observed. Three V7 turns ended in local safe failures despite complete provider calls.

All target responses and preceding turns were reviewed by an unblinded, implementation-aware assistant with root adjudication. [Full assistant review](mixed-evidence-stage-v7-live-001-assistant-review.md). No confirmation or profile promotion follows. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-paired-pedagogy-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-mixed-stage-v7-live-001.json).
