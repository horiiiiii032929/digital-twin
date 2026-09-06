# paired-pedagogy-development-001-boundary-v10-live-001

**The narrow boundary gate passed.** All 16 independent persistent runtime histories completed 16 student turns across 8 paired synthetic contexts. The experiment compares V4 with V10 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This boundary sidecar trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 80 calls and USD 2. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-boundary-v10-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v10 | 8 | 0 | 0.0033962 |
| v4 | 8 | 0 | 0.0043634 |

There were 0 actual restarts and 0 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 12.213 seconds.

The full repository verification pipeline was deferred during this trial. These local timings remain descriptive, not a deployed capacity benchmark.

## Decision and limits

Independent assistant review found V10 useful in 8/8 contexts versus V4 in 4/8, with zero verified candidate critical events. Keep this narrow boundary result; the main and mixed-stage development gates remain pending. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-typed-compact-v10-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-boundary-v10-live-001.json).

[Independent boundary review](boundary-classification-v10-live-001-assistant-review.md).
