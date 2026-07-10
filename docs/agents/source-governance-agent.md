# Source Governance Agent

## Purpose

Track which course and external sources the Digital Twin may use, how those
sources are labeled, and whether any source must remain excluded.

## Current status

Prototype. Implemented as metadata-only source inventory. The prototype records
file name, MIME type, byte size, permission status, source label, sensitivity
flag, and notes. It does not read file contents.

## Inputs

- Course-material metadata from the browser file picker.
- Professor permission decisions.
- Source labels:
  - `course-approved`
  - `professor-approved-external`
  - `system-suggested-trusted`
  - `unapproved-external`

## Outputs

- Source inventory item.
- Source inventory release blockers.
- Source labels used by preview evidence.

## Guardrails

- Do not parse, embed, summarize, upload, or store local file contents in Sprint
  1.
- Sensitive-looking names default to excluded unless explicitly documented.
- Pending sources block release until approved or excluded.
- Source labels must be visible in preview evidence.

## Evaluation

- Source inventory create/update API tests.
- Sensitive-source default tests.
- Release blocker tests.
- Manual source metadata review.

## Open work

- Define a permission record before ingesting real materials.
- Add source versioning and deletion behavior.
- Add retrieval-quality checks once real ingestion exists.
