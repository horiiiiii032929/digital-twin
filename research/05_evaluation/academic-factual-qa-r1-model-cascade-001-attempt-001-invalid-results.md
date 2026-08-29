# R1 model cascade — attempt 001

Result ID: `academic-factual-qa-r1-model-cascade-001-attempt-001-invalid`

Decision: **Invalid execution / one harness-only correction**

The authorized cascade started from clean revision `99b7665`. The committed
preflight incorrectly reported the retrieval index as ready because it checked
only that the root directory existed. The directory contained no binding
pointers or immutable artifact manifests, so the first product arm stopped
before case 1 when the fresh runtime verified its release-bound index.

This is an index-readiness harness defect, not a product-quality result. The
provider ledger contains zero calls and zero cost. No response, hidden-gold,
control, advisory, final-10,000, private-data, or public-tunnel stage opened.

The ignored attempt directory is preserved as
`reports/generated/r1-model-cascade-001-attempt-001-invalid/`. The provider
ledger SHA-256 is
`19632e1fc820c9544827302f8ca78ead2f38ceb27d87ff3d426a7a34fd1e2c67` and
the product-state database SHA-256 is
`c988607e0705133468710c5e354f7dc56cb476b09016461d40ee7421d550c2ae`.

AFQC-085 changes only readiness detection: four binding pointers and four
immutable manifests must exist before the preflight can report `ready`;
otherwise the already-authorized local materializer builds them. Attempt 002
uses a fresh output directory and code revision. A further harness correction
is not automatic.
