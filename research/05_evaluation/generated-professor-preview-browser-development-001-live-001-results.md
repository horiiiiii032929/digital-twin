# Generated professor preview: bounded browser diagnostic

Run `generated-professor-preview-browser-development-001-live-001` completed the actual synthetic generate/save/approve/refresh journey. **Keep this workflow for further evaluation; this does not qualify V14-medium for deployment.** One live generated answer matched the source, and its exact artifact hash was submitted by the UI and retained in the approval record.

## Question and comparison

The comparison is expectation-only guidance versus an actual saved response, with a withdrawn-profile negative control. An isolated local HTTPS server used synthetic professor/student accounts and three permitted synthetic lecture/transcript/forum sources. The reviewed onboarding fixture and browser session pointer were provisioned before the journey, so this is not a full onboarding-from-scratch evaluation. One single-turn case tests operation only, with no statistical quality or learning inference.

The source states “Glimmer lease expires after nine ticks.” The fictional student asked how many ticks; the tutor answered “The Glimmer lease expires after nine ticks. How many ticks would remain after six ticks?” The assistant judged that answer supported and consistent with the explanation-first synthetic profile. This is not human validation.

## Observations

- The UI clearly distinguishes ten static expectations from generated responses. Actual generation saved one artifact; the case decision explicitly bound its ID and SHA256 `9f484694464cef0c69b54668ccd3bd9d044ac9a6bb538705b2b5aa8796ef78c7`.
- Approval persisted and was shown as accepted after refresh without additional provider calls. The stored review retained the same artifact hash.
- Withdrawing the synthetic v2 profile through the existing local API caused subsequent approval to return HTTP409 `teaching_profile_withdrawn`. Source replacement/profile-content stale branches were not tested. A wrong-hash probe409 was observed but its response body was lost to the diagnostic observer error, so it is not counted as full branch verification.
- Real-runtime conversations, messages, learner states, learning-gap signals and outreach outbox remained zero; generated artifact/review counts each increased from0 to1. No real student data was involved.
- Normal UI showed no application exception. Initial401 was unauthenticated session discovery; later409s were deliberate negative probes. Chrome reported password-form accessibility hints. A diagnostic request observer failed after refresh, was removed, and withdrawal rejection was independently recaptured.

## Configuration and accounting

Frozen code `e441193c7fa1260ed327ebf43c59483f85817be8`, dirty `True`, isolated source archive SHA256 `22e1a89cb38916685dbd4517b60509f8472fd734110a963e4f7651428f91bba5`. End-of-run file comparison found no mismatches. Initial setup failed before provider use because the frontend build lacked session mode; rebuilding only the isolated frontend and refreezing resolved setup. Both setup versions remain preserved.

Unselected `v14-luna-sol-medium`: actual `gpt-5.6-luna` low-effort generation and `gpt-5.6-sol` medium-effort conditional revision, each output cap3000; the revision kept the original. Two calls, zero provider failures/unknown costs,3166 input+244 output=3410tokens, **USD0.009635** reported. Total budget-observed provider latency5714.007ms. Shared limits60calls/USD9.60 were not reset; server stopped after the journey. No candidate alias/default/profile promotion.

## Evidence and limits

[Machine record](records/generated-professor-preview-browser-development-001-live-001.json), [sanitized assistant review](generated-professor-preview-browser-development-001-live-001-assistant-review.json), and [preregistered plan](../04_experiments/2026-09-06-generated-preview-browser-diagnostic-plan.md). Raw browser snapshots, screenshot, exact synthetic request bodies, DB counts, provider ledgers and source archive: `reports/generated/generated-professor-preview-browser-development-001-live-001/`. Record stores hashes, including the accepted-preview screenshot.

Only one local browser case was tested. Refresh persistence does not establish server-restart recovery. No source mutation, simultaneous users, load, real instructor fidelity or student learning was assessed. This operational evidence complements earlier API tests and does not override failed semantic candidate gates.
