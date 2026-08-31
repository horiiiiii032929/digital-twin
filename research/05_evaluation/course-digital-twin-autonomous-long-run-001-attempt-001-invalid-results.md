# Autonomous long-run 001 attempt 001 invalid result

## Outcome

Attempt 001 is an operationally invalid execution. It produced no provider
request, token usage, cost, product response, hidden-gold access, or academic
quality measurement.

The candidate canary stopped before transport construction because the direct
OpenAI binding omitted the transport field that declares its already pinned
`https://api.openai.com/v1/responses` URL to be first-party. The orthogonal
local regression also referenced two test files that had moved.

## Preserved evidence

- Execution revision: `cd50278f337391e89ee8c3fc3f6fe40e3f582ecb`.
- Parent result hash: `038781a7dcd7384233621e89a0f2ff9398bca54679fc67580e84409ef212b004`.
- Grounding checkpoint hash: `6390834e8cf98510b5d91c5ec6aa1bac191f3aaaccb839f61d0275241ab86ada`.
- Provider calls / attempts: `0 / 0`.
- Reported cost: `USD 0.00`.
- Hidden gold opened: no.
- Sealed 10,000+1,000 package opened or rerun: no.

The unrestricted local ledgers remain ignored under
`reports/generated/course-digital-twin-autonomous-long-run-001/` and
`reports/generated/academic-factual-qa-grounding-selection-002/`.

## Decision

Use the one preregistered harness-only correction. Attempt 002 changes only:

1. the missing `first_party_endpoint: true` transport declaration; and
2. the two moved local-regression test paths.

It does not change cases, hidden gold, prompts, model identity, generation,
retrieval, policies, quality gates, or progression rules. Attempt 002 is the
final permitted execution attempt for this program.
