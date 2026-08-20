# Repository correctness dependency remediation — 2026-08-19

Status: complete security remediation; retrieval quality remains unevaluated

## Decision

Keep the remediated dependency lock for prospective work. Do not reuse the old
retrieval compatibility decision for the upgraded stack: historical runs remain
bound to their recorded versions, while every prospective retrieval method and
profile remains unqualified until the repository correctness freeze passes and
a new evaluation is authorized.

## Changes

- `torch`: 2.9.1 to 2.13.0
- `transformers`: 4.57.6 to 5.15.1
- `sentence-transformers`: 5.2.0 to 6.0.0
- Optional retrieval dependencies remain outside the production image.
- The temporary nine-finding exception list is closed with zero active
  exceptions.

The versions were resolved from the current PyPI package metadata and locked by
uv. No retrieval benchmark, model inference, provider call, private source read,
or held-out access occurred.

## Verification

- `uv lock --upgrade-package sentence-transformers --upgrade-package torch --upgrade-package transformers`
- `npm run audit:python`: zero known vulnerabilities; zero exceptions
- `npm run audit:js`: zero vulnerabilities
- Clean runtime API and frontend container builds with digest-pinned bases

This is a dependency-security result, not evidence that retrieval behavior is
equal to or better than the historical stack.
