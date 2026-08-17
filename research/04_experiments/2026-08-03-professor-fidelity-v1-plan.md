# Professor fidelity and pedagogy v1 plan

Date: 2026-08-03

Run status: first development source run invalid for selection; corrected v2
boundary implemented; private authoring drafts 001-003 rejected or superseded;
corrected v1.2.3 draft 004 awaiting independent human review; held-out tutor
outputs unopened.

Instrument: [`professor_fidelity_v1.json`](../05_evaluation/instruments/professor_fidelity_v1.json)

## Status amendment — 2026-08-07

The selected M2/BM25 product boundary, citations, course isolation, and
provider-failure fallback now pass the bounded synthetic student workflow. The
prospective generator qualification ran on official DeepSeek V4 Flash in
non-thinking JSON mode. Direct P0 and conservative P1 failed citation
correctness. Strict-evidence P2 passed every 48-case development floor, all 36
stability attempts, and all 104 attempts in the authorized one-time synthetic
held-out run. Its complete first review and frozen 20-case second review passed.
The exact generator and P2 prompt are selected in the experimental profile;
the second pass was Codex-delegated rather than independent human judgment.

The private `course-tutor-v1` development and held-out sets and judge
calibration remain incomplete.
No sealed professor-fidelity tutor output has been generated.

## Status amendment — 2026-08-10

The first private C0-C3 development source run completed 192/192 provider
attempts, but its result is invalid for selection. The audit found:

1. the v1.1 cases had no independent human authoring review;
2. C2/C3 prompts contained case expected actions and tutoring moves;
3. C3 used ad hoc text windows rather than the selected page-bounded chunker;
4. exact passage IDs, the condition-set hash, and a shared policy/prompt hash
   were not recorded; and
5. citation completeness, semantic grounding, and judge contracts were
   misinterpreted or unresolved.

The correction is registered as
`professor-fidelity-v1-development-001-analysis-correction-001`. It preserves
the outputs, makes no profile change, and keeps held-out unopened.

The v2 implementation removes case gold labels, binds one shared policy and
integration prompt by hash, uses the selected chunker corpus, records exact
passage hashes and the condition hash, fails provider errors into the
unconditional denominator, and prevents held-out parsing before the one-time
ledger transition. A 48-case development plus 104-case held-out v1.2 authoring
draft was built successfully with exact selected-chunk evidence. It created no
seal and no held-out ledger; a completed non-Codex human authoring review is
required next.

## Status amendment — 2026-08-12

Codex cross-reviewed all 152 private authoring cases and their exact approved
lecture evidence without opening tutor outputs or the blinded condition
mapping. The initial prediction that only isolated edits were needed failed.
Draft 001 contained systematic false-misconception, wrapper-paraphrase,
lecture-mismatched ambiguity, unrelated multi-evidence, broken lineage, and
semantic claim-to-page defects inherited from the invalid rapid retrieval
instrument. Case-level advisory triage was 43 clear, 19 uncertain, and 90
issues; the draft was preserved privately and dropped.

Corrected draft 002, version `course-tutor-v1.2.1`, treats the rapid instrument
only as an inventory and explicitly curates every positive question, atomic
claim, and approved page. Deterministic checks and a second semantic advisory
pass report 133 clear cases, 19 uncertain no-evidence cases, and no unresolved
LLM-detected issue. The 19-case private focus packet includes local lexical
nearest-neighbor diagnostics. This remains `codex_assisted: true`, is not human
approval, creates no seal or ledger, and does not waive independent review of
all 152 cases. The result is registered as
`course-tutor-v1.2.1-authoring-cross-review-001`.

## Second authoring-QA amendment — 2026-08-12

An independent second pass invalidated the draft-002 `133 clear / 19 uncertain`
conclusion. The tracked builder contained private source-derived authoring
content, development and held-out shared nine exact approved passage
identities, multi-evidence cardinality did not establish passage necessity,
and the permission/version negative control did not represent a conflicting
superseded version. Several multi-evidence claims also exceeded their exact
pages.

Intermediate draft 003 repaired those classes but deeper family-by-family
inspection found one answer-bearing past-assessment source and three incomplete
or overbroad atomic claims. Those findings are preserved privately and draft
003 was dropped.

Draft 004, version `course-tutor-v1.2.3`, keeps the private authoring blueprint
ignored, has zero exact approved-passage and authored-family overlap across
splits, removes the assessed-answer source, binds all 114 required factual
claims to approved citation identities, and uses a true excluded
superseded-version conflict in all 19 permission cases. Expanded advisory
triage is 114 clear, 38 uncertain, and 0 detected issues. The 38 uncertain cases
are exactly the 19 no-evidence and 19 multi-evidence cases. Independent human
review of all 152 cases remains mandatory. The result is registered as
`course-tutor-v1.2.3-authoring-cross-review-002`.

## Decision question

With question, course scope, generator, decoding, output schema, and evidence
lineage held constant, does an explicit professor policy improve safe grounded
tutoring behaviour over generic tutoring policy? Separately, what quality and
operational loss is introduced when approved oracle evidence is replaced by
the selected M2 retrieval profile?

This is a bounded course-specific evaluation. It does not estimate learning
outcomes, human usability, student satisfaction, adoption, or universal model
quality.

## Current prediction

- C1 should improve safe grounded task success over C0 because it receives
  approved course evidence.
