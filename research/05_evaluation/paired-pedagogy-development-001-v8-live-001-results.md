# paired-pedagogy-development-001-v8-live-001

**The narrow development gates pass; overall improvement is still required.** All 96 independent persistent runtime histories completed 168 student turns across 48 paired synthetic contexts. The experiment compares V4 with V8 under identical fixed student inputs, approved source cards, teaching profiles, Luna model, and 3,000-token output cap. It does not infer semantic success from a returned answer or citation.

## Method and provenance

This main development trial used the frozen prospective plan, deterministic scheduling seed 7801, one repeat, and at most four concurrent histories. Its bounds were 800 calls and USD 20. The main development packet is openly reused; the boundary and mixed-stage packets remain separate evaluations. Gold annotations were excluded from runtime and provider inputs.

Revision `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty state `True`. Actual implementation IDs were checked before use and after each restart. All source and input hashes remained unchanged: `True`. The manifest, original packet, archived source snapshot, provider ledger, and complete per-turn outputs remain under `reports/generated/paired-pedagogy-development-001-v8-live-001`.

## Operational results

| Arm | Actual calls | Provider-record failures | Reported cost (USD) |
|---|---:|---:|---:|
| v4 | 108 | 0 | 0.0563796 |
| v8 | 108 | 0 | 0.0390160 |

There were 40 actual restarts and 0 provider-record failures. No unknown-cost calls or budget stops occurred. Failed responses remain in the planned semantic denominator. All action counts, full latency records, and schema diagnostics are retained in the machine-readable record and raw artifacts. Elapsed time was 156.247 seconds.

Local repository verification ran concurrently on the same host. These timings are descriptive, not a deployed capacity benchmark.

## Decision and limits

V8 achieved 39/48 useful contexts and 16/16 primary instructional contexts, meeting the unchanged narrow development gates. V4 achieved 16/48 and 2/16. The V8 arm had no verified critical event; the V4 control had two secondary-concept disclosures. Six explanatory-profile failures remain, so passing this engineering gate does not satisfy the broader profile-alignment contract. One preceding V8 turn ended in a local guarded failure.

[Full assistant review](paired-pedagogy-development-v8-live-001-assistant-review.md). The review was unblinded and implementation-aware, with root adjudication. Known profile defects keep confirmation closed; no release promotion follows. These purposive synthetic contexts do not measure instructor fidelity, human learning, real student behavior, public deployment, or population error rates. Source bindings establish provenance rather than semantic truth. The narrow development gates do not replace the project's factual, profile, and boundary completion contract. Confirmation remains unopened, and no default or selected release changed.

[Prospective plan](../04_experiments/2026-09-06-paired-pedagogy-runner-plan.md) · [Machine-readable record](records/paired-pedagogy-development-001-v8-live-001.json).
