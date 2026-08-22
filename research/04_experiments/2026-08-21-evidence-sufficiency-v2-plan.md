# Evidence sufficiency v2 release-gate plan

## Decision question

Can the product decide whether the exact retrieved evidence is sufficient to
answer a student question, while producing no unsupported answers and retaining
at least 90% of genuinely answerable questions?

This is an open-set answerability decision, not another retrieval leaderboard.
The selected retriever still ranks evidence; this gate decides whether that
evidence may reach generation.

## Boundary correction

Evidence sufficiency owns `answer` versus `abstain` when evidence is absent,
incomplete, contradictory, outside the course or version boundary, or too
ambiguous. Academic-integrity refusal remains a separate deterministic tutor
policy. Its cases are safety non-regressions, not answerability labels. This
prevents the evaluator from crediting an evidence gate for behavior it does not
own.

## Method

The historical AnyHit behavior remains an unsafe control and can never be
selected. The successor separates semantic scoring from the final policy:

1. the selected retriever returns only eligible course/version evidence;
2. an injected verifier scores direct support, completeness, contradiction,
   ambiguity, and the exact supporting hit IDs;
3. a deterministic calibrated gate validates those IDs and applies frozen
   thresholds;
4. malformed output, unknown evidence IDs, verifier failure, or missing
   configuration always abstains;
5. generation receives only the accepted original evidence and revalidates its
   citations.

Prospective candidates are an inspectable feature classifier, a cross-encoder
support verifier, and a cross-encoder plus NLI completeness/contradiction
verifier. Exact model/provider identities are deliberately unbound during the
build-only phase. They must be rechecked from first-party metadata within 24
hours of any authorized execution. No Gemma or Claude model is eligible.

## Data separation

- The 30-case v1 calibration set and consumed 50-case v1 held-out set become
  development-only evidence. They can expose known failure modes but cannot
  support a v2 selection.
- A deterministic 120-case synthetic-public decision draft now contains 80
  answerable and 40 abstain cases. Every answerable case binds atomic claims to exact
  source quotes; every abstain case must have empty authoritative lineage and a
  source-independent boundary reason.
- Required slices are direct, paraphrase, multi-evidence, ambiguous,
  cross-course, near-domain vocabulary sharing, no-evidence, permission, and
  source-version cases. Text and multimodal evidence are reported separately.
- Source labels are deterministic. Multiple models may advise on wording and
  label consistency but cannot create or override ground truth.
- The new decision split must pass structural review, independent advisory
  review, and a maximum 12-case priority human packet before it is frozen.

The exact draft is committed at
`research/05_evaluation/drafts/evidence_sufficiency_v2_decision_draft_001.json`
with content hash
`7c43a9195ad95c660ec113e7499904439e5853ecf2653bf1025c32f233bcf023`.
It passes deterministic structure and lineage validation but remains pending
independent advisory review and the bounded priority review packet. It is not
frozen or opened. The preflight therefore remains
`blocked-dataset-not-frozen`; this intentionally prevents a build-only draft
from becoming evaluation authority.

The independent-review workflow began as
`evidence-sufficiency-v2-independent-review-001`. It reconstructs 12 blinded
ten-case batches and a separate six-clean/six-defect sensitivity control. The
review contract checks question naturalness and answerability, action, claims,
exact evidence, course/version boundaries, boundary reasons, and modality
representation. Advisory output cannot modify deterministic truth. Any dataset
defect requires a corrected draft with a new hash and a successor review ID;
any sensitivity failure invalidates the reviewer result. The network-free
simulation is not review evidence. Instrument `001` remains the historical
provider-unbound predecessor.

Prospective successor `evidence-sufficiency-v2-independent-review-002` binds
the advisory reviewer to exact OpenRouter routing for
`mistralai/mistral-small-2603`, current published pricing, a USD 0.50 emergency
ceiling, zero retries, and synthetic-public inputs. The binding does not
authorize a provider call, freeze the draft, or open candidate evaluation; its
preflight must remain `blocked-not-authorized` until a separate one-time
authorization is recorded against fresh metadata.

Build result `evidence-sufficiency-v2-independent-review-002-build` adds the
missing execution boundary without authorizing it. The runner executes the
six-clean/six-defect sensitivity call first, stops before bulk review if that
gate fails, checkpoints every call atomically, validates resume bindings, and
accounts for model identity, tokens, latency, and cost. Its complete
13-call/132-judgment network-free simulation passed. A clean live metadata-only
preflight also matched the exact model and pricing and found the credential and
output boundary ready; it remained blocked by provider authorization,
instrument freeze, and the bounded allowlist exactly as designed.

## Metrics and gates

Selection requires all of the following on the one-time decision split:

- zero false answers across all 40 abstain cases;
- answerable recall at least 0.90 and balanced accuracy at least 0.95;
- no permission, active-version, course-isolation, or citation-lineage failure;
- multi-evidence recall at least 0.90 and near-domain abstention accuracy 1.00;
- selective accuracy and coverage reported together, with unconditional
  retrieval Recall@3 and nDCG@3 visible;
- all citation-removal, citation-truncation, contradiction, wrong-course, and
  stale-version mutations detected;
- verifier p95 at most 500 ms on the declared release hardware, peak added
  memory at most 2 GiB, and complete token/cost accounting when applicable.

Latency and cost are operational gates, not quality tie-breakers. A candidate
that fails a quality gate is refined or dropped; thresholds are never changed
after opening the decision split.

## Progression and stopping rules

1. Complete the provider-neutral gate, dataset contract, validator, simulations,
   and tests without model, provider, private-source, or held-out execution.
2. Freeze the independently reviewed 120-case decision set in a separate
   checkpoint.
3. Bind exact candidates and current pricing/routing/retention metadata, then
   obtain explicit calibration and one-time decision authorization.
4. Register every result. Select no method unless every gate passes.
5. If selected, bind the method into the product profile and rerun the same
   current-image HTTPS publication journey from V8.

No public deployment, paid call, private Academia Vault read, held-out run, or
release claim is authorized by this plan.
