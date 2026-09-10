# IT5004 presentation teaching001/002 results

## Identity and decision

2026-09-08. **Keep** IT5004 as the requested presentation source and retain the
candidate dialogue as a bounded illustrative example. No component promotion or
change to application defaults. Code revision
`9b16c15b8c1463b4f2ed1bbdbe2b25e65a436f5d`, dirty workspace, source checks unchanged.

Run001 failed before all provider calls because three researcher-authored
objectives had identical labels. It is retained as a fixture/configuration
failure, not a model failure. Run002 changed only those labels, keeping source,
questions, profiles and runtime configuration. Both plans and private packets
remain versioned and traceable.

## Data and method

Actual IT5004 Lecture5 PDF pages24,33,34 (printed slides25,34,35), approved by the
user for these examples. Two authored shopping-website questions, two synthetic
teaching profiles, two experimental configurations, eight delivered responses.
One topic is sufficient to illustrate a comprehensible interaction, not to
estimate general quality, robustness, instructor fidelity or learning outcomes.
No private student data, assignments or answers were used.

Existing persistent application-service runner, seed7801, one repeat,
concurrency4, output caps3000. V4 Luna-low control; V19 Luna-low generation with
Luna-medium audit/repair. No Sol. No planner calls occurred in this run.
The second turn restarts the persisted runtime. This is actual external-model
execution through the app's services, not a browser recording or mocked answer.

Qualitative dimensions were set in the original plan: source consistency,
first-turn teaching stage, relevant continuation, understandable terms,
unsupported details and withheld outputs. These observations are author review,
not independent calibrated model scores. No semantic pass percentage is given.

## Results

| Configuration and profile | Observed first response | Observed continuation |
| --- | --- | --- |
| Candidate, explanatory | Explains the separation of responsibilities and asks a check question | Describes the request/data-return flow and asks a check question |
| Candidate, Socratic | Asks the student to trace responsibilities before deciding | Confirms the supplied assignment of responsibilities and explains the flow |
| Control, both profiles | Validation failure | Validation failure |

All four histories completed by returning messages, but control messages were
all explicit safe failures. This distinction prevents successful execution from
being reported as useful tutoring. The exact control validation cause is not
fully diagnosed; no prompt or validation weakening was attempted.

Private verbatim output and lecture lineage:
`reports/generated/it5004-presentation-teaching-live-002/dialogue-ja.md`,
per-history `turns.jsonl`, and `data/interim/it5004-presentation-001/`.
The public-facing record retains sanitized observations and hashes, not copied
lecture passages or derived full responses. No sample or failed response excluded.

## Operational results

Run002 took37.01seconds. V4:4calls,5652input/1544output tokens,US$0.0029832.
V19:8calls,16018input/4294output tokens,US$0.0083564. Total12calls,
US$0.0113396, zero provider failures and zero unknown-cost calls. Model transport
success does not mean response validation success. Per-turn elapsed time is
retained in the machine record. Memory, capacity and24/7availability not measured.
Unused reservation released. Run001 costUS$0 with zero calls.

## Validity and follow-up

New exposed presentation-development data, no held-out claim or calibrated
independent review. Teaching settings are synthetic; source authorship does not
make them the professor's actual style. One topic cannot replace the previous
selection decision. Keep previous control failures and historical datasets under
their original identities. Web recording and replacement of the full slide deck
are still pending; this run supplies actual responses, not completed media.

[Original plan](../04_experiments/it5004-presentation-teaching-001.md) ·
[Correction and reproduction](../04_experiments/it5004-presentation-teaching-002.md) ·
[Run001 record](records/it5004-presentation-teaching-live-001.json) ·
[Run002 record](records/it5004-presentation-teaching-live-002.json).
