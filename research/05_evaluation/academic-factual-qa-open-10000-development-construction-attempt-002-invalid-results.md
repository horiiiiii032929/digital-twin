# Open 10,000 factual-QA development construction — attempt 002

Result ID: `academic-factual-qa-open-10000-development-construction-attempt-002-invalid`

Decision: **Invalid execution / Refine malformed-output handling**

The clean, authorized run started from revision `84ed851` against the frozen
AFQC-035 source plan and provider binding 002. Both provider canaries passed:
DeepSeek returned the exact `deepseek-v4-flash` slug with runtime fingerprint
`a26a7955944dc5c60445bff77fac9c8e`, and Gemini returned the exact
`google/gemini-3.7-flash` slug through Google AI Studio at the pinned `default`
service tier.

The first bulk DeepSeek author response was valid JSON but used an `items`
array instead of the required `questions` array. Deterministic schema
validation rejected it. The run stopped before the first verifier call and
before any development cluster was accepted.

The ledger records three completed provider responses: two canaries and one
bulk author call. Total reported usage was 2,206 input tokens, 477 output
tokens, and USD 0.00213626. No retry occurred. Zero of 100 development
clusters and zero of 500 development cases were accepted. No product response,
final case, hidden final gold, private course source, or student information was
opened.

This is an operationally invalid construction attempt and says nothing about
question quality or T0 product quality. It also exposed a prospective harness
gap: although the frozen design requires malformed author output to be
quarantined and replaced by explicitly labelled deterministic wording, the
runner terminated the whole construction and left its raw ledger status as
`interrupted`. Any successor must implement and test that preregistered fallback
without accepting the malformed provider shape.

The ignored exclusive ledger is
`data/interim/academic_factual_qa_open_10000_v1_development_construction_attempt_002.sqlite3`
with SHA-256
`fa8a7302f0fbe6873b11fb3c51415946cb364a4d8f30199809555a194df99e69`.
The ignored source plan has SHA-256
`a1bc0211cfdfc4f22adb87b989454bd019065b1662df96dbaa23064db6a53f92`.

Attempt 002 authorization is revoked. The sealed 10,000-case execution remains
unauthorized.
