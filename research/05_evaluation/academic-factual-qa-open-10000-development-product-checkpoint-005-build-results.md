# Mixed-wording T0 product checkpoint 005 build result

## Outcome

`Go Deeper` to one separately authorized 500-case T0 candidate plus 100-case
paired any-hit control run. The successor reuses the immutable wording result
from checkpoint 004: 452 accepted model-written questions and 48 explicit
canonical fallbacks. It makes no new wording calls.

This is build and network-free simulation evidence. It is not a product-quality
result and does not authorize the untouched 10,000-case evaluation.

## Method

- The committed product-visible package contains exactly 500 public cases and
  records whether each question came from the accepted model wording or the
  deterministic canonical fallback.
- Every fallback is checked byte-for-byte against its canonical public source
  question. The materializer also verifies the immutable checkpoint-004 result
  and content hashes before it can construct the package.
- The candidate and control use the same corpus, hybrid retriever, exact
  `gpt-5.4-mini-2026-03-17` generator, policy, and decoding. They differ only in
  the evidence gate: structured lexical coverage versus any-hit release.
- Product execution receives only course ID and question. Hidden source-linked
  gold opens only after both response ledgers are durably complete.
- Exact `gpt-5.4-2026-03-05` performs a non-blocking post-score audit of every
  deterministic failure plus a seeded passing sample. Deterministic source,
  action, claim, citation, boundary, and policy checks remain authoritative.

The checkpoint permits at most 500 candidate calls, 100 control calls, and 54
advisory calls. It has zero retries and an aggregate USD 18 emergency ceiling.
All provider and final-execution authority remains false in this build.

## Evidence

- Package composition is exactly 452 accepted model variants plus 48 canonical
  fallbacks, with zero new wording calls.
- Candidate and control packages contain 500 and 100 cases respectively; the
  control is the fixed paired subset.
- Five network-free terminal simulations cover Keep, product-quality failure,
  provider failure, malformed advisory review, and a potential truth defect.
- The response executor cannot import the hidden-gold package. The scoring
  process checks both durable ledgers before opening gold.
- Atomic resume bindings include instrument, provider binding, candidate,
  control, provenance, system manifests, and code revision hashes.
- Package re-materialization and product execution both fail closed under the
  repository-wide execution freeze.
- Official OpenAI model, pricing, Responses API, and retention metadata were
  refreshed on 2026-08-28 for both exact dated model snapshots.

## Limitations and next action

- No provider call, token use, paid cost, private-data read, product-quality
  measurement, or final-split access occurred.
- The development set is a known benchmark because its earlier wording result
  informed this prospective composition decision.
- GPT-5.4 and GPT-5.4 mini are separate configurations from one provider
  family; advisory review is disclosed and cannot establish independent ground
  truth.
- A valid development quality failure will stop scaling for one method-level
  decision. It will not trigger another wording or reviewer tuning loop.
- A development pass will prepare a separately frozen 10,000-case checkpoint;
  it will not authorize that run.

The next action is an explicit authorization for
`academic-factual-qa-open-10000-development-product-checkpoint-005` after its
clean live no-call preflight.
