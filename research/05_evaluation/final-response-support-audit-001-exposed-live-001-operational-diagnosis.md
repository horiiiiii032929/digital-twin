# Independent stopped-run diagnosis

Run `final-response-support-audit-001-exposed-live-001` stopped after 54 admitted/provider calls (47 audit, 7 repair), two provider-wrapper failures, $1.012588 known cost, zero unknown-cost calls. Sources remained unchanged. This is an incomplete run, not a qualification pass.

## Operational cause

`provider-audit.jsonl` attempts 40 and 45 identify C2 initial quality audits of evidence-relations-09-adequate (Rovik ticket arithmetic) and -10-adequate (Oswen strict/inclusive boundaries). Both returned HTTP 200, status completed, one output text, no refusal, no incomplete reason, exact requested Sol identity and known usage. The failures are `schema-validation`, with `value_error` at `entries[0]` and `entries[1]`. They are not transport outages, token-cap truncations, unknown cost or observed hash mismatches.

The frozen `UnitAudit.consistent` validator has the relevant cross-field rule: supported/no_factual_assertion requires issue_code none; unsupported/uncertain requires a non-none code. Entry-level model-validator failure at both positions therefore identifies inconsistent verdict/code combinations. The exact returned pairs cannot be established: the transport retains a response hash and sanitized error locations, but not rejected output text. Do not claim the model emitted a specific pair, or assert that its underlying factual judgment was wrong.

The shared stop behaved as designed; a second already-admitted call could finish and fail after the first stop. All later admissions were blocked and planned cases retained. No unchecked original or rewrite was delivered for these failures.

Bounded correction: keep fail-closed validation; add an explicit verdict/code truth table and distinguish factual issue codes from teaching dimensions in the separately versioned instruction/schema description. Add adversarial injected cases for each inconsistent pair. Preserve sanitized rejected field values (entry ID, verdict, issue_code) or approved structured output text for diagnosis, never provider reasoning. Do not silently repair an inconsistent judgment into PASS. Evaluate this correction as a new version/run; no automatic retry of the failed output.

## Separate semantic policy problem

The frozen C2 prompt says “New concepts require their own attempt” unconditionally, immediately alongside “Respect direct explanation profiles.” These conflict for a new, ordinary, non-assessed question under an explanation-first profile. The existing profile integrity clause concerns assessed work; it does not turn every first question into assessed work. A source-only C1 assessment cannot resolve this pedagogical conflict.

Observed evidence, not just hypothetical wording risk: C2 labels source-supported direct answers premature, repairs them into questions, then accepts those questions. This happens for evidence-relations-02-adequate, -04-adequate, -05-adequate, -06-adequate and -08-adequate. Case -07-adequate is unnecessarily changed and then quarantined after the second audit calls the direct response premature. All six have the detailed/direct profile whose structure begins “state the explanation.” These are lost requested answers or unnecessary abstention, even though the post-repair audit often says adequate. Representative -05 changes “12 chambers” into asking the learner for the calculation; -04 changes the checklist answer into counting seals. Full source/profile/original/final/audit evidence is in the companion JSON.

Bounded correction: require a current-concept attempt only when the authoritative teaching policy is Socratic/attempt-first for this turn or the actual request is assessed work. Explicitly permit supported direct explanations/applications on new ordinary questions under explanation-first profiles; do not infer assessment from missing history. Coverage must still require the requested answer in that context. Test matched same-source/profile-swapped initial questions, assessed/unassessed contrasts, and topic transfer before a fresh evaluation. This is a semantic prompt intervention, distinct from the parser/diagnostic correction; neither is established effective by the injected preflight.

Do not integrate C2 or claim improvement from the stopped run. Retain its operational failure and false-rejection evidence, then freeze the bounded corrections and comparison before another paid run.
