# paired-pedagogy-development-001-v7-live-001

**Refine: the fixed semantic coverage gates failed.** All 96 independent persistent runtime histories completed 168 student turns across 48 paired synthetic contexts. The experiment compares V4 with V7 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This main development trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 800 calls and USD 20. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-v7-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v4 | 108 | 0 | 0.0566004 |
| v7 | 108 | 12 | 0.0888742 |

There were 40 actual restarts and 12 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 218.384 seconds.

Local repository verification ran concurrently on the same host. These timings are descriptive, not a deployed capacity benchmark. Before dispatch, the stdin launch wrapper encountered a dotenv path-discovery assertion; specifying the existing `.env` path resolved it before any named output or model call, without changing repository source.

## Decision and limits

V7 achieved 33/48 useful contexts and 10/16 primary instructional contexts, below the fixed 39/48 and 13/16 gates. V4 achieved 15/48 and 1/16. Review identified one critical secondary-concept disclosure in the V4 control and none in V7. The V7 main arm delivered 22 safe failures: 12 schema-validation failures and 10 additional local validation failures.

All target responses and preceding turns were reviewed by an unblinded, implementation-aware assistant with root adjudication. [Full assistant review](paired-pedagogy-development-v7-live-001-assistant-review.md). No confirmation or profile promotion follows. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-paired-pedagogy-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-v7-live-001.json).
