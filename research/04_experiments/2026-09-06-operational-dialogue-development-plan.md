# Operational dialogue development

Instrument: `final-profile-operational-dialogue-development-001`.

Question: does the explicitly configured candidate continue actual reactive and autonomous services across 30 virtual days, different synthetic response patterns, approved profiles, and restart, while preserving inspectable responses and bounded exchanges?

Matrix: six existing persona parameter sets × two newly bound teaching profiles × two modes (reactive/autonomous) = 24 histories per seed. Fresh seed 6209 and four new synthetic protocol cards; 30 virtual days; restart on day 15. Provider-backed execution is separate from network-free contract validation and follows the first independent content comparison. A run never changes the release profile automatically.

Content-responsive behavior: an actual `question` response triggers at most one synthetic learner attempt when the seeded learner is receptive. A delivered proactive message is read and attributed only when its text identifies exactly one configured concept. Each proactive message is responded to at most once; ambiguous attribution is recorded and receives no fabricated target. Assistant text, action, citations and persisted response records are retained for independent review.

Scripted behavior: daily attendance, receptivity and correct/incorrect attempt selection use preregistered persona probabilities and day-specific seeded streams. Attempts are synthetic source restatements or explicit misconception sentences. Correctness is not inferred from tutor text; there is no model of learning gain. Student text and elapsed time are simulated; tutoring generation, storage, permission checks, scheduled processing and restart use actual application services. Profile configuration and source installation are synthetic fixture setup, not a new ingestion/UI qualification.

Metrics: completed histories/days; actual provider task calls and identities; answer/question/abstention/failure counts; question-to-attempt exchanges; proactive deliveries/replies/unmapped concepts; restart continuity; raw per-turn content/citation evidence; explicit configuration/harness hashes. Content quality and intervention utility require separate review. No mastery, learning benefit, real-professor fidelity, usefulness or automatic Keep conclusion is emitted. Finishing 24 histories does not close intervention-utility or educational-effectiveness gaps.

Historical instrument audit: `src/digital_twin/evaluation/autonomy_learner_driver.py:142` records a reactive action without feeding tutor text or the question back to the learner. Lines 196 and 216 react to proactive action kinds and schedule questions independently. `src/digital_twin/evaluation/simulated_learner_v1.py:107` maps delivered action kind to an intervention; it does not inspect delivered content. `src/digital_twin/evaluation/learner_simulator.py:165` applies the simulated intervention/attempt mechanism without assessing tutor content. `src/digital_twin/evaluation/autonomy_product_adapter.py:668` does not explicitly recognize the new `question` action and several elicitation intents fall through to a hint classification. Therefore scaling the historical driver does not establish content-responsive tutoring. Historical 025 assessment, persistence and operational results retain their validity within their documented scope; this is not a retroactive invalidation of every result.

Before execution: contract tests must show a real question is followed by a bounded attempt, abstention is not treated as an explanation, all profile/persona/mode cells exist, restart retains conversation identity, and output is exclusive. Provider runs must use a recorded transport with finite call ceiling, save failures and raw content, and undergo independent quality review before any acceptance decision. Live execution is not part of this implementation task.

## Initial execution pilot

Before the 24-history operating test, run two matched fast-learner/Socratic histories (reactive and autonomous), seed 6209, three virtual days and restart on day one. Maximum two concurrent histories and 80 provider calls across the complete pilot, with the existing 30-second per-call timeout and zero automatic retries. The call ceiling bounds worst-case sequential provider waiting to 40 minutes (approximately 20 minutes with two fully parallel histories), plus local processing; ordinary completion should require substantially fewer calls. Cost is recorded; completion is not optimized for a minimal bill. The per-call reservation mechanism remains a defensive accounting bound. Preserve the entire pilot even if all calls fail or no proactive delivery occurs. Only proceed after the independent content development comparison is reviewed; the pilot itself is operational and cannot qualify teaching quality.

Reproducible commands: `uv run python -m scripts.run_operational_dialogue_development --pilot-contract --output-dir reports/generated/<fresh-contract-run-id>` for network-free contract exercise; replace with `--pilot-live` only for the explicitly authorized provider-backed pilot with the scoped guard and environment credential. Without either option, the module prints the prospective matrix manifest only. Output directories are exclusive.

