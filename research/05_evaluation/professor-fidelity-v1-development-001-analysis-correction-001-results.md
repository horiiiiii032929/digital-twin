# Professor-fidelity development analysis correction 001

Date: 2026-08-10

Correction ID: `professor-fidelity-v1-development-001-analysis-correction-001`

Source run: `professor-fidelity-v1-development-001`

Decision: **Refine; source run invalid for selection, keep held-out unopened,
and do not claim professor fidelity.**

## Answer first

All 192 provider attempts completed, so the preserved outputs are useful as an
operational trace and as diagnostic failure examples. They are not valid
evidence for selecting the professor policy or the selected M2 product
condition.

The audit found defects beyond the original denominator and citation-label
errors:

- the v1.1 cases had no independent human authoring review;
- C2 and C3 received each case's expected action and tutoring moves, leaking
  gold rubric labels into the prompt;
- C3 used ad hoc `pdftotext` character windows instead of the selected
  page-bounded heading/paragraph chunker;
- the run omitted the condition-set hash, exact retrieved-passage identity,
  and a hash-frozen shared policy/prompt binding; and
- the local judge and lexical semantic score did not follow the frozen
  contracts.

The corrected audit therefore makes no C0-C3 effect or professor-fidelity
claim. It preserves `Refine`, makes no profile change, and keeps the 104-case
course-tutor held-out split unopened.

## Corrected diagnostic measurements

These values describe the preserved outputs only. They are not selection
eligible because the dataset and condition bindings fail before quality is
considered.

| Condition | Structural success | Action | Citation-ID validity | Source/page correctness | Claim-source coverage | Exact evidence@3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C0 | 6/48 (12.5%) | 35/48 (72.9%) | 18/48 (37.5%) | 0/30 (0%) | 0/30 (0%) | 0/30 (0%) |
| C1 | 35/48 (72.9%) | 40/48 (83.3%) | 48/48 (100%) | 30/30 (100%) | 25/30 (83.3%) | 30/30 (100%) |
| C2 | 44/48 (91.7%) | 48/48 (100%) | 48/48 (100%) | 30/30 (100%) | 26/30 (86.7%) | 30/30 (100%) |
| C3 | 23/48 (47.9%) | 47/48 (97.9%) | 48/48 (100%) | 13/30 (43.3%) | 19/30 (63.3%) | 0/30 (0%) |

The C3 exact-evidence result is zero because none of its ad hoc chunk IDs and
hashes matched the selected chunker passages named by the source benchmark.
Its source/page evidence proxy was 19/30 (63.3%), but a page match cannot be
promoted to exact-passage retrieval. Similarly, claim-source coverage means
only that the response cited a source/page associated with every required
claim. It is not semantic citation completeness.

Safe-grounded success, true citation completeness, reviewed presented-context
sufficiency, and pedagogy remain unresolved. Structural success is a
deterministic diagnostic, not a substitute for those judgments.

## Diagnostic contrasts

The recomputed structural contrasts are retained only to make the historical
outputs auditable:

- C1 − C0: +60.4 points (95% paired-bootstrap interval +43.8 to +75.0;
  Holm-adjusted exact McNemar p<0.000001).
- C2 − C1: +18.8 points (+8.3 to +31.2; adjusted p=0.003906).
- C3 − C2: −43.7 points (−58.3 to −29.2; adjusted p=0.00000286).
- C3 − C0: +35.4 points (+18.8 to +52.1; adjusted p=0.000443).

No causal or selection interpretation is allowed. The apparent C2 action gain
is especially contaminated by gold expected-action leakage.

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| Human authoring review | Fail | v1.1 mechanical/Codex checks were mislabeled `double_review` |
| Selected retriever and chunker identity | Fail | C3 used a different corpus/chunk construction and recorded no complete binding |
| Condition-set hash bound | Fail | The source run omitted `conditions_sha256` |
| Shared policy/prompt hash bound | Fail | The source run embedded case gold labels and recorded no policy hash |
| Zero C3 deterministic hard-gate failures | Fail | 23/48 passed; 25 failed at least one deterministic gate |
| Semantic support resolved | Fail | 11 structurally passing C3 answers still require blinded semantic review |
| C3 safe-grounded success ≥80% | Unresolved / fail closed | Semantic review incomplete |
| C3 exact complete evidence@3 ≥80% | Fail | 0/30 exact selected-passage matches |
| C3 citation source/page correctness ≥95% | Fail | 13/30 (43.3%) |
| C3 semantic citation completeness ≥95% | Unresolved / fail closed | No eligible blinded response review |
| Pedagogy resolved and ≥80% | Fail | Earlier judge contract drifted; no eligible blinded reference |
| Reliable completion ≥95% | Pass | 192/192 attempts completed |
| C3 p95 latency ≤10 seconds | Pass | 1.758 seconds under the shared nearest-rank definition |
| Held-out isolation | Pass | Existing course-tutor and multimodal held-out ledgers remain unopened |

