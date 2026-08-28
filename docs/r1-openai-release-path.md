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
AFQC-056 therefore removes calibration as a product prerequisite while keeping
deterministic truth authoritative and GPT-5.4 review advisory. AFQC-057 records
the one-time authorization for checkpoint 004 after refreshing both exact model
snapshots, pricing, Responses API support, and retention documentation. The
sealed 10,000 cases remain unauthorized.
AFQC-058 records the valid paid outcome: all 50 wording calls completed, but
only 452/500 model variants passed the frozen 95% acceptance gate. Forty-eight
canonical fallbacks remain available, with zero duplicates or leaks. The runner
stopped before every product and scoring stage, USD 0.555499 was reported, and
all authority is revoked. This is a wording-layer failure, not a T0 result.

AFQC-059 resolves the prospective method decision by retaining the immutable
452 accepted variants and labelling 48 exact canonical fallbacks. AFQC-060
builds product checkpoint 005 around that fixed package. It has no wording
stage: 500 candidate and 100 fixed paired control product responses must be
durable before deterministic scoring opens hidden gold. AFQC-061 keeps exact
GPT-5.4 mini for product answers, assigns routine non-blocking review to exact
GPT-5.4 nano, and limits exact full GPT-5.4 to 12 possible truth-defect
escalations. Five network-free outcomes pass under a 666-call, zero-retry, USD
8 ceiling. All paid, provider, final, promotion, and deployment authority
remains false.

Checkpoint 005 is now terminal: neither attempt reached a product response, and
the corrective run exposed an unusable on-demand dense-index startup. AFQC-065
adds immutable release-bound indexes and passes the network-free lifecycle
qualification with zero runtime document embedding. The actual adapter is
verify-only. A real local-Qwen build/load qualification under #139 is the next
stop; no successor 500+100 run is designed or authorized yet.

## Finite critical path

1. Keep the rotated replacement key only in the ignored repository-root `.env`
   as `OPENAI_API_KEY`.
2. Preserve the frozen 452-model/48-canonical mixed-wording package; do not
   rerun or reinterpret checkpoint 004.
3. Separately authorize #139's resumable local-Qwen 2,100-region index
   qualification. It opens no product or final case.
4. If that resource gate passes, freeze and separately authorize one new 500
   candidate plus 100 control T0 checkpoint; checkpoint 005 is not rerun.
5. If development passes, separately freeze and authorize the untouched
   10,000-case final run. A valid quality failure receives one method-level
   decision and is not tuned against the sealed set.
6. Use the leakage-free result to select or reject #105's production grounding
   gate, then run #107's untouched T0/T1 confirmation with T0 retained as
   rollback.
7. Complete #132 learning-gap API/UI/deletion/key-rotation evidence and #134's
   fresh outreach-method comparison. In-app outreach stays disabled until it
   passes; Discord stays outside R1.
8. Obtain professor approval for an explicit profile and complete #24's C0-C3
   behavior evaluation separately from factual hard gates.
9. Deploy one immutable revision, verify HTTPS, roles, persistence, monitoring,
   backup/restore, rollback, and complete professor/student journeys, then close
   #88, #9, #25, and parent #8 in that order.

## Human stop points

Work stops for six remaining inputs only:

1. explicit authorization for #139's local-Qwen index qualification;
2. explicit authorization for the successor 500+100 product checkpoint;
3. explicit authorization for the sealed 10,000-case paid run after development;
4. explicit authorization for the paid T0/T1 confirmation;
5. professor approval of the explicit teaching profile;
6. production domain/DNS access and deployment authorization.

True visual evaluation #131, real-source work #102, an external student pilot
#10, and the final report #13 remain post-R1 and do not block this release.
