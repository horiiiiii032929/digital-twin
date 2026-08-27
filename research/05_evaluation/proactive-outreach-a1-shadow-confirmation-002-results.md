# Evaluation result: proactive-outreach-a1-shadow-confirmation-002

## Run identity

- Component: proactive tutoring trigger
- Date: 2026-08-27
- Clean execution revision: `c41b68062235c348a4ada13d7c1de43bd61a8d7a`
- Candidate: deterministic evidence-recovery A1, publication-integrated shadow mode
- Control: fixed no-autonomous-outreach policy
- Data: 60 synthetic cases from 12 source clusters and four computing families
- Executed instrument SHA-256:
  `07f2faa9180fb70d0d9f3c6d896f9a7100f542c9db3c9b43599efc79e61cbf42`
- Ignored generated result:
  `reports/generated/proactive-outreach-a1-shadow-confirmation-002.json`
- Generated result SHA-256:
  `7227aba41d51cae5f2f859eb10dd498c05f275280dee2453955549b3a2e64e6a`
- Boundary: local synthetic data only; zero network, provider, paid, private-data,
  real-student, or external-delivery operation

## Decision question

Does the publication-integrated A1 shadow loop detect newly supportable prior
no-evidence turns across multiple computing topics while preserving no-action,
publication, consent, lineage, idempotency, and zero-delivery boundaries?

## Method

The immutable instrument defined 12 source clusters across operating systems,
networking, data structures, and Python. Each cluster produced a direct
supported question, a paraphrased supported question, an unsupported adjacent
question, an unchanged-lineage question, and one rotating suppression case.
This yielded 24 expected proposals and 36 expected no-actions.

For every case, the runner persisted a prior no-evidence turn under an earlier
release and published a new synthetic release through the normal publication
service. The post-publication hook then invoked A1 in shadow mode. A1 searched
only genuinely new source lineage with BM25 and applied the frozen raw-token
lexical-coverage gate. The runner separately checked hook ordering, exactly-once
invocation, rollback exclusion, redacted failure handling, publication
durability, suppression, lineage, and the absence of triggers, messages, outbox
items, providers, private reads, and deliveries.

## Result

The clean execution completed as `completed-refine`:

- 59/60 actions and reasons matched the frozen labels (98.33%);
- 23/24 supportable questions were detected and all 36 no-action cases remained
  suppressed;
- all 23 observed proposals used valid current-release source lineage;
- all 60 publications completed and all 12 integration checks passed;
- persisted shadow triggers, messages, outbox items, provider calls, tokens,
  cost, private-data reads, and external deliveries were all zero.

One valid method failure occurred in
`ds-hash-collision-paraphrase-supported`. The evidence says that separate
chaining stores colliding entries in a bucket list, while the question asks
where entries that collide are stored. Retrieval returned the correct source,
but the raw-token gate matched only 4 of 9 query terms (44.44%), below the
frozen 50% threshold. Inflection changes such as `store`/`storing` and
`collide`/`colliding`/`collisions`, plus unmatched query terms, exposed the
method's lack of morphological or semantic normalization. The system failed
closed and sent nothing, so this was a conservative missed opportunity rather
than an unsupported release.

## Decision

- Outcome: **Refine** the A1 evidence-support method.
- Keep professor-scheduled A0 outreach as the release control.
- Keep A1 in shadow mode and do not select active A1 or Discord delivery.
- Do not lower the lexical threshold or rerun this same confirmation set.
- A method successor should compare a deterministic normalized lexical baseline
  with a bounded semantic-support candidate on fresh, independently sourced
  opportunities while preserving deterministic lineage and suppression
  authority.

The one-time network-free authorization was revoked after the result was
persisted.

## Limitations and next gate

The cases are synthetic and deliberately stratified rather than an independent
sample of student interactions. They establish publication integration,
fail-closed behavior, source lineage, and suppression mechanics; they do not
establish intervention usefulness, interruption burden, learning outcomes,
professor fidelity, production scheduling reliability, or external-channel
delivery quality.

Any successor evaluation must use a new run identity and fresh cases. Real
student data, active delivery, provider-composed messages, and external channels
remain separately approval-gated.
