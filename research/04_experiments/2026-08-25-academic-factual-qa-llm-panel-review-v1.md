# Academic factual-QA LLM-panel review v1

Date: 2026-08-25

Status: sources, 200 cases, 40 controls, and blinded packet built; reviewer
execution and researcher audit unopened

Owner issue: [#127](https://github.com/horiiiiii032929/digital-twin/issues/127)

Instrument: `academic-factual-qa-confirmation-002`

## Decision

Use a three-family blinded LLM panel plus a bounded researcher audit because an
external 200-case human review is not feasible within the project schedule.
Preserve confirmation 001 as the unexecuted external-human design. Confirmation
002 replaces it before any source content, case label, or provider call was
opened.

This is not a claim that several LLM votes become human ground truth. The
reference is described as a **deterministic, source-derived, LLM-panel-reviewed,
researcher-audited silver benchmark**.

## Why this can still answer the factual-QA question

Most reference fields are objective and source-derived: source eligibility and
version, source IDs, evidence offsets, the boundary transform, expected action,
atomic claim IDs, and canonical answer. Code creates these fields before model
review and models cannot edit them. The panel evaluates semantic validity:
whether the question is understandable, answerable from the supplied sources,
faithful to the constructed claims, and correctly assigned to its boundary.

This role separation is important because LLM judges exhibit position,
self-preference, superficial-quality, and leniency biases. Multiple judges also
make correlated errors, so nominal panel size cannot be treated as independent
sample size. The design therefore requires deterministic checks, blinded
independent votes, planted controls, unanimity for automatic acceptance, a
researcher audit, and explicit claim limits.

Primary references informing these controls:

- [Humans or LLMs as the Judge? EMNLP 2024](https://aclanthology.org/2024.emnlp-main.474/)
- [Benchmarking Cognitive Biases in LLM Evaluators, ACL Findings 2024](https://aclanthology.org/2024.findings-acl.29/)
- [Judging the Judges, GEM 2025](https://aclanthology.org/2025.gem-1.33/)
- [Nine Judges, Two Effective Votes, 2026 preprint](https://arxiv.org/abs/2605.29800)

The last source is a recent preprint and is used only to motivate the correlated-
error caveat, not as settled evidence.

## Reviewer panel

Each reviewer receives the same blind packet containing only the eligible source
excerpt(s), source/version identifiers, question, and response fields needed by
the rubric. Reviewers cannot see the product condition, answer model identity,
canonical labels, other votes, or researcher decision.

| Reviewer | Family | Coverage | Role and limitation |
| --- | --- | ---: | --- |
| Isolated Codex task reviewer | OpenAI | 200 | Primary semantic audit in a fresh task receiving only the blinded packet. It is not API-snapshot reproducible; model-family design involvement remains disclosed. |
| Mistral Small 4 (`mistral-small-2603`) | Mistral | 200 | Independent primary semantic vote through exact OpenRouter routing with fallback disabled, subject to fresh metadata and identity checks. |
| DeepSeek V4 Pro (`deepseek-v4-pro`) | DeepSeek | 200 | Adversarial sensitivity vote through the official API. It shares a vendor family with the product generator, so that dependence is reported and it never acts as a sole tie-breaker. |

The Mistral and DeepSeek identities reflect the official
[Mistral Small 4 model card](https://docs.mistral.ai/models/mistral-small-4-0-26-03)
and [DeepSeek model list](https://api-docs.deepseek.com/api/list-models/)
checked on 2026-08-25. They must be checked again within 24 hours of any
execution. The Codex reviewer must run in a fresh isolated task because the
design task constructed the source and control artifacts and therefore cannot
honestly be called blinded. It is not a substitute name for an OpenAI API
model. If an exact API reviewer later replaces it, that change requires a new
instrument revision. Current official OpenAI guidance identifies
GPT-5.6 Terra as the cost/capability-balanced API option, but it is not silently
substituted for the Codex task reviewer and no OpenAI API call is part of this
protocol.

## Calibration before reviewing confirmation cases

All three reviewers first receive the same 40 blinded, source-linked controls:
20 clean cases and 20 cases with planted action, claim, citation, ambiguity, or
boundary defects. Controls are disjoint from the 200 confirmation cases.

Each reviewer must achieve at least:

- 90% action accuracy;
- 90% mutation sensitivity;
- 90% specificity; and
- 90% citation-defect sensitivity.

A failed reviewer contributes no confirmation votes. Replacing or repairing a
reviewer requires a new version; confirmation cases remain unopened until the
panel passes calibration.

## Consensus and researcher audit

Deterministic validation runs first. A case is accepted automatically only when
all deterministic checks pass and all three blinded reviewers agree on its
semantic action and raise no claim, evidence, citation, ambiguity, or boundary
objection. A 2–1 vote is not treated as truth.

The researcher reviews:

1. every disagreement; and
2. a seeded balanced sample of 20 unanimous cases—10 answerable and 10 boundary.

If more than 40 of 200 cases disagree, the panel fails rather than creating an
unbounded researcher workload. The researcher packet therefore contains at
most 60 cases. Original votes and rationales remain immutable before the
researcher disposition.

The panel is acceptable only if:

- unanimous semantic agreement is at least 80%;
- action Krippendorff alpha is at least 0.67;
- no reviewer fails calibration;
- the researcher finds zero critical errors and no more than one material error
  in the fixed unanimous sample; and
- every disagreement receives a recorded disposition.

Pairwise action agreement, claim-set F1, exact evidence-link agreement,
confusion matrices, slice disagreement, and reasons for disagreement are always
reported. Confidence scores are descriptive only.

## Product decision and claim ceiling

The original product gates remain unchanged. Passing every deterministic,
product, panel, and researcher-audit gate permits a provisional method decision:
`Keep with LLM-panel and researcher-audit caveat`, and permits design of the
separate 600-case final tranche. It does not establish:

- independently human-annotated ground truth;
- private-course external validity;
- professor teaching fidelity;
- student learning outcomes;
- human usability; or
- production release readiness.

The professor report must state exactly how truth was constructed, which model
families reviewed it, how many cases the researcher audited, disagreement and
calibration results, and that correlated judge errors remain possible.

## Built source and packet checkpoint

The bound build contains 160 non-overlapping section sources: 120 used by the
100 confirmation clusters and 40 used only by calibration. The 200 confirmation
cases comprise 100 answerable and 100 boundary cases across the preregistered
strata. The 40 controls comprise 20 clean and 20 planted defects. Raw public
repositories remain ignored; the committed manifest binds exact revisions,
licenses, section ranges, file/section hashes, and local dependent assets.

Network-free simulations prove reviewer calibration failure, malformed output,
identity/resume drift, and more than 40 disagreements fail closed. A clean
simulation produces the fixed balanced 20-case researcher packet. Simulation
is harness evidence only and is not a review result.

## Current stopping boundary

Source download and deterministic construction are complete and their temporary
authority is closed. This checkpoint authorizes no Codex review, provider call,
spending, private source, confirmation product execution, researcher audit,
final tranche, product binding, or release promotion.
