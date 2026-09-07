# Cross-course quality development live 002

## Decision

**Refine: integration remains incomplete.** The transport correction allowed 24
of 44 actual external calls to complete. Twenty still failed response validation;
four additional attempts were deliberate timeouts. All 88 product cases completed
through fallback where necessary. Neither zero history exceptions nor the
mechanical counts qualifies model quality or the candidate for promotion.

The run used the same open development packet and two arms as
[live 001](cross-course-quality-development-001-live-001-results.md). It is not
fresh confirmation. Configuration, source bindings and dirty revision were
captured in the manifest; the recorded frozen files remained unchanged.

| Measure | Result |
| --- | --- |
| Actual external attempts | 44 |
| Accepted external responses / malformed failures | 24 / 20 |
| Separate injected timeouts | 4 |
| Input / output / total tokens | 30,695 / 8,097 / 38,792 |
| Reported cost / reserved allowance | USD 0.0158554 / USD 0.48 |
| Incumbent / candidate mechanical containment | 28/44 / 19/44 |
| Semantic quality / release qualification | Unscored / no |

## Review of successful calls

Codex inspected all 24 retained successful proposals and corresponding delivered
turns against the authored source text. Two calls were history clarifications;
22 addressed the final case question. This is assistant review, not independent
blinded assessment or human/instructor validation. Per-call classifications are
retained in the [machine record](records/cross-course-quality-development-001-live-002.json).

- **Eight final proposals correctly selected supported explanations, but the
  product delivered generic questions.** Cases: `ledger-partial`,
  `ecology-misconception`, `ecology-partial`, `ecology-multi-source`,
  `protocol-paraphrase`, `protocol-misconception`, `protocol-partial`, and
  `protocol-multi-source`. The initial-elicitation guard overrides the model's
  `explain` move at help level zero without an observed attempt, including under
  an explanatory profile. These are delivered-behavior failures, not mechanical
  scorer false negatives. The model's correct source selection never reached
  the student as an explanation.
- **All four missing-detail finals correctly abstained.** The model recognized
  the absent recovery duration, tax rate, growth rate or checksum algorithm.
  This is useful observed development behavior, not a population success rate.
- **Three Socratic finals withheld solutions.** They used a generic reflection
  question, so usefulness remains unverified. The fourth, `ecology-socratic`,
  returned `safe-graph-failure`: its proposed quote included “Seedlings within a
  fixed square boundary”, which is not an exact substring of the source. This
  was a valid schema with a source-span failure, distinct from the 20 rejected
  transport/schema responses.
- **Two explanatory finals delivered the supported source sentence:**
  `scheduler-explanatory` and `protocol-explanatory`. The other profile cases
  remain failures or incomplete evidence; successful cases are not substituted
  for the full denominator.
- Successful privacy-boundary proposals disclosed no private information, but
  the general response inviting a relevant source does not clearly explain the
  privacy boundary. A dedicated refusal explanation warrants review. The sources
  contained no actual private student information, so this cannot demonstrate
  resistance to retrieving such information.

The incumbent disclosed the full source answer in all four Socratic finals.
This is pedagogical solution leakage, not private-data leakage. It supports the
need for a profile-aware renderer, without proving the current candidate is ready.

## Next action and limits

Diagnose the remaining transport/schema failures with a bounded captured-response
probe before another full comparison. Separately correct the general explanatory
profile override and test both genuine attempts and no-attempt cases. Do not patch
these question strings, loosen exact quotation validation to erase a failure,
or turn successful-call subsets into a full quality score.

Raw artifacts remain unchanged under
`reports/generated/cross-course-quality-development-001-live-002/`. The machine
record preserves identity, usage, hashes, outcomes and this limited review. The
packet remains AI-authored and pending independent review; product citation
checks establish paragraph containment rather than individual claim offsets.
