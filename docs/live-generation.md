# Grounded generation and tutor-policy enforcement

## Current decision state

Issue #24 is in progress. The repository now has a deterministic grounded
generator control, direct grounded prompt candidate, deterministic policy
enforcer, deterministic citation validator, and a LiteLLM service adapter. No
live provider or prompt is selected, no API credential is stored, and no paid
call has been made.

The 25-case synthetic preflight establishes that the control path is safe enough
to compare with a live candidate. It is not evidence that the control produces
high-quality tutoring explanations, nor that any model is best.

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

The regression gate requires 1.00 for policy-action accuracy, citation validity,
graded-work redirection, no-evidence behavior, and required provider
suppression. It also requires zero provider tokens and no reported cost. Full
per-case output is local and ignored under `reports/generated/`.

## Remaining live decision

To complete #24, freeze one provider/model and a spending cap, then run the same
cases through the live generator. The live comparison must additionally score
factual grounding, pedagogy, misconception correction, policy compliance,
citation validity, latency, token use, cost, and diagnosed failures. Only then
may generator, prompt, policy-enforcement, and citation-validation profile
entries become selected or receive standard component decision records.

IT5002 files remain outside this flow until an explicit professor approval
grants processing and tutoring permission.
