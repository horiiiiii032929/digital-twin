# Project Brief

## Problem

Human teaching time does not scale to every student interaction. Students can
use generic AI tools, but those tools usually lack course boundaries,
instructor-specific source material, and the educator's preferred teaching
style.

## Product direction

Build and evaluate a professor-configurable pedagogical Digital Twin for
multiple professors and courses. Each professor controls approved evidence,
teaching behaviour, tutoring policy, evaluation cases, publication, withdrawal,
and rollback. Invited students receive course-isolated, cited tutoring.

The product runs locally for the final project and remains hosting-ready.
Student recruitment is out of scope; evaluation uses researcher-verified
course anchors, deterministic checks, calibrated LLM judges, frozen simulated
students, scripted synthetic accounts, and capacity tests.

## Focused research questions

1. Across heterogeneous courses, how much do dense, hybrid, and reranked
   retrieval improve evidence completeness and safe no-evidence handling over
   heading-aware BM25?
2. With generator and evidence held constant, how much does professor policy
   improve professor fidelity, pedagogical behaviour, misconception handling,
   and academic-integrity compliance over a generic tutoring policy?
3. Can the resulting system complete multi-course professor and student
   workflows with publication control, isolation, recovery, and bounded
   simulated capacity?

Every replaceable method and architecture boundary must be evaluated against a
control. This includes parsing/chunking, retrieval, returned-context
sufficiency, generation, prompts/policy, conversation state, authentication,
authorization, persistence, storage, deployment, and usability.

## Delivery phases

- Scope and architecture lock: authoritative thesis, course portfolio,
  evaluation questions, provider boundary, and repository structure.
- Cross-course retrieval study: verified benchmark, M0-M3 comparison, sealed
  result, and selected or rollback retrieval profile.
- Pedagogical Digital Twin: multi-course professor configuration,
  evaluation-before-publication, and student tutoring journeys.
- End-to-end validation: professor fidelity, pedagogy, isolation, failures,
  recovery, simulated interactions, and bounded capacity.
- Evidence and communication: technical freeze by 2026-08-16, then report,
  figures, presentation, reproducibility, and demo stabilization.

## Current phase

Instructor onboarding is complete and approved. Grounding foundations include
provider-neutral contracts, approved local parsing, deterministic chunking,
BM25 retrieval, dense/RRF comparisons, component profiles, and result
governance. Retrieval v2, evidence-sufficiency v1, and exploratory local
generation all produced `Refine` or no-selection results.

The exact no-participant judge, simulator, run-record, analysis, and stop-rule
contracts are frozen and validated. The IT5002 pilot provides useful
development evidence but does not select a final method: local Qwen3 reranking
reached 10/13 answerable cases versus 3/13 for heading BM25, while the separate
59-case one-time run failed after 29 cases and is invalid. Jina is an unselected
provider spike with no result.

The current phase is professor-fidelity refinement and end-to-end validation. The one-time
60-case held-out M0-M3 comparison selected M2 hybrid retrieval for the
experimental profile and retained BM25 as rollback. The first durable synthetic
student slice now connects that profile to course authorization, published
releases, persisted turns, citations, fallback, withdrawal, and restart checks.
Generator/prompt qualification is complete, while the first 48-case
professor-policy comparison ended in `Refine`: C3 missed safe-grounded and
complete-evidence floors, automated pedagogy was ineligible, and the one-time
held-out split remains unopened. Next comes scoring, multi-evidence retrieval,
assessed-work, and blinded-anchor repair, alongside broader professor/student,
recovery, and capacity evidence. The
authoritative baseline is the [frontier Digital Twin scope](../research/00_admin/2026-07-27-frontier-digital-twin-scope.md).
