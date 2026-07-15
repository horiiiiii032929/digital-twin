# Project Brief

## Problem

Human teaching time does not scale to every student interaction. Students can
use generic AI tools, but those tools usually lack course boundaries,
instructor-specific source material, and the educator's preferred teaching
style.

## Product Direction

Build a Digital Twin System that gives students contextual tutoring support and
gives instructors visibility into common confusion patterns. The system should
use instructor-approved course material and preserve a configurable teaching
policy.

## Research Questions

- What source material is required to create a useful instructor knowledge base?
- Which response controls make the tutor feel aligned with the instructor?
- How should the system refuse or redirect requests outside course boundaries?
- Which learning-gap signals are useful enough for instructors to act on?
- How should the system be evaluated against a generic assistant baseline?

## Initial Iterations

- I1 Instructor Onboarding
- I2 Student Active Tutoring
- I3 Proactive Interaction
- I4 Learning Gap Report
- I5 Evaluation and Refinement

## Current Phase

I1 instructor onboarding is complete and approved. I2 is active under roadmap
issue #7, with execution split into sub-issues #19-#25, #34, #37, and #41. The
repository now has modular onboarding, API, and frontend boundaries plus
provider-neutral grounding contracts, approved local parsing, deterministic
chunking, evaluated BM25 retrieval, a harder BM25/dense/RRF comparison, a
versioned experimental component profile, and durable evaluation-result
governance. Retrieval v2
and evidence-sufficiency v1 both resulted in `Refine` with no replacement or
gate selected. BM25 v1 remains a provisional rollback baseline, and a successor
open-set answerability verifier is required before the smoke demo can claim
end-to-end grounding. Live generation, policy enforcement, citation validation,
and the demonstration remain Sprint 2 work. Canvas remains an optional future
source adapter.
