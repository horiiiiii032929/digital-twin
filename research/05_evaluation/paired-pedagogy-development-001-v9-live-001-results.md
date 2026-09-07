# paired-pedagogy-development-001-v9-live-001

**Overall Refine: the main appropriate-explanation gate failed.** All 96 independent persistent runtime histories completed 168 student turns across 48 paired synthetic contexts. The experiment compares V4 with V9 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This main development trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 800 calls and USD 20. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-v9-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v4 | 108 | 0 | 0.0587890 |
| v9 | 108 | 0 | 0.0402200 |

There were 40 actual restarts and 0 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 140.078 seconds.

Local repository verification ran concurrently on the same host. These timings are descriptive, not a deployed capacity benchmark.

## Decision and limits

V9 achieved 45/48 useful contexts and 16/16 primary instructional contexts, versus V4 at 16/48 and 2/16. The earlier main engineering gates pass, but the prospective 12/12 appropriate-explanation gate fails at 11/12 because one explanatory case ended in a local guarded fallback. All outcomes remain included. Overall Refine; confirmation remains closed.

[Full assistant review](paired-pedagogy-development-v9-live-001-assistant-review.md). Review was unblinded and implementation-aware, with root adjudication. No profile promotion follows. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-paired-pedagogy-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-v9-live-001.json).
