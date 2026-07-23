# Frozen evaluation instruments

This directory contains the public contracts for the no-participant tutor
evaluation. The v1 instrument set is selected in
[`2026-07-23-evaluation-instrument-freeze.md`](../../04_experiments/2026-07-23-evaluation-instrument-freeze.md).

## Contracts

| Contract | Input | Output |
| --- | --- | --- |
| LLM judge | `llm_judge_input_v1.schema.json` | `llm_judge_output_v1.schema.json` |
| Simulated student | `simulated_student_state_v1.schema.json` plus a frozen observed event | `simulated_student_turn_v1.schema.json` |
| Evaluation run | Frozen run configuration and attempted items | `evaluation_run_v1.schema.json` |
| Analysis | Validated run records | `analysis_v1.json` |

The exact prompts are `llm_judge_v1.prompt.md` and
`simulated_student_v1.prompt.md`. `instrument_freeze_v1.json` inventories every
frozen file and its SHA-256.

## Privacy boundary

Committed examples are synthetic and public. Do not commit:

- IT5002 source text or derived passages;
- private course questions, claims, policies, or state cards;
- raw tutor, simulator, or judge output; or
- secrets, provider credentials, or real user data.

Store private per-case artifacts under ignored `data/` and raw run output under
ignored `reports/generated/`. Commit only schemas, prompts, hashes, sanitized
aggregates, and redacted representative failures.

## Validation

```bash
uv run python scripts/validate_evaluation_instruments.py
```

Validation proves structural and cross-file consistency. It does not prove that
a judge is calibrated, a simulator is valid on final trajectories, or a tutor
passes evaluation.
