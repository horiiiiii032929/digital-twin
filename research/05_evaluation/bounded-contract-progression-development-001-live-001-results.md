# Bounded contract communication comparison

Run `bounded-contract-progression-development-001-live-001`, 6 September 2026.
Decision: keep the explicit v3 contract as an opt-in development candidate;
**Refine teaching usefulness and continuation**. No selected release or default changed.

The fixed-1,500-token comparison completed all 36 two-turn histories (72 turns),
with three order repetitions of six synthetic situations and real Luna calls.
Both arms used the actual application factory, approved synthetic profiles and
source bindings, with one restart per history. V3 alone exposed unchanged local
response limits in its prompt. Sources remained unchanged; exact source snapshots,
provider messages, returned identities, usage and all outputs are retained.

| Measure | V2 | V3 |
|---|---:|---:|
| Actual calls | 36 | 36 |
| Valid responses | 22 | 36 |
| Schema failures / delivered guarded failures | 14 | 0 |
| Answers | 9 | 12 |
| Questions | 10 | 14 |
| Clarifications | 3 | 7 |
| No evidence | 0 | 3 |
| Input / output tokens | 45,418 / 11,964 | 51,774 / 12,036 |
| Cost USD | 0.0234404 | 0.0247980 |
| Median / p95 call latency ms | 3,518 / 5,389 | 3,836 / 5,695 |

Elapsed time was 74.24 seconds. Bounds were 240 calls / USD 4.80, four isolated
histories concurrently, 30-second timeout and no retries. Timing is descriptive
because other provider evaluation was co-resident. The sample provides repeated
development observations, not independent courses or a population success estimate.

An [independent assistant review](bounded-contract-live-001-assistant-review.md)
inspected all 72 outputs and their actual contexts; the
[per-case findings](bounded-contract-live-001-assistant-findings.json) remain
separate from mechanical validity. All 21 rendered answers preserved the requested
facts as source-exact paragraphs. This does not establish effective instruction:
the narrowed named follow-up after a nine-detail request still clarified in all
three repetitions in both arms. Their traces identify `provider_model=not-called`
and `prompt_version=not-built`: the deterministic ambiguity router matched
“explain that” despite the earlier explicit Cobalt referent. This is a pre-model
policy overmatch, not evidence that a model proposal ignored the clarification.
No-attempt withholding remained intact, but
questions often repeated a generic starting prompt.

The fixture named `topic-reset` is incorrectly named: Amber question followed by
Amber attempt never changes concept. It supplies **no concept-switch evidence**.
The unchanged fixture and result are preserved; a separately preregistered small
boundary check will address this missing coverage. No semantic judge score or
human pedagogical qualification is claimed. Later histories differ by actual
responses, so this is a comparison of dialogue trajectories after the first turn.

Plan: [bounded contract communication](../04_experiments/2026-09-06-bounded-contract-communication-plan.md).
Exact revision, dirty state, source hashes, per-history actions and budgets,
artifact digests and source snapshot hash are in the
[machine record](records/bounded-contract-progression-development-001-live-001.json).
Raw artifacts: `reports/generated/bounded-contract-progression-development-001-live-001`.
Reproduce with the documented `scripts.run_bounded_contract_progression_development`
command in `scripts/README.md`, a fresh output directory and explicit `--live`.
