# Grounded generation and tutor-policy enforcement

Status: exact DeepSeek V4 Flash non-thinking binding and strict-evidence P2/v3
prompt selected in the experimental profile from completed synthetic
qualification; deterministic rollback retained.

## Current decision state

Issue #24 is reopened and `In Progress` because its C0-C3 development run is
invalid for selection. The preserved provider trace completed 192/192
attempts, while the
registered correction found missing human authoring review, gold-label leakage
in C2/C3, a drifted C3 chunking corpus, and missing condition/policy bindings.
C3 had 13/30 source/page citation correctness, 19/30 source/page evidence
coverage, and 0/30 exact selected-passage matches. Safe grounding, true
citation completeness, and pedagogy remain unresolved, so no professor-
fidelity claim or profile change is justified. The 104-case one-time held-out
ledger remains unopened. The generator sub-boundary remains complete: the
repository selects the exact
DeepSeek binding and P2 prompt after its own development, stability, one-time
held-out, and citation review gates passed. No API credential is stored. A
local Ollama Gemma 3 4B candidate was exercised historically with zero monetary
cost, but it is not currently installed or selected.

On 2026-07-16, the project fixed the DeepSeek API as a product constraint for
the primary generator rather than opening a broad LLM competition. On
2026-08-07, the prospective first candidate was frozen as official
`deepseek-v4-flash` through LiteLLM model
`deepseek/deepseek-v4-flash`, explicit non-thinking JSON mode, temperature 0,
600 output tokens, one attempt, and a 15-second timeout. Flash was chosen as the
bounded first candidate because the final system has a 10-second p95 target and
the current official API positions it as the faster, lower-cost V4 option. This
is a candidate freeze, not evidence that it works or that DeepSeek is best.
Issue #24's source-holder-authorized development exception permits eligible
IT5002 lecture passages and synthetic case fields under the cumulative USD 10
cap. Student data, judge inputs, simulator trajectories, and public deployment
remain prohibited.

