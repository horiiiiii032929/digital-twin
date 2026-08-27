# R1 OpenAI release path

Status date: 2026-08-27

## Current checkpoint

The flow-independent evaluation, privacy-preserving learning-gap core, and
proactive-outreach core are consolidated on `main` through PRs #130, #133, and
#135. The prospective R1 branch now uses one direct OpenAI Responses API
boundary:

- `gpt-5.4-mini-2026-03-17` for question wording and product generation;
- `gpt-5.4-2026-03-05` for advisory semantic review;
- deterministic source, action, claim, citation, and boundary truth remains
  authoritative.

These are two version-locked OpenAI models, not independent provider families.
Every request disables storage with `store: false`; active bindings have no
router, fallback, retry, or alternate-provider path. Historical DeepSeek,
Gemini, Mistral, OpenRouter, and local-model evidence is preserved but cannot be
selected by the active R1 profile or its paid preflight.

The 500-case wording simulation and the flow-independent adapter simulation pass
without network access. The live preflights correctly report
`blocked-not-authorized`. No OpenAI inference call or product-quality claim has
been made at this checkpoint.

## Finite critical path

1. Revoke the OpenAI key exposed in chat and place only its replacement in the
   ignored repository-root `.env` as `OPENAI_API_KEY`.
2. Refresh official model identity, pricing, limits, and data-control metadata;
   freeze and explicitly authorize the 500-case development checkpoint.
3. Run 500 candidate cases and the paired 100-case any-hit control, score hidden
   gold only after responses are durable, and publish either Keep, Refine, or
   invalid-execution.
4. If development passes, separately freeze and authorize the untouched
   10,000-case final run. A valid quality failure receives one method-level
   decision and is not tuned against the sealed set.
5. Use the leakage-free result to select or reject #105's production grounding
   gate, then run #107's untouched T0/T1 confirmation with T0 retained as
   rollback.
6. Complete #132 learning-gap API/UI/deletion/key-rotation evidence and #134's
   fresh outreach-method comparison. In-app outreach stays disabled until it
   passes; Discord stays outside R1.
7. Obtain professor approval for an explicit profile and complete #24's C0-C3
   behavior evaluation separately from factual hard gates.
8. Deploy one immutable revision, verify HTTPS, roles, persistence, monitoring,
   backup/restore, rollback, and complete professor/student journeys, then close
   #88, #9, #25, and parent #8 in that order.

## Human stop points

Work stops for five inputs only:

1. confirmation that the exposed key was revoked and its replacement installed;
2. explicit authorization for the revised 500-case paid run;
3. explicit authorization for the sealed 10,000-case paid run after development;
4. professor approval of the explicit teaching profile;
5. production domain/DNS access and deployment authorization.

True visual evaluation #131, real-source work #102, an external student pilot
#10, and the final report #13 remain post-R1 and do not block this release.
