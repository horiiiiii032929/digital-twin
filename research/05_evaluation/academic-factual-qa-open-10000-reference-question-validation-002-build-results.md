# Reference-question validation 002 build result

## Outcome

**Go Deeper (build only).** One prospective successor now aligns the OpenAI
Structured Outputs contract with the existing local author-response invariant.
The provider schema requires every generated question to match `\\?$`, while
the local Pydantic validator continues to require the normalized question to
end in `?`.

Attempt 001 remains immutable and invalid. This successor uses new instrument,
binding, ledger, result, and materialized-package identities. It does not import
the seven completed attempt-001 calls.

## What changed

- Added the terminal-question-mark pattern to the strict provider schema.
- Parameterized the runner by immutable attempt identity and fresh output paths.
- Added explicit attempt-002 validate, simulate, preflight, execute, resume,
  score, and materialize commands.
- Added regressions proving attempt 001 stays unchanged, attempt 002 enforces
  the provider/local invariant, and attempt 002 is blocked without authority.

No source, case, hidden gold, prompt, model snapshot, acceptance threshold,
quota, call ceiling, retry policy, or cost ceiling changed. OpenAI documents
string `pattern` as supported by Structured Outputs.

## Verification

- Fresh pool: 160 source-disjoint candidate clusters / 800 cases.
- Network-free selection: exact 100 complete clusters / 500 cases.
- Focused tests: 8 passed.
- Provider calls: 0.
- Product calls: 0.
- Private or sealed-final data opened: no.
- Paid/provider execution: unauthorized.

## Decision and limits

Attempt 002 is ready for a separately authorized reference-question validation
run, subject to fresh provider metadata and a clean live preflight. This build
does not establish question quality, T0 product quality, readiness for the
10,000-case run, Professor Digital Twin fidelity, or deployment readiness.

The next paid action requires the exact authorization:
`Authorize academic-factual-qa-open-10000-reference-question-validation-002 paid run.`
