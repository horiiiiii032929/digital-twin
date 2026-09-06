# paired-pedagogy-development-001-v10-live-001

**The narrow development gates passed.** All 96 independent persistent runtime histories completed 168 student turns across 48 paired synthetic contexts. The experiment compares V4 with V10 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This main development trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 800 calls and USD 20. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-v10-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v10 | 108 | 0 | 0.0425426 |
| v4 | 108 | 0 | 0.0565956 |

There were 40 actual restarts and 0 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 137.956 seconds.

The full repository verification pipeline was deferred during this trial. These local timings remain descriptive, not a deployed capacity benchmark.

## Decision and limits

Independent assistant review found V10 useful in 48/48 contexts versus V4 in 15/48, with zero verified candidate critical events. Keep this narrow result; it does not establish the broader completion contract. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-typed-compact-v10-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-v10-live-001.json).

The primary instructional slice passed 16/16, and the prospective appropriate-explanation slice passed 12/12. One preceding local guarded failure remains adverse operational evidence even though the later target recovered.

[Independent semantic review](paired-pedagogy-development-v10-live-001-assistant-review.md).
