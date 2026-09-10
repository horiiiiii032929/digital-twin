# Post-report final selection 002

Status: prospective plan, 2026-09-08. This reopens final selection after the
bounded B1–B6 engineering pass; that pass did not establish the best candidate.
Submitted report artifacts remain unchanged.

## Decision and prediction

Can a cheaper explicitly versioned audited candidate improve delivered tutoring
against the incumbent while preserving course isolation, policy and recovery?
First repair the external review instrument: separate exact evidence locations
from semantic ratings. Predict that Mini's previously correct 64/64 raw control
labels will survive a valid evidence contract. Previous strict failures remain
failures and are not retroactively rescored into passes.

## Instrument comparison

Retain blind-review-001 as control. Version 002 uses the same five semantic axes,
overall rating and 32 synthetic calibration cases repeated twice, but evidence is
an exact string paired with a JSON pointer into the supplied payload. This permits
response, source and citation evidence without confusing their provenance.
No changing gold labels or dropping cases. Missing-content defects may have no
excerpt. Require 64/64 valid matching controls before using ratings for selection.
Mini first; at most one Nano calibration with the same contract if needed. A failed
calibration blocks model-based promotion, not preservation of diagnostic results.
Record format validity, axes, false acceptance/rejection, repeats, latency, tokens,
cost, source hashes and all raw failures. No human validity or learning claim.

## Product comparison and selection

Freeze a separately named cheap-role candidate before live execution; never
silently substitute the Sol role in V19. Use the same current-turn inputs,
materials, profiles and history for incumbent and candidate. Include exposed
regression cases separately from new synthetic transfer cases, normal explanation,
misconception, Socratic obligation, missing evidence, source-state questions,
permission/adversarial requests and provider failure. Freeze packet, exact models,
seeds, call caps and thresholds before execution in a supplemental configuration.
Keep the incumbent if the candidate fails hard gates or improvement is inconclusive.
No additional Sol calls. Total external budget remains US$30, cumulative ledger
including previous US$1.5567143. Every run reserves its worst-case budget first.

## Completion checklist

- [ ] Repair and calibrate the versioned reviewer, retain prior failures.
- [ ] Freeze and compare incumbent and explicit cheap candidate; record selection.
- [ ] Verify selected API and worker configuration through the complete journey.
- [ ] Inspect existing decision/history UI; fill missing explanation and state links.
- [ ] Verify stop, withdrawal, isolation, timeout, restart and duplicate suppression.
- [ ] Record selected runtime latency and cost; no inferred learning effectiveness.
- [ ] Polish actual demo screens and reproducible multi-person virtual-time recording.
- [ ] Update implementation diagrams, comparisons and slides from verified evidence.

Local regressions use synthetic fixtures, injected provider failures and persisted
restart state. Reuse unaffected checks. Record limits and remaining work honestly;
no claim of global optimality, human usability validation or completed presentation
until those deliverables have actually been inspected.

## Candidate implementation freeze before development

Name: `v19-luna-luna-medium`. Identical V19 routing, typed draft, repair bounds and
V2 final audit prompts; planner and draft use gpt-5.6-luna low, revision/audit use
gpt-5.6-luna medium, all caps 3000. This is an explicit experimental variant,
not a replacement of `v19-luna-sol-medium`. Prediction: lower audit cost, possibly
more quarantine or missed defects. Exact role identity must be checked in transport,
audit acceptance and delivered provenance. The Sol variant and default release
remain unchanged. The variant is not selected by merely passing contract tests.

## One bounded instrument correction after 002

Run 002 Mini produced 51/64 strict matches; 12 results used exact numeric values
at valid citation/source pointers that the string-only validator rejected, and
one exceeded the five-evidence-item limit. Additionally this plan was extended
while the run was active, triggering source drift. Preserve the run as invalid
for selection. Version 003 explicitly permits exact canonical JSON scalar values
(numbers, booleans, null) at evidence pointers and repeats the existing five-item
limit in the prompt. Arrays/objects and mismatched numeric values remain invalid.
No gold/semantic-gate changes. Execute one further 64-control Mini calibration,
then at most one Nano calibration if needed, without editing frozen files during
either run. This is an instrument correction, not a product improvement claim.
