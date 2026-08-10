# Generator qualification v1 development attempt 001 results

## Run identity

- Result ID: `generator-qualification-v1-development-attempt-001`
- Components: DeepSeek V4 Flash generator transport and P0/P1 prompt comparison
- Status: completed development comparison; held-out unopened
- Date and owner: 2026-08-07, project researcher with Codex-assisted review
- Code revision: `e8c0ff2bbfa6f84839fad24ceeabde020d6ff3b2`
  with the disclosed dirty implementation worktree
- Dataset: `generator-qualification-v1.0.0-development`, 48 public synthetic
  oracle-evidence cases, six per scenario
- Reproduction: `npm run benchmark:generator-qualification-development`
- Ignored raw output: `reports/generated/generator-qualification-v1-development.json`
  with SHA-256
  `afabb9092b36c8614318a493b14a3ae479f3fa560415cf834dd845ec52c74fde`
- Durable review: [`generator-qualification-v1-development-attempt-001.json`](judgments/generator-qualification-v1-development-attempt-001.json)
- Paid external data boundary: synthetic public cases only; no private course or
  student text

## Decision context

The prospective question was whether existing direct prompt P0 or support-first
prompt P1 could qualify one exact DeepSeek V4 Flash non-thinking binding before
the sealed professor-fidelity run. The deterministic generator remained the
rollback. The prediction was that P1 would reduce unsupported additions without
losing required claims.

Both prompt conditions used the same 48 cases, approved oracle evidence,
policy, model, returned JSON schema, temperature 0, 600-token ceiling,
15-second timeout, no retry, and provider fingerprint. Six no-evidence and six
assessed-work cases per condition stopped before the provider call.

## Operational result

All 96 attempts completed. The provider returned one fingerprint,
`fp_a18b46594c_prod0820_fp8_kvcache_20260402`. Total usage was 23,456 input and
4,730 output tokens; total reported cost was USD 0.00460824. Aggregate p50 was
1.393 seconds and aggregate p95 was 2.198 seconds. There were no private-course
external calls, retries, provider failures, malformed responses, permission
leaks, superseded-token disclosures, or assessed-work violations.

| Metric | P0 direct v1 | P1 conservative v2 | Floor |
| --- | ---: | ---: | ---: |
| Safe grounded task success | 41/48 (85.4%) | 39/48 (81.3%) | 80% |
| Required-claim recall, answer cases | 30/30 (100%) | 30/30 (100%) | 90% |
| Citation correctness, model-called cases | 29/36 (80.6%) | 27/36 (75.0%) | 95% |
| Citation completeness, answer cases | 30/30 (100%) | 30/30 (100%) | 95% |
| Reliable turn completion | 48/48 (100%) | 48/48 (100%) | 95% |
| p95 latency | 1.968 s | 2.198 s | at most 10 s |
| Reported cost | USD 0.002037 | USD 0.002572 | below USD 1 |

## Review findings

Every generated development answer was inspected. P0 added unsupported
security mechanics or examples in seven cases. P1 did so in nine cases and
also induced unnecessary misconception correction, configuration questions,
or check-understanding questions in 13 cases. No unsupported addition was
classified high severity, but a valid citation ID did not support the added
claim, so those cases failed citation correctness.

Development also exposed three analysis defects: inflected `rotates` failed an
exact `rotated` term check, correctly cited ambiguity explanations were treated
as citation failures, and P1 check-understanding questions were mistaken for
clarification actions. These rules were corrected prospectively without
regenerating or hiding any output. The durable raw result remains immutable.

## Decision

**Refine; select no prompt.** Both candidates miss the 0.95 citation-correctness
floor. P1 did not satisfy its prediction and is dropped from the next bounded
screen. The next candidate should remove mandatory tutoring elaboration and
explicitly forbid examples, mechanisms, motivations, implementation advice,
and background facts absent from the evidence. The held-out split remains
sealed and its access ledger remains absent.

This result does not qualify a generator, professor fidelity, private course
processing, human usability, learning outcomes, or deployment capacity. The
single Codex-assisted review is sufficient for development refinement but not
the planned held-out double-review requirement.
