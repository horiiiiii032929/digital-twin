# Local R1 governed V2.1 release qualification 006 attempt 001

## Outcome

`invalid-execution`. The API failed closed during startup before the live
journey, provider calls, or sealed-data access.

The release binding expected profile SHA-256
`a287db56a00714848d3b97e6e0d6fa66a9dc4acfa8547e9d61e79c10c54f7bc5`,
but the image contained
`a8e306d2b4e418a6cd97b3612fdc611674a97f714ff601beddbede940b568d9d`.

## Root cause and correction boundary

Documentation-only notes had been edited inside the immutable, hash-bound
selected profile. The startup validator correctly rejected the resulting
binding drift. This is an operational preparation defect, not product-quality
evidence.

The only permitted correction is to restore the selected profile's exact
bytes, keep explanatory updates in external status documentation, rebuild the
images, and start a fresh qualification attempt. The product method, data,
checks, thresholds, and release selectors do not change.

## Claim boundary

- 0 of 43 operational journey checks executed.
- 0 provider calls and USD 0 cost.
- No hidden or sealed package was read.
- No release decision is drawn from this attempt.
