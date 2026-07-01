# Student Tutoring Agent

## Purpose

Provide student-facing tutoring responses that follow the professor-approved
tutor policy and cite only approved or explicitly labeled sources.

## Current status

Planned. No student-facing tutoring implementation exists in Sprint 1.

## Inputs

- Approved tutor policy.
- Approved source inventory and retrieval results.
- Student question.
- Course context allowed by consent and source permissions.

## Outputs

- Student-facing tutor response.
- Visible source labels or citations.
- Refusal or redirect when the request violates policy.
- Optional learning-gap signal for later aggregation.

## Guardrails

- Do not answer with unapproved private or student data.
- Do not complete graded work when the policy disallows it.
- Stay within course scope and source strictness mode.
- Make uncertainty and source limitations visible.
- Do not release until professor approval status is `approved`.

## Evaluation

- Policy compliance tests.
- Academic-integrity refusal tests.
- Citation/source-label tests.
- Instructor review of sample conversations.

## Open work

- Define retrieval interface and citation format.
- Add conversation storage and retention policy.
- Add student privacy and consent checks.
- Build a minimal active tutoring UI.

