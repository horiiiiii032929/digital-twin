# Open 10,000 factual-QA reviewer calibration 004

Result ID: `academic-factual-qa-open-10000-reviewer-calibration-004-invalid`

Decision: **Invalid execution / stop calibration**

Calibration 004 started from clean authorization revision `26ac3c6` with a
fresh exclusive ledger. GPT-5.4 completed three four-control calls with the
exact `gpt-5.4-2026-03-05` identity. The ledger records 7,036 input tokens,
1,443 output tokens, 15.511 seconds aggregate latency, and USD 0.039235 reported
cost.

The first two batches passed the deterministic semantic parser. In the third
batch, one `clarify` vote correctly marked the question unanswerable and
ambiguous but omitted the mandatory boundary reason. This violates the frozen
atomic boundary contract, so the parser rejected the batch and stopped the run.
The failure is operationally invalid rather than evidence that GPT-5.4 passed
or failed the 40-control quality thresholds.

No retry occurred. Expected labels remained unopened, and no fourth through
tenth calibration batch, wording call, T0 product case, paired control, private
data, or final 10,000-case call occurred.

The ignored ledger is
`reports/generated/academic-factual-qa-open-10000-openai-reviewer-calibration-004.sqlite3`
with SHA-256
`37c8169a6b891d55df7fe843003a1a614530259edbaea4f8c6c612f21dcaa533`.
Authorization is revoked. The next step is a method-level decision, not another
silent schema or prompt revision.