The temporal provider facts were checked against DeepSeek's official
[models and pricing](https://api-docs.deepseek.com/quick_start/pricing/),
[thinking-mode](https://api-docs.deepseek.com/guides/thinking_mode), and
[JSON-output](https://api-docs.deepseek.com/guides/json_mode/) documentation on
2026-08-07. A later provider change requires a new binding and run identity.

The qualification instrument, 48-case development split, 104-case sealed
held-out split, hash manifest, review protocol, cost stops, and one-time
held-out ledger are executable. P0 and P1 failed citation correctness in
development. The refined strict-evidence P2 prompt passed all development
floors, then passed 36/36 attempts on the frozen 12-case, three-repeat stability
check. Routine CI verifies held-out only by hash and sealed metadata without
parsing its cases. The credential value is never emitted or accepted in
provider options.

The 25-case synthetic preflight establishes that the control path is safe enough
to compare with a live candidate. It is not evidence that the control produces
high-quality tutoring explanations, nor that any model is best.

The exploratory local run passed all structural checks and produced strict JSON
for 18 model-called cases. A post-run single-reviewer audit found only 15/18
answers fully supported by their cited evidence. Because that rubric was not
frozen before the run, the result is diagnostic and the decision is `Refine`.
See
[`generation-v1-gemma3-4b-results.md`](../research/05_evaluation/generation-v1-gemma3-4b-results.md).

## Runtime flow

```text
question + BM25 hits + approved TutorPolicy
  -> remove hits without tutoring permission
  -> deterministic policy decision
       |- policy not approved: stop
       |- empty question: stop
       |- no approved evidence: stop
       |- direct graded-work completion: redirect
       `- normal grounded question: continue
  -> frozen prompt condition
       |- P0 direct-grounded-prompt v1
       `- P1 conservative-grounded-prompt v2
  -> TutorGenerator implementation
       |- deterministic control
       `- LiteLLM-backed live candidate
  -> parse {answer, citation_ids}
  -> deterministic citation validation
  -> TutorAnswer + citations + warnings + usage trace
```

Stopping before generation matters. A model never receives an unapproved
policy, an empty request, a direct graded-work completion request, or a question
with no approved evidence. The provider cannot compensate for or override these
rules with fluent text.

## Policy algorithm

`DeterministicPolicyEnforcer` applies an inspectable rule order:

1. Reject an empty question.
2. Require `TutorPolicy.release_status == approved`.
3. Require at least one hit whose inherited `retrieval_allowed` flag is true.
4. Detect a direct-completion phrase together with a graded-context phrase.
5. Redirect matching graded-work requests to attempt-first help.
6. Allow other evidence-bearing questions to proceed.

The graded-work detector deliberately requires both kinds of phrase. This
reduces false refusals for conceptual questions that merely discuss assignments
or integrity policy. It remains a lexical v1 baseline: paraphrases and indirect
requests can evade it, so adversarial cases and a later classifier comparison
are required before selection.

## Prompt algorithm

`GroundedPromptBuilder` creates two messages. The system message defines the
evidence trust boundary and exact JSON output shape. The user message is a JSON
object containing the question, selected approved policy values, and evidence
records labeled `S1`, `S2`, and so on. Each evidence record retains source ID,
source version, locator, and text.

Course text is explicitly reference data, not executable instructions. The
prompt asks for:

```json
{"answer": "...", "citation_ids": ["S1"]}
```

The parser forbids extra top-level fields. This makes malformed output explicit,
but JSON structure alone does not prove factual grounding or pedagogical
quality; those require live-case scoring.

## Citation algorithm

The model cites only prompt-local IDs. `DeterministicCitationValidator` then:

1. rejects duplicate citation IDs;
2. requires at least one citation for a normal grounded answer;
3. rejects IDs not present in the retrieved evidence bindings;
4. rejects any binding whose chunk lacks tutoring permission; and
5. constructs the displayed source ID, title, and locator from the retrieved
   chunk rather than trusting provider-generated citation text.

This proves that a citation points to a retrieved approved hit. It does not yet
prove that every sentence is entailed by that hit; factual-support scoring is a
live evaluation metric and potential future validator.

## Provider adapter and failures

`services/llm/LiteLlmClient` uses the LiteLLM Python SDK's asynchronous
completion interface and normalized response format. The constructor requires a
model name but accepts no API-key argument; provider credentials remain in the
environment understood by LiteLLM. The adapter records input tokens, output
tokens, total tokens, model identity, and approximate cost when pricing is
available. See the [official LiteLLM documentation](https://docs.litellm.ai/).

Provider timeout, authentication, bad configuration, rate limit, connection,
service, generic API, empty-response, invalid-JSON, and invented-citation paths
all return a safe answer with a sanitized warning. Original provider exception
messages are never copied into `TutorAnswer`, because they may contain request
or credential details.

The live adapter remains inactive in the API architecture: no route or
application dependency constructs it. The experimental profile records the
qualified provider/model binding, but runtime activation is a separate,
evaluation-gated integration step. Tests inject a completion function and make
no network calls.

## Synthetic preflight

The versioned `generation-v1` set contains 25 cases: direct grounding,
misconceptions, integrity boundaries, ambiguous questions, and no-evidence
questions. `npm run verify:generation` rebuilds the approved synthetic corpus,
retrieves with selected BM25, and evaluates the deterministic control.
The clean-revision measurements are recorded in
[`generation-v1-preflight-results.md`](../research/05_evaluation/generation-v1-preflight-results.md).

The regression gate requires 1.00 for policy-action accuracy, citation validity,
graded-work redirection, no-evidence behavior, and required provider
suppression. It also requires zero provider tokens and no reported cost. Full
per-case output is local and ignored under `reports/generated/`.

## Remaining live decision

The authorized one-time 104-case P2 held-out run completed with 104/104 task,
claim, citation, policy, and completion checks passing. The full first review
and the frozen 20-case second review found no defect. The exact binding and P2
are now selected in the experimental profile with the deterministic rollback.
The second pass was delegated to Codex and is not independent human judgment.
Sufficient oracle evidence keeps qualification from being confounded by
retrieval misses.

The issue requires at least 40 development/calibration cases and 100 held-out
cases, three repeats on a stability subset, and double review of at least 30
percent of answer cases. Record per-case and cumulative cost, stop before the
approved USD 10 cap can be exceeded, and make no call with private course
material. The comparison scores claim support, citations, pedagogy,
misconception correction, policy behavior, latency, tokens, cost, footprint,
and diagnosed failures. Only a configuration that passes every prospective
hard gate may update the generator, prompt, policy-enforcement, or
citation-validation profile entries.

After qualification, freeze the selected DeepSeek and prompt configuration
while comparing full-document context, BM25, dense, hybrid, and justified
reranked RAG strategies. That later experiment answers the primary research
question without confusing model variation with retrieval variation.

All 13 inventoried IT5002 lecture PDFs remain outside this flow until explicit
professor approval grants tutoring permission. External-provider use requires a
separate approval even after local tutoring permission exists.
