# Deterministic open factual-QA development package

Result ID: `academic-factual-qa-open-10000-deterministic-development-001-build`

Decision: **Keep the build / product execution unauthorized**

The prospective AFQC-044 method replaces unreliable model-owned dataset
construction with deterministic, source-linked truth for the development split.
It does not rewrite attempts 001–003. The implementation at
`fdf571ce99eaaa451e97bb2fa27533cf2ae07483` constructed exactly 500 public
development cases and 500 separate hidden-gold rows from the frozen 100 public
source clusters. A fixed 20-cluster subset supplies 100 paired control cases.

The historical deterministic v1 control derived all 500 rows without provider
calls but left four normalized duplicate questions. The selected v2 package
contains 400 answerable and 100 boundary cases. Every answerable
row has exact source-range claims; every boundary row has empty evidence
lineage and an explicit reason. Case IDs and normalized questions are unique,
public cases contain no answer, action, claim, citation, or boundary gold, and
two rebuilds produced the same package content hashes. No provider call,
private source, final case, product response, token, or cost was involved.

The first v2 validation caught 15 questions whose generated cue repeated the
full canonical answer. The prospective cue logic was corrected before any
package was written, and the final leakage count is zero. This demonstrates the
value of the fail-closed check; it is not evidence of product quality.

The canonical questions are deterministic development templates. They are
adequate for harness and retrieval-path validation but are not treated as final
evidence of natural student wording. Future model output may paraphrase wording
and provide advisory review only; it cannot modify actions, answers, claims,
citations, boundary reasons, or source lineage.

A provider-neutral first-party transport is also build-verified for exact
OpenAI `gpt-5.4-mini-2026-03-17` and Mistral `mistral-small-2603` bindings. The
OpenAI dated snapshot is retained instead of an unversioned latest alias so a
future run can be reproduced. Strict schema validation, exact model identity,
transport-only retry, durable retry accounting, cost reservation, and direct
endpoint selection pass network-free tests. Provider metadata, credentials,
retention terms, and authorization must be checked again before execution.

Limitations:

- this is dataset-build evidence, not a 500-case Digital Twin result;
- deterministic wording is intentionally mechanical and still needs separately
  evaluated natural-language paraphrasing;
- the final 10,000 cases remain unconstructed and sealed;
- no external human annotation or independent semantic product audit occurred.

The next stop is a clean, separately authorized 500-case candidate plus
100-case control development execution after the direct-provider decision and
credentials are available. The 10,000-case final run remains unauthorized.
