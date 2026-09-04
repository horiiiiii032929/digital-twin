# Governed full-autonomy V2.1 multi-concept confirmation 025

## Decision

**Completed Keep for the multi-concept assessment correction.** The corrected
T1-v2 runtime passed every preregistered assessment and operational gate on 72
fresh synthetic learner histories. This result qualifies the correction for
local release requalification; it does not establish real learning or professor
fidelity.

## Run identity

| Field | Value |
| --- | --- |
| Instrument | `governed-full-autonomy-v2-1-multi-concept-confirmation-025` |
| Revision | `f4c244983c5b6482924e51e62b774d52f506423e` |
| Dirty at execution | No |
| Conditions | T1-v2 reactive; T1-v2 autonomous |
| Cases | 72: six personas × two simulator families × three fresh seeds × two conditions |
| Horizon | 30 virtual days per case; restart on day 15 |
| Concepts | Six fresh concepts with zero source/concept overlap with extension 014 |
| Network/provider | None; zero calls, tokens, and cost |
| Runtime | Actual `StudentTutoringService`, SQLite, LangGraph checkpoints, autonomy worker, outbox, delivery, and `VirtualUtcClock` through `StudentProductAutonomyAdapterV1` |

Extension 014 had found that one turn-level assessment was copied across three
weak concept matches, grading every hidden-correct attempt `partial`. The
successor records all attributed concepts but binds an assessment only to one
unambiguous primary concept. A tied attribution remains unassessed instead of
fabricating evidence.

## Preregistered gates

| Gate | Reactive | Autonomous | Threshold | Result |
| --- | ---: | ---: | ---: | --- |
| Concept attribution accuracy | 100% | 100% | ≥95% | Pass |
| Assessment agreement | 100% | 100% | ≥95% | Pass |
| Attempt recognition | 100% | 100% | 100% | Pass |
| Quiet-hour violations | 0 | 0 | 0 | Pass |
| Frequency violations | 0 | 0 | 0 | Pass |
| Cooldown violations | 0 | 0 | 0 | Pass |
| Provider calls | 0 | 0 | 0 | Pass |

## Diagnostics

Autonomous operation delivered a mean 9.69 messages per learner over 30 days.
Its simulated final hidden-mastery proxy was 0.365 versus 0.332 for reactive
T1-v2, a paired mean difference of +0.0324 (percentile-bootstrap 95% interval
+0.0040 to +0.0617). These are simulator outcomes, not measured learning.

The count-based belief estimate remains weak as a next-outcome predictor:
autonomous AUROC was 0.466 and its intervention wasted rate was 32.9%. Those
diagnostics do not fail this assessment-correction confirmation, but they remain
limitations and prohibit a real-learning claim.

## Evidence and limitations

- Full per-case truth, response, and score ledgers remain ignored under
  `reports/generated/governed-full-autonomy-v2-1-multi-concept-confirmation-025/`.
- Durable hashes are recorded in the machine-readable result.
- The wording is deterministic and synthetic. No private course, professor, or
  student data was used.
- The evaluator shares the product's public adapter and approved policy
  contract; this is a product regression, not independent pedagogical evidence.
- The result does not establish usability, professor fidelity, real learning,
  or broad factual grounding. The unfavorable known 10,000+1,000 result remains
  unchanged and was not read, rerun, or rescored.
