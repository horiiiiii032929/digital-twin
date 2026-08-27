# Fair factual-QA evaluation loop

Date: 2026-08-25

Status: frozen development protocol; confirmation and final execution closed

Owner issue: [#127](https://github.com/horiiiiii032929/digital-twin/issues/127)

## Research question

For the same student questions, course-scoped corpus, retrieval profile, and
generated drafts, does a two-boundary release method reduce unsupported answers
and incomplete citations without materially reducing supported-answer
retention relative to T0?

The two boundaries answer different questions:

1. Before generation, does the selected evidence address the student's
   question and remain inside the authenticated course scope?
2. After generation, is every factual claim supported by its declared,
   server-owned evidence lineage?

Post-generation entailment alone is insufficient: an irrelevant claim may be
entailed by an irrelevant passage. Pre-generation evidence sufficiency alone is
also insufficient: a generator may omit required evidence or introduce a new
claim.

## Units, data, and label tiers

The independent unit is a source and question-family cluster, not an individual
paraphrase. Report row counts and cluster counts together. Ten thousand
template-related rows are operational coverage, not 10,000 independent academic
observations.

- Development data may be synthetic, unblinded, and repeatedly used to correct
  code or method defects. It must never be described as independent gold.
- Confirmation data must be frozen before use, independently source-validated,
  and unavailable to method development.
- Final data must use fresh source/question clusters and remain unopened until
  the method and numeric gates are frozen.
- Automated and multi-model agreement is advisory. The full set may be called
  source-linked or silver only. A gold or reference anchor requires independent
  human validation with documented adjudication.

## Paired estimand and ablations

Each eligible case is run through:

- T0 any-hit control;
- T0 plus question-to-evidence selection;
- T0 plus the same selection and post-generation atomic-claim validation.

Case IDs, corpus, retriever, policy, and generator are fixed. The selection-only
and two-boundary arms must have identical draft hashes wherever generation is
permitted. Report paired changes in unsupported-release rate,
supported-answer retention, action accuracy, claim completeness, citation
precision/recall, latency, and safe-fallback frequency. Cluster-bootstrap 95%
intervals are reported for the primary proportions.

## Prospective gates

Development gates detect integration and method defects; passing them permits a
fresh confirmation but cannot select or promote the method. Confirmation gates
must be frozen before the split opens and include:

- zero severe unsupported releases in the human-calibrated anchor;
- 100% source/version-valid citations for released answers;
- prespecified minimum claim precision, claim recall, citation completeness,
  supported-answer retention, and boundary-action accuracy;
- zero exact duplicate questions and reported near-duplicate clusters;
- complete malformed-output, identity, latency, token, cost, and persistence
  accounting.

Thresholds must be justified by product risk and interval precision, not chosen
after observing the confirmation result.

## Failure and revision rule

A failed result blocks promotion, not development.

1. Preserve and register the result.
2. Classify the cause as data, label, retrieval, evidence selection, generation,
   claim validation, citation, policy, integration, or operational.
3. Correct only on development data.
4. Re-run development comparisons and retain every attempt.
5. Freeze one successor and evaluate it once on a fresh confirmation split.

If confirmation or final evaluation fails, do not tune on that consumed split.
Make an explicit method-level decision and create a new version with fresh
clusters. A poor result is therefore evidence for revision, not a reason to
declare the research complete.

## Current stopping boundary

`academic-factual-qa-end-to-end-pilot-002` is limited to the existing 160-case
synthetic-public development set. It cannot establish academic effectiveness,
open private sources, select a product component, authorize 1,000/10,000-case
execution, or promote T1. The next academically meaningful checkpoint is one
clean, separately authorized confirmation on independently validated, fresh
source/question clusters.
