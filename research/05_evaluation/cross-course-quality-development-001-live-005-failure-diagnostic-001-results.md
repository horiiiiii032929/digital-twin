# Live 005 operational failure sidecar diagnostic

## Decision

**Keep a separate operational diagnostic; do not rescore quality.** All four
candidate injected-timeout cases in live 005 delivered the registered nonfactual
failure response with no citations or exposed claims. Each response is tied to
the case's recorded injected timeout and failed provider ledger entry.

The original candidate mechanical result remains **39/44**. The original gold,
responses, failure classification and ecology-fragment score are unchanged.

`provider-failure-diagnostic-v1` is implemented independently in
`scripts/provider_failure_diagnostic.py`. It accepts `safe-graph-failure` only for
the provider-failure case type, an explicit injected-timeout summary/ledger link,
empty citations/claims and the exact registered nonfactual failure template.
TutorTurn does not expose atomic claim objects; unknown response text is therefore
not accepted as claim-free. This is not a blanket mapping of every safe-looking
action into success. It does not approve the clarity of the generic error message.

The incumbent's four named provider-failure cases took deterministic paths and
never reached the injection. They cannot be counted as verified provider failure
handling. The sidecar retains that distinction.

Eight adversarial tests passed, rejecting answers, attached claims/citations,
empty or changed text, missing injection linkage, malformed-response events and
non-provider cases. This read-only analysis made zero model calls and incurred
zero cost. The [record](records/cross-course-quality-development-001-live-005-failure-diagnostic-001.json)
retains the source artifact and diagnostic-code hashes plus all eight case
observations. The source run is [live 005](cross-course-quality-development-001-live-005-results.md).
