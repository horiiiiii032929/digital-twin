# DeepSeek V4 Pro generator qualification v2 plan

Date: 2026-08-14

Status: prospectively frozen after provider drift; development only

## Trigger

The corrected 12-case professor-fidelity anchor attempt stopped on its first
provider response because the selected V4 Flash alias returned fingerprint
`a26a7955944dc5c60445bff77fac9c8e` instead of the qualified fingerprint
`fp_a18b46594c_prod0820_fp8_kvcache_20260402`. No case, checkpoint, or result
artifact was written. The exact selected generator is therefore unavailable
and must not be silently rebound.

The user already selected the current DeepSeek model rather than Gemma. The
prospective candidate is official `deepseek-v4-pro`, currently documented as
model version `DeepSeek-V4-Pro`, with the fingerprint established by the
completed v6 public stress gate. Strict-evidence P2 and the synthetic
development dataset remain unchanged so the candidate can be compared with
the historical V4 Flash control. DeepSeek's current model table and changelog
confirm the alias, non-thinking and JSON support, and pricing:
<https://api-docs.deepseek.com/quick_start/pricing/> and
<https://api-docs.deepseek.com/updates/>.

## Binding and prediction

- Model: `deepseek-v4-pro`.
- Mode: non-thinking JSON, temperature 0, one attempt, 1,200 output tokens,
  60-second timeout.
- Prompt: unchanged strict-evidence P2/v3.
- Dataset: unchanged 48-case public synthetic development split.
- Provider identity: exact model plus fingerprint
  `a307abda487cd1b463329ccb945ce396`.
- Cost stop: USD 1 for this run; cumulative issue cap remains USD 10.
- Prediction: all 48 deterministic case checks pass with one fingerprint.

## Decision rule

Any model/fingerprint drift, missing usage/cost, malformed response, permission
or assessed-work violation, unsupported high-severity claim, incomplete ledger,
or cost stop invalidates the attempt. Passing deterministic checks permits
cross-model output review and bounded anchor calibration only. It does not
select V4 Pro in the component profile or authorize generator held-out.

## Command

```bash
npm run benchmark:generator-qualification-v4-pro-development
```
