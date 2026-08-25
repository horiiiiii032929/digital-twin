# Academic factual-QA end-to-end pilot 001 build

Result ID: `academic-factual-qa-end-to-end-pilot-001-build`

Date: 2026-08-25

Status: Complete build-only checkpoint; development execution unauthorized

Decision: **Go Deeper. The leakage-free T0 harness is ready, but neither
control is selectable and the atomic-claim candidate plus independent gold data
are still missing.**

## Decision question

Can the repository evaluate the actual T0 product path without passing expected
answers, actions, claims, source IDs, or citations into the system under test?

## Build evidence

The development dataset contains:

- 160 synthetic-public cases across eight courses;
- 32 materially distinct source units;
- 80 answerable and 80 boundary cases;
- 80 explicit source/question clusters, with at most three rows per cluster;
- direct, paraphrase, multi-source, no-evidence, cross-course, ambiguous, and
  academic-integrity slices; and
- zero exact normalized duplicate questions.

It is explicitly `development-synthetic-unblinded`, is not independently
validated, and is not a final evaluation split.

The runner uses the normal `StudentTutoringService` in T0 mode, the selected
retriever with its BM25 fallback, normal generation contract, citation
validation, persistence, and course/release authorization. A strict product
input schema permits only case identity, request identity, course identity, and
the question. Gold fields remain evaluator-only until after the response has
been persisted.

## Network-free diagnostic simulation

Two deliberately unselectable controls exercised all 160 cases:

| Condition | Action accuracy | Unsupported release | Supported retention | Complete expected claims | Citation precision | Citation recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| T0 fail-closed control | 25.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| T0 any-hit control | 68.8% | 60.0% | 100.0% | 80.0% | 96.3% | 88.1% |

Cluster-bootstrap 95% intervals were 15.0%–35.4% and 57.9%–80.0% for the two
action-accuracy estimates. The any-hit unsupported-release interval was
42.5%–76.3%. These intervals describe only this clustered development fixture;
they are not academic estimates of product performance.

Retrieval recovered all declared required sources in both conditions. The
any-hit control nevertheless failed all 16 multi-source cases on complete
expected-claim and citation coverage because the deterministic generator used
only one retrieved passage. The fail-closed control released nothing. The
any-hit control made 48 unsupported releases, including every no-evidence case,
14/16 ambiguous cases, and 10/16 cross-course cases. Persistence was consistent
for all 320 condition-case rows.

## Validity and boundaries

- Gold fields crossing the system input boundary: 0.
- Provider calls, tokens, and paid cost: 0.
- Private or held-out data read: false.
- Independent gold claimed or opened: false.
- Method selected: false.
- Product binding or release promotion: false.

Claim precision and semantic factual F1 are intentionally unavailable in this
deterministic simulation. They require independently validated reference claims
and a separately qualified scoring protocol.

## Next checkpoint

Issue #105 must integrate the provisional atomic-claim candidate behind the
same T0 product boundary. Issue #127 must then add independently validated,
source-linked data while preserving the input firewall. Only a separately
frozen development execution may compare the candidate with these controls.
The 1,000- and 10,000-case stages remain closed.