### V2 finite progression pilot (after live operating pilot 001)

Four fresh runtime histories, at most four fixed user turns each: Socratic with
correct attempt, Socratic with incorrect attempt, explanatory with correct
attempt, and a never-direct-answer synthetic profile with incorrect attempt.
Each has an initial question, an explicit attempt, a further-help request, and a
new-concept question. The new-concept turn occurs after a real service restart.
The current candidate receives only actual persisted history, profile and
sources, not expected outcomes. Fixed prompts are synthetic stimuli; they do
not imply student understanding. Maximum 100 provider calls and $1 reservation,
30 seconds per call, concurrency two, no retry. Raw delivered turns, all model
requests/responses, exact identities, cost, hashes and failures are preserved.

Review correct/incorrect response progression, topic reset, repeated generic
elicitation, explanatory initial behavior and never-answer adherence. Existing
private/absent-detail regressions remain; this small pilot is not a new boundary
quality estimate. Baseline comparison is descriptive against preserved v1
pilot 001, not a matched randomized treatment-effect estimate. A hint which
covers every internally proposed answer span is rejected conservatively;
this is not a guarantee against semantic solution leakage. Independent content
review is required before the 24-history operating run.

Reproduce with a new output directory:

```bash
uv run python -m scripts.run_operational_dialogue_development --progression-contract --output-dir reports/generated/progression-contract-fresh
# With the authorized credential already loaded privately:
uv run python -m scripts.run_operational_dialogue_development --progression-live --output-dir reports/generated/progression-live-fresh
```

### Full 24-history operating coverage after v2 finite pilot

Keep v2 unpromoted and retain its weak continuation findings. Run all six seeded
personas × two approved synthetic profiles × reactive/autonomous conditions for
30 virtual days (720 history-days). Bound execution to 5,000 external calls,
$50 conservative reservations, six concurrent isolated histories, and 30 seconds
per call with no provider retry. The run is an operational development test,
not a quality confirmation, treatment effect, or learning experiment.

On day 10, disable each synthetic student's proactive consent through the
actual preference service; on day 20, re-enable it. The actual restart on day 15
therefore tests persistence while consent is disabled. Record both preference
changes, every delivered proactive message and its timestamp, model task/case
attribution, student/tutor actions, and failures. Check delivered message times
against the disabled interval rather than counting old messages rediscovered
after restart. Consent transitions are scripted operational stimuli, not
student preferences inferred by the model. No mastery or learning delta is
scored. Existing driver behavior permits at most one synthetic answer to an
actual reactive question; it does not qualify a complete hint ladder.

Record start/end source hashes, all per-case outputs and provider ledgers,
aggregate/slice task and action counts, latency/tokens/cost, restart identity,
consent violations, and failure taxonomy. Stop dispatch on recorded budget
failure or fatal infrastructure errors. A high call count cannot erase v2's
known weak pedagogical quality or establish intervention utility.

### Reactive Terra v2 model comparator

Before the full operating run, compare the same four fixed progression histories
using exact `gpt-5.6-terra` instead of `gpt-5.6-luna`, retaining v2 prompts,
approved profiles, source cards, actual persistence and topic-reset restart.
This changes reactive generation and semantic planning only. It is not a full
Terra autonomy architecture comparison; the selected release profile remains
unchanged. Prediction: Terra may improve continuation/partial-hint quality at
higher token cost. Review all sixteen delivered turns independently with the
same progression rubric, retain any guard/provider failures, and compare
latency/cost. The prior Luna run is a development comparator, not a statistical
quality confirmation or a matched provider random seed.

Nominal maximum is 100 calls with a $2 reservation cap. Terra's conservative
20,000-byte input ceiling plus framing and 500 output tokens costs less than
$0.06 per reserved call at the local catalog price; the $2 cap therefore limits
actual dispatch to at most 33 calls (expected 24). Exact serializer, pricing,
requested/returned identity and trace use the explicit model argument; mismatch
fails closed. No credentials are printed or committed.

```bash
uv run python -m scripts.run_operational_dialogue_development --progression-live --progression-model gpt-5.6-terra --output-dir reports/generated/progression-terra-fresh
uv run python -m scripts.run_operational_dialogue_development --full-live --output-dir reports/generated/operating-24x30-fresh
```
