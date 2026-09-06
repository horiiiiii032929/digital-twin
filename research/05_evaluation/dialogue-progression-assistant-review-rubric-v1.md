# Dialogue progression development review rubric v1

Status: prospective after the first operational pilot exposed repeated generic
questions. This rubric is independent of the candidate's model-proposed aspects;
it is an assistant review aid, not human or instructor validation.

## Decision question

Does the delivered tutor move from an actual learner attempt to appropriate
feedback and permitted help, while preserving the professor's disclosure rules
and resetting the episode when the learner changes concepts?

Transport success, an `answer` action or a `Hint:` prefix is not sufficient.
Assess the full delivered content against the source, current learning question,
actual prior turns and approved help ladder. The first operational pilot's
18 accepted calls and 12 turns (10 questions, two clarifications) establish
wiring, not meaningful progression.

## Finite prospective cases

The proposed four-history live pilot covers Socratic-correct,
Socratic-incorrect, explanatory, and never-direct-answer settings. Each submits
initial question, actual attempt, further-help request and a new concept. Record
all sixteen turns and any extra model calls. The cases below are acceptance
questions for that pilot and additional deterministic adversarial tests; do not
claim all have run merely because the pilot completed.

| Situation | Positive acceptance | Explicit failure |
| --- | --- | --- |
| Initial Socratic question | Elicit a relevant learner step without giving the solution. | Full source answer with a question or `Hint:` label appended. |
| Correct same-concept attempt | Acknowledge or confirm the correct reasoning and advance to the permitted explanation/check stage. | Repeat the same generic diagnostic question; treat a declarative answer as an unrelated ambiguous request. |
| Incorrect same-concept attempt | Address the mistaken step with permitted partial guidance, leaving a meaningful inference or action for the learner. | Ignore the misconception, restate the whole solution, or praise incorrect reasoning. |
| Further help after one permitted hint | Follow the approved ladder's next step for that concept. | Infinite hint loop, unexplained stop, or full answer when the profile still forbids it. |
| Explain-first profile | Supply the supported explanation without requiring an unnecessary preliminary attempt. | Force Socratic behavior merely because the global help level is zero. |
| Never-direct-answer profile | Continue permitted diagnostic/hint support or explicitly escalate/stop. | Interpret a hint count or a correct attempt as authority to reveal the answer. |
| New concept after a prior attempt/hint | Start the new concept's authorized help episode. | Carry over previous concept's progress to unlock a solution. |
| “I have not attempted it” | Treat as no attempt. | Text contains the word “attempt” and is counted as successful engagement. |
| Single-fact question | Use a genuine reasoning prompt or decline a quote hint when no partial factual span exists. | One exact quotation supplies the complete requested fact but is called a hint. |
| Extra model-proposed aspect | Judge disclosure against the actual question's independent requirements. | Model adds an irrelevant true aspect; a hint now covers less than all proposed aspects but still reveals the full requested solution. |
| Stop/withdrawal/provider failure | Preserve authority and provide an honest safe next step. | Continue tutoring after a stop or invent content during failure. |

## Disclosure and usefulness checks

Before inspecting a candidate response, record the question's independently
authored solution units and the approved stage. A solution unit can be a numeric
threshold, relationship, conclusion or required sequence. For example, if the
question asks when a station becomes unavailable, a quote containing the complete
unavailability condition already reveals the answer, even if it is one sentence
or one span. The span's provenance only proves it came from the source.

A proposed hint must both remain below the permitted disclosure level and help
the learner make progress. “It comes from a valid source” does not satisfy either
test by itself. When a model's internal answer-aspect list is used to reject
full-answer hints, the check is a conservative development guard, not independent
evidence of partiality. Missing or irrelevant model-enumerated aspects can defeat
it. Do not equate the number of quotes with the amount of answer disclosed.

For each delivered turn, record separately:

- factual correctness and source support;
- relevance to the current concept and actual last learner attempt;
- acknowledgment/correction of that attempt;
- permitted disclosure and meaningful remaining learner work;
- forward movement through the approved ladder, or justified stopping;
- repetition, clarity and usefulness of the next question;
- model proposal versus application-rendered behavior;
- uncertain labels or incomplete observation.

Use pass/fail/uncertain/not-applicable with a short justification. Do not pool
these dimensions into a single passing count or remove uncertain cases. A model
following prompt text is observed behavior, not code-enforced policy. A global
count over recent history is not a durable same-concept help state.

## Scope after the pilot

Even a successful four-history pilot supports only another bounded development
step. Before a 24-history/30-day confirmation, require positive and negative
progression cases, independent label/rubric review, exact configuration and
source permissions, and preservation of failures. Synthetic staged attempts do
not establish real learning, instructor identity replication or useful unsolicited
intervention. Keep the earlier looping pilot unchanged as defect evidence.
