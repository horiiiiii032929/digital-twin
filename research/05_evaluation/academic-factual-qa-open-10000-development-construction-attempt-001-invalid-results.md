# Open 10,000 factual-QA development construction — attempt 001

Result ID: `academic-factual-qa-open-10000-development-construction-attempt-001-invalid`

Decision: **Invalid execution / Refine provider identity binding**

The clean, authorized run started from revision `3dbc4ed` against the frozen
AFQC-035 source plan. The first DeepSeek V4 Flash canary returned the requested
model name but a runtime revision fingerprint different from the preregistered
fingerprint. The exact-identity guard rejected it before the Gemini canary or
any of the 100 development clusters ran.

The executor recorded one failed canary, zero accepted provider responses, zero
bulk calls, zero generated cases, and no reported token or cost data. The
absence of provider usage fields is recorded as unavailable, not as proof of
zero provider billing. No final case, hidden final gold, private course source,
or student information was opened.

This is an operationally invalid attempt and says nothing about question
quality or T0 product quality. The ignored exclusive ledger is
`data/interim/academic_factual_qa_open_10000_v1_development_construction.sqlite3`
with SHA-256
`5952b5573f0e164d28f3f6465c5d0150828236603c308d5f2dc4b81310a89d2b`.
The ignored source plan has SHA-256
`a1bc0211cfdfc4f22adb87b989454bd019065b1662df96dbaa23064db6a53f92`.

Attempt 001 authorization is revoked. A prospective successor may keep the
exact documented model slug and record the runtime fingerprint as diagnostic
metadata, because the provider does not expose a separately pinnable
fingerprint in its model registry. It requires a new immutable binding, fresh
ledger, clean preflight, and separate paid authorization. The sealed 10,000
cases remain unauthorized.
