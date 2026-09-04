# Corpus confirmation 027 (invalid attempt)

## Outcome

**Invalid execution.** 282 of 670 responses were persisted, then the run failed
with `ActualProductEvaluationError: direct transport canary binding drifted`.

Hidden gold was never opened for this package.

## Cause

Operator error, not a code defect.

`_transport_canary_totals` recomputes the run binding before every case and
compares it to the binding stored in the direct transport canary. That binding
includes `code_revision` from `_git_revision()`. The operator committed the
preceding result records while this run was executing, HEAD changed, and the
comparison failed at case 282.

The check behaved exactly as designed: it exists to detect the code changing
underneath a running evaluation, and it did. Weakening it to tolerate a
mid-run commit would remove a real integrity guarantee, so nothing in the
harness is changed.

## What did complete

- 282 of 670 responses persisted
- 793 provider calls, exact returned model `gpt-5.6-luna`
- 396,487 input and 75,751 output tokens, USD 0.17019860
- Hidden gold unopened

## Correction

Operational, and recorded on the successor instrument as an explicit
constraint: no git operation may run while an evaluation is executing, and the
working tree must be clean with HEAD stable before execution starts.

## Decision

Revoke 027 and draw no quality conclusion. Because the package's hidden gold
has still never been opened across 026 and 027, bind that identical unopened
public and gold payload to one further attempt,
`governed-full-autonomy-v2-1-corpus-confirmation-028`, with no code change at
all.

## Limitations

Public synthetic sources and personas. No release, quality, or safety
conclusion is drawn from a partial ledger.
