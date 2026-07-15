# Evaluation Plan

Use the repository-wide
[evaluation architecture](../../docs/evaluation-architecture.md) for component
comparisons and system-profile decisions. Component-specific records supplement
this final tutor evaluation; they do not replace it.

## Goals

- Compare Digital Twin answers against a generic assistant baseline.
- Measure factual grounding in instructor-approved source material.
- Measure alignment with the instructor's teaching style.
- Identify student confusion patterns that the dashboard should summarize.

## Candidate Evaluation Sets

- Course-bound factual questions
- Socratic tutoring prompts
- Out-of-scope questions
- Assignment policy questions
- Misconception diagnosis questions

## Evidence To Capture

- Prompt and source bundle version
- Model and retrieval settings
- Answer citations
- Rubric scores
- Instructor review notes

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
