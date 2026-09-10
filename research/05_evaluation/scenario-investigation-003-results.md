# Evaluation result: scenario-investigation-003

## Run identity and decision question

10 September 2026; revision `9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty. Exact inspected source hashes and sanitized results are in the [machine record](records/scenario-investigation-003.json). This exploratory investigation asks which lifecycle findings admit a repair that preserves all app decisions. It is not a preregistered quality comparison and proposes no algorithm replacement or profile promotion.

Control is the current implementation. Hypothesis investigated: optional metadata reads can prevent completed primary operations from leaving loading state. Alternative proposed for later implementation: independent metadata loading with stale-response guards. No candidate implementation was tested here.

## Dataset, configuration and reproducibility

Synthetic hook fixtures use the repository's mocked hook harness and deferred learner-evidence promises. Two branch-specific cases cover send completion and saved-conversation loading. Three fixed built-in previews, two different synthetic custom prompts and archived synthetic persona refusal prompts support source-level investigations. No private course content or credentials are retained. No split or random seed applies. Sample size covers the identified paths only; it does not estimate user incidence or overall reliability.

Retained hook probe: [source](../../tests/manual/scenario-investigation-003-hook-probes.ts.txt). To reproduce from the repository root, first ensure the temporary destination does not already exist:

```sh
cp tests/manual/scenario-investigation-003-hook-probes.ts.txt apps/web/src/hooks/scenario-investigation.test.ts
npm --workspace apps/web test -- --run src/hooks/scenario-investigation.test.ts
rm apps/web/src/hooks/scenario-investigation.test.ts
```

The source is retained as text so the defect-demonstration assertions are not mistaken for desired-behavior regression tests in the default suite. Original local outputs are under `output/browser-qa/scenario-investigation-003/`; sanitized results are also retained in the machine record. Preview and interpreter probes are exploratory local function calls cross-checked against the named source files, not a full end-to-end graph replay.

## Results and failed-case classification

| Probe | Observed result | Classification |
| --- | --- | --- |
| Completed send, stalled evidence | Reply exists while composer remains submitting and sent draft remains uncleared | Confirmed frontend integration/liveness defect H-001 |
| Saved conversation, stalled evidence | Primary history read succeeds but history stays hidden/loading | Confirmed frontend integration/liveness defect H-002 |
| Legacy preview content | 3/3 built-ins CSRF; two custom prompts produce the same response | Fixed prototype behavior, including publication design limitation |
| Self-check refusal | V3 router does not reject; interpreter flags direct solution because `write my` matches | Confirmed decision-rule false positive; constraint-to-refusal mapping source-traced |

Both hook tests passed because they assert the defective behavior. Neither bug is repaired. Total Vitest duration 148 ms; tests 5 ms. No provider calls, tokens, billed model cost or AWS calls. Memory and production request latency were not measured. No statistical uncertainty estimate is meaningful for these targeted deterministic probes.

## Gates and validity

No production source, model selection, prompt, validator, decision threshold, approval gate, repair limit or deployment changed. Temporary runnable probe removed after execution. These are local hook tests, not computer-use/browser observations and not proof of the historical AWS hang's cause. Previous test-suite results belong to slide-codefix-002; they were inspected, not rerun or relabeled as this run.

The original lifecycle has 106 scenarios with 35 passes, 27 partial, 14 failed, 8 blocked and 22 not run. This investigation reviews the findings and coverage gaps; it does not fill all those gaps. No rejected model output is accepted and no failure evidence is omitted.

## Decision and follow-up

**Refine** the two UI loading paths in a subsequent coding-only change; **Keep** the frozen decision behavior. The self-check regex false positive is still out of scope because changing it changes a refusal decision. No release profile update is warranted. The [full disposition report](../../docs/scenario-findings-fix-boundaries-2026-09-10.md) maps every B-001–B-009 finding, the two new coding defects and remaining coverage groups to permitted and prohibited actions.

Required repair checks: deferred and rejected optional reads, normal completion, duplicate-submit protection, same request ID, stale responses across successive turns/conversations/courses/accounts, and rendered-browser repeated-turn/reload recovery. Keep AWS paused while performing local work. Prior local metadata fixes remain undeployed.
