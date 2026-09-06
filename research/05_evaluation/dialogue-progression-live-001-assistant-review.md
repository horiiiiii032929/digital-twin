# Dialogue progression pilot: independent assistant review

Run: `final-profile-operational-dialogue-development-001-progression-live-001`.
Review date: 2026-09-06. Reviewer: a separate coding assistant from the candidate implementer; **not an independent human or instructor reviewer**.
Rubric: [prospective progression rubric](dialogue-progression-assistant-review-rubric-v1.md).
Evidence: all 16 delivered tutor messages and all 16 generation proposals in the saved provider ledger; the additional eight calls selected reactive tutoring intent. Raw evidence remains under `reports/generated/final-profile-operational-dialogue-development-001-progression-live-001/`; hashes are preserved in the [run record](records/final-profile-operational-dialogue-development-001-progression-live-001.json).

## Decision

**Refine pedagogical quality.** The pilot demonstrates a finite progression in one incorrect-attempt history, actual profile-dependent initial responses, and continuation after restart. It does not establish consistently useful support, faithful instructor imitation, or learning benefit. A larger operating simulation can investigate persistence and delivery under an explicit operational-development scope; its size cannot remedy the quality failures below or turn these reused development cases into confirmation evidence.

Provider success was 24/24, with reported cost USD 0.0113548 and unchanged frozen files. Delivered actions were eight questions, six answers (including two hints), and two guarded failures. These denominators describe different events: transport success is not successful tutoring.

## History-level findings

| History | Observed behavior | Assessment |
| --- | --- | --- |
| Socratic, incorrect attempt | Initial elicitation; slot-attachment hint; explanation that an older update is rejected; new-topic elicitation after restart | Concrete progress beyond repeated elicitation. The hint is a prerequisite, not a targeted contrast or explicit correction of the misconception. No claim of complete profile fidelity. |
| Socratic, correct attempt | Initial elicitation; two source fragments restating the correct rule; guarded failure on application help; new-topic elicitation | A correct attempt can reach explanation, but no explicit acknowledgement or application reasoning is provided. The next request receives no substantive help. |
| Explanatory, correct attempt | Direct initial explanation; generic request for the explanation the learner just supplied; slot-attachment hint when asked to apply the older-update rule; direct new-topic explanation | Initial mode and topic reset are appropriate. Continuation regresses: the generic question ignores demonstrated work, and the subsequent hint repeats an already-known prerequisite instead of addressing the requested application. |
| Never-answer, incorrect attempt | Initial elicitation; generic question repeating the incorrect proposition; guarded failure on application help; new-topic elicitation | No complete solution is delivered. Safe withholding is preserved, but meaningful misconception guidance and usable recovery are absent. |

## Guard behavior and residual risk

Both guarded failures followed successful, schema-valid model proposals. In the Socratic-correct and never-answer histories, the model proposed the entire sole answer span—“rejects an update when its slot number is older than the stored number”—as a hint. The code rejected these proposals because the proposed hint covered every internally selected answer span. This is useful negative evidence: the new guard actually prevented delivery of a complete answer labelled as a hint.

It does not establish general partial-disclosure safety. Answer requirements are still proposed by the same model; an irrelevant additional requirement could prevent complete-span coverage while the hint reveals the whole answer to the actual question. Exact quotation establishes source membership, not adequacy, pedagogical usefulness, or the absence of answer leakage. The two delivered hints were partial with respect to the initial two-part rule, but neither establishes high-quality application support.

All four histories switch to a different concept after a restart; initial question/explanation modes are preserved in these four examples. This does not demonstrate general concept-episode tracking or a consistently enforced help ladder across arbitrary histories. No numeric semantic pass rate is assigned retrospectively.

## Next quality comparison

Keep this run immutable. Before promoting another candidate, use a fresh finite packet containing correct and incorrect application attempts, explicit non-attempts, requests for a contrast, a one-fact answer with no legitimate quoted partial hint, and a new concept after several earlier hints. Predeclare acceptance for substantive progress and appropriate recovery, not merely the presence of a `Hint:` prefix. Retain the current candidate as the comparison and preserve unfavorable outputs. Instructor review and permissioned representative course materials remain necessary for claims about the professor's style or actual-course quality.
