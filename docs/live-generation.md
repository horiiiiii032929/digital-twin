# Grounded generation and tutor-policy enforcement

## Current decision state

Issue #24 is in progress. The repository now has a deterministic grounded
generator control, direct grounded prompt candidate, deterministic policy
enforcer, deterministic citation validator, and a LiteLLM service adapter. No
live provider or prompt is selected, no API credential is stored, and no paid
call has been made. A local Ollama Gemma 3 4B candidate has been exercised with
zero monetary cost, but no generator or prompt is selected.

On 2026-07-16, the project fixed the DeepSeek API as a product constraint for
the primary generator rather than opening a broad LLM competition. This is not
evidence that DeepSeek is universally best. It remains pending until an exact
model identifier and configuration pass the prospective #24 qualification.
Only synthetic evaluation data is permitted, and the complete #24 external API
run has a cumulative USD 10 cap. Private course material remains prohibited.

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
  -> direct-grounded-prompt v1
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

The adapter is disabled by architecture rather than a Boolean switch: no API
route or application dependency constructs it, and no provider/model selection
exists in the system profile. Tests inject a completion function and make no
network calls.

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

To complete #24, freeze the exact DeepSeek model identifier and parameters,
quality rubric, thresholds, review protocol, and prompt variants before
inspecting held-out outputs. Use sufficient gold evidence for answer cases so
the generator qualification is not confounded by a retrieval miss. Compare
DeepSeek with the deterministic structural control and retain local Gemma as an
offline fallback; do not turn this issue into a broad model leaderboard.

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
