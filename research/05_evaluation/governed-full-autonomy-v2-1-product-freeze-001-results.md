# Evaluation result: governed-full-autonomy-v2-1-product-freeze-001

## Run identity

- Component: governed autonomous tutoring V2.1 development candidate
- Date: 2026-08-31
- Base revision: `cfd38fea5ad69925a3ab9d090c62e1540a00585a`
- Execution state: candidate working tree; dirty state disclosed
- Instrument SHA-256:
  `3bbfda8d1e2f21bf4136dc2b27201182dda4acf6d8596c7ce28e92827c980471`
- Candidate implementation manifest SHA-256:
  `c83d147be564ab619a36c7e0cd3267a0a87b7d7945874669a1778000528594c5`
- Boundary: network-free, provider-free, synthetic, no private or sealed-final data
- Machine record:
  `research/05_evaluation/records/governed-full-autonomy-v2-1-product-freeze-001.json`

## Decision question

Does the V2.1 candidate implement a finite, restart-safe, policy-governed loop
that can initiate cited in-app tutoring without per-message professor approval?

## Method

The run first applied the deterministic action router to 500 fresh development
cases: 400 answerable, 50 abstain, 25 clarify, and 25 refuse. It then operated
one synthetic learner goal for seven simulated days. Each due event started one
finite graph job. The test restarted the repository after day two, linked a
student reply to the originating action and goal, withdrew consent, and copied
the SQLite database into a clean restore.

The planner and wording generator were deterministic development
implementations. No provider was called. The known Program 011 final package
was not opened.

## Result

The development execution passed every frozen gate:

- action routing: 500/500 correct;
- seven finite jobs completed across seven simulated days;
- three cited messages delivered, then four `no-action` outcomes enforced the
  three-message weekly limit;
- zero invalid citation lineage, duplicate messages, or duplicate actions;
- restart state, response-to-goal linkage, consent-withdrawal termination, and
  backup/restore state were consistent;
- no job exceeded one planning proposal or one generation attempt; and
- provider calls, tokens, and cost were zero.

## Decision

Outcome: **Go Deeper**.

Keep V2.1 as the implementation candidate and retain T1-v1/T0 as controls and
rollback. This result is sufficient to continue integration and prospective
provider-backed evaluation. It does not promote V2.1 into the release profile,
close the grounding blocker, or establish teaching quality.

## Limitations

- The seven-day learner, evidence, professor profile, and responses are
  synthetic.
- Routing accuracy is fresh development evidence, not a held-out confirmation.
- The run tests control, persistence, lineage, and termination; it does not
  estimate professor fidelity, student usability, learning outcomes, or natural
  LLM response quality.
- The UI was separately inspected on desktop and mobile, but no external user
  participated.
- Program 011 remains the authoritative unfavorable 10,000+1,000 actual-product
  factual result.
