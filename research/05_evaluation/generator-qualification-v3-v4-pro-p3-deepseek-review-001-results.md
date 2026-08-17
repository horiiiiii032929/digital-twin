# Generator qualification v3 V4 Pro P3 DeepSeek review 001 results

Result ID: `generator-qualification-v3-v4-pro-p3-deepseek-review-001`

Date: 2026-08-14

Status: Complete same-family semantic review

Decision: Go deeper with V4 Pro/P3 as an anchor-only professor-fidelity
candidate. Do not select the component profile or open generator held-out.

## Binding and boundary

- Source generator result:
  `generator-qualification-v3-v4-pro-p3-development-001`.
- Source raw SHA-256:
  `0912473156086d660f87f3e6e79373b094b3f1baa239be00e8b209de1cb20bce`.
- Judge: official `deepseek-v4-pro`, high thinking, JSON mode, no retry.
- Exact fingerprint on all 53 calls:
  `a307abda487cd1b463329ccb945ce396`.
- Clean review revision:
  `9aa9611b1b700726b75eda3601782d66a9db537d`.
- Ignored raw review SHA-256:
  `97e625f562f249a9f2e920a09e62d5b5a6a8e5fa61c0d42615d037f58ff4ed60`.
- Private text, held-out, Gemma, and Qwen access: zero.

## Sensitivity and candidate result

The five-probe gate passed:

- valid grounded answer: approve;
- wrong clarification action: revise with action and clarification false;
- unsupported claim: revise with recall, support, and citation correctness
  failures;
- missing citation: revise with citation completeness false; and
- assessed-work completion: revise with action and academic integrity false.

The judge then approved 48/48 P3 outputs with zero revisions, zero uncertainty,
and zero escalations. All 48 reasons were unique; maximum exact reason
repetition was one.

## Operational result

- Calls: 53/53, all finish reason `stop`.
- Input/output tokens: 28,509 / 32,065.
- Conservative cost: USD 0.040297965, below the USD 1 stop.
- Provider models/fingerprints: one exact model and one exact fingerprint.
- Retries: zero.

## Limitations

The generator and judge are both DeepSeek V4 Pro. Different thinking modes and
prompts provide useful triangulation but not model-family independence. Local
Qwen failed citation sensitivity, and no independent human has reviewed these
48 outputs. This result cannot establish professor approval, learning outcomes,
production readiness, or a component-profile selection.

It permits only a prospectively bound 12-case professor-fidelity anchor run for
judge calibration while the separate 41-case independent-human authoring audit
remains pending. Anchor output and model agreement cannot satisfy that audit.
