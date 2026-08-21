# Factual-QA v3 deterministic truth successor plan

Date: 2026-08-21

Issue: #87

Status: build complete; professor guidance and paid pilot authorization pending

## Decision question

Can a method-independent deterministic source and claim layer support a
trustworthy 10,000-case dummy dataset while limiting LLMs to optional wording
and advisory review?

## Working answer

Use deterministic truth as the authoritative default. This remains valid if the
professor later prefers multiple LLMs for canonical generation: model-generated
wording can change, but actions, claims, answers, citations, and acceptance are
still checked against source-derived truth.

## Frozen composition

- 20 synthetic courses, 1,000 sources, and 8,000 claims.
- 10,000 cases: 8,000 answerable plus 2,000 boundary cases.
- Boundaries: 500 no-evidence, 500 ambiguous, 500 cross-course confusion, and
  500 academic-integrity cases.
- Cross-course confusion must abstain and carry no authoritative lineage.
- No Academia Vault, professor, student, credential, private path, or held-out
  content.

## Method

1. Build canonical questions, answers, actions, claim structures, exact source
   quotes, citations, boundary reasons, and hashes deterministically.
2. Permit the author model to return only `question_variant`.
3. Reject normalized duplicates, report near-duplicates, and preserve malformed
   output before deterministic canonical fallback.
4. Use qualified Mistral Small 4 only for question faithfulness and naturalness.
5. Use DeepSeek V4 Pro only for at most 24 unresolved semantic disputes.
6. Keep deterministic checks authoritative over every model verdict.

## Staged progression

Pilot 003 remains provider-unauthorized. After professor-method interpretation
and explicit authorization, execute exactly 100 cases. A full pass may lead to
a separately frozen 1,000-case checkpoint. Only a passing 1,000-case result can
lead to the final 9,000-case completion stage. There is no automatic promotion
and no repeated sequence of prompt-only 100-case refinements.

## Separate Professor Digital Twin track

Factual correctness, citations, safety, and boundaries are hard gates. C0-C3
then isolates professor policy and retrieval effects using fixed questions,
generator, decoding, and applicable evidence. Teaching style, depth, examples,
misconception handling, and integrity are rated separately against a
professor-approved profile. The calibration packet remains unopened until the
professor advises on profile setup.

## Freshness and stopping rules

Every external-information-dependent checkpoint must refresh the branch, PR,
issues, Project, registry, freeze, exact model slugs, revisions, prices, limits,
routing, and retention terms. Provider metadata older than 24 hours blocks paid
execution. A changed or mismatched model requires a new frozen instrument and
network-free verification.

Stop for the first genuinely external decisions: professor-method
interpretation and explicit paid pilot-003 authorization. No private, paid,
held-out, 1,000-case, or 10,000-case execution is authorized by this plan.
