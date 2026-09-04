# Grounding floor audit reproduction and metric correction

## Outcome

The selected gate remains `dominance-scoped-ambiguity-safe-v3`, but two claims
are corrected before release qualification.

First, selection 004 labelled overall task success as fully grounded factual
success. Re-scoring the hash-verified, byte-identical response ledgers gives:

| Arm | Answerable fully grounded | Overall task success | Severe releases |
| --- | ---: | ---: | ---: |
| Incumbent | 26.00% | 36.80% | 0 |
| Candidate | **42.50%** | **50.00%** | 0 |

The registered relative decision still passes: the candidate improves the
actual factual metric by 16.50 points with no increase in severe releases or
operational failures. Both arms still fail 12 absolute product-quality gates,
so this is a relative development selection, not a factual-quality pass.

Second, the four subsequent floor audits did not have committed executable
commands. A new provider-free command rebuilt their shared measurements from
the committed 500-case public package, registered region corpus, and immutable
selection-003 ledgers. It verified every ledger metadata binding, response ID,
and response payload hash before calculation.

## Reproduced surface

- 238 single leaders, of which 231 point to a gold region.
- 196 tied leader sets across 192 cases.
- 185 answerable cases contain a tie; every tie contains gold in 181 cases.
- 194 of 196 tied sets contain different canonical claim classes.
- Crediting locator provenance and narrowing the required term set both reduce
  correct single leaders from 231 to 226 under the now-executable definitions.

The central safety result is reproducible: releasing every tied passage would
release contradictory source claims in 194 tied sets. The bounded mechanisms
therefore do not justify replacing the fail-closed behavior.

## Historical discrepancy

The current source-defined run parses 556 targets, while the historical notes
report 554. It also finds two wrong single leaders where one historical record
reports one and another reports two. Because the original scratch calculations
were never committed, those exact historical numbers cannot be reconstructed.
They remain preserved as historical evidence rather than silently rewritten.

Accordingly, the academically defensible claim is narrower: the four audits
provide convergent development evidence against the tested mechanisms. They do
not establish a universal task ceiling, and 50.00% is not the factual metric.

## Reproduction

```bash
uv run python scripts/reproduce_grounding_floor_audits.py
```

The command makes zero provider calls and does not load, rerun, or rescore the
sealed 10,000-case package.

## Decision

Keep the relative development selection, require exact Luna/H+E1 plus
`dominance-scoped-ambiguity-safe-v3` binding, and run one fresh local HTTPS
qualification. Do not claim an absolute grounding pass from selection 004.
