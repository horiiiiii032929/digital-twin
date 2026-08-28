# R1 OpenAI release path

Status date: 2026-08-28

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

PR #136 merged this direct-provider base. Checkpoint 003 now adds a mandatory
40-control GPT-5.4 calibration before wording, 500 candidate cases, 100 paired
controls, and deterministic scoring. Pass, calibration-failure,
wording-failure, and product-failure simulations all stop correctly without
network access. AFQC-050 authorized exactly this checkpoint once. Two fresh
calibration attempts each made one exact GPT-5.4 call and stopped before hidden
labels or later stages: the first exposed a schema/parser taxonomy mismatch;
the corrected second returned defect-bearing records marked semantically valid.
AFQC-052 records both as invalid and revokes authority. No product-quality claim
exists, and the sealed 10,000 cases remain unauthorized.

AFQC-053 now freezes a standalone method successor: calibration 004 removes the
provider-owned overall-validity field and derives it deterministically from the
five atomic defect judgments. It reuses the same 40 controls and gates without
importing either invalid attempt. Three network-free terminal simulations pass;
all paid authority was initially false and no product progression was available.
AFQC-055 now preserves its paid result as invalid: three exact GPT-5.4 calls
covered 12 controls before a clarify vote omitted the mandatory boundary reason.
Authority is revoked, hidden labels remain closed, and no product evidence exists.

## Finite critical path

1. Keep the rotated replacement key only in the ignored repository-root `.env`
   as `OPENAI_API_KEY`.
2. Make one explicit reviewer-method decision that avoids another strict-output
   calibration loop while retaining deterministic source truth.
3. Once that decision is frozen, separately authorize a successor with
   500 candidate cases and the paired 100-case any-hit control; score hidden
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

Work stops for four inputs only:

1. explicit selection of the reviewer method after invalid calibration 004;
2. explicit authorization for the sealed 10,000-case paid run after development;
3. professor approval of the explicit teaching profile;
4. production domain/DNS access and deployment authorization.

True visual evaluation #131, real-source work #102, an external student pilot
#10, and the final report #13 remain post-R1 and do not block this release.