## Corrective implementation

Analysis and boundary revision
`3c61f563c15439f26fb4a801438510d0e38227b7`:

- recomputes scores from the hash-matched dataset and preserved outputs;
- requires exact passage IDs and content hashes for complete evidence while
  retaining source/page recall only as a labeled proxy;
- separates citation-ID validity, source/page correctness, structural
  claim-source coverage, semantic alignment, and true citation completeness;
- fails selection when dataset review, condition hash, selected
  retriever/chunker identity, or policy/prompt binding is absent;
- removes all case gold labels from future C0-C3 prompts and freezes one shared
  policy/prompt binding by hash;
- uses the selected page-bounded heading/paragraph chunks for both authoring
  evidence and future C3 retrieval;
- records exact passage identity, condition hash, policy hash, provider
  failures, and unconditional denominators in future runs;
- changes new datasets to review-only v1.2 drafts and requires a completed
  non-Codex human review before an immutable v2 seal can be created;
- prevents preflight from parsing held-out content and transitions the
  one-time ledger before any held-out parse; and
- uses condition-blinded semantic/citation/pedagogy review plus frozen
  per-dimension pairwise judge contracts.

The v1.2 48-case development and 104-case held-out authoring drafts were built
successfully with exact selected-chunk identities. No v2 seal or held-out
ledger was created. Private development and held-out review packets plus a
hash-bound 152-case checklist are prepared under ignored
`reports/generated/course-tutor-v1.2-authoring-review/`. Human authoring review
is the next required decision point.

### Subsequent authoring-QA amendment — 2026-08-12

The statement above established mechanical chunk identity, not semantic
claim-to-passage correctness. The later registered
[`course-tutor-v1.2.1-authoring-cross-review-001`](course-tutor-v1.2.1-authoring-cross-review-001-results.md)
found 90 case-level issues plus a dataset-wide lineage defect in draft 001.
That draft is preserved privately and dropped. Corrected draft 002 is now the
only candidate for independent human review; no seal or held-out tutor-output
ledger exists.

### Second authoring-QA amendment — 2026-08-12

The draft-002 conclusion above was subsequently superseded. The registered
[`course-tutor-v1.2.3-authoring-cross-review-002`](course-tutor-v1.2.3-authoring-cross-review-002-results.md)
found additional privacy, split-isolation, source-version, evidence-necessity,
and semantic defects in drafts 002 and 003. Both were preserved privately and
dropped. Draft 004 is now the only candidate for independent human review; no
seal or held-out tutor-output ledger exists.

## Multimodal boundary

The historical C0-C3 run was text-only. It did not use visual page rendering,
OCR, diagrams, layout descriptions, or image embeddings. The separate
multimodal development study evaluated those methods, selected no multimodal
profile, and kept its 24-case held-out split unopened. This correction does not
change that stop decision.

## Reproduction

The historical analyzer command used for this correction is retired and must
not be confused with the prospective v2 analyzer. The durable result and
machine record remain reproducible evidence. Current integrity verification
requires no provider call and no held-out content access:

```bash
npm run verify:evaluation-results
npm run verify:professor-fidelity-post-audit
npm run check
```

The ignored generated audit is
`reports/generated/professor-fidelity-v1-development-001-analysis-correction-001.json`.
The sanitized component record is
[`records/professor-fidelity-v1-development-001-analysis-correction-001.json`](records/professor-fidelity-v1-development-001-analysis-correction-001.json).

## Claim boundary

This correction establishes only that the provider path completed reliably and
that the historical evaluation was not selection-valid. It does not establish
safe grounding, professor-like pedagogy, a policy effect, selected-retriever
quality, citation completeness, learning outcomes, usability, student
readiness, multimodal support, or deployment approval.
