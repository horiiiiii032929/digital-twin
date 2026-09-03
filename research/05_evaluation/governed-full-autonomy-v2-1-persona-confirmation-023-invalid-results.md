# Persona confirmation 023 invalid result

## Result

Confirmation 023 is **invalid execution**, not a product-quality result.

- Five exact `gpt-5.6-luna` calls completed.
- Two public canary responses were durably persisted.
- Cost was USD 0.0006816 (1,770 input and 273 output tokens).
- No bulk case ran and hidden gold remained unopened.
- The run stopped because the instrument capped cost at USD 3 while the shared
  runner rounds its p99 projected stop upward to a minimum of USD 5.

This is an instrument/harness consistency defect. It says nothing about T0 or
T1-v2 quality. Authority is revoked. One harness-only successor may retain the
same cases, gold, prompts, models, methods, gates, and call ceiling while
raising only the emergency ceiling to USD 5. A second operational failure ends
the branch.
