# Atomic-claim confirmation interpretation correction 001

Result ID:
`evidence-sufficiency-v3-atomic-claim-confirmation-001-analysis-correction-001`

Date: 2026-08-25

Status: Complete retrospective analysis; no model or evaluation rerun

Decision: **Go Deeper. Retain the NLI boundary as a provisional development
candidate, but revoke the production-method interpretation and do not bind it
to the release profile yet.**

## Why the interpretation changes

The 120 recorded rows are generated from ten fact groups crossed with twelve
fixed templates. They are therefore clustered contract checks, not 120
independent samples of realistic product claims and evidence.

The observed counts remain correct:

- zero releases among 80 reject rows;
- 38/40 supported drafts retained;
- 18/20 multi-claim drafts retained; and
- complete mutation, lineage, and malformed-contract rejection.

Under an optimistic independent-row assumption, the two-sided exact 95%
intervals are approximately 83.1%–99.4% for supported retention and
68.3%–98.8% for multi-claim retention. Zero false releases among 80 rows has a
one-sided 95% upper bound of approximately 3.7% (approximately 4.5% for the
upper endpoint of a two-sided interval). Repeated templates within fact groups
violate that independence assumption, so these intervals overstate the
effective information in the dataset.

The direct Codex review confirmed consistency with the frozen synthetic
contract. It was not an independent annotation study. The run also bypassed
real product retrieval and generation, so it did not test the distribution of
claims that the Digital Twin will actually produce.

## Claims that remain valid

The result remains useful as a development contract test showing that, on its
frozen synthetic cases, the implementation:

- directs NLI correctly with evidence as premise and claim as hypothesis;
- fails closed on invalid lineage, malformed output, and planted mutations;
- operates within the measured local latency and memory bounds; and
- retains more paraphrased supported claims than the exact-quote control.

## Corrected decision boundary

The candidate is no longer selected for product binding. Issue #105 returns to
`Go Deeper` until the validator is evaluated inside the actual T0 product path
using independently constructed, source-linked examples and realistic
generated claims. Product release authority, T1 promotion, deployment, private
sources, and human use remain closed.

The successor evaluation must report cluster-aware uncertainty, include enough
independently validated supported and unsupported cases to estimate false
release and retention, and preserve the exact-quote fail-closed control.

## Provenance and limitations

- Source result: `evidence-sufficiency-v3-atomic-claim-confirmation-001`.
- Source execution revision: `c9208cb`.
- Source raw-output SHA-256:
  `95ea159e7c13982905754f6c97cd2ce17a437ae5a09296c515c9bdbb1cd30256`.
- Analysis inputs: committed instrument, runner, synthetic generator, result
  summary, and priority-review packet.
- Provider calls, paid cost, private-data access, and held-out access for this
  correction: zero.

The original result and decision remain immutable historical evidence. This
record supersedes only the current selection and generalization claim.
