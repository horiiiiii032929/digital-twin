# Evaluation result: governed-full-autonomy-v2-1-actual-product-evaluation-002 build

## Run identity

- Component: realistic-time actual-product full-autonomy evaluation boundary
- Date: 2026-09-01
- Base code revision: `7205d262416ef95fa789ccb5702d15e17ae6f492`
- Dirty state: yes; this run qualified the implementation worktree before its
  publication commit
- Instrument SHA-256:
  `05a1187eee2697b11308a12d9bd1e778c259f7276c2246bbc82e30f711a83661`
- Public contract SHA-256:
  `7c73e97c11f774885456aa3100c6b7be0b2f1000dd8ae6a1b2c816a388cf9aec`
- Hidden gold SHA-256:
  `4bb31df4055bdeb167ce0d7d14f7c6aee15e2519cca0d29f76435949b8292af1`
- Reproducible command:
  `npm run simulate:governed-autonomy-v2-1-actual-product-evaluation-002`
- Provider boundary: network-free; zero calls, tokens, and cost
- Machine record:
  `research/05_evaluation/records/governed-full-autonomy-v2-1-actual-product-evaluation-002-build.json`

## Decision question

Can the complete 820-case autonomy portfolio drive the real product services
under realistic 24-hour, seven-day, and 30-day policy timing without waiting
for wall-clock time or rewriting database timestamps?

## Method

The successor uses one injected `VirtualUtcClock` across tutoring, governed
autonomy, proactive outreach, workers, leases, cooldowns, quiet hours,
frequency windows, expiry, and wake-ups. Production continues to use
`SystemUtcClock`; no production environment variable can enable virtual time.

The immutable public package contains 820 cases:

- 600 multi-turn trajectories: 50 templates × four conditions × three seeds;
- 100 synthetic learners over 30 virtual days; and
- 120 proactive opportunities.

Every case passed through `StudentTutoringService`,
`GovernedAutonomyService`, `ProactiveOutreachService`,
`SQLiteStudentRepository`, LangGraph checkpoints, the transactional outbox,
and delivery processing. Public inputs contained no expected action or state.
Hidden gold was joined only after responses completed.

This qualification substituted deterministic local planning and generation
for provider calls. It therefore tests evaluation plumbing, product
integration, policy timing, persistence, and deterministic fallback—not model
quality.

## Result

All four conditions passed every network-free hard gate:

| Condition | Cases | Action accuracy | Goal termination | Restart | Safe provider fallback |
| --- | ---: | ---: | ---: | ---: | ---: |
| T0 grounded control | 150 | 100% | 100% | 100% | 100% |
| T1-v1 reactive control | 150 | 100% | 100% | 100% | 100% |
| T1-v2 reactive | 150 | 100% | 100% | 100% | 100% |
| T1-v2 autonomous | 370 | 100% | 100% | 100% | 100% |

Across all 820 cases there were zero unauthorized or unexpected actions,
wrong-recipient or wrong-course/release actions, invalid citation lineage,
consent violations, duplicate deliveries, unbounded loops, or model-owned
authority mutations. Calls, tokens, and cost were zero.

During qualification, two harness defects were corrected before this final
registered run: provider-failure injection initially left the deterministic
reactive generator active, and expected action labels did not match the frozen
professor-policy event mapping. The correction changed neither hard gates nor
product policy. The final hashes above bind the corrected prospective package.

## Decision

Outcome: **Go Deeper**.

Select the realistic-time actual-product adapter and virtual-clock boundary as
the infrastructure for #157. Do not promote T1-v2.1 from this result. First run
the separately frozen #153 grounding selection. Only a valid `Keep` result may
open the provider-backed 820-case portfolio.

## Limitations

- Perfect deterministic rates are not provider-backed product performance.
- This result does not establish factual grounding quality; #153 remains the
  first decision gate.
- It does not establish professor fidelity, external usability, or learning
  improvement.
- It uses public synthetic sources and learners, not private course or student
  data.
- The run was executed on an implementation worktree. The base revision,
  instrument hash, public/gold hashes, and execution-source hashes in the
  machine record preserve traceability until publication.
