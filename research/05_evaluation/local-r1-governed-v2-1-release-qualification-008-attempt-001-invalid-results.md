# Local R1 governed V2.1 release qualification 008 attempt 001

## Decision

`invalid-execution`. The exact R1.2 candidate passed its fresh 25-check HTTPS
journey and six restart checks, but the offline backup command could not start
without an inference credential. No backup/restore or rollback result is
claimed from this attempt.

The failure exposed a release-operations defect: bootstrap, backup, restore,
and lifecycle commands instantiated the full runtime credential validator even
though they never construct a provider client. This contradicted the runbook's
credential-independent backup and recovery contract.

## Evidence

| Check | Result |
| --- | ---: |
| Fresh HTTPS journey | 25/25 |
| Restart persistence | 6/6 |
| Backup | Not started; configuration rejected |
| Clean restore | Not started |
| T0 rollback / V2 restoration | Not started |
| Provider calls / cost | 0 / USD 0 |

The failure occurred on clean source revision
`660381f0d198cf3cc27ead7e39791041a14fb2e0`. The known 10,000+1,000 package was
not read, rerun, or rescored.

## Corrective boundary

One root-cause successor may make offline administrative settings validation
credential-independent while retaining every origin, profile, qualification,
lineage, path, and staging safety check. The product runtime and workers must
continue to require their configured provider credentials. The successor must
start from a new clean revision and a fresh isolated Compose project.
