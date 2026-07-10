# Preview Evidence Agent

## Purpose

Generate professor-reviewable response previews that compare configured tutor
behavior against generic tutor behavior and expose source evidence.

## Current status

Prototype. Preview cases are deterministic and use a local trusted-source
catalog. No live search, RAG, or model provider is called in Sprint 1.

## Inputs

- Current tutor policy.
- Policy version.
- Deterministic trusted-source catalog.
- Professor custom preview prompt and tag.

## Outputs

- Preview case.
- Configured tutor response.
- Generic comparison response.
- Source audit entries.
- Warnings.
- Evidence snapshot.
- Preview acceptance blockers.

## Guardrails

- Configured response is the release candidate; generic response is only a
  comparison.
- External grounding must carry visible source labels.
- Rejected previews block release until accepted or resolved by revision.
- A professor custom prompt must be added and accepted before release.

## Evaluation

- Preview generation tests.
- Evidence snapshot tests.
- Preview decision API tests.
- Manual preview review flow.

## Open work

- Replace scripted responses with provider-backed generation after deterministic
  tests define expected behavior.
- Add source-conflict checks once retrieval is available.
- Add richer preview tags for assignment-specific evaluation.
