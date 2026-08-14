# Professor-fidelity post-audit v3 plan

Date: 2026-08-14

Status: prospectively implemented; execution blocked by the frozen 41-case
independent-human authoring audit

## Decision boundary

After the authoring audit approves the exact v1.2.3 draft and the immutable v2
seal is created, run the corrected C0-C3 development comparison, evaluate its
pedagogical outputs with the current DeepSeek model plus a local sensitivity
reviewer, and decide whether the one-time held-out split may be opened.

This plan does not waive or postpone the audit past sealing. Generating tutor
outputs from the unapproved review draft would make the comparison invalid and
could expose held-out content before its ledger exists.

The separately sealed 12-case anchor may run before the authoring audit solely
to prepare judge calibration. Anchor output cannot approve the v1.2.3 draft,
substitute for the 41-case authoring audit, or authorize development/held-out.

## Frozen model roles

| Role | Binding | Purpose |
| --- | --- | --- |
| Tutor generator | Selected DeepSeek V4 Flash non-thinking/P2 binding | Preserve the already qualified generator while isolating policy and retrieval effects |
| Primary pedagogical judge | Official `deepseek-v4-pro`, documented `DeepSeek-V4-Pro-0813`, fingerprint `a307abda487cd1b463329ccb945ce396`, JSON mode, thinking `high` | Evaluate every development response under the frozen per-dimension contract |
| Position sensitivity | The same DeepSeek V4 Pro binding on a stable 25% sample with C1/C2 order swapped | Detect order sensitivity without changing model family |
| Family sensitivity | Frozen local `qwen3:4b` on a stable 25% sample | Measure cross-family agreement without external transmission |

Gemma is excluded from active professor-fidelity commands. Its historical
exploratory and failed-attempt records remain preserved and must not be
rewritten as if they did not occur.

The newest DeepSeek model is used for judging. The tutor generator is not
silently replaced with V4 Pro because the selected V4 Flash/P2 combination is
a separately qualified component. Replacing the generator would require a new
prospective qualification and comparison before it could support a component
selection claim.

## Operational bounds

- Development primary judge: at most 350 calls and USD 3.
- Held-out primary judge: at most 750 calls and USD 6.
- Each DeepSeek response must return model `deepseek-v4-pro` and the frozen
  fingerprint above; drift stops the run.
- Each call records finish reason, latency, input/output/reasoning tokens, and
  a conservative cost that prices every input token as a cache miss.
- The model receives blinded response labels and no condition, provider, or
  tutor-model identity.
- Local Qwen is a sensitivity reviewer, not an independent human reference.
- The repository-wide cumulative DeepSeek budget and approved course-data
  boundary continue to apply.

## Ordered execution

1. While the authoring audit is pending, execute the corrected 12-case anchor,
   run primary/swapped/sensitivity judges, and prepare its blinded human
   calibration packet. Without the completed reference, calibration remains
   ineligible and diagnostic.
2. Complete the 41-case blinded independent-human authoring audit.
3. Validate the exact frozen ensemble/audit pair and create the immutable v2
   development/held-out seal plus unopened held-out ledger.
4. Execute C0-C3 on development only with the selected generator, M2 retrieval,
   exact policy/prompt hash, and deterministic hard-gate scoring.
5. Run the all-case DeepSeek pedagogical judge, the 25% swapped DeepSeek sample,
   and the 25% Qwen sensitivity sample.
6. Complete the separately blinded semantic, citation-completeness,
   context-sufficiency, and judge-calibration boundary. Model agreement alone
   cannot establish this boundary.
7. Analyze and register the development result. Open held-out once only if all
   frozen development, calibration, privacy, cost, completion, citation,
   pedagogy, and operational gates pass.

## Commands prepared in advance

```bash
npm run benchmark:professor-fidelity-anchor
npm run judge:professor-fidelity-anchor
npm run judge:professor-fidelity-anchor-swapped
npm run judge:professor-fidelity-anchor-qwen-sensitivity
npm run prepare:professor-fidelity-anchor-review
npm run calibrate:professor-fidelity-anchor-prehuman

npm run seal:course-tutor-splits -- \
  --ensemble-review reports/generated/course-tutor-v1.2.3-hybrid-authoring-review/ensemble_review.json \
  --human-audit reports/generated/course-tutor-v1.2.3-hybrid-authoring-review/human_audit_template.json \
  --github-purge-confirmed

npm run benchmark:professor-fidelity-development
npm run judge:professor-fidelity-development
npm run judge:professor-fidelity-development-swapped
npm run judge:professor-fidelity-development-qwen-sensitivity
npm run analyze:professor-fidelity-development
```

The seal command is expected to fail until the human audit is complete. The
development and judge commands are expected to fail until their exact upstream
artifacts exist. No command in this plan authorizes the held-out run early.

## Decision rule

Any authoring-audit defect returns to a new candidate and prospective review.
Any unresolved semantic/citation or judge-calibration gate keeps the
development result at `Refine` or `Go Deeper`. Only a fully registered
development result whose hard gates and floors pass may authorize the one-time
held-out command.
