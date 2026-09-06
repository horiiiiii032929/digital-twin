# Calibrated advisory semantic review

Program: `completion-semantic-review-development-001`. Prospective plan for the
user's request to remedy evaluation quality/quantity deficiencies (2026-09-06).

## Decision and prediction

Can a separately prompted Terra reviewer identify defects that exact-span
containment misses? Compare its judgments with the unchanged mechanical scorer
on explicit synthetic controls, before reviewing frozen live005 responses.
Prediction: added unsupported prose, contradiction and paraphrased premature
solutions are detectable; generic Socratic questions may remain ambiguous.
This is an advisory cross-model diagnostic, not independent human qualification.

## Frozen scope and gates

Use the eleven variants from `evaluation_calibration_cluster_analysis.calibration`:
clean answer, unsupported addition, contradiction, missing requirement, wrong
version, malformed citation, empty text, duplicate text, generic question,
irrelevant question and paraphrased premature solution. Freeze their public
inputs and locally authored expectations before dispatch. Hide mutation labels,
expected judgments, historical scores and arm identities from the reviewer.
Run two separately shuffled passes (seeds 620906 and 620907), with no retries.
Seeds affect order only; the provider is not assumed deterministic.

Calibration gate: every call valid; clean answer has no major defect; all eight
unambiguous defective variants are identified in both passes. Generic and
repeated-text variants are advisory only. Require specific expected axes for
unsupported/contradiction, missing/empty, citation defects, irrelevance and
premature solution. Failure stops downstream judgments. Never tune the prompt
and quietly rerun the same controls. A successor needs a new recorded decision.

If calibration passes, judge all 88 frozen live005 responses, individual and
shuffled (seed 620908), without scores/arm labels. Show actual preceding tutor
responses where recorded, the current student question, approved profile and
source/citation metadata. Public fixture labels are removed. Preserve all
responses, uncertainty, parser errors and failed judgments. Do not compare the
reviewer's binary count directly with the 95% human semantic gate.

## Provider and measurements

OpenAI Responses API, `gpt-5.6-terra`, reasoning low, maximum output 1,500 tokens,
`store=false`, no tools or retries. Reuse the existing explicit transport and
pricing catalog through an evaluation-only schema subclass. Only fictional
source cards, synthetic questions/profiles and their already generated answers
leave the machine. No real course material, student data or credentials appear
in the payload or durable summaries. Account-specific retention/training/region
settings are not independently verified; non-stored requests do not imply zero
provider retention. Raw sanitized results remain local; aggregate, hashes and
representative findings are versioned. User's current instruction authorizes
this bounded synthetic evaluation.

Maximum 120 calls, USD 10 conservative reservations, concurrency two. Record
exact returned model, valid/failed status, usage, measured latency, actual cost,
payload/response hashes and configuration. Reserve a conservative bounded cost
before dispatch; unknown usage or a cost above the reserve stops further calls.
The API key is loaded from the existing local configuration and never logged.

Report calibration sensitivity by defect, clean acceptance, repeat agreement,
all five quality axes, missing judgments, per-course/kind slices and paired
candidate/control discordance. These are reused four-mini-course development
responses. More judgments improve diagnostic coverage, not course diversity or
real-professor validity. No release/profile changes follow automatically.
