# Independent factual revision of instructional drafts

## Decision and alternatives

V11's instruction-only change does not solve the observed semantic problem:
both profile trials contain an unsupported universal detection guarantee, while
main dialogue reaches96/96 useful targets and sidecars8/8. Preserve its27/28
short result,10/12 on-style opportunities, two critical errors and all successful
cases. No further single-topic prompt patch or relaxed acceptance rule follows.

Compare unchanged V11 with V12: the same Luna-low instructional draft followed
by exactly one Sol-low revision in a separate request. The reviewer receives the
actual question, history, profile, approved chunks and draft proposal. It returns
the same typed instructional schema, not a quality score or an approval label.
Its purpose is to correct unsupported entity attribution, implication strength,
quantifiers, dependencies and invented guarantees while preserving supported
content, requested goals and the permitted teaching stage. No iterative repair
loop, secret gold facts or topic-specific replacement is allowed. A one-pass
correction can introduce errors; source IDs remain provenance, not entailment.
The earlier broad advisory judge was dropped and remains adverse evidence.

## Inspectable implementation

Keep V10 and V11, release defaults and the typed draft schema unchanged. Use a
distinct V12 implementation/prompt ID and explicit experimental configuration:
Luna-low planning, Luna-low draft generation and Sol-low factual revision, all
with3000-token caps. Record separate task identities, exact prompts, request and
response bodies, provider/model/reasoning, timings, usage and bounded ledgers.
The delivered trace identifies the final provider and explicitly distinguishes
combined usage from single-provider usage. Do not silently relabel Sol as Luna.
The current API, worker and evaluation composition must share this selection.

The final proposal passes the same structural, source-permission and policy
checks. Invalid draft/schema, unavailable revision or unknown usage fails closed;
never silently deliver an unchecked draft. Maintain conservative reservations
and stop admission on unknown usage. Per-role bounds must sum within the global
bound. Account for up to five actual model calls per tutoring turn where the
graph requests two generations plus planning; do not retain a three-call estimate.
Keep all failures and any unmodified/revised proposal observable. Per-request
state must remain isolated under concurrency and restart.

## Stage A: prospective revision controls

Before live evaluation, author64 versioned synthetic controls:32 already adequate
proposals and32 defective proposals across eight logical/pedagogical families.
Include attribution, one-way implication versus explicit equivalence, quantifier
strength and exceptions, unsupported dependencies/guarantees, concrete arithmetic
application, genuinely unresolved referents, missing requested evidence and
Socratic withholding. Include normal, boundary, adversarial and no-evidence
situations. The runtime sees public question/profile/history/source/draft only;
gold meanings and error labels remain outside the request. Independently check
all controls and mappings before dispatch. These are development controls, not
the sealed confirmation or population samples.

Acceptance: all32 adequate controls retain their required meaning and permitted
teaching move; at least30/32 defective proposals become adequate; zero critical
errors in any revised response; complete accounting and no identity/source drift.
Assess corrected answers semantically, not by string equality or the model's own
self-rating. Report failures and uncertainties, including unnecessary refusal,
omitted supported application and newly disclosed initial answers. Freeze exact
inputs and bounds before the first call. One full planned run, no output-selected
retries. A failure means Refine and investigation, not automatic stageB.

## Stage B: integrated developmental transfer

Only after stageA passes, evaluate the actual V12 runtime on the exposed28-case
entity/implication packet, two48-context main trials (schedule seeds8001/8002),
two24-condition profile trials, and the unchanged boundary/mixed sidecars.
Sampling remains stochastic. Keep all planned trials and review every delivered
turn, including preceding turns and provider fallbacks. V11 is a disclosed,
nonconcurrent development reference; calculate paired gains only for reviewable
matched outputs and report unavailable pairs rather than inventing wins.

Use the unchanged V11 advancement criteria:28/28 short, at least92/96 main with
39/48 and13/16 per-trial floors and12/12 explanatory moves per trial; all12 on-style
profile outputs and six qualified contrasts; both sidecars at least7/8 with
mixed-stage at least3/4 per stage; zero critical events in candidate histories;
complete planned candidate histories, known usage and unchanged identity/source.
Report tokens, actual and conservative cost, latency, local/provider failures,
coverage and revision-induced improvements/regressions. Extra cost or a valid
schema is not acceptance. Two repeated48-case packets are not96 independent
source families or students.

## Subsequent qualification

Only a candidate passing both stages may open the untouched fresh48-context
confirmation once under its existing protocol. On acceptance, use the already
permitted32-case course diagnostic and the same frozen configuration for actual
30-virtual-day operations, authenticated HTTPS and browser evaluation. A separate
experiment must justify any concurrency change; added revision latency cannot
be hidden behind earlier single-pass capacity results. Generated-response
professor approval remains a separate integration task, and no professor rating
may be fabricated. Maintain all unsuccessful records and update the concise
English LaTeX report with observed benefits, costs and limitations.

## Prospective execution envelopes

Stage A sends exactly one revision per control: 64 calls / USD 10.24, with the
existing conservative USD 0.16 reservation and no automatic retry. Stage B remains
conditional on Stage A's semantic gates. Its paired main trials use 1,200 calls /
USD 192 each, boundary 120 / USD 19.20 and mixed-stage 180 / USD 28.80. These envelopes
account for five calls per tutoring turn and fixed three-role partitions;
candidate generation and revision each receive enough calls for two passes per
turn if the existing graph requests its one repair. Profile runs use 150 calls /
USD 30 (50 per role), and the short diagnostic uses 200 / USD 32 (66 per role).

The optional subsequent HTTPS trial requires 1,200 calls / USD 192 for 180 POSTs;
400 calls per role cover up to 360 generation/revision calls and 180 planning
calls. Eight-history operations retain 4,800 calls / USD 768 per arm, with V12's
candidate arm split into three roles and its V4 control unchanged. All old V10
and V11 execution ceilings remain preserved. The same API/worker selector must
show the final Sol revision provider while retaining the Luna draft role in
observed metadata; combined usage is not attributed to only one provider.

## Pre-dispatch review clarifications

“Independent” describes a separate revision request/model role, not independent
factual ground truth: it still sees the same evidence and the preceding draft.
StageA reviews the actual server-rendered revised answer, including the fixed
clarify/private/graded wording, rather than scoring proposal text alone. Any
newly unsupported unit or prohibited disclosure counts even when the original
error was corrected. The64 controls comprise32 matched scenarios, each with an
adequate and defective draft, across eight families; they are not64 independent
source situations. Root independently read all64 public drafts, questions,
sources, histories/profiles and gold meanings before output and found the
intended32/32 labels coherent. This is assistant review, not professor approval.

Full draft/revision bodies are retained in the authorized local evaluation
ledgers. Never expose the unchecked draft through a student-facing trace or API:
it may contain precisely the answer or private fabrication removed by revision.
Public response metadata identifies the delivered provider, usage scope and
failure stage without including rejected prose. Internal evaluation observability
is not permission to publish student content or hidden drafts.
