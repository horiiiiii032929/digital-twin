# Evaluation result: deployable-product-foundation-v8-current-image-attempt-001

## Run identity

- Component: current container image and live product publication boundary
- Date: 2026-08-21
- Clean implementation revision: `7ff5a0e1ecaf9df9d2cc61fa92e1bdb658124fb3`
- Candidate: `a1-single-node-staging-v8-current-image`
- Data: synthetic administrator, professor, student, course, generated PDF,
  ingestion job, onboarding policy, and draft release
- Boundary: no private or held-out data; zero model/provider calls; USD 0
- API image: `sha256:a78a99e17e3a5b2bdba52aa6c490ca7aa532df9b46b2b9c9f136840360cde929`
- Web image: `sha256:242c39320e0acbee5f014854c430014501a716cbb7d055ca9884ad468f644028`

## Decision question

Can the current post-correctness code build as pinned containers and complete
the documented clean administrator-to-professor-to-student HTTPS workflow
without substituting a test-only component?

## Result

Docker Desktop recovered after one controlled restart. Both current images
built from their digest-pinned bases, and a new `digital-twin-v8` Compose
project created isolated runtime and Caddy volumes. API, worker, and web
containers became healthy through local Caddy HTTPS.

The first clean attempt exposed an independent packaging defect: the API image
did not include the documented administrator bootstrap, backup, restore, or
lifecycle entrypoints. The image was corrected to copy only those exact
operational scripts rather than the broad `scripts/` tree. Focused
configuration tests passed, the clean images rebuilt, and all four operational
commands returned their in-container help successfully. Administrator
bootstrap then completed without emitting the generated process-only password.

The live journey proceeded through credentialed account creation, course and
student assignment, course-bound professor setup, source ingestion, and release
preflight. Publication then failed closed with HTTP 409 and code
`evidence_sufficiency_required` because the active release profile has no
selected evidence-sufficiency method. This is the intended product boundary
recorded by `evidence-sufficiency-v1-clean`, not a container transport error.
The any-hit gate used by the 42/42 in-process verifier is explicitly a
synthetic control and is not eligible for product publication.

The containers remained healthy after the refusal. A scan of the bounded
container logs found no authorization header, password field, or generated
credential marker. Observed steady-state memory after the failed journey was
263.1 MiB for API, 73.92 MiB for worker, and 21.37 MiB for web; these are
diagnostic local measurements, not an SLA.

## Interpretation correction

V7's 42/42 result remains valid for the mechanics exercised by its injected
synthetic evidence gate. It does not establish that the current product profile
can publish a release. Statements that the in-process publication check proved
a releasable configuration are therefore narrowed prospectively by this
result. Historical records and hashes are unchanged.

## Decision

- Outcome: **Refine; select no current release candidate.**
- Keep the exact operational-script image fix.
- Keep product publication fail closed; do not configure `AnyHitEvidenceGate`
  as a production shortcut.
- Design a prospective evidence-sufficiency successor as open-set
  answerability classification, with source-linked truth, near-domain
  negatives, multi-evidence cases, calibration, and false-answer/false-
  abstention gates.
- Do not repeat the public-host walkthrough until a selected evidence gate is
  bound into the same immutable profile and images.

## Limitations and next gate

The verifier did not emit a partial JSON result because the HTTP 409 raised
before its final write; the command failure, image identities, clean revision,
container health, and sanitized refusal code are retained here. The journey
used synthetic data, deterministic generation, local Caddy trust, and one
development machine. It establishes neither public TLS nor real-source answer
quality. The next decision-bearing work is the evidence-sufficiency successor,
not another container prompt or host retry.
