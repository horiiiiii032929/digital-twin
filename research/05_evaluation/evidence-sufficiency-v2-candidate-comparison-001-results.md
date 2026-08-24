# Evidence-sufficiency candidate comparison 001

## Decision

**Refine; select no method.** The execution was valid, but none of the three
selectable methods passed the frozen quality gates. Authorization is revoked.

## Execution

- Clean revision: `1da528e7974c9f96f8b1e17c98373adf50e3744a`
- Dataset: corrected frozen 120-case synthetic-public draft 002, opened once
- Distribution: 80 answerable and 40 abstain cases across nine slices
- Retrieval: fixed course-scoped active/approved BM25 top five, without gold
  evidence injection
- Local models: GTE ModernBERT reranker revision
  `f7481e6055501a30fb19d090657df9ec1f79ab2c` and DeBERTa-v3-base NLI revision
  `6c749ce3425cd33b46d187e45b92bbf96ee12ec7`
- Provider calls and paid cost: zero
- Private or held-out data: none

## Results

| Method | False answers | Answer recall | Balanced accuracy | Mutation detection | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| AnyHit unsafe control | 39 | 100.0% | 51.3% | 5.0% | Unselectable / fail |
| Inspectable feature control | 0 | 8.8% | 54.4% | 85.7% | Fail |
| GTE support verifier | 7 | 15.0% | 48.8% | 91.7% | Fail |
| GTE + DeBERTa NLI | 7 | 15.0% | 48.8% | 91.7% | Fail |

The learned candidates stayed below the 500 ms p95 and 2 GiB added-memory
gates, but quality failed decisively: both produced seven false answers, only
15% answer recall, zero multi-evidence recall, 20% near-domain accuracy, and
seven citation-lineage failures. The NLI augmentation produced no aggregate
quality improvement.

## Direct priority audit

Codex reviewed all 12 prioritized cases against the frozen questions, source
text, required lineage, retrieved hits, and per-candidate signals.

- Five cross-course and two near-domain abstentions were correctly labelled;
  learned verifiers accepted generic or lexically tempting same-course passages.
- Two valid direct answers exposed the lexical control's low recall.
- Two valid direct answers exposed the learned ambiguity proxy; pairwise NLI
  also created false contradiction signals across independent evidence passages.
- One clean direct-answer control passed all selectable methods.

No ground-truth or harness defect was found. This is a method-level failure.
Threshold tuning against the now-opened decision split would invalidate the
prospective comparison, so these exact candidates will not be retried.

## Operational evidence and limitations

- GTE support p95: 188.0 ms; added peak memory: 464,060,416 bytes
- GTE + NLI p95: 244.7 ms; added peak memory: 491,700,224 bytes
- Raw ignored result file SHA-256:
  `a622612c41f20268c7943bdd70ebfef5a2f9d9074edab1df6b77b40db58a4976`
- Canonical result SHA-256:
  `26b80b1e1a3d0ce4a92460d6c14e66f7382267184819eb97e450bb865db38da6`

The memory measurement reflects this macOS process and lazy model loading. The
comparison isolates answerability under fixed BM25 rather than evaluating the
selected production retriever. Because no method passed, no product profile,
deployment, or release claim is authorized.

## Next decision

Do not start another model or prompt search. Reframe the product boundary at a
method level: evidence sufficiency should validate a proposed answer's atomic
claims against retrieved evidence, rather than infer answerability from an
interrogative query and passages alone. That successor requires a new issue,
development data, and prospective confirmation split; it must preserve this
unfavorable result unchanged.
