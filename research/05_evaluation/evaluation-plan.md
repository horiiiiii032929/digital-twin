# Evaluation plan

The selected project-wide protocol is
[`2026-07-22-deployable-tutor-evaluation-protocol.md`](../04_experiments/2026-07-22-deployable-tutor-evaluation-protocol.md).
This file is the compact evaluation index; component plans and named result
records provide the exact frozen configuration for each run.

Use the repository-wide
[evaluation architecture](../../docs/evaluation-architecture.md) for component
comparisons and system-profile decisions. Component-specific records supplement
this final tutor evaluation; they do not replace it.

## Research questions

- Does approved oracle evidence improve safe grounded task success over a
  generic assistant using the same generator?
- Does the professor-approved policy measurably change pedagogical behavior
  when evidence and generator settings are held constant?
- What loss is introduced when retrieved context replaces oracle evidence?
- When all approved documents fit in context, is RAG better than the full-
  document control under quality, latency, token, and cost constraints?
- Can invited professor and student roles complete the deployed pilot tasks
  safely, reliably, and without cross-role or cross-course exposure?

## Dataset portfolio

1. Existing synthetic web-security data remains the public regression suite.
2. `course-tutor-v1` contains 12 professor-anchor, 48 development/calibration,
   and 72 sealed held-out cases over eight predeclared scenario types.
3. Supervised pilot records provide usability and operational evidence only;
   they do not select the RAG method or establish learning improvement.

Public RAG and tutoring benchmarks supply constructs and instrument checks.
They are not substitutes for the versioned course-specific benchmark.

## Frozen conditions

- C0: generic assistant, no course context;
- C1: oracle evidence plus generic tutoring policy;
- C2: the same oracle evidence plus professor policy;
- C3: retrieved evidence plus professor policy; and
- C4: all approved documents plus professor policy when they fit safely.

Hold question, generator, decoding, token budget, and output schema constant.

## Primary outcomes and gates

- unconditional safe grounded task success;
- complete-evidence success@k; and
- professor-policy pedagogical success plus blinded policy-condition
  preference.

Permission, privacy, authorization, assessed-work, citation identity, source
version, unsupported high-severity claims, provider failure, and approved cost
and data boundaries are hard gates. A higher quality average cannot compensate
for a gate failure.

## Component evaluation contract

For each replaceable component, capture:

- one inspectable control and every bounded candidate;
- the same versioned inputs, permissions, configuration, and operational
  conditions;
- hard privacy, provenance, integrity, citation, and failure-behavior gates;
- quality thresholds plus latency, memory, token, cost, and reliability metrics
  where relevant;
- per-case results and diagnosed failures;
- exact code, dataset, model, prompt, and configuration versions;
- a Keep, Refine, Go Deeper, or Drop decision;
- the resulting system-profile change and retained rollback option.

Use the templates in [`templates/`](templates/) and store validated records in
[`records/`](records/) and component selections in [`profiles/`](profiles/).

## System-level evaluation

The final product comparison uses a frozen release-candidate profile. A generic
assistant baseline and the configured tutor must receive the same question set
and documented conditions. Report grounding, pedagogy, policy compliance,
citation validity, no-evidence behavior, latency, tokens, cost, uncertainty,
and limitations without hiding component hard-gate failures inside an aggregate
score.

Use paired inputs and report raw counts, 95% intervals, paired differences,
predeclared confirmatory tests where useful, reviewer agreement, slice results,
operational measurements, and representative failures. An automated evaluator
is diagnostic until validated against the in-domain blinded human labels.
