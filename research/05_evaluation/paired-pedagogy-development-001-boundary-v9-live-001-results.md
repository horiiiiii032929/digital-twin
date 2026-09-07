# paired-pedagogy-development-001-boundary-v9-live-001

**Overall Refine: the main appropriate-explanation gate failed.** All 16 independent persistent runtime histories completed 16 student turns across 8 paired synthetic contexts. The experiment compares V4 with V9 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This boundary sidecar trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 80 calls and USD 2. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-boundary-v9-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v4 | 8 | 0 | 0.0043694 |
| v9 | 8 | 0 | 0.0031642 |

There were 0 actual restarts and 0 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 11.389 seconds.

Local repository verification ran concurrently on the same host. These timings are descriptive, not a deployed capacity benchmark.

## Decision and limits

V9 achieved 8/8 useful contexts, versus V4 at 4/8, and passed the unchanged boundary sidecar gates. This does not remove the separate main appropriate-explanation gate failure or authorize confirmation.

[Full assistant review](boundary-classification-v9-live-001-assistant-review.md). Review was unblinded and implementation-aware, with root adjudication. No profile promotion follows. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-paired-pedagogy-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-boundary-v9-live-001.json).