- C2 should improve professor-policy pedagogical success over C1 when evidence
  and generator are unchanged.
- C3 should approach C2 but may lose complete-evidence success, claim coverage,
  or citation completeness because retrieval can return partial context.
- Any applicable hard-gate failure dominates quality averages and prevents a
  selection claim.

## Conditions

| ID | Evidence | Policy | Role |
| --- | --- | --- | --- |
| C0 | None | Generic tutoring | Generic assistant baseline |
| C1 | Researcher-approved oracle evidence | Generic tutoring | Grounding upper-bound without professor policy |
| C2 | The same oracle evidence | Structured professor policy | Policy contribution control |
| C3 | Selected M2 hybrid retrieval, or BM25 rollback if M2 is unavailable | The same structured professor policy | Product-profile condition |

The exact condition identities and allowed data boundaries are frozen in the
machine-readable instrument. C4, the all-approved-documents control, remains
conditional and is not part of this required first run.

## Dataset and split discipline

Use the researcher-verified `course-tutor-v1` portfolio:

- 12 anchor cases for judge and instrument calibration;
- 48 development cases for runtime and rubric checks; and
- 104 sealed held-out cases for the final paired comparison.

The eight scenario types are direct explanation, paraphrase, misconception,
multi-evidence synthesis, ambiguity, no evidence, assessed-work pressure, and
permission/version conflict. The held-out split is opened once, through a
one-time ledger, after every runtime binding and threshold is frozen.

Private course text, derived passages, and tutor outputs remain ignored local
artifacts. Durable records contain hashes, configuration, aggregate metrics,
redacted failures, and no course wording.

## Generator and policy freeze

The deterministic grounded generator remains the structural control. The
sealed R2 comparison cannot begin until one exact non-control generator and
prompt binding is qualified. The current Gemma result is exploratory and did
not select a generator or prompt; it cannot be silently promoted.

The generator binding must record model/provider, immutable revision, prompt
version, decoding, output schema, provider data boundary, timeout, cost cap,
and deterministic fallback. The same binding is used for C0-C3.

C0 and C1 use the generic tutoring policy. C2 and C3 use the same approved
`structured-professor-policy-v1`. Policy changes create a new instrument
version rather than modifying this one in place.

## Measurements

### Primary outcomes

- unconditional safe grounded task success over all cases;
- professor-policy pedagogical success on applicable cases;
- complete-evidence success@3;
- citation identity and locator validity; and
- no-evidence accuracy.

### Diagnostics

Report required-claim recall, supported-claim precision, contradiction and
unsupported-claim counts, misconception repair, academic-integrity action,
answer-revelation control, judge calibration, latency, tokens, cost, provider
failures, fallback activations, and scenario/topic slices.

### Hard gates

Fail the applicable case or run for permission/course-scope leakage, inactive
source use, citation identity failure, unsupported high-severity claims,
assessed-work violations, secret or private-data leakage, malformed output,
timeout without bounded recovery, unapproved external course processing, or a
missing ledger record. A quality gain cannot compensate for a hard-gate
failure.

## Failure classification

Every failed case is classified as one or more of data, parsing, chunking,
query, retrieval, context sufficiency, generation, prompt, policy, citation,
judge, simulator, integration, or operational failure. A missing output stays
in the unconditional denominator. Invalid simulated trajectories are reported
separately and are never regenerated or hidden.

## Analysis and decision

Use 10,000 paired bootstrap replicates with seed 5002, exact McNemar tests for
predeclared paired binary contrasts, and Holm correction across the primary
contrasts. Report raw numerators and denominators, intervals, invalid counts,
slice counts, representative favorable and unfavorable cases, operational
measurements, and limitations.

The decision order is lexicographic: hard gates, quality floors, operational
limits, paired effects, then complexity and reversibility. The possible
outcomes are Keep, Refine, Go Deeper, or Drop. A no-selection result preserves
the deterministic generator and BM25 rollback.

## Reproduction commands

Validate the frozen instrument without opening private data:

```bash
npm run verify:professor-fidelity-plan
```

Prepare a sanitized run manifest from a locally approved development or
held-out dataset and its condition file:

```bash
uv run python scripts/run_professor_fidelity_experiment.py \
  --dataset data/processed/course_tutor_v1/sealed_v2/development.json \
  --conditions data/processed/course_tutor_v1/sealed_v2/development_conditions.json \
  --split development \
  --dry-run \
  --output reports/generated/professor-fidelity-v1-preflight.json
```

The manifest command is validation-only. The separate execution adapter now
fails closed unless the exact generator, selected retriever/chunker, frozen
policy/prompt, reviewed v2 dataset, condition hash, credential, and output
boundary are present. Development output may be generated before judge
calibration, but it cannot become decision evidence until eligible blinded
semantic and pedagogical review is bound.

## Known blockers before a corrected development run

1. Human-confirm the 38 no-evidence and multi-evidence focus cases, then
   independently review all exact-passage v1.2.3 authoring cases without using
   the Codex advisory as an automatic approval.
2. Create the immutable v2 development/held-out seal and unopened ledger.
3. Run corrected development once with the hash-bound v2 adapter.
4. Complete condition-blinded semantic, citation, and pedagogy review and judge
   calibration.
5. Register a valid development result and pass every prospective floor before
   considering the one-time held-out opening.
