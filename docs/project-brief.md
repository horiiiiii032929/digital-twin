# Project Brief

## Problem

Human teaching time does not scale to every student interaction. Students can
use generic AI tools, but those tools usually lack course boundaries,
instructor-specific source material, and the educator's preferred teaching
style.

## Product Direction

Build and evaluate a deployable Digital Twin tutoring system for one professor
and one course. The system should use approved course material, preserve a
configurable teaching policy, give student-role accounts grounded tutoring with
inspectable citations, and give the professor release and audit control.
Student recruitment is out of scope; evaluation uses researcher-frozen course
anchors, calibrated LLM judges, frozen simulated students, and scripted
synthetic accounts. Optional professor review is an expert-validity check, not
a prerequisite for local experiments.

## Focused research question

For one course and a fixed generator, how do approved course evidence and a
professor-configured tutoring policy affect safe grounded task success,
citation completeness, boundary compliance, calibrated pedagogical success,
multi-turn safe trajectory completion, reliable turn completion, latency, and
cost relative to a generic assistant?

Every replaceable method and architecture boundary must be evaluated against a
control. This includes parsing/chunking, retrieval, returned-context
sufficiency, generation, prompts/policy, conversation state, authentication,
authorization, persistence, storage, deployment, and usability.

## Revised delivery phases

- Instructor onboarding: complete and professor-approved.
- Grounded RAG qualification: freeze the protocol and qualify the generator,
  verifier, and end-to-end RAG profile.
- Deployable application: authenticated professor/student roles, persistence,
  private storage, staging, and visible failures.
- Evaluation qualification: security, privacy, reliability, professor review,
  LLM-judge calibration, simulated-student stress tests, and synthetic-account
  deployment acceptance.
- Final evaluation and reporting: blinded comparisons, evidence freeze,
  deployed demonstration, and reproducibility package.

Proactive intervention and a full learning-gap analytics product are deferred
from the final critical path.

## Current Phase

Instructor onboarding is complete and approved. Grounding foundations include
provider-neutral contracts, approved local parsing, deterministic chunking,
BM25 retrieval, dense/RRF comparisons, component profiles, and result
governance. Retrieval v2, evidence-sufficiency v1, and exploratory local
generation all produced `Refine` or no-selection results.

The project is not yet deployable: it has no selected returned-context verifier
or live generator/prompt, no end-to-end RAG decision, no authentication or
durable persistence, no student release flow, and no staging environment. Issue
#11 is therefore the immediate gate: freeze the method, data-governance,
privacy, dataset, rubric, and reporting protocol before implementation
continues. This is a researcher-controlled reproducibility gate, not a request
for the professor to select the method. The full rescope is recorded in the
[deployable pilot plan](../research/00_admin/2026-07-22-deployable-pilot-rescope.md).
