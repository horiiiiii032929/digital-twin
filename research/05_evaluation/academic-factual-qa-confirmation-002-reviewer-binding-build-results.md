# Academic factual-QA confirmation 002 reviewer binding

## Decision

**Go Deeper.** The blinded three-family review is technically ready but remains
execution-unauthorized. This checkpoint binds reviewers and proves the complete
no-call state machine; it does not contain semantic judgments or a product
result.

## Run identity

- Date: 2026-08-26
- Implementation revision: `be43067d3bdbde06e030e1755689f68e36727b37`
- Instrument: `academic-factual-qa-confirmation-002`
- Reviewer binding: `academic-factual-qa-confirmation-002-reviewer-bindings-001`
- Source packet: 40 calibration controls followed by 200 confirmation cases
- Real reviewer/model calls, tokens, and cost: zero
- Private or held-out data read: no

## Frozen reviewers

- OpenAI family: a fresh isolated Codex task using `gpt-5.6-sol` at medium
  reasoning. The design task is ineligible because it has seen hidden controls.
- Mistral family: `mistralai/mistral-small-2603` through the first-party
  Mistral `mistral/zdr` endpoint, with fallback disabled, parameter support
  required, data collection denied, and zero-data-retention routing required.
- DeepSeek family: direct official `deepseek-v4-pro`, documented as
  `DeepSeek-V4-Pro-0813`, with peak prices used for the safety reservation.

The metadata snapshot is valid for at most 24 hours. A paid execution must
repeat the live model, price, endpoint, credential, and routing checks.

## Execution contract

The provider path uses batches of four, calibration before confirmation, zero
retries, atomic checkpoints after every call, exact resume bindings, and stable
model/provider identity across the run. The maximum is 120 provider calls. The
conservative peak reservation is USD 1.563034 and the emergency hard stop is
USD 3.00.

The Codex reviewer receives two sanitized phase packets in an isolated
workspace. Its calibration and confirmation artifacts must report the same
task, model, reasoning setting, parent packet hash, and complete strict votes.
Confirmation cannot start until all three reviewers meet every 0.90 calibration
gate.

## Network-free and metadata verification

The complete simulated path produced 720 judgments, exactly 120 simulated
provider calls, three passing calibrations, unanimous confirmation, and a
bounded 20-case researcher packet. Malformed output stops after one recorded
attempt without retry. Tests also cover strict response shape, token and cost
limits, task/model identity drift, hash-bound resume, and gold-free Codex
workspace preparation.

The live metadata-only preflight found no model, price, or endpoint drift and
confirmed both provider credentials without exposing their values. It made no
inference call. Execution remains blocked by the absent bounded authorization,
false review authorities, and missing fresh Codex calibration votes. Calibration
and confirmation have separate authorities: calibration can be authorized first,
while confirmation remains locked until every calibration gate passes.

The complete repository gate passed with 925 Python tests, 46 frontend tests,
frontend lint and production build, 539/539 audited execution-relevant files,
and 72/72 protected entrypoints.

## Validity and limitations

Reviewer diversity reduces but cannot eliminate correlated model error.
DeepSeek overlaps the product generator family, and Codex is not an independently
reproducible API snapshot. Reviewer unanimity remains advisory; deterministic
source truth stays authoritative, and the later researcher audit is explicitly
not independent annotation.

No factual-quality, evidence-sufficiency, Digital Twin fidelity, usability, or
release claim follows from this checkpoint.

## Next checkpoint

Create one fresh isolated Codex task and separately authorize only the bounded
calibration phase. If all three reviewers pass calibration, continue the same
Codex task and the two provider reviewers over the 200 confirmation cases. Stop
at the generated researcher packet for the bounded audit and decision.
