# Local R1 governed V2.1 release qualification 009 attempt 001

## Decision

`invalid-execution`. The exact final-profile environment completed all 43
surface checks, but the API log showed that governed T1-v2 restoration rejected
a region-bearing LangGraph checkpoint. The HTTP path failed closed, so this is
not a safety release; however, it also means the run cannot support the claimed
node-level restart consistency.

## Evidence

| Check | Result |
| --- | ---: |
| Fresh HTTPS journey | 25/25 |
| Restart surface checks | 6/6 |
| Clean restore | 6/6 |
| T0 rollback | 3/3 |
| Governed restoration surface checks | 3/3 |
| Internal checkpoint log audit | Failed |
| Provider calls / cost | 0 / USD 0 |

The first journey invocation also used the verifier's historical default
profile and was correctly rejected before execution. Supplying the exact final
profile fixed that operator error, but the subsequently completed run exposed
the independent serializer defect.

## Root cause and correction boundary

Live document chunks carry `RegionKind.TEXT`. The T1-v2 checkpoint serializer
allowed `SourceCitation` but omitted the nested `RegionKind` enum, while the
existing restart fixture used `region_kind=null`. The only permitted correction
is to add that enum to the allowlist, extend the existing interrupt/restart test
with a region-bearing citation, rebuild immutable images, and rerun the exact
qualification once on a fresh Compose project.

No private data or known 10,000+1,000 benchmark data was used.
