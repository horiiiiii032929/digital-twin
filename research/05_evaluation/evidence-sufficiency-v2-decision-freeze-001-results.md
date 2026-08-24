# Evaluation result: evidence-sufficiency-v2-decision-freeze-001

## Run identity

- Component: evidence-sufficiency decision data
- Status: frozen and unopened
- Date and owners: 2026-08-24, researcher confirmation and Codex validation
- Dataset: `evidence-sufficiency-v2-decision-draft-002`
- Dataset content hash: `ae367ed195a97e5144667f4936c799edcc64991a96ffbebeb505497ffc58c9df`
- Reproduction: `npm run verify:evidence-sufficiency-v2-decision-freeze`

## Result

The researcher approved all four decision-bearing boundaries:

1. multi-evidence cases require two distinct active source units;
2. modality-tagged cases evaluate derived text only;
3. active versions are authoritative and stale pairs are explicit distractors;
4. ambiguous evidence abstains while the tutoring layer may clarify.

The freeze binds the immutable 120-case draft and the four-case confirmation
packet by exact hashes. It contains 80 answer and 40 abstain cases over 40
source versions. Candidate evaluation has not opened, and no provider, local
model, private source, held-out data, or paid execution was used.

## Decision

- Outcome: **Go Deeper** to one prospectively frozen candidate comparison.
- Dataset changes after this point require a new successor identity and freeze.
- AnyHit remains an unsafe historical control and cannot be selected.
- Candidate execution, automatic selection, profile mutation, and release
  promotion remain unauthorized.
